#!/usr/bin/env python3
"""Walk rungs 1–5 then knock one domino (needs proof + lesson)."""

from coherence import Coherence

c = Coherence(title="full-example", seed_cascade=True)

c.skills.audit("demo-skill", ["read"], source="local")
c.decisions.lock("style", "MUST keep public API stable", by="example")
proof = c.claimproof.cmd("tests", "pytest -q", exit_code=0)
c.replay.check()
triage = c.review.triage()

head = c.dominos.head()
if head:
    c.solve_domino(
        head.id,
        proof=str(proof.proven or proof.status),
        lesson="Always attach cmd exit as evidence before merge talk",
        proof_record_id=proof.id,
    )

print(c.plain_english())
print("triage:", triage.meta.get("priority"))
