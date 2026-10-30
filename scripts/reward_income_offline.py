"""AxieOS Task135H /96CB: reward-income evidence report from reviewed96CA.

Standard library only. No database, network or project imports. Reads the saved
report; writes new JSON/Markdown files. Does not change source classifications.
"""
import argparse
import hashlib
import json
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

SOURCE_NAME = 'AxieOS_Checkpoint96CA_Reward_Normalization_Review.json'
REVIEWED_SHA256 = '2136a620b84928b2f0c32c12d592b028ee3fa28ba36c953220ba0b6623e2036e'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def quantity(value):
    require(isinstance(value, str) and len(value) <= 80 and
            re.fullmatch(r'\d+(?:\.\d+)?', value),
            'Missing or invalid quantity; cannot substitute zero')
    return Decimal(value)


def decimal_sum(values):
    with localcontext() as ctx:
        ctx.prec = 200
        return format(sum((quantity(x) for x in values), Decimal(0)), 'f')


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def build_report(source, source_hash):
    require(source['checkpoint'] == '96CA', 'Expected96CA reviewed evidence')
    require(source['validation']['status'] == 'PASS_SCOPED_OFFLINE_NORMALIZATION_REVIEW',
            'Source normalization review has not passed')
    rows = source['normalized_review_records']
    require(len(rows) == source['summary']['candidate_accounting_rows'] == 34,
            'Reviewed candidate count changed')
    keys, hashes = [], []
    rewards, movements = [], []
    for reviewed in rows:
        original = reviewed['source_accounting_row']
        event = reviewed['resolver_output']
        keys.append(event['accounting_key'])
        hashes.append(event['txhash'])
        require(event['accounting_key'] == original['accounting_key'] and
                event['txhash'] == original['txhash'] and event['quantity'] == original['quantity'],
                'Normalized event differs from source row')
        quantity(event['quantity'])
        require(reviewed['cached_status_gate_passed'] is True and not reviewed['review_reasons'],
                'Event requires evidence review')
        require((event['confidence'], event['resolution_basis']) in {
            ('HIGH', 'EXPLICIT_METHOD'), ('MEDIUM', 'FLOW_PATTERN')},
            'Unsupported confidence or classification basis')
        require(event['token'] in {'AXS', 'bAXS'}, 'Unsupported reward token')
        if event['event_type'] in {'CLAIM', 'RESTAKE_REWARD'}:
            require(reviewed['finance_review_bucket'] == 'REWARD_EVENT' and event['direction'] == 'IN',
                    'Reward classification or direction mismatch')
            require((event['token'], event['economic_source']) in {
                ('AXS', 'AXS_STAKING'), ('bAXS', 'BOUNTY'), ('bAXS', 'TERRARIUMS')},
                'Unreviewed reward source')
            rewards.append(reviewed)
        else:
            require(event['event_type'] in {'STAKE', 'UNSTAKE'} and
                    reviewed['finance_review_bucket'] == 'STAKING_MOVEMENT_NOT_INCOME',
                    'Nonreward event needs review')
            require(event['direction'] == ('OUT' if event['event_type'] == 'STAKE' else 'IN'),
                    'Staking movement direction mismatch')
            movements.append(reviewed)
    require(all(isinstance(k, str) and k for k in keys + hashes), 'Missing event identity')
    require(len(set(keys)) == len(keys) and len(set(hashes)) == len(hashes),
            'Duplicate event identity; no silent deduplication permitted')
    counts = Counter(x['resolver_output']['event_type'] for x in rows)
    require(dict(counts) == source['summary']['event_type_counts'], 'Event count mismatch')
    require(len(rewards) == source['summary']['reward_event_candidates'] == 18 and
            len(movements) == source['summary']['staking_movements_excluded_from_income'] == 16,
            'Reward/movement partition mismatch')
    require(dict(Counter(x['resolver_output']['confidence'] for x in rows)) ==
            source['summary']['resolver_confidence_counts'], 'Confidence count mismatch')

    grouped = defaultdict(list)
    for reviewed in rewards:
        event = reviewed['resolver_output']
        grouped[(event['token'], event['economic_source'], event['confidence'],
                 event['event_type'])].append(event['quantity'])
    groups = [{'token': token, 'economic_source': origin, 'confidence': confidence,
               'event_type': kind, 'events': len(values), 'quantity': decimal_sum(values)}
              for (token, origin, confidence, kind), values in sorted(grouped.items())]
    token_subtotals = []
    for token in sorted({x['resolver_output']['token'] for x in rewards}):
        events = [x['resolver_output'] for x in rewards if x['resolver_output']['token'] == token]
        token_subtotals.append({
            'token': token, 'events': len(events),
            'explicit_method_quantity': decimal_sum([x['quantity'] for x in events if x['confidence'] == 'HIGH']),
            'flow_inferred_quantity': decimal_sum([x['quantity'] for x in events if x['confidence'] == 'MEDIUM']),
            'scoped_reward_quantity_including_inferred': decimal_sum([x['quantity'] for x in events]),
        })
    times = [x['resolver_output']['datetime'] for x in rows]
    return {
        'project': 'AxieOS V0.13', 'task': '135H', 'checkpoint': '96CB',
        'report_schema_version': '1.0',
        'source': {'filename': SOURCE_NAME, 'sha256': source_hash},
        'coverage': {'candidate_datetime_range_as_stored': [min(times), max(times)],
                     'timezone_normalized': False, 'candidate_rows': len(rows),
                     'reward_events': len(rewards), 'staking_movements_excluded': len(movements),
                     'complete_reward_history': False, 'gas_included': False},
        'scoped_token_subtotals': token_subtotals,
        'reward_groups': groups,
        'reward_evidence_records': rewards,
        'staking_movements_excluded_from_income': movements,
        'unknown_metrics': {'php_reward_income': None, 'complete_all_time_reward_income': None,
                            'realized_profit_php': None, 'current_unrecovered_principal_php': None},
        'accounting_notes': [
            'These are scoped token reward amounts from saved evidence, not PHP cash recovery or net profit.',
            'HIGH means explicit method in cached evidence; MEDIUM means flow-pattern inference. Neither is a new receipt verification.',
            'RESTAKE_REWARD is one reward operation; no second claim or stake reward is added.',
            'STAKE and UNSTAKE amounts are excluded from reward income.',
            'The10manual staking_reward_events rows are not added to these events.',
            'Marketplace sales, other rewards, pending claims, spending and gas are outside this report scope.',
            'Input confidence, raw quantities and evidence records are preserved. Unknown values are not converted to zero.',
        ],
        'validation': {'status': 'PASS_SCOPED_TOKEN_REPORT_ONLY', 'database_opened': False,
                       'database_writes': 0, 'network_calls': 0, 'wallet_operations': 0,
                       'funding_register_changed': False, 'checkpoint96_closed': False},
    }


