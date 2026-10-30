"""Task135H / 96CF: offline view of stored marketplace purchase payments.

Reads the reviewed 96BV JSON extraction. Purchases are asset acquisitions,
not fresh capital contributions or automatically deductible expenses.
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

SOURCE_NAME = 'AxieOS_Checkpoint96BV_Finance_Source_Rows_20261030T022027_384339Z.json'
SOURCE_SHA256 = '33d3b63a0da4e9daf29b24217b58a7319ceaf217438e5289156f6166c74384c7'
MATCH_FIELDS = ('classification', 'asset_name', 'asset_token_id', 'quantity',
                'payment_asset', 'gross_amount', 'marketplace_fee', 'net_amount')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def amount(value):
    require(isinstance(value, str) and len(value) <= 80 and
            re.fullmatch(r'\d+(?:\.\d+)?', value), 'Missing or invalid gross amount')
    return Decimal(value)


def build_report(source, digest):
    require(source['checkpoint'] == '96BV', 'Expected 96BV extraction')
    tables = source['tables']
    accounting = tables['blockchain_accounting_records']['rows']
    economics = tables['blockchain_economic_events']['rows']
    require(len(accounting) == tables['blockchain_accounting_records']['row_count'] == 405,
            'Accounting row count changed')
    require(len(economics) == tables['blockchain_economic_events']['row_count'] == 128,
            'Economic row count changed')
    for rows, key in ((accounting, 'accounting_key'), (accounting, 'txhash'),
                      (economics, 'event_key'), (economics, 'txhash')):
        values = [r[key] for r in rows]
        require(all(isinstance(v, str) and v for v in values) and
                len(values) == len(set(values)), 'Missing or duplicate ' + key)
    economic_by_hash = {r['txhash']: r for r in economics}
    require(set(economic_by_hash) <= {r['txhash'] for r in accounting},
            'Unmatched economic transaction')
    purchases = [r for r in accounting if r['event_type'] == 'ASSET_PURCHASE']
    require(len(purchases) == 53, 'Purchase count changed')
    grouped = defaultdict(list)
    reviews = []
    for row in purchases:
        require(row['classification'] == 'MARKETPLACE_BUY' and row['direction'] == 'IN'
                and row['is_internal_transfer'] == 0, 'Purchase classification changed')
        require(row['accounting_status'] == 'READY' and
                row['asset_category'] in {'AXIE_NFT', 'CONSUMABLE'} and
                row['payment_asset'] == 'Ronin Wrapped Ether', 'Purchase scope changed')
        amount(row['gross_amount'])
        other = economic_by_hash.get(row['txhash'])
        require(other is not None and
                all(row[k] == other[k] for k in MATCH_FIELDS),
                'Missing or mismatched economic purchase: ' + row['txhash'])
        require(all(row[k] is None and other[k] is None for k in
                    ('marketplace_fee', 'net_amount', 'cost_basis', 'realized_pl')),
                'Previously unknown purchase field changed; review required')
        reviews.append({'accounting_row_preserved': row,
                        'economic_comparison_row_preserved': other,
                        'payment_fields_match': True,
                        'receipt_or_success_verified_by_this_report': False,
                        'approved_cost_basis': None})
        grouped[(row['payment_asset'], row['asset_category'], row['accounting_status'])].append(row)
    groups = []
    for (payment, category, status), rows in sorted(grouped.items()):
        with localcontext() as ctx:
            ctx.prec = 200
            total = format(sum((amount(r['gross_amount']) for r in rows), Decimal(0)), 'f')
        groups.append({'payment_asset': payment, 'asset_category': category,
                       'accounting_status': status, 'purchases': len(rows),
                       'stored_gross_outlay': total})
    return {
        'project': 'AxieOS V0.13', 'task': '135H', 'checkpoint': '96CF',
        'source': {'filename': SOURCE_NAME, 'sha256': digest},
        'scope': 'Stored marketplace purchase amounts only; historical and incomplete',
        'coverage': {'accounting_rows': len(accounting),
                     'economic_comparison_rows': len(economics),
                     'stored_purchases_counted_once': len(purchases),
                     'economic_rows_added_as_purchases': 0,
                     'purchase_dates_as_stored': [min(r['datetime'] for r in purchases),
                                                  max(r['datetime'] for r in purchases)],
                     'timezone_normalized': False, 'complete_history': False},
        'groups_by_asset_and_stored_status': groups,
        'purchase_evidence_reviews': reviews,
        'unknown_metrics': {'complete_purchase_cost_including_gas': None,
                            'verified_expenses': None, 'approved_cost_basis': None,
                            'php_purchase_outlays': None, 'fresh_capital_contributed': None,
                            'current_unrecovered_principal_php': None},
        'accounting_notes': [
            'The 53 economic rows match these purchases and are comparison evidence, not additional purchases.',
            'Gross amounts are stored WETH payment figures; transaction success and wallet receipt were not checked here.',
            'Fees, gas, net payment and approved asset cost basis are unknown.',
            'Asset purchases are not automatically operating expenses or new external capital.',
            'Do not add these amounts to the PHP contribution register; a funding link is required.',
            'Sales, swaps, staking movements, burns, rewards and transfers are outside this report.',
        ],
        'validation': {'status': 'PASS_STORED_PURCHASE_AMOUNTS_ONLY',
                       'database_opened': False, 'database_writes': 0,
                       'network_calls': 0, 'checkpoint96_closed': False},
    }


def markdown(report):
    c = report['coverage']
    lines = ['# AxieOS — Stored marketplace purchase outlays — Checkpoint 96CF', '',
             'Partial historical evidence; Checkpoint 96 OPEN.', '',
             'Dates as stored: ' + ' to '.join(c['purchase_dates_as_stored']) +
             '. Timezone not normalized.', '',
             '53 stored purchases counted once.', '',
             '| Payment asset | Category | Stored status | Purchases | Gross outlay |',
             '|---|---|---|---:|---:|']
    for row in report['groups_by_asset_and_stored_status']:
        lines.append(f"| {row['payment_asset']} | {row['asset_category']} | "
                     f"{row['accounting_status']} | {row['purchases']} | "
                     f"{row['stored_gross_outlay']} |")
    lines += ['', 'Verified expenses, gas, approved cost basis, PHP outlays and '
              'complete capital recovery: **UNKNOWN**.', '']
    lines += ['- ' + note for note in report['accounting_notes']]
    lines += ['', f"Source SHA256: `{report['source']['sha256']}`", '',
              'Database opened: NO | Writes: 0 | Network calls: 0',
              'VALIDATION: PASS (stored purchase amounts only; Checkpoint 96 OPEN).', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path,
                        default=Path('reports/axieos_v013/checkpoint96') / SOURCE_NAME)
    parser.add_argument('--output-dir', type=Path,
                        default=Path('reports/axieos_v013/checkpoint96'))
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        raw = args.input.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == SOURCE_SHA256, 'Source differs from reviewed 96BV bytes')
        report = build_report(json.loads(raw, object_pairs_hook=unique_json), digest)
        if args.check_only:
            print('VALIDATION: PASS (offline source and purchase checks; no output written)')
            return 0
        args.output_dir.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.96CF_pending_', dir=args.output_dir))
        try:
            report['created_at_utc'] = datetime.now(timezone.utc).isoformat()
            (stage / 'purchase_outlays.json').write_text(
                json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
            (stage / 'purchase_outlays.md').write_text(markdown(report), encoding='utf-8')
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
            destination = args.output_dir / ('AxieOS_Checkpoint96CF_Purchase_Outlays_' + stamp)
            require(not destination.exists(), 'Output already exists')
            stage.rename(destination)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        print('AXIEOS V0.13 - TASK135H - CHECKPOINT96CF')
        print('Stored purchases:53 | Economic rows added as purchases:0')
        print('WETH gross outlay grouped by asset category; fees/gas/cost basis UNKNOWN')
        print('Verified expenses, PHP outlays and fresh capital UNKNOWN')
        print('New JSON and Markdown reports: ' + str(destination.resolve()))
        print('Database opened:NO | Writes:0 | Network calls:0')
        print('VALIDATION: PASS (stored purchase amounts only; Checkpoint96 OPEN)')
        return 0
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        print('STOP: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
