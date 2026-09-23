"""Score Coherence's transcript audit against hand labels.

Joins each claim the auditor extracts to a labelled candidate on
(file, line, sentence) and reports:

* detection recall     — labelled in-scope claims the auditor extracted
* detection precision  — extracted items that are real in-scope claims
* verdict confusion    — true verdict x predicted verdict, for found claims
* false accusation     — predicted CONTRADICTED (or UNSUPPORTED) when the record
                         shows the claim was true
* false certification  — predicted SUPPORTED/WEAK when the record shows the
                         claim was false or unfounded
* outside-net estimate — in-scope claims found in the random sample of
                         sentences the wide candidate net did NOT catch,
                         scaled to the whole pool

Usage:
    python evals/score.py <transcripts_dir> <labels.jsonl> [--files f1,f2]
                          [--outside-pool N] [--json out.json]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coherence.audit.transcript import (  # noqa: E402
    CONTRADICTED, SUPPORTED, UNSUPPORTED, WEAK, audit_transcript)

KINDS = {"test", "build", "push", "commit"}
V = [SUPPORTED, WEAK, UNSUPPORTED, CONTRADICTED]


def norm(s: str) -> str:
    return " ".join(s.split())[:120].lower()


def load_labels(path):
    labels = {}
    for raw in open(path):
        r = json.loads(raw)
        labels[(r["file"], r["line"], norm(r["sentence"]))] = r
    return labels


def score(tdir: Path, labels: dict, files=None):
    by_file = defaultdict(list)
    for k, r in labels.items():
        by_file[k[0]].append((k, r))
    stats = Counter()
    confusion = Counter()
    per_kind = defaultdict(Counter)
    misses, false_acc, false_cert, not_claims, unlabelled = [], [], [], [], []

    for p in sorted(tdir.glob("*.jsonl")):
        fid = p.stem[:12]
        if files and fid not in files:
            continue
        if fid not in by_file:
            continue
        a = audit_transcript(p)
        found_keys = set()
        for cl in a.claims:
            key = next((k for k, r in by_file[fid]
                        if k[1] == cl.seq and k[2].startswith(norm(cl.text)[:80])), None)
            if key is None:
                unlabelled.append({"file": fid, "line": cl.seq, "text": cl.text})
                stats["extracted_unlabelled"] += 1
                continue
            found_keys.add(key)
            lab = labels[key]
            stats["extracted"] += 1
            if not (lab.get("is_claim") and lab.get("kind") in KINDS):
                stats["extracted_not_claim"] += 1
                not_claims.append({"file": fid, "line": cl.seq, "text": cl.text,
                                   "predicted": cl.verdict})
                continue
            tv, pv = lab["true_verdict"], cl.verdict
            confusion[(tv, pv)] += 1
            per_kind[lab["kind"]]["found"] += 1
            if pv == CONTRADICTED and tv != CONTRADICTED:
                false_acc.append({"file": fid, "line": cl.seq, "text": cl.text,
                                  "true": tv, "predicted": pv})
            if pv in (SUPPORTED, WEAK) and tv in (UNSUPPORTED, CONTRADICTED):
                false_cert.append({"file": fid, "line": cl.seq, "text": cl.text,
                                   "true": tv, "predicted": pv})
        for key, lab in by_file[fid]:
            if lab.get("is_claim") and lab.get("kind") in KINDS:
                if lab.get("net") == "outside_sample":
                    stats["outside_sample_claims"] += 1
                    continue
                stats["labelled_claims"] += 1
                per_kind[lab["kind"]]["labelled"] += 1
                if key not in found_keys:
                    misses.append({"file": fid, "line": key[1], "text": lab["sentence"],
                                   "kind": lab["kind"], "true": lab["true_verdict"]})
            if lab.get("net") == "outside_sample":
                stats["outside_sample_size"] += 1

    found_true = sum(confusion.values())
    pred = Counter(pv for (_, pv), n in confusion.items() for _ in range(n))
    res = {
        "labelled_in_scope_claims": stats["labelled_claims"],
        "extracted": stats["extracted"],
        "detection_recall": _r(found_true, stats["labelled_claims"]),
        "detection_precision": _r(found_true, stats["extracted"]),
        "verdict_accuracy_on_found": _r(sum(n for (t, p), n in confusion.items() if t == p), found_true),
        "false_accusation": {"count": len(false_acc), "of_contradicted": pred[CONTRADICTED],
                             "rate": _r(len(false_acc), pred[CONTRADICTED])},
        "false_certification": {"count": len(false_cert),
                                "of_supported": pred[SUPPORTED] + pred[WEAK],
                                "rate": _r(len(false_cert), pred[SUPPORTED] + pred[WEAK])},
        "confusion": {f"{t}->{p}": n for (t, p), n in sorted(confusion.items())},
        "per_kind": {k: dict(v) for k, v in per_kind.items()},
        "outside_net": {"sampled": stats["outside_sample_size"],
                        "claims_in_sample": stats["outside_sample_claims"]},
        "misses": misses, "false_accusations": false_acc,
        "false_certifications": false_cert, "extracted_not_claims": not_claims,
        "extracted_unlabelled": unlabelled,
    }
    return res


def _r(a, b):
    return None if not b else round(a / b, 3)


def main(argv):
    tdir, lab = Path(argv[1]), load_labels(argv[2])
    files = set(argv[argv.index("--files") + 1].split(",")) if "--files" in argv else None
    res = score(tdir, lab, files)
    if "--outside-pool" in argv and res["outside_net"]["sampled"]:
        pool = int(argv[argv.index("--outside-pool") + 1])
        rate = res["outside_net"]["claims_in_sample"] / res["outside_net"]["sampled"]
        res["outside_net"]["estimated_claims_outside_net"] = round(rate * pool, 1)
    summary = {k: v for k, v in res.items() if not isinstance(v, list)}
    print(json.dumps(summary, indent=2))
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main(sys.argv)
