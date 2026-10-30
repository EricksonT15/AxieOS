"""AxieOS Task135H /96CD: stored marketplace proceeds, offline evidence only.

Reads the reviewed96BV extraction; never opens SQLite or accesses a network.
Accounting rows supply sales; economic rows provide comparisons, not more sales.
No cost basis is approved and no realized profit or PHP recovery is calculated.
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

SOURCE_NAME = 'AxieOS_Checkpoint96BV_Finance_Source_Rows_20261030T022027_384339Z.json'
REVIEWED_SHA256 = '33d3b63a0da4e9daf29b24217b58a7319ceaf217438e5289156f6166c74384c7'
PAYMENT_FIELDS = ('classification', 'asset_name', 'asset_token_id', 'quantity',
                  'payment_asset', 'gross_amount', 'marketplace_fee', 'net_amount')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def amount(value):
    require(isinstance(value, str) and len(value) <= 80 and
            re.fullmatch(r'\d+(?:\.\d+)?', value),
            'Missing or invalid amount; zero must not be substituted')
    return Decimal(value)


def sum_field(rows, field):
    with localcontext() as ctx:
        ctx.prec = 200
        return format(sum((amount(r[field]) for r in rows), Decimal(0)), 'f')


def unique(rows, key):
    values = [r[key] for r in rows]
    require(all(isinstance(v, str) and v for v in values), 'Missing ' + key)
    require(len(values) == len(set(values)), 'Duplicate ' + key + '; review before aggregation')


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def build_report(source, digest):
    require(source['checkpoint'] == '96BV', 'Expected reviewed96BV extract')
    tables = source['tables']
    accounting = tables['blockchain_accounting_records']['rows']
    economics = tables['blockchain_economic_events']['rows']
    require(len(accounting) == tables['blockchain_accounting_records']['row_count'] == 405,
            'Accounting source count changed')
    require(len(economics) == tables['blockchain_economic_events']['row_count'] == 128,
            'Economic source count changed')
    unique(accounting, 'accounting_key')
    unique(accounting, 'txhash')
    unique(economics, 'event_key')
    unique(economics, 'txhash')
    economic_by_hash = {r['txhash']: r for r in economics}
    require(set(economic_by_hash) <= {r['txhash'] for r in accounting},
            'Unexpected economic-only activity; review required')
    sales = [r for r in accounting if r['event_type'] == 'ASSET_SALE']
    require(len(sales) == 75, 'Reviewed sale count changed')
    reviews, conflicts = [], []
    grouped = defaultdict(list)
    for row in sales:
        require(row['classification'] == 'MARKETPLACE_SALE' and row['direction'] == 'OUT',
                'Sale classification or direction mismatch')
        require(row['is_internal_transfer'] == 0, 'Sale flagged as internal transfer')
        require(row['accounting_status'] in {'READY', 'REVIEW'}, 'Unreviewed accounting status')
        require(row['asset_category'] in {'AXIE_NFT', 'CONSUMABLE'}, 'Unreviewed sale category')
        require(row['payment_asset'] == 'Ronin Wrapped Ether', 'Unreviewed payment asset')
        gross, fee, net = (amount(row[k]) for k in ('gross_amount', 'marketplace_fee', 'net_amount'))
        with localcontext() as ctx:
            ctx.prec = 200
            require(gross - fee == net, 'Gross minus fee differs from stored net: ' + row['txhash'])
        other = economic_by_hash.get(row['txhash'])
        require(other is not None, 'Missing economic comparison row')
        require(all(row[k] == other[k] for k in PAYMENT_FIELDS),
                'Cross-source payment fields differ: ' + row['txhash'])
        differences = {k: {'accounting': row[k], 'economic': other[k]}
                       for k in ('cost_basis', 'realized_pl') if row[k] != other[k]}
        if differences:
            conflicts.append({'txhash': row['txhash'], 'differences': differences})
        reviews.append({'accounting_row_preserved': row, 'economic_comparison_row_preserved': other,
                        'payment_fields_match': True, 'gross_minus_fee_equals_net': True,
                        'cost_basis_or_profit_conflict': bool(differences),
                        'accepted_cost_basis': None, 'accepted_realized_profit': None,
                        'receipt_verified_by_this_report': False})
        grouped[(row['payment_asset'], row['asset_category'], row['accounting_status'])].append(row)
    require(len(conflicts) == 24, 'Reviewed cost/profit conflict count changed')
    groups = [{'payment_asset': currency, 'asset_category': category, 'accounting_status': status,
               'sales': len(rows), 'stored_gross_proceeds': sum_field(rows, 'gross_amount'),
               'stored_marketplace_fees': sum_field(rows, 'marketplace_fee'),
               'stored_net_proceeds_excluding_gas': sum_field(rows, 'net_amount')}
              for (currency, category, status), rows in sorted(grouped.items())]
    return {
        'project': 'AxieOS V0.13', 'task': '135H', 'checkpoint': '96CD',
        'report_schema_version': '1.0', 'source': {'filename': SOURCE_NAME, 'sha256': digest},
        'scope': 'Stored marketplace payment arithmetic, not independently verified income or recovery',
        'coverage': {'accounting_rows': len(accounting), 'economic_comparison_rows': len(economics),
                     'stored_sales_counted_once': len(sales), 'economic_rows_added_as_sales': 0,
                     'sale_dates_as_stored': [min(r['datetime'] for r in sales), max(r['datetime'] for r in sales)],
                     'timezone_normalized': False, 'complete_history': False,
                     'new_receipt_or_wallet_balance_verification': False,
                     'cost_basis_or_profit_conflicts': len(conflicts)},
        'groups_by_asset_and_stored_status': groups,
        'sale_evidence_reviews': reviews,
        'cost_basis_profit_conflicts_preserved': conflicts,
        'non_sale_accounting_event_counts_not_totaled': dict(Counter(r['event_type'] for r in accounting if r['event_type'] != 'ASSET_SALE')),
        'unknown_metrics': {'verified_total_income': None, 'realized_profit': None,
                            'php_proceeds': None, 'php_cash_recovery': None,
                            'complete_gas_cost': None, 'current_unrecovered_principal_php': None},
        'accounting_notes': [
            'READY and REVIEW are stored source statuses, not independent verification. Both are shown separately.',
            'Gross, fees and net are alternative components of the same sale, not additive income streams.',
            'Marketplace fees are already deducted in net proceeds. Do not subtract them again when using net.',
            'Economic events corroborate the same128 accounting hashes; they are not extra transactions.',
            'All24 consumable cost/profit conflicts are preserved. No cost basis or profit field is approved, including rows without a cross-source conflict.',
            'Sale receipts retained in crypto are not automatically PHP cash recovery or fresh capital.',
            'Purchases, swaps, rewards, transfers and burns are outside these proceeds subtotals.',
            'Transaction success, gas, complete historical coverage and source attribution require separate evidence.',
        ],
        'validation': {'status': 'PASS_STORED_ARITHMETIC_ONLY', 'database_opened': False,
                       'database_writes': 0, 'network_calls': 0, 'wallet_operations': 0,
                       'production_source_changes': 0, 'funding_register_changed': False,
                       'checkpoint96_closed': False},
    }


def markdown(report):
    c = report['coverage']
    lines = ['# AxieOS — Stored marketplace proceeds — Checkpoint96CD', '',
             'Partial historical evidence; overall Checkpoint96 OPEN.', '',
             'Sale dates as stored: ' + ' to '.join(c['sale_dates_as_stored']) + '. No timezone normalization.', '',
             '75 stored sales counted once. Economic rows are comparison evidence, not additional sales.', '',
             '| Payment asset | Category | Stored status | Sales | Gross | Fees | Net excluding gas |',
             '|---|---|---|---:|---:|---:|---:|']
    for row in report['groups_by_asset_and_stored_status']:
        lines.append(f"| {row['payment_asset']} | {row['asset_category']} | {row['accounting_status']} | {row['sales']} | {row['stored_gross_proceeds']} | {row['stored_marketplace_fees']} | {row['stored_net_proceeds_excluding_gas']} |")
    lines += ['', '24 cost-basis/profit conflicts preserved. Accepted cost basis and realized profit remain unknown for every sale in this report.', '',
              'Verified total income, PHP proceeds, PHP recovery, complete gas and current unrecovered principal: **UNKNOWN**.', '']
    lines += ['- ' + note for note in report['accounting_notes']]
    lines += ['', f"Source SHA256: `{report['source']['sha256']}`", '',
              'Database opened:NO; writes:0; network calls:0; wallet operations:0.',
              'VALIDATION: PASS (stored payment arithmetic only; Checkpoint96 OPEN).', '']
    return '\n'.join(lines)


def write_reports(report, root):
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.96CD_pending_', dir=root))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    destination = root / ('AxieOS_Checkpoint96CD_Marketplace_Proceeds_' + stamp + '_' + stage.name[-8:])
    try:
        report['created_at_utc'] = datetime.now(timezone.utc).isoformat()
        (stage / 'marketplace_proceeds.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        (stage / 'marketplace_proceeds.md').write_text(markdown(report), encoding='utf-8')
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
        require(digest == REVIEWED_SHA256, 'Source differs from reviewed96BV bytes; review required')
        report = build_report(json.loads(raw, object_pairs_hook=unique_json), digest)
        if args.check_only:
            print('VALIDATION: PASS (offline source/arithmetic checks; no output written)')
            return 0
        destination = write_reports(report, args.output_dir)
        print('AXIEOS V0.13 - TASK135H - CHECKPOINT96CD')
        print('Stored sales:75 | Economic rows added as sales:0 | Cost/profit conflicts:24')
        print('Gross/fee/net arithmetic passes; READY/REVIEW retained separately')
        print('Verified income, realized profit and PHP recovery UNKNOWN')
        print('New JSON and Markdown reports: ' + str(destination.resolve()))
        print('Database opened:NO | Writes:0 | Network calls:0')
        print('VALIDATION: PASS (stored payment arithmetic only; Checkpoint96 OPEN)')
        return 0
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        print('STOP: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
