# Issuer public keys

`aurumflux-attest.pub` — the AurumFlux AI, Inc. attestation key. A record signed under it means **we** ran the gate and signed the result; verify it with nothing but the record and this file:

```bash
pip install "coherence-check[attest]"   # 0.8.0 or newer; or straight from git:
# pip install "coherence-check[attest] @ git+https://github.com/aurumflux20/coherence"
coherence verify attestation.json --pub KEYS/aurumflux-attest.pub --session session.json
```

A worked example that anyone can reproduce is in `examples/attestation/` — a real proven fact about this repository, signed under this key. The private key is not in this repository and never will be.

The example is also anchored in Sigstore's public Rekor transparency log. To check the timestamp as well as the signature:

```bash
coherence verify examples/attestation/attestation.json --pub KEYS/aurumflux-attest.pub \
  --session examples/attestation/session.json --rekor examples/attestation/attestation.rekor.json
```

## Verify without cloning — one command

```bash
pip install "coherence-check[attest]" && coherence verify \
  https://raw.githubusercontent.com/aurumflux20/coherence/main/examples/attestation/attestation.json \
  --pub https://raw.githubusercontent.com/aurumflux20/coherence/main/KEYS/aurumflux-attest.pub \
  --session https://raw.githubusercontent.com/aurumflux20/coherence/main/examples/attestation/session.json \
  --rekor https://raw.githubusercontent.com/aurumflux20/coherence/main/examples/attestation/attestation.rekor.json
```

`verified` + `anchored` means: the signature is AurumFlux's, the session is the exact file that was signed, its chain recomputes, and the public log holds this record with a timestamp nobody controls.
