# Verifiable Agent Summit — Demo Test Vectors

**Status:** All seven vectors have signed fixtures and pass an independent verifier run.  
**Drafted:** August 14, 2026  
**Last updated:** August 19, 2026  
**Oracle:** `demo/interface-contract.md`  
**Fixtures:** `demo/fixtures/tv-0*.json`  
**Run:** `python demo/tools/verify_chain.py`

## Common fixture

- Agent: aauth:planner@example
- Session: urn:uuid:11111111-1111-1111-1111-111111111111
- Resource: https://inference.example/v1/chat
- Mission: summarize approved CUI documents
- Allowed model: model://approved/summarizer-v3
- Budget: USD 5.00
- Minimum resource level: Senior
- ATF profile: exact version and policy hash to be supplied by Josh
- TRACE profile: tag:agentrust-io.com,2026:trace-v0.2

## TV-01 — Fresh qualifying evidence permits an in-scope request

Given a valid, fresh TRACE record whose agent/session match the AAuth request; a signed Senior ATF appraisal; a proof-of-possession AAuth authorization; and mission, model, budget, and AGT policy that permit the action:

- AAuth verification: PASS.
- ATF appraisal verification: PASS.
- Resource eligibility: PASS.
- AGT decision: ALLOW.
- Dispatch state: DISPATCHED.
- A signed event references appraisal ID, policy hash, session, and action hash.

Contradicting evidence: any invalid signature, mismatched subject/session, stale appraisal, insufficient level, denied policy, or non-dispatched result invalidates this PASS outcome.

## TV-02 — Stale evidence fails closed

Change only the appraisal expiry so it precedes request time:

- Appraisal verification: FAIL_STALE.
- Eligibility: FAIL.
- Decision: DENY.
- Dispatch: DENIED_NOT_DISPATCHED.
- The expired Senior level must not be reused silently.

## TV-03 — Demotion supersedes an unexpired token

Given appraisal sequence 42 at Senior, a signed prohibited-route event, and sequence 43 demoting the agent:

- The old AAuth token may remain cryptographically valid.
- Currency check: FAIL_SUPERSEDED.
- Eligibility: FAIL.
- Dispatch: DENIED_NOT_DISPATCHED.

Distinct defect detected: a verifier that checks expiry but ignores sequence/status would incorrectly allow the request.

## TV-04 — Evidence substitution is rejected

Given a Senior appraisal bound to TRACE hash A, present TRACE record B through the same URI:

- Evidence binding: FAIL_HASH_MISMATCH.
- Trust level is not accepted.
- Dispatch: DENIED_NOT_DISPATCHED.

## TV-05 — Agent identity mismatch is rejected

Given an appraisal for planner@example and a proof-of-possession request from worker@example:

- Subject binding: FAIL_SUBJECT_MISMATCH.
- Parent level is not copied implicitly to a sub-agent.
- Delegation or a new appraisal must be established.
- Dispatch: DENIED_NOT_DISPATCHED.

## TV-06 — Senior does not override local policy

Given valid Senior evidence and authorization but a forbidden model route or exceeded budget:

- Level eligibility: PASS.
- Final resource/AGT decision: DENY.
- Dispatch: DENIED_NOT_DISPATCHED.
- Reason identifies local policy, route, mission, or budget.

Distinct defect detected: treating Senior as unconditional authorization would incorrectly dispatch.

## TV-07 — Status channel unavailable

Given a valid token, but the high-risk resource requires current status and cannot reach the event/status channel:

- Result: DENY or REQUIRE_HITL according to explicit policy.
- Unavailable status must not be treated as current.
- Dispatch waits for the configured fallback.

## Summit demonstration subset

Use:

1. TV-01 for the successful chain.
2. TV-03 for dynamic demotion before token expiry.

Use TV-02 as the simpler fallback if the signed event stream is not ready.

## Reason codes the verifier emits

| Vector | Decision | Reason code |
|---|---|---|
| TV-01 | allow | `eligible_and_permitted` |
| TV-02 | deny | `appraisal_stale` |
| TV-03 | deny | `appraisal_superseded` |
| TV-04 | deny | `evidence_hash_mismatch` |
| TV-05 | deny | `subject_mismatch` |
| TV-06 | deny | `model_route_denied` |
| TV-07 | deny | `status_unavailable` |

Check order is load-bearing. Subject binding is checked before evidence binding,
so a sub-agent presenting its parent's appraisal is reported as an identity
failure rather than a hash mismatch. The first is actionable, the second is
misleading.

## Evidence required before claiming a working integration

- Exact fixtures and public verification keys.
- Trust-policy configuration.
- CLI or HTTP transcripts for every verification step.
- Signed outputs and decision events.
- Exit codes or HTTP status codes.
- Proof that denied cases produced no downstream request.
- An independent verifier run outside the issuing environment.

**Status against that bar, August 19, 2026.** Met: exact fixtures, public
verification keys, trust-policy configuration in each case file, a full CLI
transcript per step, decision events, exit codes, and proof that every denied
case produced `denied_not_dispatched`. Not met: the verifier and the issuer were
run by the same party on the same machine, and no ATF evaluator or AAuth issuer
other than these fixtures has produced input. Independent means Josh's evaluator
and Dick's issuer, not a second script of ours.

