"""Rung 4 — Replay: are proven steps stable if re-checked?"""

from __future__ import annotations

from typing import Callable, Optional

from coherence.core.types import Artifact, Bundle, Record, Truth, digest, new_id


class Replayer:
    def __init__(self, bundle: Bundle) -> None:
        self.bundle = bundle

    def check(
        self,
        *,
        recompute: Optional[Callable[[Record], str]] = None,
    ) -> Record:
        """Compare stored proven fingerprints vs recompute (if provided).

        Without recompute: reports which steps are replay-ready (have artifacts).
        With recompute: marks drift when fingerprint changes.
        """
        steps = [r for r in self.bundle.by_rung(1) if r.truth == Truth.PROVEN]
        if not steps:
            rec = Record(
                id=new_id("rpl"),
                rung=4,
                kind="replay",
                truth=Truth.OPEN,
                summary="no PROVEN steps to replay",
                claimed="session claimed work",
                proven="",
                next_action="prove steps on rung 1 before replay",
            )
            return self.bundle.add(rec)

        stable = []
        drifted = []
        for s in steps:
            fp = s.artifacts[0].fingerprint() if s.artifacts else ""
            if recompute:
                new_fp = recompute(s)
                if new_fp == fp:
                    stable.append(s.id)
                else:
                    drifted.append(s.id)
            else:
                if fp:
                    stable.append(s.id)
                else:
                    drifted.append(s.id)

        if drifted and recompute:
            truth = Truth.BLOCKED
            nxt = "replay drift — do not trust green CI; re-run or fix nondeterminism"
            proven = f"stable={len(stable)} drifted={len(drifted)}"
        elif not stable:
            truth = Truth.CLAIMED
            nxt = "steps lack artifacts — not replayable"
            proven = "0 replayable"
        else:
            truth = Truth.PROVEN
            nxt = "replay surface OK — safe input for review radar"
            proven = f"stable={len(stable)} drifted={len(drifted)}"

        art = Artifact(
            kind="replay_report",
            value=digest({"stable": stable, "drifted": drifted}),
            meta={"stable": stable, "drifted": drifted},
        )
        rec = Record(
            id=new_id("rpl"),
            rung=4,
            kind="replay",
            truth=truth,
            summary="replay check",
            claimed=f"{len(steps)} proven steps",
            proven=proven,
            artifacts=[art],
            links=stable + drifted,
            next_action=nxt,
            meta={"stable_n": len(stable), "drifted_n": len(drifted)},
        )
        return self.bundle.add(rec)
