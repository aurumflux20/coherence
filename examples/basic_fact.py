#!/usr/bin/env python3
"""Minimal Fact usage — the whole product in ~10 lines."""

from coherence import Coherence

c = Coherence(title="example")

# NOT done — chat is a claim
c.said(
    "agent said tests passed",
    next="run pytest and attach exit code as evidence",
)

# DONE — has evidence
c.prove(
    "pytest -q",
    evidence="exit_code=0",
    next="chain complete",
)

print(c.plain_english())
print("open:", len(c.open_facts()), "done:", len(c.done_facts()))
