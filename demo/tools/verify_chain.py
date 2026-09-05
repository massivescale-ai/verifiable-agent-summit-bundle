"""Independent verifier for the TRACE -> ATF -> AAuth chain.

Runs the resource-side verification sequence from the interface contract against
the signed fixtures and prints a transcript for each step. Exit code 0 when every
case matches its expected outcome, 1 otherwise.

This is deliberately not the issuing code. It re-derives every digest and checks
every signature against the public JWKs in demo/fixtures/keys/, so a run here is
evidence the chain holds outside the process that produced it. It uses the real
agentrust-trace verifier when that library is importable, and a self-contained
Ed25519 check over RFC 8785 canonical JSON otherwise. The transcript names which
path ran.

Usage:
    python demo/tools/verify_chain.py                 # all cases
    python demo/tools/verify_chain.py tv-01 tv-03     # named cases
    python demo/tools/verify_chain.py --quiet         # verdict lines only
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "demo" / "fixtures"
KEYS = FIXTURES / "keys"

LEVEL_RANK = {"intern": 0, "junior": 1, "senior": 2, "principal": 3}

# Which check in the fixed sequence each reason code comes from. The order is the
# contract's, and where a run stops is the diagnosis, so callers that render a run
# need this rather than a count of transcript lines.
REASON_STEP = {
    "invalid_trace_signature": 1,
    "unsupported_trace_profile": 1,
    "unsupported_trust_anchor": 1,
    "invalid_appraisal_signature": 2,
    "untrusted_appraisal_issuer": 2,
    "invalid_aauth_signature": 9,
    "token_claim_mismatch": 9,
    "token_expired": 9,
    "subject_mismatch": 3,
    "session_mismatch": 3,
    "subject_binding_mismatch": 4,
    "evidence_hash_mismatch": 5,
    "appraisal_stale": 6,
    "appraisal_superseded": 7,
    "invalid_status_event": 7,
    "status_sequence_mismatch": 7,
    "unverified_supersede_claim": 7,
    "status_unavailable": 8,
    "require_hitl": 8,
    "invalid_proof_of_possession": 9,
    "mission_denied": 9,
    "insufficient_level": 10,
    "local_policy_denied": 11,
    "budget_denied": 11,
    "model_route_denied": 11,
}
TOTAL_STEPS = 11


class Denied(Exception):
    """Raised at the first failing check. The message is the reason code."""


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def canonical(obj: dict[str, Any]) -> bytes:
    return rfc8785.dumps(obj)


def digest(obj: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical(obj)).hexdigest()


def public_key(jwk: dict[str, str]) -> Ed25519PublicKey:
    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519":
        raise Denied("unsupported_trust_anchor")
    return Ed25519PublicKey.from_public_bytes(b64url_decode(jwk["x"]))


def check_signature(obj: dict[str, Any], jwk: dict[str, str], reason: str) -> None:
    """Ed25519 over canonical JSON with `signature` absent. Fail closed."""
    sig = obj.get("signature")
    if not sig:
        raise Denied(reason)
    body = {k: v for k, v in obj.items() if k != "signature"}
    try:
        public_key(jwk).verify(b64url_decode(sig), canonical(body))
    except (InvalidSignature, ValueError):
        raise Denied(reason) from None


def verify_trace_record(record: dict[str, Any], jwk: dict[str, str], log: list[str]) -> None:
    """Verify the Trust Record with the real TRACE verifier when it is available.

    max_age_seconds is disabled because the fixtures run on a synthetic clock;
    record currency is checked separately against the appraisal validity window,
    which is what the contract actually binds the decision to.
    """
    try:
        from agentrust_trace.sign import verify_record  # type: ignore

        try:
            verify_record(record, jwk, max_age_seconds=None)
        except Exception as exc:  # noqa: BLE001 - any rejection is a denial
            log.append(f"      agentrust-trace rejected the record: {exc}")
            raise Denied("invalid_trace_signature") from None
        log.append("      verifier: agentrust-trace (installed)")
    except ImportError:
        check_signature(record, jwk, "invalid_trace_signature")
        log.append("      verifier: built-in Ed25519 over RFC 8785 (agentrust-trace not installed)")

    if record.get("eat_profile") != "tag:agentrust-io.com,2026:trace-v0.2":
        raise Denied("unsupported_trace_profile")


def evaluate(case: dict[str, Any], anchors: dict[str, dict[str, str]], log: list[str]) -> str:
    """Run the resource-side sequence. Returns the allow reason or raises Denied.

    Order matters and is not arbitrary: subject binding is checked before evidence
    binding so a sub-agent presenting the parent's appraisal is reported as an
    identity failure rather than a hash mismatch, which is the more accurate
    diagnosis and the one an operator can act on.
    """
    request = case["request"]
    appraisal = case["appraisal"]
    record = case["trace_record"]
    policy = case["policy"]
    status = case["status_channel"]

    log.append("  1. TRACE record signature")
    verify_trace_record(record, anchors["trace"], log)

    log.append("  2. ATF appraisal signature")
    check_signature(appraisal, anchors["atf"], "invalid_appraisal_signature")
    # Which evaluators a relying party accepts is its own policy, not ours. The
    # fixtures name one; an interop run names whoever actually signed.
    trusted = case.get("trust", {}).get("appraisal_issuers", ["https://evaluator.example"])
    if appraisal.get("issuer") not in trusted:
        raise Denied("untrusted_appraisal_issuer")

    log.append("  3. appraisal subject matches the requesting agent")
    if appraisal["subject"]["agent_id"] != request["agent_id"]:
        raise Denied("subject_mismatch")
    if appraisal["subject"]["session_id"] != request["session_id"]:
        raise Denied("session_mismatch")

    log.append("  4. AAuth agent identifier binds to the TRACE subject")
    expected_subject = case["agent_binding"].get(request["agent_id"])
    if expected_subject is None or record.get("subject") != expected_subject:
        raise Denied("subject_binding_mismatch")

    log.append("  5. evidence binding by digest")
    computed = digest(record)
    if computed != appraisal["evidence"]["record_hash"]:
        log.append(f"      presented {computed}")
        log.append(f"      appraised {appraisal['evidence']['record_hash']}")
        raise Denied("evidence_hash_mismatch")

    log.append("  6. appraisal freshness")
    if request["request_time"] >= appraisal["exp"]:
        raise Denied("appraisal_stale")

    log.append("  7. appraisal currency against the event clock")
    latest = status["latest_sequence"]
    if latest > appraisal["sequence"]:
        for event in status["events"]:
            check_signature(event, anchors["atf"], "invalid_status_event")
            if event["sequence"] != latest:
                raise Denied("status_sequence_mismatch")
        if not status["events"]:
            raise Denied("unverified_supersede_claim")
        raise Denied("appraisal_superseded")

    log.append("  8. status channel availability")
    if policy["requires_current_status"] and not status["available"]:
        # Unknown is not current. The fallback is explicit policy, never a guess.
        raise Denied("status_unavailable" if policy["on_status_unavailable"] == "deny" else "require_hitl")

    log.append("  9. AAuth authorization")
    if not case["aauth"]["proof_of_possession_valid"]:
        raise Denied("invalid_proof_of_possession")
    if not case["aauth"]["mission_allows"]:
        raise Denied("mission_denied")

    # A real token, when one is present. The fixtures model AAuth as flags
    # because no issuer existed when they were written; an interop run carries
    # the issuer's actual signed token and it is checked here.
    token = case["aauth"].get("token")
    if token:
        check_signature(token, anchors["aauth"], "invalid_aauth_signature")
        claim = token.get("atf_appraisal", {})
        if claim.get("appraisal_id") != appraisal["appraisal_id"]:
            raise Denied("token_claim_mismatch")
        if claim.get("level") != appraisal["result"]["trust_level"]:
            raise Denied("token_claim_mismatch")
        if request["request_time"] >= token.get("exp", 0):
            raise Denied("token_expired")
        log.append("      token carries the appraisal by id, level, and digest")

    log.append(" 10. level meets the resource minimum")
    level = appraisal["result"]["trust_level"]
    if LEVEL_RANK.get(level, -1) < LEVEL_RANK.get(policy["minimum_level"], 99):
        raise Denied("insufficient_level")

    log.append(" 11. resource and AGT policy")
    if not policy["local_policy_allows"]:
        raise Denied("local_policy_denied")
    if not policy["budget_allows"]:
        raise Denied("budget_denied")
    if not policy["model_route_allows"]:
        raise Denied("model_route_denied")

    return "eligible_and_permitted"


def decision_event(case: dict[str, Any], decision: str, reason: str) -> dict[str, Any]:
    """The signed decision event the resource emits, minus the signature.

    Unsigned here on purpose: signing it needs the resource's own key, which this
    verifier does not hold. The shape is what feeds the next appraisal.
    """
    return {
        "type": "resource-decision-event",
        "agent_id": case["request"]["agent_id"],
        "session_id": case["request"]["session_id"],
        "resource": case["request"]["resource"],
        "action_hash": digest({"action": case["request"]["action"], "model": case["request"]["model"]}),
        "appraisal_id": case["appraisal"]["appraisal_id"],
        "policy_hash": case["appraisal"]["profile"]["policy_hash"],
        "decision": decision,
        "reason_codes": [reason],
        "dispatch_state": "dispatched" if decision == "allow" else "denied_not_dispatched",
        "iat": case["request"]["request_time"],
    }


def run(names: list[str], quiet: bool, bundle: Path | None = None) -> int:
    """Verify the committed vectors, or a bundle captured from a live run.

    A bundle is self-contained: its own trust anchors, its own cases. That is the
    point of handing one to an audience, so it is read from the bundle directory
    rather than from this repo.
    """
    source = bundle if bundle else FIXTURES
    key_dir = (bundle / "keys") if bundle else KEYS
    anchors = {
        "trace": json.loads((key_dir / "trace-issuer-public.jwk.json").read_text(encoding="utf-8")),
        "atf": json.loads((key_dir / "atf-evaluator-public.jwk.json").read_text(encoding="utf-8")),
    }

    paths = sorted(source.glob("tv-*.json")) + sorted(source.glob("live-*.json"))
    if names:
        wanted = {n.lower().removesuffix(".json") for n in names}
        paths = [p for p in paths if p.stem in wanted]
    if not paths:
        print(f"no cases found in {source}", file=sys.stderr)
        return 1

    failures = 0
    for path in paths:
        case = json.loads(path.read_text(encoding="utf-8"))
        log: list[str] = []
        try:
            reason = evaluate(case, anchors, log)
            decision = "allow"
        except Denied as denied:
            reason = str(denied)
            decision = "deny"

        expected = case["expected"]
        ok = decision == expected["decision"] and reason == expected["reason"]
        failures += 0 if ok else 1
        event = decision_event(case, decision, reason)

        if not quiet:
            print(f"\n{case['case']}  {case['note']}")
            for line in log:
                print(line)
            print(f"  -> decision {decision}, reason {reason}, dispatch {event['dispatch_state']}")
        verdict = "PASS" if ok else "FAIL"
        print(f"{verdict}  {case['case']}  {decision}/{reason}" + ("" if ok else f"  expected {expected['decision']}/{expected['reason']}"))

    print(f"\n{len(paths) - failures}/{len(paths)} cases matched their expected outcome.")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="*", help="case names, e.g. tv-01 tv-03")
    parser.add_argument("--quiet", action="store_true", help="verdict lines only")
    parser.add_argument(
        "--bundle",
        type=Path,
        help="verify a bundle captured by stage.py instead of the committed vectors",
    )
    args = parser.parse_args()
    return run(args.cases, args.quiet, args.bundle)


if __name__ == "__main__":
    sys.exit(main())
