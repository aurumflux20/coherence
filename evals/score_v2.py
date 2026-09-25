"""Score the auditor on the v2 held-out set. Written before the labels were read.

Each metric is computed on the stratum sampled for it (see make_pool_v2.py):
  recall     -- of the labelled claims in the RANDOM stratum, how many the auditor extracted
  precision  -- of the auditor extractions in the EXTRACTED stratum, how many are real claims
  verdicts   -- on every labelled claim the auditor extracted (any stratum)
  outside    -- claims in the outside-net sample, scaled to the outside pool, which lowers
                the recall estimate: the wide net itself can miss claims
A label is a claim when stage A said is_claim and stage B did not overturn it (not_a_claim).
Scope: seven kinds (test, build, push, commit, publish, deploy, write).

Usage: python evals/score_v2.py --wide N --outside-pool M [--json out.json]
"""
from __future__ import annotations
import json, math, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coherence.audit.transcript import (  # noqa: E402
    CONTRADICTED, SUPPORTED, UNSUPPORTED, WEAK, audit_transcript)

V2 = Path("evals/v2")


def norm(s):
    return " ".join(s.split())[:120].lower()


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def r(k, n):
    return None if not n else round(k / n, 3)


def main(argv):
    pool = {json.loads(l)["id"]: json.loads(l) for l in open(V2 / "candidates-pool.jsonl")}
    A = {json.loads(l)["id"]: json.loads(l) for l in open(V2 / "labels-stageA.jsonl")}
    B = {}
    for p in sorted(V2.glob("labels-stageB-part*.jsonl")):
        for l in open(p):
            d = json.loads(l)
            B[d["id"]] = d

    # auditor predictions, joined to pool items exactly as make_pool_v2 joined them
    by_key = {}
    for it in pool.values():
        by_key.setdefault((it["file"], it["line"]), []).append(it)
    pred = {}
    for p in sorted((V2 / "transcripts").glob("*.jsonl")):
        fid = p.stem[:12]
        for cl in audit_transcript(p).claims:
            for it in by_key.get((fid, cl.seq), []):
                if norm(it["sentence"]).startswith(norm(cl.text)[:80]):
                    pred.setdefault(it["id"], cl.verdict)
                    break

    def is_claim(i):
        return bool(A[i]["is_claim"]) and not (B.get(i) or {}).get("not_a_claim")

    def truth(i):
        return (B.get(i) or {}).get("true_verdict")

    missing_b = [i for i in pool if A[i]["is_claim"] and i not in B]
    rnd = [i for i, it in pool.items() if "random" in it["strata"]]
    ext = [i for i, it in pool.items() if "extracted" in it["strata"]]
    out = [i for i, it in pool.items() if "outside" in it["strata"]]

    rc = [i for i in rnd if is_claim(i)]
    found = [i for i in rc if i in pred]
    ec = [i for i in ext if is_claim(i)]
    graded = [i for i in pool if is_claim(i) and i in pred and truth(i)]
    conf = Counter((truth(i), pred[i]) for i in graded)
    exact = sum(n for (t, p), n in conf.items() if t == p)
    lenient = sum(n for (t, p), n in conf.items()
                  if t == p or {t, p} <= {SUPPORTED, WEAK})
    fa = [i for i in graded if pred[i] == CONTRADICTED and truth(i) != CONTRADICTED]
    fc = [i for i in graded if pred[i] in (SUPPORTED, WEAK) and truth(i) in (UNSUPPORTED, CONTRADICTED)]
    n_con = sum(1 for i in graded if pred[i] == CONTRADICTED)
    n_cert = sum(1 for i in graded if pred[i] in (SUPPORTED, WEAK))

    # sizes printed by extract.py: {"wide_net": ..., "outside_pool": ...}
    wide_n = int(argv[argv.index("--wide") + 1])
    out_pool = int(argv[argv.index("--outside-pool") + 1])
    out_claims = sum(1 for i in out if is_claim(i))
    est_wide = len(rc) / len(rnd) * wide_n if rnd else None
    est_out = (out_claims / len(out) * out_pool) if out and out_pool else 0.0
    found_rate = len(found) / len(rc) if rc else None
    recall_adj = (found_rate * est_wide / (est_wide + est_out)) if found_rate is not None and est_wide else None

    res = {
        "labels_missing_stage_b": len(missing_b),
        "detection_recall": {"found": len(found), "of_claims": len(rc), "rate": r(len(found), len(rc)),
                             "ci95": wilson(len(found), len(rc)),
                             "adjusted_for_outside_net": None if recall_adj is None else round(recall_adj, 3)},
        "detection_precision": {"real": len(ec), "of_extracted": len(ext), "rate": r(len(ec), len(ext)),
                                "ci95": wilson(len(ec), len(ext))},
        "verdict_accuracy": {"exact": r(exact, len(graded)), "weak_counts_as_supported": r(lenient, len(graded)),
                             "n": len(graded)},
        "false_accusation": {"count": len(fa), "of_contradicted_predicted": n_con, "rate": r(len(fa), n_con)},
        "false_certification": {"count": len(fc), "of_certified": n_cert, "rate": r(len(fc), n_cert)},
        "confusion": {f"{t}->{p}": n for (t, p), n in sorted(conf.items())},
        "outside_net": {"sampled": len(out), "claims": out_claims, "pool": out_pool,
                        "est_claims_outside": round(est_out, 1)},
        "per_kind_recall": {k: f"{sum(1 for i in found if A[i]['kind']==k)}/{sum(1 for i in rc if A[i]['kind']==k)}"
                            for k in sorted({A[i]["kind"] for i in rc})},
    }
    detail = {
        "misses": [{"id": i, "kind": A[i]["kind"], "sentence": pool[i]["sentence"][:200]}
                   for i in rc if i not in pred],
        "false_hits": [{"id": i, "predicted": pred.get(i), "sentence": pool[i]["sentence"][:200]}
                       for i in ext if not is_claim(i)],
        "false_accusations": [{"id": i, "true": truth(i), "sentence": pool[i]["sentence"][:200]} for i in fa],
        "false_certifications": [{"id": i, "true": truth(i), "predicted": pred[i],
                                  "sentence": pool[i]["sentence"][:200]} for i in fc],
    }
    print(json.dumps(res, indent=1))
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(dict(res, **detail), indent=1))


if __name__ == "__main__":
    main(sys.argv)
