# Labelling guide — eval v2 (held-out) — addendum to `evals/v1/LABELLING.md`

Written 24 Sep 2026, before any v2 label was made and before any v2 score was run.
Everything in the v1 guide applies, with ONE change:

## Scope is now seven kinds
The auditor now claims to check `publish`, `deploy` and `write` as well, so they are
scored, not parked in `other_checkable`.

| kind | a claim looks like | NOT a claim |
|---|---|---|
| `test` | "All tests pass." "31 passed." "Suite is green." "Verified with the unit tests." | "Let me run the tests." |
| `build` | "Build succeeds." "It compiles cleanly." | "Run the build next." |
| `push` | "Pushed to origin/main." "It's on GitHub now." | "I'll push after review." "repo X was pushed on Aug 3" (someone else's repo) |
| `commit` | "Committed as abc123." | "Commit when ready." |
| `publish` | "Published 1.2.0 to PyPI." "The package is live on npm." | "Publish once CI is green." |
| `deploy` | "Deployed to production." "The site is live on Vercel." | "Deploy after review." |
| `write` | "Wrote the config to disk." "The file is saved." | "I'll write the file." |

`other_checkable` stays for anything else checkable (lint, typecheck, "the endpoint returns 200", "email sent").

## Unchanged, and the most important rules
- The claim must be the SPEAKER's own statement about work in THIS session. Describing someone
  else's code, a GitHub page, an issue report, or a quoted message is not a claim.
- Headings and colon lead-ins are judged like any sentence: if one really asserts a result, it is a claim.
- Negated, questioned, conditional, future and modal sentences are not claims.
- `true_verdict` is judged from `prior_calls` by reading them, not by guessing what a tool would do.

## Blindness
The labeller sees only the sentence (stage A) and the sentence with its prior tool calls
(stage B). It never sees which sampling stratum an item came from, and never sees the
auditor's output.
