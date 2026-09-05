# TRACE → ATF → AAuth Interface Contract

**Status:** Discussion draft, non-normative. Canonical copy lives in this repo.  
**Drafted:** August 14, 2026 (Imran, after the Josh / Dick / Imran session)  
**Last updated:** August 19, 2026  
**Executable form:** `demo/test-vectors.md`, `demo/fixtures/`, `demo/tools/`  
**Awaiting:** the decisions listed at the end. Josh owns the ATF block, Dick owns the AAuth block.

## Verifier statement

When every verification step succeeds, a relying party may state:

> At the stated appraisal time, the identified evaluator verified the referenced TRACE evidence under the named ATF profile, assigned the stated time-bounded trust level to the identified agent instance, and signed an appraisal result bound into the AAuth authorization presented for this resource request.

This does not establish that the agent is universally safe, CSA-certified, covered outside the declared session, physically located in a claimed geography, or authorized independently of resource-owner policy.

## Authority boundaries

| Component | Owns | Does not own |
|---|---|---|
| TRACE issuer/verifier | Runtime evidence, integrity, provenance, observation boundary | ATF scoring or resource authorization |
| ATF evaluator | Appraisal profile, level, reasons, validity period | Runtime enforcement or AAuth issuance |
| AAuth issuer / Person Server | Agent authorization, mission, resource binding, claim delivery | Independent truth of referenced evidence |
| Resource / AGT PEP | Final allow, deny, narrow, or require-approval decision | Rewriting evidence or appraisal |

## TRACE evidence input

ATF consumes a verified TRACE result, not an unverified JSON document.

Minimum normalized input:

| Field | Purpose |
|---|---|
| trace_profile | Exact TRACE profile identifier |
| record_id and record_hash | Stable identity and canonical digest |
| agent_id and session_id | Subject and observation boundary |
| issued_at and freshness result | Currency |
| runtime platform and measurement | Runtime assurance |
| policy.bundle_hash | Exact evaluated policy |
| model identity | Model and provenance status |
| tool_transcript.hash | Governed session activity |
| verification result | PASS/FAIL per required module and level |
| trust anchors | Roots and reference values used |

The evaluator must reject or return a non-qualifying result for an invalid signature, stale evidence, subject/session mismatch, unsupported profile, missing required module, or unresolved required digest.

## Proposed signed ATF appraisal result

    {
      "type": "atf-appraisal-result",
      "version": "0.1-draft",
      "appraisal_id": "urn:uuid:...",
      "issuer": "https://evaluator.example",
      "subject": {
        "agent_id": "aauth:agent@example",
        "session_id": "urn:uuid:..."
      },
      "profile": {
        "id": "csa-atf",
        "version": "<exact-version>",
        "policy_hash": "sha256:..."
      },
      "evidence": {
        "trace_profile": "tag:agentrust-io.com,2026:trace-v0.2",
        "record_id": "urn:uuid:...",
        "record_hash": "sha256:...",
        "verification_level": 1
      },
      "result": {
        "trust_level": "senior",
        "decision": "qualifying",
        "reason_codes": ["ATF-ID-OK", "ATF-POLICY-BOUND"],
        "limitations": []
      },
      "iat": 1786748400,
      "exp": 1786752000,
      "sequence": 42,
      "supersedes": null
    }

Required invariants:

- The issuer is authenticated and authorized by relying-party policy.
- Profile version and policy hash make the judgment reproducible.
- Record hash prevents evidence substitution.
- Agent and session binding prevent cross-agent or cross-session reuse.
- Issued-at, expiry, sequence, and supersedes support freshness and replacement.
- The statement is signed. Envelope and algorithm profile remain open.

## Proposed AAuth carriage

AAuth carries the appraisal result by reference or embeds a signed compact form. It does not reinterpret the ATF level.

    {
      "atf_appraisal": {
        "level": "senior",
        "profile": "csa-atf:<exact-version>",
        "issuer": "https://evaluator.example",
        "appraisal_id": "urn:uuid:...",
        "appraisal_hash": "sha256:...",
        "evidence_hash": "sha256:...",
        "iat": 1786748400,
        "exp": 1786752000,
        "sequence": 42
      }
    }

Open choices for Dick:

1. Embed the complete signed appraisal.
2. Carry minimum fields plus digest and resolvable URI.
3. Use selective disclosure when evidence is private.

Resource verification sequence:

1. Verify the AAuth proof-of-possession request.
2. Verify agent, resource, mission, and token expiry.
3. Verify the ATF appraisal signature and trusted issuer.
4. Match appraisal subject to the AAuth agent, and match that agent to the TRACE
   record subject. These are two different namespaces and the binding between
   them is currently undefined (see Dick's decisions).
5. Reject expired, revoked, superseded, or insufficient appraisals.
6. Apply resource-owner and AGT action policy.
7. Emit a signed decision event.

## Two-speed freshness model

### Baseline clock

- A session-level TRACE record establishes the baseline.
- ATF appraisal and AAuth claim have bounded lifetimes.
- Normal refresh creates a new record, appraisal, and token.

### Event clock

- Approved, denied, anomaly, policy-change, model-route, and budget events are signed.
- A severe event can immediately invalidate or supersede the baseline.
- The Person Server or PEP publishes a monotonic sequence.
- High-risk resources consume the stream or query status before acting.

Demotion invariant:

> A resource must not accept appraisal sequence n after learning of a valid superseding result or invalidation event with sequence greater than n.

This supports rapid demotion without requiring fresh hardware attestation and token issuance on every call.

## Final decision invariant

    eligible(request) =
        valid AAuth authorization
        AND current ATF appraisal
        AND level meets resource minimum
        AND mission allows request

    permit(request) =
        eligible(request)
        AND AGT/local policy allows
        AND budget allows
        AND model route allows
        AND runtime state allows

A qualifying level creates eligibility only. It never creates unconditional permission.

## Signed decision event

Minimum content:

- event ID and monotonic sequence;
- agent and session IDs;
- resource and action digest;
- appraisal ID and policy digest;
- decision and reason codes;
- dispatch state;
- issuance time and signature.

Dispatch state must distinguish: not evaluated, denied/not dispatched, dispatched, failed after dispatch, and unknown.

## Decisions required

### Josh / ATF

- Who may issue an appraisal?
- Which exact ATF version and level vocabulary apply?
- Is level computation deterministic from a machine-readable profile?
- Which TRACE evidence is mandatory at each level?
- How are downgrade and revocation represented?

### Dick / AAuth

- How does an AAuth agent identifier bind to a TRACE `subject`? The record
  carries a SPIFFE ID or DID; the appraisal names an AAuth agent. Nothing today
  says who asserts that these are the same principal, so the demo fixtures carry
  the mapping explicitly as `agent_binding` and the verifier checks it. That is a
  placeholder standing in for a real rule.
- Where does the claim live?
- Is the appraisal embedded, referenced, or selectively disclosed?
- How is the issuer trusted and discovered?
- How do sub-agents inherit or re-establish appraisal?
- What is fail-closed behavior when status is unavailable?
- How does the decision-event stream align with Shared Signals?

## Limits

- This is an integration proposal, not an adopted CSA or IETF specification.
- The fixtures in `demo/fixtures/` are really signed and really verified, but the
  runtime measurements, policy digests, and transcript hashes in them are fixture
  values, not captures from a live enclave.
- Claim names, envelopes, algorithms, and discovery are placeholders.
- Trust-level vocabulary must be checked against Josh's selected ATF version.
- Session aggregation cannot prove coverage of uninstrumented paths.
- A resource without invalidation events is bounded only by expiry.

