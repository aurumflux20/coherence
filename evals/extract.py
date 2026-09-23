"""Pull every labelling candidate out of a set of Claude Code transcripts.

A candidate is one assistant sentence, split exactly the way
``coherence.audit.transcript`` splits text, so a label and an audit verdict
can be joined on (file, line, sentence text).

The net here is deliberately WIDER than Coherence's own claim patterns. Recall
can only be measured against claims the auditor did not find, so the
candidate net must not be the auditor's net. Sentences outside even this
wide net are sampled separately (``--sample-outside``) so the net's own miss
rate can be estimated rather than assumed to be zero.

Each candidate carries the tool calls that happened before it (any tool, not
only Bash), so a labeller can judge the claim from the record without reading
the whole file.

Usage:
    python evals/extract.py <transcripts_dir> <out.jsonl> [--sample-outside N]
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from pathlib import Path

SPLIT = re.compile(r"(?<=[.!\n])\s+")      # same as the auditor
WIDE_NET = re.compile(
    r"\b(?:tests?|spec|suite|pytest|jest|vitest|cargo|unittest|pass(?:ed|es|ing)?|"
    r"green|build(?:s|ing)?|built|compil\w*|push(?:ed)?|commit(?:ted)?|merged?|"
    r"deploy(?:ed)?|shipped|released?|published|verified|confirmed|works|working|"
    r"succeed\w*|success\w*|done|fixed|lint\w*|typecheck\w*|ran|run)\b|✅|✓",
    re.I)
CONTEXT_CALLS = 12
RESULT_TAIL = 500


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(path: Path):
    """Yield ('call', line, id, name, input) / ('result', id, text, is_error)
    / ('text', line, text) in file order."""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line_no, raw in enumerate(f, 1):
            try:
                d = json.loads(raw)
            except Exception:
                continue
            content = (d.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if d.get("type") == "assistant":
                    if c.get("type") == "text" and c.get("text"):
                        yield ("text", line_no, c["text"])
                    elif c.get("type") == "tool_use":
                        yield ("call", line_no, c.get("id"), c.get("name"),
                               c.get("input") or {})
                elif c.get("type") == "tool_result":
                    body = c.get("content")
                    if isinstance(body, list):
                        body = "\n".join(b.get("text", "") for b in body
                                         if isinstance(b, dict))
                    yield ("result", c.get("tool_use_id"), str(body or ""),
                           c.get("is_error"))


def describe(inp: dict) -> str:
    for k in ("command", "cmd", "path", "file_path", "pattern", "query", "url"):
        if k in inp:
            return str(inp[k])[:300]
    return json.dumps(inp)[:300]


def candidates(path: Path, file_id: str):
    calls: list[dict] = []
    by_id: dict = {}
    inside, outside = [], []
    for ev in walk(path):
        if ev[0] == "call":
            _, line, tid, name, inp = ev
            rec = {"line": line, "tool": name, "input": describe(inp),
                   "is_error": None, "result_tail": None}
            calls.append(rec)
            by_id[tid] = rec
        elif ev[0] == "result":
            _, tid, body, is_err = ev
            if tid in by_id:
                by_id[tid]["is_error"] = is_err
                by_id[tid]["result_tail"] = body[-RESULT_TAIL:]
        else:
            _, line, text = ev
            for idx, sentence in enumerate(SPLIT.split(text)):
                s = sentence.strip()
                if len(s) < 4:
                    continue
                cand = {"file": file_id, "line": line, "idx": idx,
                        "sentence": s[:400],
                        "prior_calls": [dict(c) for c in calls[-CONTEXT_CALLS:]]}
                (inside if WIDE_NET.search(s) else outside).append(cand)
    return inside, outside


def main(argv):
    src, out = Path(argv[1]), Path(argv[2])
    n_out = int(argv[argv.index("--sample-outside") + 1]) if "--sample-outside" in argv else 0
    rng = random.Random(20260923)
    manifest, rows, outside_pool = [], [], []
    for p in sorted(src.glob("*.jsonl")):
        fid = p.stem[:12]
        manifest.append({"file": fid, "sha256": sha256(p), "bytes": p.stat().st_size})
        ins, outs = candidates(p, fid)
        rows += [dict(r, net="wide") for r in ins]
        outside_pool += outs
    rows += [dict(r, net="outside_sample")
             for r in rng.sample(outside_pool, min(n_out, len(outside_pool)))]
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(json.dumps({"files": len(manifest), "wide_net": sum(r["net"] == "wide" for r in rows),
                      "outside_pool": len(outside_pool),
                      "outside_sampled": sum(r["net"] == "outside_sample" for r in rows)}))
    Path(out).with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main(sys.argv)
