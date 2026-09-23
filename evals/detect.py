"""Claim-DETECTION scoring: did the auditor find the claims that are there?

Joins the auditor's extracted claims to Stage-A labels on (file, line,
sentence). Needs only Stage-A labels (is it a claim, which kind), so it runs
before any verdict labelling.

Usage:
    python evals/detect.py <transcripts_dir> <candidates_full.json> <stageA.jsonl>
                           <manifest.json> [--split dev|test] [--json out.json]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coherence.audit.transcript import audit_transcript  # noqa: E402

KINDS = {"test", "build", "push", "commit"}


def norm(s):
    return " ".join(s.split()).lower()


def run(tdir, cands, labels, manifest, split=None):
    files = {m["file"]: m for m in manifest if split in (None, m["split"])}
    by_file_line = {}
    for cid, c in cands.items():
        if c["file"] in files:
            by_file_line.setdefault((c["file"], c["line"]), []).append(cid)
    st = Counter()
    misses, fps, kind_mismatch, unmatched = [], [], [], []
    found_ids = set()
    for fid in files:
        path = next(tdir.glob(fid + "*.jsonl"))
        a = audit_transcript(path)
        for cl in a.claims:
            st["extracted"] += 1
            ids = by_file_line.get((fid, cl.seq), [])
            t = norm(cl.text)[:100]
            cid = next((i for i in ids if norm(cands[i]["sentence"]).startswith(t)
                        or t.startswith(norm(cands[i]["sentence"])[:100])), None)
            if cid is None:
                st["extracted_unmatched"] += 1
                unmatched.append({"file": fid, "line": cl.seq, "text": cl.text, "kind": cl.kind})
                continue
            lab = labels.get(cid, {})
            if lab.get("is_claim") and lab.get("kind") in KINDS:
                st["extracted_true_claim"] += 1
                found_ids.add(cid)
                if lab["kind"] != cl.kind:
                    kind_mismatch.append({"id": cid, "label": lab["kind"], "auditor": cl.kind})
            else:
                st["extracted_not_claim"] += 1
                fps.append({"id": cid, "text": cl.text, "auditor_kind": cl.kind,
                            "label_other": lab.get("other_checkable")})
    for cid, c in cands.items():
        if c["file"] not in files:
            continue
        lab = labels.get(cid, {})
        if not (lab.get("is_claim") and lab.get("kind") in KINDS):
            if c["net"] == "outside_sample":
                st["outside_sampled"] += 1
            continue
        if c["net"] == "outside_sample":
            st["outside_sampled"] += 1
            st["outside_claims"] += 1
            continue
        st["labelled_claims"] += 1
        st[f"labelled_{lab['kind']}"] += 1
        if cid in found_ids:
            st[f"found_{lab['kind']}"] += 1
        else:
            misses.append({"id": cid, "kind": lab["kind"], "text": c["sentence"][:200]})
    r = lambda a, b: None if not b else round(a / b, 3)
    summary = {
        "split": split or "all", "files": len(files),
        "labelled_in_scope_claims": st["labelled_claims"],
        "found": len(found_ids),
        "detection_recall": r(len(found_ids), st["labelled_claims"]),
        "extracted": st["extracted"],
        "detection_precision": r(st["extracted_true_claim"], st["extracted"]),
        "extracted_not_a_claim": st["extracted_not_claim"],
        "extracted_unmatched": st["extracted_unmatched"],
        "per_kind_recall": {k: r(st[f"found_{k}"], st[f"labelled_{k}"]) for k in sorted(KINDS)},
        "per_kind_labelled": {k: st[f"labelled_{k}"] for k in sorted(KINDS)},
        "outside_net_sample": {"sampled": st["outside_sampled"], "claims": st["outside_claims"]},
    }
    return summary, {"misses": misses, "false_positives": fps,
                     "kind_mismatch": kind_mismatch, "unmatched": unmatched}


def main(argv):
    tdir = Path(argv[1])
    cands = json.load(open(argv[2]))
    labels = {json.loads(l)["id"]: json.loads(l) for l in open(argv[3])}
    manifest = json.load(open(argv[4]))
    split = argv[argv.index("--split") + 1] if "--split" in argv else None
    summary, detail = run(tdir, cands, labels, manifest, split)
    print(json.dumps(summary, indent=2))
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps({"summary": summary, **detail}, indent=2))


if __name__ == "__main__":
    main(sys.argv)
