# The Relying Resource Contract

**Status:** Discussion draft, non-normative. Canonical copy lives in this repo.
**Drafted:** September 6, 2026 (Dick, closing the AAuth side of `demo/interface-contract.md`)
**Revised:** September 7, 2026, twice. First after Imran ran the endpoint: two
403s withdrawn, a revocation endpoint added, and two statements this document
made about the code corrected. Then after AAuth §Token Revocation was revised
by spec PR #147, which settled issue #146 and, in naming what is revocable and
where, established that a resource under identity-based access has no
revocation path at all. D-06 is answered a third time and the four-party
question is opened.
**Live:** https://atf-demo.aauth.dev
**Implementation:** https://github.com/aauth-dev/atf-demo (public, Apache 2.0)
**Captured run:** `transcript.txt` in that repository, against the deployed resource

`interface-contract.md` left four questions to the AAuth side and said the
briefing must label the affected artifact a proposal until they closed. This
document answers three of them — D-04, D-05 and D-06 — in the only way that
settles anything, which is a resource that runs.

Everything here is the resource's own policy. None of it is AAuth, none of it
is ATF, and the one piece that touches the AAuth specification is filed as an
issue rather than assumed.

## What the resource does

An agent presents an AAuth agent token, signed by its agent provider, carrying
a `https://agentictrustframework.ai/atf` claim. The resource verifies the
provider's signature, reads the grade the provider vouches for, applies its own
policy, and then asks who the person is.

Two endpoints, one gate:

| | |
|---|---|
| `GET /agent/echo` | Agent identity access. On pass, `200` and a report of what was verified and who established it. |
| `GET /api/summarize` | The same gate, then `401 AAuth-Requirement: requirement=person-token`. |

The second endpoint is the point. A qualifying level is eligibility for
consideration, not permission, and the resource refuses a Senior agent for a
reason that has nothing to do with its grade.

## D-04 — Embed, reference, or selectively disclose

**The provider asserts the grade. The resource verifies the provider.**

No change to what Imran's provider issues today. The claim it already emits is
the contract:

```json
"https://agentictrustframework.ai/atf": {
  "profile":           "csa-atf:0.9.1",
  "level":             "senior",
  "exp":               1788634617,
  "sequence":          42,
  "appraisal_id":      "urn:uuid:f398589fc587869a9541b61c9ba19908",
  "appraisal_issuer":  "https://demo.verifiedagents.ai",
  "appraisal_hash":    "sha256:…",
  "evidence_hash":     "sha256:be134c87…",
  "appraisal_subject": "spiffe://example.org/agent/planner",
  "workload_id":       "spiffe://example.org/agent/planner",
  "binding_status":    "demo-proposal"
}
```

The resource acts on `profile`, `level`, `exp`, `sequence`, `appraisal_issuer`,
`appraisal_subject` and `workload_id`. It does not verify the evaluator's
signature, and it cannot: `appraisal_hash` is a digest of the complete signed
appraisal with no URI to resolve the document behind it.

That is a deliberate choice, not an oversight, and it has a cost. **The grade
reaches the resource on the agent provider's authority, exactly as `sub` and
`cnf` do.** A relying party that trusts a provider to say which agent this is
is being asked to trust it on what the agent earned as well. The `200` body
says so in its own words rather than leaving it to be inferred.

Two alternatives were considered and rejected for this demo:

- **Embed the signed appraisal** as a nested JWS in the claim. The resource
  then verifies both signatures and the stronger statement holds. It costs
  about 2 KB on every request and work on the provider side. Worth revisiting;
  a resource can require it by declaring `atf_appraisal_required`.
- **Reference it by URI** and fetch. Small token, but it puts the evaluator in
  the request path and creates a fail-closed question that is otherwise moot.

`appraisal_hash` and `evidence_hash` are kept. They are commitments: anyone who
obtains the appraisal or the TRACE record by any path can bind it to this
token. They are not checks this resource performs.

**Consequence for the briefing.** "The resource verifies each link itself, it
trusts no one's word for the one before" is not what happens and should not be
said. What happens is that the resource verifies the provider and the provider
verified the evaluator, with the evidence for that named and digested in the
token so anyone can check the provider's work.

## D-05 — Binding AAuth identity to the TRACE subject

**Checked for self-consistency, asserted by the provider, and labelled.**