def markdown(report):
    coverage = report['coverage']
    lines = ['# AxieOS — Offline reward income — Checkpoint96CB', '',
             'Historical, partial token evidence; overall Checkpoint96 OPEN.', '',
             'Stored candidate timestamps: ' + ' to '.join(coverage['candidate_datetime_range_as_stored']) + '. No timezone normalization.', '',
             '| Token | Reward events | Explicit method | Flow inferred | Scoped total including inferred |',
             '|---|---:|---:|---:|---:|']
    for row in report['scoped_token_subtotals']:
        lines.append(f"| {row['token']} | {row['events']} | {row['explicit_method_quantity']} | {row['flow_inferred_quantity']} | {row['scoped_reward_quantity_including_inferred']} |")
    lines += ['', '| Token | Source | Event type | Confidence | Events | Quantity |',
              '|---|---|---|---|---:|---:|']
    for row in report['reward_groups']:
        lines.append(f"| {row['token']} | {row['economic_source']} | {row['event_type']} | {row['confidence']} | {row['events']} | {row['quantity']} |")
    lines += ['', f"{coverage['reward_events']} reward events retained; {coverage['staking_movements_excluded']} staking movements excluded from income.", '',
              'PHP reward income, complete all-time income, realized profit and current unrecovered principal: **UNKNOWN**.', '']
    lines += ['- ' + note for note in report['accounting_notes']]
    lines += ['', f"Source SHA256: `{report['source']['sha256']}`", '',
              'Database opened:NO; writes:0; network calls:0; wallet operations:0.',
              'VALIDATION: PASS (scoped token report only; Checkpoint96 OPEN).', '']
    return '\n'.join(lines)


def write_reports(report, root):
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.96CB_pending_', dir=root))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    destination = root / ('AxieOS_Checkpoint96CB_Reward_Income_' + stamp + '_' + stage.name[-8:])
    try:
        report['created_at_utc'] = datetime.now(timezone.utc).isoformat()
        (stage / 'reward_income.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        (stage / 'reward_income.md').write_text(markdown(report), encoding='utf-8')
        require(not destination.exists(), 'Output already exists')
        stage.rename(destination)
        return destination
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('reports/axieos_v013/checkpoint96') / SOURCE_NAME)
    parser.add_argument('--output-dir', type=Path, default=Path('reports/axieos_v013/checkpoint96'))
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        raw = args.input.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == REVIEWED_SHA256, 'Source differs from reviewed96CA bytes; review required')
        report = build_report(json.loads(raw, object_pairs_hook=unique_json), digest)
        if args.check_only:
            print('VALIDATION: PASS (source and classification checks; no output written)')
            return 0
        destination = write_reports(report, args.output_dir)
        print('AXIEOS V0.13 - TASK135H - CHECKPOINT96CB')
        print('Reward events:18 | Staking movements excluded:16')
        for subtotal in report['scoped_token_subtotals']:
            print(subtotal['token'] + ' scoped reward quantity including inferred: ' +
                  subtotal['scoped_reward_quantity_including_inferred'])
        print('Confidence breakdown retained; PHP income and complete-history totals UNKNOWN')
        print('New JSON and Markdown reports: ' + str(destination.resolve()))
        print('Database opened:NO | Writes:0 | Network calls:0')
        print('VALIDATION: PASS (scoped token report only; Checkpoint96 OPEN)')
        return 0
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        print('STOP: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
