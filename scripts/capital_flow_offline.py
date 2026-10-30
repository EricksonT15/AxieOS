"""AxieOS Task135H / 96BR: offline capital-flow view of a reviewed register.

Save in scripts and run from the repository root. Standard library only.
No database, network, project imports, exchange matching or wallet actions.
"""
import argparse
import hashlib
import json
import re
import shutil
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

DEFAULT_REGISTER = 'AxieOS_Checkpoint96BN_Capital_Register_Summer_Integration.json'
UNKNOWN_METRICS = (
    'complete_all_time_external_capital_php',
    'current_all_time_unrecovered_principal_php',
    'complete_recovery_percentage', 'all_time_realized_profit_php',
    'live_portfolio_value_php',
)
CONTRIBUTION_CATEGORIES = {
    'ORIGINAL_PERSONAL_FIAT_CAPITAL', 'NEW_PERSONAL_FIAT_CAPITAL_VIA_COINSPH',
    'EXTERNAL_CRYPTO_CONTRIBUTION_APPROVED_PHP_ALLOCATION',
    'NEW_PERSONAL_CAPITAL_FOR_SUMMER_AXIE',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def amount(value):
    require(isinstance(value, str) and re.fullmatch(r'\d+(?:\.\d+)?', value),
            'Amount must be a nonnegative decimal string; missing is not zero')
    require(len(value) <= 80, 'Amount exceeds supported precision')
    return Decimal(value)


def total(rows, key='amount_php'):
    with localcontext() as ctx:
        ctx.prec = 200
        return sum((amount(row[key]) for row in rows), Decimal(0))


def unique(rows, key):
    values = [row[key] for row in rows]
    require(all(isinstance(x, str) and x for x in values), 'Missing identifier: ' + key)
    require(len(values) == len(set(values)), 'Duplicate identifier: ' + key)


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def build_report(d, source_name, source_hash):
    require(d['checkpoint'] == '96BN' and d['schema_version'] == '1.3',
            'Unsupported register; reviewed96BN/schema1.3 required')
    s = d['summary']
    contributions = d['capital_contributions']
    excluded = d['excluded_other_game_funding']
    receipts = d['historical_reported_php_cash_receipts']
    unique(contributions + excluded, 'record_id')
    unique(receipts, 'record_id')
    require(not ({x['record_id'] for x in contributions + excluded} &
                 {x['record_id'] for x in receipts}), 'Contribution/receipt ID overlap')
    for row in contributions:
        require(row['category'] in CONTRIBUTION_CATEGORIES, 'Unreviewed contribution category')
        require(row.get('included_in_axieos_capital', True) is True, 'Excluded row in active contributions')
    for row in excluded:
        require(row['included_in_axieos_capital'] is False and
                row['category'] == 'PERSONAL_CAPITAL_FOR_OTHER_GAMES_EXCLUDED_FROM_AXIEOS',
                'Unreviewed exclusion')
    for row in receipts:
        require(row['category'] == 'USER_REPORTED_HISTORICAL_PHP_CASH_RECEIVED' and
                row['net_permanent_extraction_verified'] is False,
                'Receipt classification changed; review required')
    capital, cash, other_games = total(contributions), total(receipts), total(excluded)
    require(capital == amount(s['provisional_identified_capital_php']), 'Capital total mismatch')
    require(cash == amount(s['historical_reported_php_cash_received']), 'Receipt total mismatch')
    require(other_games == amount(s['excluded_other_game_funding_php']), 'Excluded total mismatch')
    for rows, field in [(contributions, 'identified_contribution_source_rows'),
                        (excluded, 'excluded_other_game_cash_in_rows'),
                        (receipts, 'historical_reported_php_cash_receipt_rows')]:
        require(len(rows) == s[field], 'Row count mismatch: ' + field)
    coins = [x for x in contributions if x['category'] == 'NEW_PERSONAL_FIAT_CAPITAL_VIA_COINSPH']
    require(total(coins) == amount(s['provisional_axieos_coinsph_funding_php']), 'Coins subtotal mismatch')
    require(len(coins) == s['coinsph_cash_in_source_rows'], 'Coins row count mismatch')
    require(total(coins + excluded) == amount(s['all_recorded_coinsph_cash_ins_php']),
            'Original cash-in total not preserved')
    require(len(coins + excluded) == s['all_recorded_coinsph_cash_in_rows_preserved'],
            'Original cash-in rows not preserved')
    for key in UNKNOWN_METRICS:
        require(s[key] is None, 'Completeness changed without review: ' + key)

    purchases = d['purchase_payments_not_additional_capital']
    unique(purchases['records'], 'acquisition_key')
    require(len(purchases['records']) == s['historical_marketplace_purchases'], 'Purchase count mismatch')
    payment_groups = defaultdict(list)
    display_only = []
    for row in purchases['records']:
        require(row['php_fresh_capital_allocation'] is None, 'New purchase PHP allocation needs review')
        if row['payment_currency'] is None:
            require(row['net_purchase_payment_excluding_gas'] is None,
                    'Unverified payment promoted into a net payment')
            require(row.get('blockchain_reconciliation_complete') is False,
                    'Screenshot reconciliation status changed')
            amount(row['displayed_purchase_price']['amount'])
            require(row['displayed_purchase_price']['exact_settlement_token_verified'] is False,
                    'Settlement verification changed')
            display_only.append(row)
        else:
            payment_groups[row['payment_currency']].append(row)
    require(set(payment_groups) == set(purchases['payment_subtotals']), 'Payment currency mismatch')
    for currency, rows in payment_groups.items():
        declared = purchases['payment_subtotals'][currency]
        require(len(rows) == declared['acquisitions'] and
                total(rows, 'net_purchase_payment_excluding_gas') == amount(declared['amount']),
                'Purchase payment subtotal mismatch: ' + currency)
    by_id = {row['record_id']: row for row in contributions}
    for row in display_only:
        linked = by_id.get(row['linked_capital_record_id'])
        require(linked is not None and linked['asset_id'] == row['axie_id'],
                'Screenshot purchase must link to existing funding')
    partition = d['ownership_partition_at_saved_block']
    gaps = d['acquisition_evidence_gaps']['owned_ids']
    require(len(gaps) == len(set(gaps)) == partition['unresolved'] ==
            s['unresolved_owned_acquisition_ids_at_saved_block'], 'Owned gap count mismatch')
    require(sum(partition[k] for k in ('reviewed_purchases', 'reviewed_breeding_events', 'unresolved'))
            == partition['total'], 'Ownership partition mismatch')

    grouped = []
    for category in sorted(CONTRIBUTION_CATEGORIES):
        rows = [row for row in contributions if row['category'] == category]
        grouped.append({'category': category, 'rows': len(rows), 'amount_php': format(total(rows), 'f')})
    return {
        'project': 'AxieOS V0.13', 'task': '135H', 'checkpoint': '96BR',
        'report_schema_version': '1.0',
        'source': {'filename': source_name, 'sha256': source_hash, 'checkpoint': d['checkpoint']},
        'scope': 'Offline view of reviewed evidence; no new funding classification or allocation',
        'summary': {
            'provisional_identified_capital_php': format(capital, 'f'),
            'included_contribution_entries': len(contributions),
            'excluded_other_game_funding_php': format(other_games, 'f'),
            'historical_user_reported_cash_received_php': format(cash, 'f'),
            'receipt_status': 'USER_ATTESTED_NOT_BANK_MATCHED; NOT_VERIFIED_NET_PERMANENT_EXTRACTION',
            'additional_php_received_for_personal_use': s['additional_php_received_for_personal_use'],
            'additional_receipt_zero_scope': s['additional_receipt_zero_basis'],
            **{key: None for key in UNKNOWN_METRICS},
            'complete_internal_transfer_total': None,
            'historical_purchase_evidence_records': len(purchases['records']),
            'owned_acquisition_evidence_gaps_at_saved_block': len(gaps),
        },
        'contribution_groups': grouped,
        'included_contributions': contributions,
        'excluded_other_game_funding': excluded,
        'historical_reported_cash_receipts': receipts,
        'purchase_payments_not_additional_capital': purchases,
        'breeding_inputs_not_additional_capital': d['breeding_inputs_not_additional_capital'],
        'funding_route_context_not_additional_capital': d['funding_route_measures_not_additional_capital'],
        'internal_movement_coverage': {
            'status': 'NOT_A_COMPLETE_MOVEMENT_LEDGER',
            'note': 'Saved withdrawal/buy measures are whole-export context, not game-repartitioned internal transfers. No timing matching or FIFO executed. Missing movement details do not mean zero movements.'},
        'ownership_partition_at_saved_block': partition,
        'acquisition_evidence_gaps': d['acquisition_evidence_gaps'],
        'validation': {'status': 'PASS_OFFLINE_VIEW_ONLY', 'production_database_opened': False,
                       'database_writes': 0, 'network_calls': 0, 'wallet_operations': 0,
                       'additional_capital_created': False, 'checkpoint96_closed': False},
    }


def markdown(report):
    s = report['summary']
    lines = ['# AxieOS — Offline capital flow — Checkpoint96BR', '',
             'Task135H; overall Checkpoint96 OPEN. This is a partial evidence view.', '',
             f"Provisional identified investment: PHP {Decimal(s['provisional_identified_capital_php']):,.2f}", '',
             '| Contribution category | Entries | PHP |', '|---|---:|---:|']
    for row in report['contribution_groups']:
        lines.append(f"| {row['category']} | {row['rows']} | {Decimal(row['amount_php']):,.2f} |")
    lines += ['', f"Other-game funding excluded: PHP {Decimal(s['excluded_other_game_funding_php']):,.2f}.", '',
              f"Historical reported PHP cash received: PHP {Decimal(s['historical_user_reported_cash_received_php']):,.2f}. User-attested, not bank-matched or verified net permanent extraction.", '',
              'Complete all-time capital, current unrecovered principal, recovery percentage, profit and live value: **UNKNOWN**. No partial subtraction is presented as final recovery.', '',
              'Purchase payments, swaps, withdrawals, breeding and gas funded from existing capital are not additional contributions. Whole-export movement context is not a complete internal-transfer ledger and has not been repartitioned by game.', '',
              f"Purchase evidence records: {s['historical_purchase_evidence_records']}; owned acquisition gaps at the saved snapshot: {s['owned_acquisition_evidence_gaps_at_saved_block']}.", '',
              'Displayed prices with unverified settlement tokens remain separate from payment subtotals. Source evidence, exclusions and unknown fields are retained in the companion JSON.', '',
              f"Source: `{report['source']['filename']}`", f"SHA256: `{report['source']['sha256']}`", '',
              'Database opened:NO; writes:0; network calls:0; wallet operations:0.',
              'VALIDATION: PASS (offline view only; Checkpoint96 OPEN).', '']
    return '\n'.join(lines)


def write_reports(report, output_root):
    output_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.96BR_pending_', dir=output_root))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    destination = output_root / ('AxieOS_Checkpoint96BR_Capital_Flow_' + stamp + '_' + stage.name[-8:])
    try:
        report['created_at_utc'] = datetime.now(timezone.utc).isoformat()
        (stage / 'capital_flow.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        (stage / 'capital_flow.md').write_text(markdown(report), encoding='utf-8')
        require(not destination.exists(), 'Output already exists')
        stage.rename(destination)
        return destination
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('reports/axieos_v013/checkpoint96') / DEFAULT_REGISTER)
    parser.add_argument('--output-dir', type=Path, default=Path('reports/axieos_v013/checkpoint96'))
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        raw = args.input.read_bytes()
        d = json.loads(raw, object_pairs_hook=reject_duplicate_keys)
        report = build_report(d, args.input.name, hashlib.sha256(raw).hexdigest())
        if args.check_only:
            print('VALIDATION: PASS (offline validation; no output written)')
            return 0
        destination = write_reports(report, args.output_dir)
        print('AXIEOS V0.13 - TASK135H - CHECKPOINT96BR')
        print('Provisional identified investment: PHP ' + report['summary']['provisional_identified_capital_php'])
        print('Historical cash receipts remain user-attested; complete recovery metrics UNKNOWN')
        print('New JSON and Markdown reports: ' + str(destination.resolve()))
        print('Database opened:NO | Writes:0 | Network calls:0')
        print('VALIDATION: PASS (offline capital-flow view; Checkpoint96 OPEN)')
        return 0
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        print('STOP: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
