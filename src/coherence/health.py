"""Timely health of Coherence itself — detect, report, gate. Not magic self-heal.

What we automate:
  - law smoke
  - unit tests
  - storm proof
  - evolution chain integrity (if memory path present)

What we do NOT claim:
  - unsupervised auto-PR that always fixes every bug without a human
  - replacing code review

Optional: write a health report JSON for CI / dashboards.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    seconds: float = 0.0


@dataclass
class HealthReport:
    ok: bool
    checked_at: float
    checks: list[CheckResult] = field(default_factory=list)
    next_action: str = ""
    version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checked_at": self.checked_at,
            "version": self.version,
            "next_action": self.next_action,
            "checks": [asdict(c) for c in self.checks],
        }


def _run(cmd: list[str], cwd: Path, timeout: int = 300) -> CheckResult:
    name = " ".join(cmd[-3:]) if len(cmd) > 3 else " ".join(cmd)
    t0 = time.time()
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        sec = time.time() - t0
        ok = p.returncode == 0
        tail = ((p.stdout or "") + (p.stderr or ""))[-500:].strip()
        return CheckResult(
            name=name,
            ok=ok,
            detail=tail or f"exit {p.returncode}",
            seconds=sec,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(name=name, ok=False, detail="timeout", seconds=time.time() - t0)
    except Exception as e:
        return CheckResult(name=name, ok=False, detail=str(e), seconds=time.time() - t0)


def find_repo_root(start: Optional[Path] = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for cand in [p, *p.parents]:
        if (cand / "storm.py").exists() and (cand / "src" / "coherence").exists():
            return cand
        if (cand / "pyproject.toml").exists() and "coherence" in (cand / "pyproject.toml").read_text(
            encoding="utf-8", errors="ignore"
        ):
            return cand
    return p


def run_health(
    *,
    root: Optional[Path] = None,
    include_storm: bool = True,
    memory_path: Optional[Path] = None,
) -> HealthReport:
    root = find_repo_root(root)
    py = sys.executable
    checks: list[CheckResult] = []

    try:
        from coherence import __version__
    except Exception:
        __version__ = "unknown"

    # 1 law
    checks.append(_run([py, "-m", "coherence", "law"], root, timeout=30))

    # 2 unit tests (explicit modules — avoid hanging / recursion traps)
    checks.append(
        _run(
            [
                py,
                "-m",
                "unittest",
                "tests.test_fact",
                "tests.test_coherence",
                "tests.test_evolve",
                "tests.test_ci_session",
                "tests.test_health",
                "-q",
            ],
            root,
            timeout=180,
        )
    )

    # 3 storm
    if include_storm:
        storm = root / "storm.py"
        if storm.exists():
            checks.append(_run([py, str(storm)], root, timeout=180))
        else:
            checks.append(
                CheckResult("storm.py", False, "storm.py missing from checkout")
            )

    # 4 evolution chain if memory exists
    if memory_path and Path(memory_path).exists():
        t0 = time.time()
        try:
            from coherence import Coherence

            c = Coherence(title="health", memory_path=memory_path)
            ok = c.evolve.verify_chain()
            checks.append(
                CheckResult(
                    "evolution_chain",
                    ok,
                    f"lessons={len(c.evolve.lessons)} chain_ok={ok}",
                    time.time() - t0,
                )
            )
        except Exception as e:
            checks.append(
                CheckResult("evolution_chain", False, str(e), time.time() - t0)
            )

    all_ok = all(c.ok for c in checks)
    if all_ok:
        nxt = "health green — ship depth only with storm still green"
    else:
        failed = [c.name for c in checks if not c.ok]
        nxt = f"fix failing checks: {', '.join(failed)} — re-run storm before merge"

    return HealthReport(
        ok=all_ok,
        checked_at=time.time(),
        checks=checks,
        next_action=nxt,
        version=str(__version__),
    )


def write_report(report: HealthReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")


def plain_english(report: HealthReport) -> str:
    lines = [
        "COHERENCE HEALTH",
        f"  version: {report.version}",
        f"  overall: {'GREEN' if report.ok else 'RED'}",
        f"  NEXT: {report.next_action}",
        "",
    ]
    for c in report.checks:
        mark = "PASS" if c.ok else "FAIL"
        lines.append(f"  [{mark}] {c.name} ({c.seconds:.2f}s)")
        if not c.ok and c.detail:
            lines.append(f"         {c.detail[:200]}")
    return "\n".join(lines)
