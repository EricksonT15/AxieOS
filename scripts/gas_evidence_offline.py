"""AxieOS Task135H / 96CL: scoped raw gas evidence, offline only.

The fee_raw / 10^18 RON interpretation is provisional. It requires an
independent receipt comparison before use as verified financial expense.
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

CK = 'AxieOS_Checkpoint96CK_Raw_Fee_Evidence_20261030T062440_093125Z.json'
CI = 'AxieOS_Checkpoint96CI_Gas_Transaction_Evidence_20261030T055821_936006Z.json'
BV = 'AxieOS_Checkpoint96BV_Finance_Source_Rows_20261030T022027_384339Z.json'
BV_HASH = '33d3b63a0da4e9daf29b24217b58a7319ceaf217438e5289156f6166c74384c7'
CI_HASH = 'f932e417e406b62c48b81f37f2cebb2a656ec3a306fa624a9d91f9bf4f6396cc'
WALLET = '0x1ed8b3f3bd6a624de47f81beea101f0d15cdfbc8'


def check(ok, message):
    if not ok:
        raise ValueError(message)


def no_duplicate_keys(pairs):
    d = {}
    for k, v in pairs:
        check(k not in d, 'Duplicate JSON key: ' + k)
        d[k] = v
    return d


def read(path, expected_hash=None):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_hash:
        check(digest == expected_hash, 'Source differs from reviewed copy: ' + path.name)
    return json.loads(raw, object_pairs_hook=no_duplicate_keys), digest


def build(ck, ck_hash, ci, bv):
    check(ck['checkpoint'] == '96CK' and ck['source_96CI_sha256'] == CI_HASH,
          '96CK linkage changed')
    check(ci['checkpoint'] == '96CI' and ci['source_96BV_sha256'] == BV_HASH,
          '96CI linkage changed')
    accounting = bv['tables']['blockchain_accounting_records']['rows']
    by_hash = {r['txhash'].lower(): r for r in accounting}
    check(len(accounting) == len(by_hash) == 405, 'Accounting hashes changed')
    ci_rows = ci['transaction_rows']
    check(len(ci_rows) == 565 and
          {r['txhash'].lower() for r in ci_rows} == set(by_hash), '96CI rows changed')
    raw_rows = ck['raw_rows']
    hashes = [r['tx_hash'].lower() for r in raw_rows]
    check(len(raw_rows) == len(set(hashes)) == 227, 'Raw row count or uniqueness changed')
    missing = sorted(set(by_hash) - set(hashes))
    check(len(missing) == 178 and
          missing == sorted(h.lower() for h in ck['hashes_without_raw_rows']),
          'Raw coverage changed')
    groups = defaultdict(list)
    reviews = []
    for row in raw_rows:
        h = row['tx_hash'].lower()
        check(h in by_hash and row['from_address'].lower() == WALLET and
              row['status'] == 'ok', 'Raw sender or status requires review')
        fee = row['fee_raw']
        check(isinstance(fee, str) and re.fullmatch(r'[1-9][0-9]{0,79}', fee),
              'Invalid raw fee')
        check(isinstance(row['gas_used'], int) and row['gas_used'] > 0,
              'Invalid gas used')
        matches = [r for r in ci_rows if r['txhash'].lower() == h]
        check(matches and all(r['status'] == 'Success' and r['txn_fee_ron'] == '0.0'
                              for r in matches), '96CI status or placeholder changed')
        check(any(r['blockno'] == row['block_number'] for r in matches),
              'Block number mismatch')
        groups[by_hash[h]['event_type']].append(row)
        reviews.append({'txhash': row['tx_hash'], 'event_type': by_hash[h]['event_type'],
                        'fee_raw_preserved': fee, 'gas_used': row['gas_used'],
                        'raw_status': row['status'], 'raw_from_address': row['from_address'],
                        'stored_transfer_row_count': len(matches),
                        'user_paid_fee_verified_by_receipt': False})
    summaries = []
    for event_type, rows in sorted(groups.items()):
        with localcontext() as ctx:
            ctx.prec = 200
            raw_total = sum((int(x['fee_raw']) for x in rows), 0)
            candidate_ron = format(Decimal(raw_total) / Decimal(10**18), 'f')
        summaries.append({'event_type': event_type, 'raw_transaction_count': len(rows),
                          'sum_fee_raw_integer': str(raw_total),
                          'candidate_ron_if_fee_raw_is_wei': candidate_ron})
    return {
        'project': 'AxieOS V0.13', 'task': '135H', 'checkpoint': '96CL',
        'source': {'96CK_filename': CK, '96CK_sha256': ck_hash,
                   '96CI_sha256': CI_HASH, '96BV_sha256': BV_HASH},
        'coverage': {'accounting_hashes': 405, 'transaction_ledger_rows': 565,
                     'distinct_raw_transactions': 227, 'missing_raw_hashes': 178,
                     'raw_marketplace_sale_hashes': len(groups.get('ASSET_SALE', []))},
        'raw_fee_by_accounting_event_type': summaries,
        'raw_fee_evidence_rows': reviews,
        'missing_raw_hashes_preserved': missing,
        'interpretation': 'Division by 10^18 is a candidate wei-to-RON conversion, not a verified expense.',
        'unknown_metrics': {'complete_gas_ron': None, 'verified_user_paid_gas_ron': None,
                            'php_gas_cost': None, 'complete_expenses': None},
        'notes': [
            'Raw API rows are unique by hash and have status ok; all 227 have the registered primary wallet as sender.',
            'The 565 transfer-ledger rows repeat 148 hashes and contain 0.0 fee placeholders; do not sum those rows.',
            'Missing raw rows include all 75 stored marketplace sales; this alone does not establish who paid their gas.',
            'Fee unit and user payment need independent receipt corroboration before accounting acceptance.',
            'The source covers only the historical 96BV slice, not all AxieOS activity.',
        ],
        'validation': {'status': 'PASS_CANDIDATE_RAW_FEE_VIEW_ONLY',
                       'database_opened': False, 'database_writes': 0,
                       'network_calls': 0, 'checkpoint96_closed': False},
    }


def markdown(report):
    c = report['coverage']
    lines = ['# AxieOS — Raw gas evidence — Checkpoint 96CL', '',
             f"{c['distinct_raw_transactions']} unique raw rows for {c['accounting_hashes']} accounting hashes; "
             f"{c['missing_raw_hashes']} lack raw rows.", '',
             '| Accounting event | Raw transactions | Raw integer sum | Candidate RON if wei |',
             '|---|---:|---:|---:|']
    for g in report['raw_fee_by_accounting_event_type']:
        lines.append(f"| {g['event_type']} | {g['raw_transaction_count']} | "
                     f"{g['sum_fee_raw_integer']} | {g['candidate_ron_if_fee_raw_is_wei']} |")
    lines += ['', report['interpretation'], '',
              'Verified user-paid gas, complete RON gas and PHP cost: **UNKNOWN**.', '']
    lines += ['- ' + n for n in report['notes']]
    lines += ['', f"96CK source SHA256: `{report['source']['96CK_sha256']}`", '',
              'Database opened: NO | Writes: 0 | Network calls: 0',
              'VALIDATION: PASS (candidate raw fee view only; Checkpoint 96 OPEN).', '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir', type=Path, default=Path('reports/axieos_v013/checkpoint96'))
    p.add_argument('--output-dir', type=Path, default=Path('reports/axieos_v013/checkpoint96'))
    p.add_argument('--check-only', action='store_true')
    args = p.parse_args()
    try:
        ck, ck_hash = read(args.source_dir / CK)
        ci, _ = read(args.source_dir / CI, CI_HASH)
        bv, _ = read(args.source_dir / BV, BV_HASH)
        report = build(ck, ck_hash, ci, bv)
        if args.check_only:
            print('VALIDATION: PASS (offline candidate fee checks; no output written)')
            return 0
        args.output_dir.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.96CL_pending_', dir=args.output_dir))
        try:
            report['created_at_utc'] = datetime.now(timezone.utc).isoformat()
            (stage / 'gas_evidence.json').write_text(
                json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
            (stage / 'gas_evidence.md').write_text(markdown(report), encoding='utf-8')
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
            dest = args.output_dir / ('AxieOS_Checkpoint96CL_Gas_Evidence_' + stamp)
            check(not dest.exists(), 'Output exists')
            stage.rename(dest)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        print('AXIEOS V0.13 - TASK135H - CHECKPOINT96CL')
        print('Unique raw fee rows:227 | Accounting hashes lacking raw rows:178')
        print('Candidate wei-to-RON view only; verified expense and complete gas UNKNOWN')
        print('New JSON and Markdown reports: ' + str(dest.resolve()))
        print('Database opened:NO | Writes:0 | Network calls:0')
        print('VALIDATION: PASS (candidate raw fee view only; Checkpoint96 OPEN)')
        return 0
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        print('STOP: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
