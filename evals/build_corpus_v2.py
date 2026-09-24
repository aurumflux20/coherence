"""Select, redact and manifest the v2 HELD-OUT corpus.

Why v2 exists: the v1 dev split was used to find and fix errors, and the v1
test split has been run twice. Neither can give an honest number any more.
v2 is built so that nobody -- not the person fixing the auditor, not the
labeller -- has seen these sessions or the auditor's output on them before
the single scoring run.

Selection is a seeded random sample, NOT stratified on the auditor's output:
choosing sessions by what the auditor does is how an auditor grades itself.
Excluded: every v1 source (by source_sha256), and any session that discusses
this eval (it would contain the answer key's sentences).

Output stays local: evals/v2/transcripts/ is gitignored.

Usage:  python3 evals/build_corpus_v2.py [N]
"""
from __future__ import annotations
import hashlib, json, pathlib, random, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_corpus import redact, strip_opaque, VERIFY, SECRETS  # noqa: E402

OUT = pathlib.Path("evals/v2/transcripts")
ROOT = pathlib.Path.home() / ".claude" / "projects"
CONTAMINATED = ("probe_known_holes", "LABELLING.md", "evals/v1", "score-dev-",
                "test_recall_v", "EXTRACTOR-SPEC")
SEED = 20260924


def _shape(raw: str):
    bash = texts = 0
    for line in raw.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        for c in (d.get("message") or {}).get("content") or []:
            if isinstance(c, dict):
                if c.get("type") == "tool_use" and c.get("name") == "Bash":
                    bash += 1
                elif c.get("type") == "text" and d.get("type") == "assistant":
                    texts += 1
    return bash, texts


def main(n=20):
    ignored = subprocess.run(["git", "check-ignore", "-q", str(OUT / "h00.jsonl")]).returncode == 0
    if not ignored:
        sys.exit("refusing: evals/v2/transcripts/ is not gitignored")
    v1 = json.load(open("evals/v1/manifest.json"))
    seen = {f["source_sha256"] for f in v1["files"]}
    pool = []
    for p in sorted(ROOT.glob("*/*.jsonl")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        if hashlib.sha256(raw.encode()).hexdigest() in seen:
            continue
        if any(k in raw for k in CONTAMINATED):
            continue
        bash, texts = _shape(raw)
        if bash >= 3 and texts >= 8:
            pool.append((p, raw, bash, texts))
    random.Random(SEED).shuffle(pool)
    picked = pool[:n]
    OUT.mkdir(parents=True, exist_ok=True)
    manifest, leaks = [], []
    for i, (src, raw, bash, texts) in enumerate(picked):
        red = redact("\n".join(strip_opaque(l) for l in raw.splitlines() if l.strip()))
        for rx in VERIFY:
            if rx.search(red):
                leaks.append((f"h{i:02d}", rx.pattern[:40]))
        name = f"h{i:02d}.jsonl"
        (OUT / name).write_text(red, encoding="utf-8")
        manifest.append(dict(id=name, sha256=hashlib.sha256(red.encode()).hexdigest(),
                             bytes=len(red.encode()), bash_calls=bash, assistant_texts=texts,
                             source_sha256=hashlib.sha256(raw.encode()).hexdigest()))
    json.dump(dict(created="2026-09-24", corpus="v2-heldout", n=len(manifest),
                   pool=len(pool), seed=SEED,
                   selection="seeded random sample; not stratified on auditor output",
                   excluded=["all v1 sources", "sessions mentioning: " + ", ".join(CONTAMINATED)],
                   note="Redacted copies only; raw sources are not in this repo.",
                   redaction=[p.pattern[:60] for p, _ in SECRETS],
                   files=manifest), open("evals/v2/manifest.json", "w"), indent=1)
    print(f"pool={len(pool)} picked={len(manifest)}  REDACTION LEAKS:", leaks or "none")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
