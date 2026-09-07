"""Offline, live-clock preflight for this summit's TRACE-to-ATF handoff.

Authenticates the supplied artifacts against explicit pinned keys, then checks
the demo profile and exact evidence binding. It does not appraise the workload,
query status, settle D-05, or issue a token. Exit 0 means ready for demo issuance
at the reported time; it is not an authorization or conformance verdict.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import time
from pathlib import Path

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class Rejected(ValueError):
    pass


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected('duplicate_json_member')
        result[key] = value
    return result


def load(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=strict_object)
    if not isinstance(value, dict):
        raise Rejected('expected_json_object')
    return value


def digest(value):
    return 'sha256:' + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def decode(value):
    if not isinstance(value, str):
        raise Rejected('invalid_base64url')
    return base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)


def signature(value, anchor, reason):
    try:
        if anchor.get('kty') != 'OKP' or anchor.get('crv') != 'Ed25519' or 'd' in anchor:
            raise ValueError('expected public Ed25519 anchor')
        key = Ed25519PublicKey.from_public_bytes(decode(anchor['x']))
        key.verify(decode(value['signature']), rfc8785.dumps({k: v for k, v in value.items() if k != 'signature'}))
    except (InvalidSignature, ValueError, KeyError, TypeError) as error:
        raise Rejected(reason) from error


def require(condition, reason):
    if not condition:
        raise Rejected(reason)


def epoch(value):
    require(type(value) is int and value > 0, 'invalid_timestamp')
    return value


def verify(record, appraisal, trace_key, evaluator_key, profile, expected_issuer, now):
    # Both signatures precede conclusions about the signed timestamps/claims.
    signature(record, trace_key, 'invalid_trace_signature')
    signature(appraisal, evaluator_key, 'invalid_appraisal_signature')
    require(appraisal.get('issuer') == expected_issuer, 'untrusted_appraisal_issuer')
    require(profile.get('id') == 'csa-atf' and profile.get('version') == '0.9.1', 'unsupported_profile')
    require(appraisal.get('type') == profile['appraisal_type'], 'unsupported_appraisal_type')
    require(appraisal.get('version') == '0.1-draft', 'unsupported_appraisal_version')
    require(record.get('eat_profile') == profile['evidence_profile'], 'unsupported_trace_profile')
    for field in ('profile', 'evidence', 'subject', 'result'):
        require(isinstance(appraisal.get(field), dict), 'invalid_appraisal_' + field)
    require(isinstance(record.get('cnf'), dict) and isinstance(record['cnf'].get('jwk'), dict), 'invalid_record_cnf')
    p = appraisal.get('profile', {})
    require(p.get('id') == profile['id'] and p.get('version') == profile['version'], 'appraisal_profile_mismatch')
    require(p.get('policy_hash') == digest(profile), 'profile_hash_mismatch')
    evidence = appraisal.get('evidence', {})
    require(evidence.get('trace_profile') == record['eat_profile'], 'evidence_profile_mismatch')
    require(evidence.get('record_hash') == digest(record), 'evidence_hash_mismatch')
    subject = appraisal.get('subject', {})
    require(isinstance(record.get('subject'), str) and bool(record['subject']), 'missing_record_subject')
    require(subject.get('workload_id') == record['subject'], 'workload_binding_mismatch')
    require(bool(subject.get('agent_id')) and bool(subject.get('session_id')), 'missing_appraisal_subject')
    # This is the deployed resource's compatibility constraint, not a resolution
    # of whether two namespaces or agent/workload identities must be equal.
    require(subject['agent_id'] == subject['workload_id'], 'resource_subject_compatibility_unresolved')
    result = appraisal.get('result', {})
    require(result.get('decision') == 'qualifying', 'appraisal_not_qualifying')
    require(result.get('trust_level') in ('senior', 'principal'), 'resource_level_insufficient')
    require(bool(appraisal.get('appraisal_id')), 'missing_appraisal_id')
    require(type(appraisal.get('sequence')) is int and appraisal['sequence'] >= 0, 'invalid_sequence')
    cnf = record.get('cnf', {}).get('jwk', {})
    require(all(cnf.get(k) == trace_key.get(k) for k in ('kty', 'crv', 'x')), 'record_cnf_mismatch')
    issued, expires, recorded = epoch(appraisal.get('iat')), epoch(appraisal.get('exp')), epoch(record.get('iat'))
    require(expires > issued and expires > now, 'appraisal_expired_or_invalid')
    # The demo issuer/verifier use the live clock. No time override on the CLI.
    require(issued <= now, 'appraisal_not_yet_valid')
    f = profile['freshness']
    require(expires - issued <= f['appraisal_ttl_seconds'], 'appraisal_ttl_exceeded')
    require(-f['clock_skew_seconds'] <= now - recorded <= f['record_window_seconds'], 'record_not_current')
    return {
        'ready_for_demo_issuance': True,
        'checked_at': now,
        'appraisal_issuer': expected_issuer,
        'appraisal_id': appraisal['appraisal_id'],
        'record_hash': digest(record),
        'appraisal_hash': digest(appraisal),
        'profile_hash': digest(profile),
        'expires_at': expires,
        'remaining_seconds': expires - now,
        'level': result['trust_level'],
        'limits': ['status_not_queried', 'workload_not_reappraised', 'fixture_runtime_evidence', 'cross_namespace_binding_unresolved'],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('record', 'appraisal', 'trace-jwk', 'evaluator-jwk', 'profile'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--expected-issuer', required=True)
    args = p.parse_args()
    now = int(time.time())
    try:
        result = verify(load(args.record), load(args.appraisal), load(args.trace_jwk),
                        load(args.evaluator_jwk), load(args.profile), args.expected_issuer, now)
    except (Rejected, ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({'ready_for_demo_issuance': False, 'checked_at': now, 'error': str(error)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
