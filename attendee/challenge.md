# CSA Verifiable Agent Challenge

## The question

An agent is asking to call a protected resource. It presents a signed authorization that refers to an ATF appraisal, which in turn refers to a TRACE runtime record.

What can you verify before allowing the request?

## Ten-minute challenge

### Option 1: Run the verifier

Requirements: Python 3.10 or later.

```text
pip install cryptography rfc8785
python demo/tools/verify_chain.py tv-01 tv-03 tv-04
```

Expected result:

```text
PASS  TV-01  allow/eligible_and_permitted
PASS  TV-03  deny/appraisal_superseded
PASS  TV-04  deny/evidence_hash_mismatch

3/3 cases matched their expected outcome.
```

The word `PASS` means the verifier reached the expected decision. It does not mean the agent is safe or certified.

### Option 2: Inspect the evidence

If you cannot run code, inspect these committed artifacts:

- `demo/fixtures/tv-01.json`: a fresh qualifying request that is allowed
- `demo/fixtures/tv-03.json`: an unexpired claim refused after a signed demotion
- `demo/fixtures/tv-04.json`: a different valid record refused because its digest was not appraised
- `demo/transcript.txt`: the complete seven-case verifier output
- `demo/resource-contract.md`: the proposed responsibility and verification boundaries

## What to look for

For each request, identify:

1. Who issued the TRACE record?
2. Which exact record digest did the ATF evaluator appraise?
3. Which profile and version governed the appraisal?
4. Is the evaluator trusted by the relying resource?
5. Is the appraisal current, or has a later signed event superseded it?
6. Does the AAuth identity bind to the TRACE subject?
7. Does the asserted trust level meet the resource minimum?
8. Does local resource policy permit this specific action?

## Submit your observations

Please answer these questions in the CSA survey:

1. Which claims could you independently verify?
2. Which claim appeared meaningful but was not supported by evidence?
3. Would your organization rely on this chain at an agent trust boundary? Why or why not?
4. Did the superseded and substituted cases fail as you expected?
5. What should we test at the October 30 workshop?

## What this challenge does not establish

- It is not CSA certification or endorsement.
- The ATF profile is drafted for this exercise from ATF v0.9.1 and is not
  CSA-ratified.
- The committed fixtures use real signatures but synthetic runtime and policy values.
- The AAuth fixture is a proposed claim shape, not proof of adoption by AAuth or
  the IETF. The AAuth link in these vectors is produced by a stub issuer, not by
  an independently operated one.
- A verified TRACE record reports evidence within its observation boundary. It does not prove universal safety or cover uninstrumented paths.
- An ATF level creates eligibility for consideration. The relying resource still makes the authorization decision.

## The shared model

> TRACE is the evidence. ATF is the judgment. AAuth is the delivery. The relying party still decides.

## Deployed resource boundary

The demotion and status cases above exercise the local fixture verifier. The
September 7 deployed resource capture is separate and demonstrates no live
status feed. See `demo/provider/captures/september-7/README.md` and the resource
contract for the observed results and verification limits.
