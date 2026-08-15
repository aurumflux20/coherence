# Contributing to Coherence

Thanks for helping. Read this before opening a PR.

## The law (do not break)

```text
Nothing is done unless there is evidence.
Nothing is finished unless there is a next.
Nothing is remembered unless it was done.
```

If your change does not create or enforce a **Fact** (`claim` / `evidence` / `next`), ask whether it belongs here. See [docs/320IQ.md](docs/320IQ.md).

## Ways to contribute

| Kind | Welcome? |
|------|----------|
| Bug fixes + tests | Yes |
| Docs / typos / examples | Yes |
| Rung deepenings that still emit Facts | Yes |
| Features that invent PROVEN without evidence | **No** |
| Secrets, live keys, product pitch for other AurumFlux apps | **No** |

## Dev setup

```bash
git clone https://github.com/aurumflux20/coherence.git
cd coherence
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m coherence law
python -m unittest discover -s tests -v
```

## PR checklist

- [ ] Tests pass: `python -m unittest discover -s tests -v`
- [ ] Demo still works: `python -m coherence demo`
- [ ] No empty `next` / no empty “proven” without evidence
- [ ] No secrets, tokens, or personal paths
- [ ] Docs updated if behavior changed
- [ ] One clear purpose per PR

## Code style

- Python 3.10+  
- Stdlib-first in core (no hard deps for the law)  
- Prefer clear names over cleverness  
- Fail closed with a **NEXT** in the error  

## Commit messages

Use short imperative subjects, e.g. `fix: require next on Fact.make`.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