The resource checks that the claim's `appraisal_subject` and `workload_id` do
not contradict each other. The provider signed one token carrying both, so a
disagreement means the provider contradicted itself. That is a `403`, and it is
checked *before* the policy checks: policy applied to an incoherent claim means
nothing.

**It does not compare either of them to `sub`.** An earlier version of this
document said it checked all three. It never did, and could not usefully: `sub`
is `aauth:planner@provider.example` and the other two are `spiffe://` URIs, and
which pairs of those name the same principal is exactly the question D-05
leaves open. The code was right and the prose overstated it.

So what this establishes is that the provider was internally consistent about
the TRACE subject. It does not establish that an `aauth:local@domain`
identifier and a `spiffe://` workload identifier name the same principal.
Nothing in AAuth or TRACE says who asserts that.

The `200` body reports both statements, attributed:

```json
"binding": {
  "asserted_by_agent_provider": "demo-proposal",
  "established_by_this_resource": "ap-asserted",
  "means": "…"
}
```

Two parties, two claims, neither replacing the other. The provider's own
`binding_status` travels verbatim — it grades its own binding and currently
calls it a proposal — beside what this resource actually did, which is take the
provider's word for it. An earlier version reported only the second, under the
bare name `binding_status`, which read as though it were the value in the
token.

D-05 stays open. This is what a resource can do while it is. See also the note
in Limits: check 8 may be stricter than the profile requires.

## D-06 — Status-unavailable behaviour

**The resource consults no status channel. Withdrawal is AAuth revocation.**

This closed the wrong way first, and the correction is worth recording rather
than quietly replacing.

The first answer was fail closed: `status_channel` and
`on_status_unreachable: "fail_closed"` published in this resource's metadata,
with an unreachable channel refused as `403 atf_status_unavailable`. Two things
were wrong with it.

**The check did not exist.** `atf_status_unavailable` fired on a Worker
environment variable, unset in production, so the channel was permanently
"reachable" and no request could ever fail the check. The metadata promised a
fail-closed policy the code never enforced, beside a URL —
`https://demo.verifiedagents.ai/status/atf` — that does not resolve, as
`demo/profile/README.md` says of that identifier. The same was true of
`atf_appraisal_superseded`, driven by a second environment variable. Both are
gone.

**The channel was never the resource's to publish.** The evaluator names it,
under signature, inside the appraisal:

```json
"status": {
  "channel": "https://demo.verifiedagents.ai/status/atf",
  "on_unreachable": "fail_closed"
}
```

A relying party republishing that in its own metadata asserts by hand, unsigned,
something the issuing party asserts with a signature. Two places to state one
fact is one place for it to be wrong, and this one was wrong.

### What replaced it

AAuth §Token Revocation, which already covers this case:

> Under identity-based access the agent presents its agent token to the resource
> directly, and the agent provider has no record of which resources those are; a
> resource accepting agent tokens SHOULD therefore provide a revocation
> endpoint, and where none is reached that access is bounded by the agent token
> lifetime alone.

The agent provider watches the evaluator's status feed. When a grade is
withdrawn, the provider calls `POST /revoke` here with the agent token's
`(iss, jti)`, and the token stops working on the next request.

Push rather than poll. No evaluator in the request path, no per-request fetch,
and no fail-open/fail-closed question at all, because there is nothing to fail
to reach. It also matches what the briefing already says: posture lives at the
agent provider, enforced by refusing tokens.

The cost is the one AAuth states: revocation reaches only the resources the
provider knows to call, and a resource no revocation reaches is bounded by
token lifetime. Polling a feed has no such gap. For agent tokens measured in
minutes, that is the right trade.

### The endpoint

```http
POST /revoke
Content-Type: application/json
Signature-Key: sig=jwks_uri;id="https://ps.example";dwk="aauth-person.json";kid="key-1"
Content-Digest: sha-256=:…:

{ "jti": "…", "exp": 1788794517 }
```

