# Generated standalone adapter; see tools/build_converters.py and local README.
# Independently authored; PolyForm Noncommercial 1.0.0; see LICENSE.txt/NOTICE.
"""Standard-library runtime embedded into each standalone versioned converter.
New adapter code; no upstream predictor code, weights or execution.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile

COLUMNS = ['schema_version','peptide_sequence','scope','mhc_key','task','provider',
           'predictor_version','model_version','run_id','metric','metric_kind',
           'metric_semantics','score','score_direction','unit','status','reason','source_row']
AA = re.compile(r'[ACDEFGHIKLMNPQRSTVWY]+')


def chain(value):
    """Reversible two-field human HLA spelling conversion; never fuzzy matching."""
    if not isinstance(value, str) or value != value.strip():
        raise ValueError('Invalid or padded HLA')
    s = value.removeprefix('HLA-')
    patterns = [r'(A|B|C|DRA|DRB[1345]|DPA1|DPB1|DQA1|DQB1)\*(\d{2}):(\d{2})',
                r'(A|B|C|DRA|DRB[1345]|DPA1|DPB1|DQA1|DQB1)\*?(\d{2})(\d{2})',
                r'(A|B|C|DRA|DRB[1345]|DPA1|DPB1|DQA1|DQB1)_(\d{2})_(\d{2})',
                r'(A|B|C|DRA|DRB[1345]|DPA1|DPB1|DQA1|DQB1)(\d{2}):(\d{2})']
    for pattern in patterns:
        m = re.fullmatch(pattern, s)
        if m:
            locus, a, b = m.groups()
            return f'HLA-{locus}*{a}:{b}'
    raise ValueError('Unsupported/ambiguous HLA spelling: ' + value)


def presenter(value, spec, declared):
    if '__' in value:
        parts = value.split('__')
    elif '~' in value:
        parts = value.split('~')
    else:
        parts = [value]
    keys = [chain(x) for x in parts]
    if len(keys) == 1 and re.fullmatch(r'HLA-[ABC]\*\d{2}:\d{2}', keys[0]):
        if spec['class'] != 'I':
            raise ValueError('Class I allele in Class II output')
        return keys[0]
    if spec['class'] != 'II':
        raise ValueError('Only human Class I A/B/C supported by this adapter')
    if len(keys) == 1 and re.fullmatch(r'HLA-DRB[1345]\*\d{2}:\d{2}', keys[0]):
        # Alpha is supplied by the user's completed project, never invented.
        matches = [k for k in declared if k.endswith('~' + keys[0])]
        if len(matches) != 1 or not matches[0].startswith('HLA-DRA*01:01~'):
            raise ValueError('DR output requires one explicit DRA*01:01~DRB presenter in bundle')
        return matches[0]
    if len(keys) != 2:
        raise ValueError('Class II requires an explicit alpha/beta pair')
    pair = '~'.join(keys)
    if not re.fullmatch(r'HLA-DP(A1\*\d{2}:\d{2})~HLA-DPB1\*\d{2}:\d{2}|HLA-DQA1\*\d{2}:\d{2}~HLA-DQB1\*\d{2}:\d{2}', pair):
        raise ValueError('Unsupported/reversed/mismatched Class II pair')
    return pair


def read_bundle(path):
    p = Path(path)
    meta = json.loads((p / 'manifest.json').read_text())
    if meta.get('schema_version') != '1.0.0' or meta.get('contract') != 'external-export-1.0.0':
        raise ValueError('Require a Neoantimon2 external-export-1.0.0 bundle')
    with (p / 'pmhc_queries.tsv').open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if not reader.fieldnames or 'mhc_key' not in reader.fieldnames:
            raise ValueError('Bundle lacks presenter queries')
        return {row['mhc_key'] for row in reader}


def table(text, delimiter):
    lines = text.splitlines()
    comments = [line for line in lines if line.startswith('#')]
    data = [(i, line) for i, line in enumerate(lines, 1) if not line.startswith('#')]
    if not data or any(not line for _, line in data):
        raise ValueError('Missing table or blank data record')
    parsed = list(csv.reader([line for _, line in data], delimiter=delimiter, strict=True))
    header = parsed[0]
    if len(set(header)) != len(header) or any(not x or x != x.strip() for x in header):
        raise ValueError('Invalid or duplicate native columns')
    rows = []
    for (number, _), cells in zip(data[1:], parsed[1:]):
        if len(cells) != len(header):
            raise ValueError('Malformed native row ' + str(number))
        if any(any(ord(c) < 32 for c in cell) for cell in cells):
            raise ValueError('Control character in native record')
        rows.append((number, dict(zip(header, cells))))
    if not rows:
        raise ValueError('Empty native table')
    return header, rows, comments


def measurements(spec, header, comments):
    kind = spec['parser']
    if kind == 'wide':
        marker = '# Output from ' + spec['banner']
        if comments.count(marker) != 1:
            raise ValueError('Require exact upstream version banner: ' + marker)
        if spec['class'] == 'II' and comments.count('# Context type: none') != 1:
            raise ValueError('Only no-context MixMHC2pred output is intrinsic to peptide/HLA')
        ranks = [x for x in header if x.startswith('%Rank_') and x not in ('%Rank_bestAllele','%Rank_best')]
        if not ranks:
            raise ValueError('Missing per-allele ranks; best-allele-only output unsupported')
        alleles = [x[len('%Rank_'):] for x in ranks]
        prefix = '# Alleles: '
        declared = [x[len(prefix):].split(', ') for x in comments if x.startswith(prefix)]
        if declared != [alleles]:
            raise ValueError('Allele declarations and per-allele columns disagree')
        required = list(spec['base_columns'])
        for a in alleles:
            required += [p + a for p in spec['allele_prefixes']]
        if set(header) != set(required):
            raise ValueError('Unknown/incomplete wide output schema')
        return [(a, [(p+a, *metric) for p, metric in spec['wide_metrics']]) for a in alleles]
    required = set(spec['required'])
    if not required <= set(header) or set(header) - required - set(spec.get('optional', [])):
        raise ValueError('Unknown/incomplete native schema for ' + spec['name'])
    return [(None, spec['metrics'])]


def convert(text, spec, declared):
    header, rows, comments = table(text, spec['delimiter'])
    measures = measurements(spec, header, comments)
    sha = hashlib.sha256(text.encode('utf-8')).hexdigest()
    result, seen, groups = [], set(), set()
    for number, row in rows:
        peptide = row[spec['peptide']]
        if not AA.fullmatch(peptide):
            raise ValueError('Require literal uppercase AA20 peptide at row ' + str(number))
        if spec.get('length_column') and row[spec['length_column']] != str(len(peptide)):
            raise ValueError('Native peptide length does not match sequence')
        if spec.get('context') and row['Context']:
            raise ValueError('Context sequence cannot be broadcast as peptide-intrinsic prediction')
        if spec.get('sample_column'):
            sample = row[spec['sample_column']]
            if not sample or sample != sample.strip():
                raise ValueError('Invalid upstream sample label')
            groups.add(sample)
            if len(groups) != 1:
                raise ValueError('Require a single upstream sample group, without repeated headers')
        # Check auxiliary declared numeric fields too; none becomes an affinity.
        for col in header:
            if col.startswith('%RankBinding_') or (spec['parser'] == 'wide' and col.startswith('Score_') and spec['name'] != 'PRIME'):
                number_value(row[col], allow_missing=False)
        for allele_column, metrics in measures:
            mhc = presenter(allele_column if allele_column is not None else row[spec['hla']], spec, declared)
            if spec.get('best_column') and row.get(spec['best_column'], ''):
                if presenter(row[spec['best_column']], spec, declared) != mhc:
                    raise ValueError('Best allele differs from supplied single allele')
            for column, metric, metric_kind, semantics, unit, direction in metrics:
                if column not in row:  # Truly optional documented metric.
                    continue
                value = row[column]
                missing = spec.get('missing', {})
                if value in missing:
                    status, reason = missing[value], 'native_missing:' + (value or 'empty')
                    score = ''
                else:
                    score = value
                    numeric = number_value(value)
                    if metric_kind == 'percentile_rank' and not 0 <= numeric <= 100:
                        raise ValueError('Percentile outside [0,100]')
                    if spec.get('bounded') and not 0 <= numeric <= 1:
                        raise ValueError('Model score outside documented [0,1]')
                    if unit == 'nM' and numeric < 0:
                        raise ValueError('Negative affinity in nM')
                    if not spec['lengths'][0] <= len(peptide) <= spec['lengths'][1]:
                        raise ValueError('Evaluated peptide outside supported length range')
                    status, reason = 'evaluated', ''
                key = (peptide, mhc, metric)
                if key in seen:
                    raise ValueError('Duplicate/conflicting native prediction')
                seen.add(key)
                source = f'sha256:{sha}:line:{number}:column:{column}'
                if spec.get('sample_column'):
                    source += ':sample:' + row[spec['sample_column']]
                result.append(dict(zip(COLUMNS, ['1.0.0',peptide,'peptide_hla',mhc,
                    spec['task'],spec['provider'],spec['predictor_version'],spec['model_version'],
                    'input-sha256:' + sha,metric,metric_kind,semantics,score,direction,unit,status,reason,source])))
    return sorted(result, key=lambda x: (x['peptide_sequence'], x['mhc_key'], x['metric']))


def number_value(value, allow_missing=False):
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?', value):
        raise ValueError('Invalid/missing/non-finite numeric value: ' + repr(value))
    n = float(value)
    if not math.isfinite(n):
        raise ValueError('Non-finite numeric value')
    return n


def main(spec):
    parser = argparse.ArgumentParser(description=spec['name'] + ' pinned-schema adapter; does not execute predictor')
    for option in ('input','output','bundle'):
        parser.add_argument('--' + option, required=True)
    args = parser.parse_args()
    source, target, bundle = Path(args.input), Path(args.output), Path(args.bundle)
    if target.exists() or target.is_symlink() or target.resolve() == source.resolve():
        raise ValueError('Output must be new; input and existing files are never overwritten')
    if target.resolve().is_relative_to(bundle.resolve()):
        raise ValueError('Do not write into the export bundle')
    declared = read_bundle(bundle)
    text = source.read_bytes().decode('utf-8')
    rows = convert(text, spec, declared)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='', dir=target.parent, delete=False) as f:
            temp = Path(f.name)
            writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter='\t', lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        # Exclusive final creation: a concurrently created user file is retained.
        with target.open('xb') as f:
            f.write(temp.read_bytes())
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)

SPEC = {'id': 'deepimmuno-cnn@1.0.0', 'name': 'DeepImmuno-CNN', 'family': 'DeepImmuno', 'category': 'IM', 'class': 'I', 'predictor_version': 'git-df42ac5b6bddfe531268335e2dcb496559cd488b', 'model_version': '', 'provider': 'deepimmuno-cnn', 'parser': 'long', 'delimiter': '\t', 'peptide': 'peptide', 'hla': 'HLA', 'required': ['peptide', 'HLA', 'immunogenicity'], 'metrics': [['immunogenicity', 'immunogenicity_score', 'raw_score', 'raw', 'unitless', 'higher_is_better']], 'lengths': [9, 10], 'source_repo': 'frankligy/DeepImmuno', 'source_commit': 'df42ac5b6bddfe531268335e2dcb496559cd488b', 'task': 'external:immunogenicity', 'bounded': True}

if __name__ == '__main__':
    try:
        main(SPEC)
    except (ValueError, OSError, KeyError, csv.Error, json.JSONDecodeError) as error:
        raise SystemExit('Conversion failed: ' + str(error))
