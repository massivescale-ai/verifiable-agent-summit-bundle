# September 7 live interoperability capture

All five agreed cases matched against Dick's deployed resource using the summit
provider's token and Josh's actual signed appraisal from commit f1720bb.
`capture-manifest.json` records timing, software versions and artifact identity.
The observed resource repository HEAD is recorded separately; the deployment
commit was not independently attested.

| Case | Observed result |
|---|---|
| Fresh Senior token | 200; exact issuer, appraisal and evidence hashes checked |
| Same token after expiry plus tolerance | 401, expired_jwt |
| Grade raised to Principal, signature retained | 401, invalid_jwt |
| Valid token without ATF | 401, requirement=agent-token |
| Senior token at person-gated endpoint | 401, requirement=person-token |
| Expired token with edited payload (extra control) | 401, invalid_jwt |

The token was issued on the live clock at 19:24:18 UTC with an explicit 300-second
TTL, expiring at 19:29:18 UTC. The expiry call ran after expiry plus 120 seconds.
It is the same compact token as the allow case, confirmed before redaction and
identified by SHA-256 in the manifest. No time override was used. Josh's appraisal
expires at 19:59:27 UTC; the shorter token lifetime was chosen to capture expiry
within this session.

Before issuance, the offline Python preflight verified the TRACE and evaluator
signatures against explicit pinned keys, canonical profile and record digests,
subject compatibility, qualifying decision and freshness. Its JSON is captured
in `handoff-verification.json`. The provider CLI itself still checks signature
presence, so this separate operator step remains necessary.

The original record and a one-field subject tamper were independently checked
with Python cryptography over RFC 8785 bytes (`record-tamper.json`). No claim of
general equivalence with the Node serializer follows from these specific bytes.

The resource verifies the provider's token and agent's request signatures. It
does not fetch or verify Josh's appraisal. The full allow report says so and
labels identity binding `ap-asserted`. Runtime measurement, policy digest,
transcript and provenance remain declared fixture values. No status feed was
consumed; this direct flow demonstrates no live revocation or demotion.

Tokens are omitted from repository transcripts. Public signed evidence and keys
are included, along with the returned report. This permits examination of the
evidence and signatures; it does not make the redacted HTTP transcript a fully
replayable request. Private keys remain outside version control.

The historical fixture verifier and its status cases remain a separate exercise.
Do not label that local fixture behavior as an observed result from this endpoint.