AAuth §Token Revocation was revised on September 7 by
[PR #147](https://github.com/dickhardt/AAuth/pull/147), which settled issue
#146 and went further. Three changes shape this endpoint:

- **`iss` is not a request parameter.** "The recipient takes it from the
  identity it verified on the signature and keys the revocation under that. A
  caller cannot name an issuer it cannot sign for, so revoking another issuer's
  token is not something a recipient refuses — it is unreachable." The earlier
  `403 not_token_issuer` compared a body member against the signer. There is no
  body member to compare now, and the property it was enforcing is structural.
- **`jti` and `exp` are both REQUIRED**, and `exp` bounds how long the recipient
  has to remember the revocation. That was the hole; there is no fallback TTL
  any more because there is no request without an `exp`. A recipient MAY reject
  an `exp` beyond the longest lifetime it accepts, which here is the 24 hours
  §Agent Tokens puts on an agent token.
- **`200 OK` with an empty body, always** — "whether or not it holds a record of
  the token", and no not-found response, because "a recipient cannot
  distinguish a token it never saw from one it saw and no longer holds, and an
  answer that varied with what it holds would disclose that." That was the
  second half of issue #146 and it is answered better than proposed.

Errors are the section's: `400 invalid_request`, `403 unsupported_iss`,
`500 server_error`. A signature that does not verify is `401` with
`Signature-Error`, since the caller's identity is established before the body
is examined.

### And the endpoint has no conforming caller

The same revision names what is revocable and where:

> An agent token is revoked only at a PS, by the agent provider that issued it.
> A resource that accepts an agent token directly under identity-based access
> has no revocation path: the agent provider holds no record of which resources
> an agent presents its token to, so it has nothing to call. That access is
> bounded by the agent token's lifetime alone, which is why an agent token
> SHOULD NOT live longer than 24 hours.

This resource serves identity-based access. The endpoint conforms and enforces
what it records — `transcript.txt` captures a token going `200`, being revoked,
and coming back `401 agent_token_revoked` — but the credential it is being
asked to revoke is one no conforming caller would bring here.

So D-06 is answered a third time, and this is the answer that holds: **under
identity-based access there is no status path and no revocation path.** The
grade is checked at issuance and the exposure is the agent token's lifetime,
which is why that lifetime is capped at 24 hours. Neither polling a status
channel nor accepting a revocation changes that.

### What would change it: the four-party flow

1. The agent gets a **person token** from the PS.
2. The agent gets a **resource token** from the resource.
3. The agent asks the PS for an **auth token**; the PS federates to an AS.
4. **The AS checks that the agent token carries what is required** and issues
   the auth token.
5. The agent calls the resource with the auth token.

Revocation then reaches the resource: the agent provider revokes the agent token
at the PS, the PS revokes the person token at the AS, and the AS revokes the
auth tokens it issued at each resource named in their `aud`.

This relocates the ATF gate. Under four-party access the party that decides
whether an agent's grade is good enough is the **AS**, at auth-token issuance —
which is where AAuth already puts policy about the agent, and it is checked once
per token rather than once per request. The resource then verifies an auth token
and reads what the AS granted.

That flow is not built. `atf-demo` is `access_mode: agent-token` and the gate in
`src/atf.ts` runs at the resource. Building it needs a PS and an AS that read
the ATF claim, and it changes what slides 8 and 12 describe. **Open decision.**

## Where the resource states its policy

`/.well-known/aauth-resource.json`, under the namespace ATF owns:

```json
{
  "issuer": "https://atf-demo.aauth.dev",
  "access_mode": "agent-token",
  "revocation_endpoint": "https://atf-demo.aauth.dev/revoke",

  "https://agentictrustframework.ai/policy": {
    "profiles": ["csa-atf:0.9.1"],
    "minimum_level": "senior",
    "evaluators": ["https://demo.verifiedagents.ai"]
  }
}
```

AAuth's document carries it; ATF defines what goes in it. There is no separate
policy document: a second place to state trust configuration is a second place
for it to be wrong.

The same rule is why there is no `status_channel` here. See D-06.

There is no `jwks_uri` and no signing key. Per AAuth §Resource Metadata,
`jwks_uri` is required only of a resource that issues resource tokens or makes
signed calls of its own. This one does neither, so it publishes no keys and
holds no secret — it verifies inbound signatures and answers.

## The gate

Check order is load-bearing, on the same principle as `test-vectors.md`:
subject binding before evidence policy, so the actionable failure is the one
reported.

These numbers are the ones in `src/atf.ts`. They used to disagree with the
code's own docblock by one; they no longer do.

| # | Check | On failure |
|---|-------|-----------|
| 1 | RFC 9421 signature, then `Signature-Key` scheme is `jwt` | 401 + `Signature-Error` |
| 2 | `typ` is `aa-agent+jwt` | 401 challenge |
| 3 | Token layer: structure, `cnf` binding, provider signature, then expiry | 401 + `Signature-Error` |
| 4 | `iss` is a trusted agent provider | 401 challenge |
| 5 | The ATF claim is present | 401 challenge |
| 6 | `profile` is one this resource reads | 401 challenge |
| 7 | `appraisal_issuer` is an evaluator this resource named | 401 challenge |
| 8 | `appraisal_subject` and `workload_id` agree | **403** `atf_subject_mismatch` |
| 9 | The appraisal has not lapsed | 401 challenge |
| 10 | `level` meets `minimum_level` | 401 challenge |
| 11 | The token has not been revoked | 401 `agent_token_revoked` |

Check 3 is ordered inside the token layer, and that order is load-bearing too.
Expiry is judged only after the provider's signature verifies, because before
that the payload is bytes the presenter chose: `expired_jwt` means the named
issuer minted this and its lifetime ran out, and reporting it from an
unauthenticated read lets any forgery produce it by carrying a past `exp`. A
caller reading that code refreshes a token when it should be refusing a
forgery. This was a real defect in two layers, found when a token that was
edited and expired at once reported `expired_jwt` here while the provider's own
verifier reported an invalid signature. Fixed in `@hellocoop/httpsig` 2.4.0 and
`@aauth/resource` 2.2.0.

Check 11 is last because it is the only check that reads storage. Everything
above it is a pure function of the token, so a token that fails one of them
never costs a lookup.

### 401 — registered codes, nothing invented

From the Signature Error Code registry in draft-hardt-httpbis-signature-key:
`invalid_request`, `invalid_input`, `unsupported_scheme`, `invalid_jwt`,
`expired_jwt`, `invalid_signature`.

Checks 1–7 and 9–10 are all conditions a better agent token repairs, so they
share one response: `401` with `AAuth-Requirement: requirement=agent-token`,
plus a `Link: …; rel="aauth-resource"` naming the metadata document that says
which profile and level are wanted.

Three body codes name what the header cannot:

| `error` | |
|---|---|
| `agent_token_required` | Nothing was presented |
| `agent_token_insufficient` | A valid agent token was presented; it does not carry what this resource requires |
| `agent_token_revoked` | The provider withdrew this token through `POST /revoke` |

The first says sign your request. The second says go get a different token. An
agent that cannot tell them apart loops.

`agent_token_revoked` carries no `Signature-Error`: the registry has no value
for a revoked token, and `expired_jwt` — the nearest — would be false. It is a
401 rather than a 403 because the signature verified and the claim was
coherent; what failed is that the credential is no longer good, which is the
same shape of condition as expiry and has the same remedy. A 403 would say
there is nothing to go and get, and whether that is true is the provider's to
report, not this resource's to guess.

### 403 — resource-defined, one of them

AAuth defines no error registry for resource endpoints, so this is the
resource's own:

| `error` | |
|---|---|
| `atf_subject_mismatch` | The claim contradicts the token carrying it |

There were three. `atf_status_unavailable` and `atf_appraisal_superseded` both
read a Worker environment variable rather than anything at runtime, so neither
could fire in production; both are gone, and D-06 explains what replaced them.
`atf_subject_mismatch` is the only one that can fire today, and does — see the
capture.

`POST /revoke` uses AAuth §Token Revocation's own error set rather than
inventing any: `400 invalid_request`, `403 unsupported_iss`, `500 server_error`.

A `403` denies after the signature verified — authentication succeeded,
authorization did not — so per AAuth §Verification it carries no
`Signature-Error`, no `Accept-Signature-*`, and no `AAuth-Requirement` either.
There is nothing the agent can go and get.

### Response bodies

Every error response, `401` and `403` alike, is `application/problem+json` with
an `error` member, per AAuth §Error Response Format. On a `401` the
`Signature-Error` header remains the machine-readable carrier, and the body's
`error` repeats that header's code rather than naming one of its own. A body
that disagrees with its own header reads as a defect in the resource.

## What the AAuth specification cannot yet say

The challenge is bare — `AAuth-Requirement: requirement=agent-token` and
nothing more. §Agent Token Required says the header carries no additional
parameters, on the premise that the agent already holds its token and need only
present it. That premise fails the moment a resource requires the token to
carry something a provider vouches for. ATF is the first case; it will not be
the last.

Filed as **https://github.com/dickhardt/AAuth/issues/145**, proposing one
framework-neutral parameter, `agent-claims`, a space-delimited String of claim
URIs. AAuth would learn that the agent token must carry claim X and nothing
about what X means.

Until then the requirement lives in the metadata document, which is why the
`aauth-resource` link relation rides on every challenge. Framework-specific
parameters (`atf-profile`, `atf-level`) are implemented behind a config switch
and not shipped: parameter keys cannot hold a URI, so every framework would
take a prefix out of one flat space.

## The four interop cases

| # | Request | Expected |
|---|---|---|
| 1 | Fresh Senior token | `200`, verification report |
| 2 | The same token past its expiry | `401` `Signature-Error: error=expired_jwt` |
| 3 | Payload edited, `level` raised to `principal` | `401` `Signature-Error: error=invalid_jwt` |
| 4 | A valid agent token carrying no ATF claim | `401` `AAuth-Requirement: requirement=agent-token` |

Then `GET /api/summarize` with the case 1 token: `401 requirement=person-token`.

And, since D-06 changed, a sixth: revoke the case 1 token at `POST /revoke` and
present it again — `401` `agent_token_revoked`. `harness/revoke.mjs` in the
atf-demo repository runs it, and it is captured in `transcript.txt` against the
deployed endpoint. It demonstrates the mechanism; per D-06 it is not a flow a
conforming agent provider would use against this resource.

Case 3 lands on the same refusal the provider's own verifier gives — signature
checked over the raw segments before anything is parsed out of them, the fix in
PR #1. Both sides agreeing on that is the interop result, not a coincidence.

Case 4 needs no appraisal and so no second signature from the evaluator. It
runs on a holiday.

Cases 2's timing is real and worth stating: both layers apply 60 seconds of
clock skew tolerance, so a token has to be **at least two minutes past its
expiry**, not five seconds. Run it early and it answers as a challenge instead.

### Running them

The agent side is fifteen lines. `@hellocoop/httpsig` does the signing; there
is no person server, no challenge loop, and nothing to obtain:

```js
import { fetch as sign } from '@hellocoop/httpsig'

const { response, sent } = await sign('https://atf-demo.aauth.dev/agent/echo', {
  signingKey: agentPrivateJwk,                    // from private/agent-key.pem
  signatureKey: { type: 'jwt', jwt: agentToken }, // out/agent-token.jwt
  returnSent: true,
})
```

`returnSent: true` hands back the exact request that went on the wire, which is
what makes a transcript evidence rather than description. `dryRun: true`
produces it without sending.

One conversion: `provider.mjs` writes `private/agent-key.pem` as PKCS#8 PEM and
`httpsig` wants a JWK — `crypto.createPrivateKey(pem).export({format:'jwk'})`,
then add `alg: 'Ed25519'`.

`client.mjs` in the atf-demo repository is that script with the four cases as
flags, and prints both sides.

## Limits

- This is one resource's policy, not a specification. AAuth defines no ATF
  vocabulary and takes no position on trust grades.
- The resource does not verify the ATF evaluator's signature. See D-04.
- The subject binding is `ap-asserted`. D-05 is open.
- `atf_subject_mismatch` is this resource's own name, registered nowhere, and
  should not be treated as ATF or AAuth vocabulary. So are
  `agent_token_required`, `agent_token_insufficient` and `agent_token_revoked`.
  `/revoke` uses AAuth's own error set.
- **Check 8 compares two fields Josh's schema allows to differ.** The provider
  fills `appraisal_subject` from `appraisal.subject.agent_id` and `workload_id`
  from `appraisal.subject.workload_id`. They are equal in the committed
  fixture, both `spiffe://example.org/agent/planner`, which is why the gate
  passes. Nothing in the profile requires them equal: `agent_id` names the
  agent and `workload_id` names the workload that produced the TRACE record,
  and D-05 is about making `agent_id` an AAuth identifier — at which point they
  differ legitimately and this resource returns a `403` saying the provider
  contradicted itself. **Josh to confirm whether the profile requires them
  equal.** Until he does, a regenerated appraisal can break the demo for a
  reason that is this resource's fault and reads as the provider's.
- **The revocation endpoint has no conforming caller.** It conforms to AAuth
  §Token Revocation and it enforces what it records, both captured live. But an
  agent token is revoked at the PS, not here, and an agent token is the only
  credential this resource accepts. Under identity-based access exposure is
  bounded by the agent token's lifetime and nothing else. See D-06.
- Nothing publishes ATF status events today either, so nothing has yet driven a
  withdrawal for a real demotion.
- A live capture proves the resource. It does not prove interoperability until
  the token was signed by a provider this project does not operate.
