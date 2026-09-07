# Verifiable Agent Summit verification bundle

The public verification bundle for the CSA virtual briefing on September 9,
2026. It holds the signed artifacts, an independent verifier, and the captured
run, so you can check the chain without the systems that produced it.

## September 7 capture and fixture scope

The deployed resource capture is in `demo/provider/captures/september-7/`.
All five agreed cases matched, including an allow and the same token refused
after real expiry. The public signed record, evaluator appraisal, public keys,
artifact hashes and credential-free response captures are included.

The seven original vectors remain a separate local fixture exercise. Their
demotion and status-unavailable results do not describe the deployed resource.
The resource verifies provider and request signatures; it does not resolve the
evaluator appraisal or consume live status. Direct agent-token access has no
conforming live revocation path in the demonstrated flow.

The signed artifacts can be checked offline with the supplied keys. The
pre-issuance verifier uses the current clock and will now reject the expired
appraisal; `handoff-verification.json` records its successful live-window run.
No token or private signing key is included. HTTP token headers are redacted,
so these transcripts are evidence of the reported run, not replayable requests.

## The question

An agent asks to call a protected resource. It presents a signed authorization
that refers to an ATF appraisal, which in turn refers to a TRACE runtime
record. What can you verify before allowing the request?

## Verify it yourself

Requirements: Python 3.10 or later.

```text
pip install cryptography rfc8785
python demo/tools/verify_chain.py
```

Expected result:

```text
PASS  TV-01  allow/eligible_and_permitted
PASS  TV-02  deny/appraisal_stale
PASS  TV-03  deny/appraisal_superseded
PASS  TV-04  deny/evidence_hash_mismatch
PASS  TV-05  deny/subject_mismatch
PASS  TV-06  deny/model_route_denied
PASS  TV-07  deny/status_unavailable

7/7 cases matched their expected outcome.
```

The ten-minute version is `python demo/tools/verify_chain.py tv-01 tv-03 tv-04`.

`PASS` means the verifier reached the expected decision. It does not mean the
agent is safe or certified.

The verifier is not the issuing code. It re-derives every digest and checks
every signature against the public keys in `demo/fixtures/keys/`, so a run here
is evidence the chain holds outside the process that produced it.

## What is in here

| Path | What it is |
|---|---|
| `attendee/challenge.md` | The ten-minute challenge and what to look for |
| `demo/tools/verify_chain.py` | The independent verifier |
| `demo/fixtures/tv-01.json` to `tv-07.json` | The seven signed cases, one allow and six refusals |
| `demo/fixtures/keys/` | Public verification keys, TRACE issuer and ATF evaluator |
| `demo/transcript.txt` | The captured seven-case run |
| `demo/test-vectors.md` | Expected results and the threat case behind each one |
| `demo/resource-contract.md` | The deployed resource contract and its limits |
| `demo/report.html` | A rendered report of the local fixture exercise, for reading without Python |

## What the seven local fixture vectors establish

- A runtime evidence record can be verified separately from the system that
  produced it.
- A named appraisal profile can appraise that exact evidence object and issue a
  signed, time-bounded judgment.
- A changed agent cannot keep spending an earlier judgment merely because its
  token has not expired. TV-03 refuses an unexpired claim after a signed
  demotion.
- A judgment about one valid record cannot be replayed against a different
  valid record. TV-04 refuses on the evidence digest.

## What it does not establish

- The seven vectors are a deterministic local fixture exercise. Independent
  deployment behavior is recorded separately in the September 7 capture.
- The AAuth link in those vectors remains modeled JSON. Do not infer live
  status propagation or revocation from its signed demotion fixture.
- The ATF profile is drafted for this exercise from ATF v0.9.1 and is not
  CSA-ratified.
- The signatures are real. Runtime measurement, policy digest, transcript
  digest, and build provenance inside these records are declared fixture
  values, not live captures from a running system.
- None of this is CSA certification or endorsement, and a verified record
  reports evidence within its observation boundary rather than universal
  safety.

> TRACE is the evidence. ATF is the judgment. AAuth is the delivery. The
> relying party still decides.

## Tell us what broke

Answer the questions in `attendee/challenge.md` through the CSA survey. The
cases that survive scrutiny and the ones that do not both go into the October
30 workshop.

## Provenance

Built from `massivescale-ai/verifiable-agent-summit` at commit
`c48682a4bb279856f75a52d6ecc42fa405228365`, September 5, 2026. `SHA256SUMS`
lists every payload file, excluding itself. The September 7 refresh uses
working-repository commit `9be0de07ef64092b6c8baa6689eea50f26d445ef` for the approved resource
contract, labeled fallback, versioned captures and offline preflight. The original
seven signed fixtures are unchanged. Check them with `sha256sum -c SHA256SUMS`.

## License

Code is Apache 2.0, in `LICENSE`. Documents are CC BY 4.0, in `LICENSE-DOCS`.
