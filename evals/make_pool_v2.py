"""Build the v2 labelling pool: three strata, shuffled together, verdicts hidden.

Why sampled: v2 yields ~9,200 wide-net candidates and ~490 auditor extractions --
too many to label by hand or by one model pass. Each metric gets its own
UNIFORM random sample, so each estimate is unbiased:

  random     -- N_RANDOM wide-net candidates        -> detection recall
  extracted  -- N_EXTRACTED auditor extractions     -> detection precision, verdicts
  outside    -- the extractor's outside-net sample  -> claims the wide net misses

A sentence can be in more than one stratum; its flags say which. The labeller
sees only id + sentence (stage A) and id + sentence + prior_calls (stage B),
never the stratum and never the auditor's verdict.

Scope, fixed BEFORE labelling: the seven kinds the auditor now claims to cover
(test, build, push, commit, publish, deploy, write).

Usage: python evals/make_pool_v2.py
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coherence.audit.transcript import audit_transcript  # noqa: E402

N_RANDOM, N_EXTRACTED, SEED = 300, 120, 20260924
V2 = Path("evals/v2")


def norm(s: str) -> str:
    return " ".join(s.split())[:120].lower()


def main():
    cands = [json.loads(l) for l in open(V2 / "candidates.jsonl")]
    rng = random.Random(SEED)
    wide = [c for c in cands if c.get("net") != "outside_sample"]
    outside = [c for c in cands if c.get("net") == "outside_sample"]
    by_key = {}
    for c in cands:
        by_key.setdefault((c["file"], c["line"]), []).append(c)

    extracted, unmatched = [], 0
    for p in sorted((V2 / "transcripts").glob("*.jsonl")):
        fid = p.stem[:12]
        for cl in audit_transcript(p).claims:
            hit = next((c for c in by_key.get((fid, cl.seq), [])
                        if norm(c["sentence"]).startswith(norm(cl.text)[:80])), None)
            if hit is None:
                unmatched += 1
            else:
                extracted.append(hit)

    pool = {}
    def add(c, flag):
        k = (c["file"], c["line"], c["idx"])
        item = pool.setdefault(k, dict(c, strata=[]))
        if flag not in item["strata"]:
            item["strata"].append(flag)
    for c in rng.sample(wide, min(N_RANDOM, len(wide))):
        add(c, "random")
    for c in rng.sample(extracted, min(N_EXTRACTED, len(extracted))):
        add(c, "extracted")
    for c in outside:
        add(c, "outside")

    items = list(pool.values())
    rng.shuffle(items)
    for i, it in enumerate(items):
        it["id"] = f"q{i:04d}"
    with open(V2 / "candidates-pool.jsonl", "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    with open(V2 / "candidates-stageA.jsonl", "w") as f:       # what the labeller sees
        for it in items:
            f.write(json.dumps({"id": it["id"], "sentence": it["sentence"]}) + "\n")
    print(json.dumps({"wide": len(wide), "outside": len(outside),
                      "extracted_total": len(extracted), "extracted_unmatched": unmatched,
                      "pool": len(items)}))


if __name__ == "__main__":
    main()
