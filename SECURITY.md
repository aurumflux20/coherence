# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` / latest 0.x | Yes |
| Older tags | Best effort |

## What Coherence is (threat model)

Coherence is a **local / library** tool for recording **claim vs evidence** and cascade order. It does **not**:

- Hold API keys or payment credentials  
- Execute untrusted agent skills for you  
- Replace OS sandboxing or code review  

A compromise of your machine or a malicious skill outside Coherence is out of scope for “Coherence failed.”

## Reporting a vulnerability

**Do not** open a public issue for security bugs.

1. Email **security@aurumflux.co**, or  
2. Use GitHub **Security → Report a vulnerability** on [aurumflux20/coherence](https://github.com/aurumflux20/coherence)

Include: description, impact, reproduction, and any suggested fix.

We aim to acknowledge within **72 hours** and provide a timeline after triage.

## Safe disclosure

Please give us reasonable time to patch before public write-ups. We will credit reporters who want credit.
