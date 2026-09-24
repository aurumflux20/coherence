"""Select, redact and manifest the v1 corpus.

Selection is stratified on purpose. 73 of 86 gradeable real sessions produce ZERO
claims from the 0.10.0 auditor. If the corpus were sampled only where the auditor
already fires, recall would be measured on the cases it already handles — which is
how an auditor certifies itself. So the corpus deliberately over-samples sessions
where the auditor is silent: those are where missed claims live.

Raw transcripts are NEVER written to the repo. Only redacted copies, plus a
SHA-256 manifest of the redacted bytes.
"""
from __future__ import annotations
import json, re, hashlib, pathlib, random, sys, os

OUT = pathlib.Path("evals/v1/transcripts"); OUT.mkdir(parents=True, exist_ok=True)
USER = os.environ.get("USER", "amanpreetkaur")

# ── redaction ────────────────────────────────────────────────────────────
SECRETS = [
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),                 "[REDACTED_API_KEY]"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),"[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),           "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                     "[REDACTED_AWS_KEY]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"),          "[REDACTED_SLACK_TOKEN]"),
    (re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{10,}"), "[REDACTED_STRIPE_KEY]"),
    (re.compile(r"\bpypi-[A-Za-z0-9_\-]{20,}"),               "[REDACTED_PYPI_TOKEN]"),
    (re.compile(r"\bATATT[A-Za-z0-9_\-=]{20,}"),              "[REDACTED_ATLASSIAN_TOKEN]"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}"),          "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"-----BEGIN[^-]{0,40}PRIVATE KEY-----.*?-----END[^-]{0,40}PRIVATE KEY-----", re.S),
                                                              "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|APIKEY|API_KEY)[A-Z0-9_]*)\s*[=:]\s*['\"]?[A-Za-z0-9._\-/+]{12,}['\"]?"),
                                                              r"\1=[REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "user@example.invalid"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),              "0.0.0.0"),
]
def strip_opaque(line: str) -> str:
    """Drop thinking blocks, their signatures, and embedded image data.

    The auditor reads ONLY assistant `text` blocks plus tool_use/tool_result, so
    none of this is input to a verdict. It is, however, opaque, large, and may
    carry private reasoning about third parties — so it has no business in a
    corpus we intend to publish alongside an accuracy claim.
    """
    import json as _j
    try:
        d = _j.loads(line)
    except Exception:
        return line
    msg = d.get("message") or {}
    content = msg.get("content")
    if isinstance(content, list):
        kept = []
        for c in content:
            if not isinstance(c, dict):
                kept.append(c); continue
            if c.get("type") in ("thinking", "redacted_thinking"):
                continue                      # removed wholesale
            c.pop("signature", None)
            if c.get("type") == "image":
                continue
            kept.append(c)
        msg["content"] = kept
    return _j.dumps(d, ensure_ascii=False)


def redact(text: str) -> str:
    for rx, sub in SECRETS:
        text = rx.sub(sub, text)
    # home paths leak the operator's identity and are the exact defect we found
    # sitting in a committed health-latest.json
    text = text.replace(f"/Users/{USER}", "/Users/USER").replace(USER, "USER")
    return text

VERIFY = [rx for rx, _ in SECRETS[:11]] + [re.compile(re.escape(USER))]

def main():
    rows = json.load(open("/tmp/survey.json"))
    withc   = sorted([r for r in rows if r["claims"] > 0], key=lambda r: -r["claims"])
    without = sorted([r for r in rows if r["claims"] == 0], key=lambda r: -r["texts"])
    random.Random(20260923).shuffle(without)

    picked  = withc[:8]                       # every session the auditor already fires on
    picked += [r for r in without if r["errors"] > 0][:8]   # silent + a real failure present
    picked += [r for r in without if r["errors"] == 0][:4]  # silent + clean run
    picked  = picked[:20]

    manifest, leaks = [], []
    for i, r in enumerate(picked):
        src = pathlib.Path(r["path"])
        raw = src.read_text(encoding="utf-8", errors="replace")
        red = redact("\n".join(strip_opaque(l) for l in raw.splitlines() if l.strip()))
        for rx in VERIFY:
            if rx.search(red):
                leaks.append((src.name, rx.pattern[:40]))
        name = f"t{i:02d}.jsonl"
        (OUT / name).write_text(red, encoding="utf-8")
        manifest.append(dict(
            id=name, sha256=hashlib.sha256(red.encode()).hexdigest(),
            bytes=len(red.encode()), lines=r["lines"], bash_calls=r["bash"],
            assistant_texts=r["texts"], failing_results=r["errors"],
            auditor_0_10_0=dict(claims=r["claims"], supported=r["sup"], weak=r["weak"],
                                unsupported=r["uns"], contradicted=r["con"],
                                not_asserted=r["not_asserted"]),
            split="dev" if i % 2 == 0 else "test",
            source_sha256=hashlib.sha256(raw.encode()).hexdigest()))
    json.dump(dict(
        created="2026-09-23", corpus="v1", n=len(manifest),
        note=("Redacted copies only. Raw sources are NOT in this repo and are not "
              "redistributable. source_sha256 lets the operator re-identify the origin "
              "locally without publishing it."),
        redaction=[p.pattern[:60] for p, _ in SECRETS],
        also_stripped=["thinking blocks", "thinking signatures", "embedded images"],
        files=manifest), open("evals/v1/manifest.json", "w"), indent=1)
    print(f"wrote {len(manifest)} redacted transcripts to {OUT}")
    print(f"dev={sum(1 for m in manifest if m['split']=='dev')} "
          f"test={sum(1 for m in manifest if m['split']=='test')}")
    print(f"auditor already fires on {sum(1 for m in manifest if m['auditor_0_10_0']['claims'])} of {len(manifest)}")
    print("REDACTION LEAKS:", leaks if leaks else "none")

if __name__ == "__main__":
    main()
