"""A deliberately broken x402 client: ONE logical purchase.

On any ambiguous failure it "retries the payment" by minting a FRESH
authorization nonce, so the facilitator sees a brand-new payment and settles
again. This is the specimen subject for the published conformance example --
it is meant to fail, so the example proves the instrument can go red.
"""
import json, os, urllib.request, urllib.error, uuid

URL = os.environ["FACILITATOR_URL"]


def settle(nonce):
    req = urllib.request.Request(
        f"{URL}/settle",
        data=json.dumps({"nonce": nonce}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.read()


def reconcile(nonce):
    with urllib.request.urlopen(f"{URL}/reconcile?nonce={nonce}", timeout=10) as r:
        return r.status, r.read()


for attempt in range(3):
    n = f"naive-{uuid.uuid4()}"          # <-- fresh identity every retry: the bug
    try:
        settle(n)
        break
    except urllib.error.HTTPError as e:
        if e.code == 504:                 # ambiguous: ask, then mis-read the answer
            try:
                status, body = reconcile(n)
                found = json.loads(body).get("found") is True
            except Exception:
                found = False             # <-- read failure collapsed into "absent"
            if found:
                break
        continue
    except Exception:
        continue
