"""Explicit local execution tests for reviewed adapters.
Not named test_*.py: automated Pages/PR hygiene must never execute converters.
Run after review: python3 tests/converter_checks.py -v
"""
import csv
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SPECS = json.loads((ROOT/'tools/converter_specs.json').read_text())

class AdapterTests(unittest.TestCase):
    spec = None
    def setUp(self):
        self.directory=ROOT/'converters'/self.spec['id']
        self.module=runpy.run_path(str(self.directory/'converter.py'),run_name='reviewed_adapter_test')
        self.text=(self.directory/'input-X.tsv').read_text()
        self.declared=self.module['read_bundle'](self.directory/'bundle')
        self.header,self.rows,self.comments=self.module['table'](self.text,self.spec['delimiter'])
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
    def convert(self,text=None):return self.module['convert'](self.text if text is None else text,self.spec,self.declared)
    def render(self,rows=None,header=None,comments=None):
        stream=io.StringIO(newline='');comments=self.comments if comments is None else comments
        if comments:stream.write('\n'.join(comments)+'\n')
        w=csv.DictWriter(stream,fieldnames=self.header if header is None else header,delimiter=self.spec['delimiter'],lineterminator='\n');w.writeheader();w.writerows([x[1] for x in self.rows] if rows is None else rows);return stream.getvalue()
    def score_column(self):
        return next(x for x in self.header if x.startswith('%Rank_') and x not in ('%Rank_best','%Rank_bestAllele')) if self.spec['parser']=='wide' else self.spec['metrics'][0][0]
    def test_exact_independent_expected_rows(self):
        with (self.directory/'expected.tsv').open(newline='') as f:expected=list(csv.DictReader(f,delimiter='\t'))
        self.assertEqual(self.convert(),expected)
        self.assertTrue(all(x['peptide_sequence'] in ('SIINFEKLA','NLVPMVATV','SIINFEKL') for x in expected))
        self.assertGreaterEqual(len({x['mhc_key'] for x in expected}),2)
    def test_numeric_lexeme_and_zero_preserved(self):
        col=self.score_column();rows=[x[1].copy() for x in self.rows];rows[0][col]='0.000000'
        got=self.convert(self.render(rows));self.assertTrue(any(x['score']=='0.000000' and x['status']=='evaluated' for x in got))
        rows[0][col]='1.234500e-3';got=self.convert(self.render(rows));self.assertTrue(any(x['score']=='1.234500e-3' for x in got))
    def test_missing_is_not_zero(self):
        col=self.score_column();rows=[x[1].copy() for x in self.rows]
        token='NA' if self.spec['class']=='II' else '';rows[0][col]=token
        if token in self.spec.get('missing',{}):
            got=self.convert(self.render(rows));self.assertTrue(any(x['score']=='' and x['status']!='evaluated' and x['reason'] for x in got))
        else:
            with self.assertRaises(ValueError):self.convert(self.render(rows))
    def test_malformed_and_unknown_schema_rejected(self):
        rows=[x[1].copy() for x in self.rows];key=self.spec['peptide'];head=[x for x in self.header if x!=key]
        for row in rows:del row[key]
        with self.assertRaises(ValueError):self.convert(self.render(rows,head))
        with self.assertRaises(ValueError):self.convert(self.text+'truncated\n')
        rows=[dict(x[1],unexpected='anything') for x in self.rows]
        with self.assertRaises(ValueError):self.convert(self.render(rows,self.header+['unexpected']))
    def test_invalid_nonfinite_and_percent_strings_rejected(self):
        col=self.score_column()
        for value in ('nan','NaN','inf','-inf','1e9999','0.2%','bad',' 0.2'):
            with self.subTest(value=value):
                rows=[x[1].copy() for x in self.rows];rows[0][col]=value
                with self.assertRaises(ValueError):self.convert(self.render(rows))
    def test_duplicate_identical_and_conflicting_rejected(self):
        for conflict in (False,True):
            rows=[x[1].copy() for x in self.rows];duplicate=rows[0].copy()
            if conflict:duplicate[self.score_column()]='0.123'
            rows.append(duplicate)
            with self.assertRaises(ValueError):self.convert(self.render(rows))
    def test_literal_peptides_never_repaired(self):
        for value in ('siinfekla','SIINFEKLX',' SIINFEKLA','SIINFEKLA ','SIINFEKL*',''):
            rows=[x[1].copy() for x in self.rows];rows[0][self.spec['peptide']]=value
            with self.assertRaises(ValueError):self.convert(self.render(rows))
    def test_hla_ambiguity_and_class_rejected(self):
        for value in ('A02','HLA-A*02:01:01',' HLA-A*02:01','HLA-A*0201,HLA-B*0702','DQB1_06_02','DPA1_02_01__DQB1_06_02'):
            with self.assertRaises(ValueError):self.module['presenter'](value,self.spec,self.declared)
        if self.spec['class']=='I':
            with self.assertRaises(ValueError):self.module['presenter']('DPA1_02_01__DPB1_01_01',self.spec,self.declared)
        else:
            with self.assertRaises(ValueError):self.module['presenter']('A0201',self.spec,self.declared)
    def test_direction_units_and_category_contract(self):
        got=self.convert()
        for row in got:
            if row['metric_kind']=='percentile_rank':
                self.assertEqual(row['score_direction'],'lower_is_better');self.assertEqual(row['unit'],'percent')
                self.assertEqual(row['metric_semantics'],'external_percentile' if self.spec['category']=='IM' else 'mhc_binding_percentile' if self.spec['category']=='BA' else 'mhc_presentation_percentile')
            elif row['unit']=='nM':self.assertEqual(self.spec['category'],'BA');self.assertEqual(row['score_direction'],'lower_is_better')
            else:self.assertEqual(row['metric_semantics'],'raw');self.assertEqual(row['score_direction'],'higher_is_better')
            self.assertEqual(row['provider'],self.spec['provider']);self.assertEqual(row['model_version'],'');self.assertIn('line:',row['source_row']);self.assertIn('column:',row['source_row'])
    def test_cli_deterministic_standalone_staging_and_no_input_changes(self):
        work=Path(self.temp.name);script=work/'converter.py';script.write_bytes((self.directory/'converter.py').read_bytes())
        raw=work/'input-X';raw.write_text(self.text);before=raw.read_bytes()
        outputs=[]
        for n in (1,2):
            target=work/f'out-{n}.tsv';p=subprocess.run([sys.executable,str(script),'--input',str(raw),'--output',str(target),'--bundle',str(self.directory/'bundle')],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);outputs.append(target.read_bytes())
        self.assertEqual(outputs[0],outputs[1]);self.assertEqual(outputs[0],(self.directory/'expected.tsv').read_bytes());self.assertEqual(before,raw.read_bytes())
        p=subprocess.run([sys.executable,str(script),'--input',str(raw),'--output',str(work/'out-1.tsv'),'--bundle',str(self.directory/'bundle')],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0);self.assertEqual((work/'out-1.tsv').read_bytes(),outputs[0])
    def test_crlf_hash_tracks_exact_original_bytes(self):
        work=Path(self.temp.name);raw=work/'crlf';payload=self.text.replace('\n','\r\n').encode();raw.write_bytes(payload);target=work/'out.tsv'
        p=subprocess.run([sys.executable,str(self.directory/'converter.py'),'--input',str(raw),'--output',str(target),'--bundle',str(self.directory/'bundle')],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        with target.open(newline='') as f:rows=list(csv.DictReader(f,delimiter='\t'))
        self.assertTrue(all(x['run_id']=='input-sha256:'+hashlib.sha256(payload).hexdigest() for x in rows));self.assertEqual(raw.read_bytes(),payload)
    def test_bad_input_leaves_no_partial_output(self):
        raw=Path(self.temp.name)/'bad';raw.write_text(self.text+'truncated\n');out=Path(self.temp.name)/'out'
        p=subprocess.run([sys.executable,str(self.directory/'converter.py'),'--input',str(raw),'--output',str(out),'--bundle',str(self.directory/'bundle')],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0);self.assertFalse(out.exists());self.assertIn('Conversion failed:',p.stderr)
    def test_version_boundary_or_versionless_limitation(self):
        if self.spec['parser']=='wide':
            with self.assertRaises(ValueError):self.convert(self.text.replace(self.spec['banner'],self.spec['banner'].replace('v','v99',1)))
        else:
            rows=[dict(x[1],predictor_version='unsupported-version') for x in self.rows]
            with self.assertRaises(ValueError):self.convert(self.render(rows,self.header+['predictor_version']))
        self.assertIn(self.spec['source_commit'],(self.directory/'PROVENANCE.json').read_text())

for spec in SPECS:
    globals()['Check_'+spec['id'].split('@')[0].replace('-','_')]=type('Check_'+spec['id'].split('@')[0].replace('-','_'),(AdapterTests,),{'spec':spec})
del AdapterTests  # abstract base is not an extra test/converter identity

class CrossAdapterTests(unittest.TestCase):
    def test_canonical_class_i_keys_consistent(self):
        for spec in SPECS:
            if spec['class']=='I':
                m=runpy.run_path(str(ROOT/'converters'/spec['id']/'converter.py'))
                for token in ('A0201','HLA-A0201','HLA-A*0201','HLA-A*02:01','A_02_01'):
                    self.assertEqual(m['chain'](token),'HLA-A*02:01')
    def test_class_ii_pairs_dr_context_and_missing(self):
        spec=next(x for x in SPECS if x['class']=='II');d=ROOT/'converters'/spec['id'];m=runpy.run_path(str(d/'converter.py'));decl=m['read_bundle'](d/'bundle');text=(d/'input-X.tsv').read_text()
        for value,wanted in [('DPA1_02_01__DPB1_01_01','HLA-DPA1*02:01~HLA-DPB1*01:01'),('DQA1_01_02__DQB1_06_02','HLA-DQA1*01:02~HLA-DQB1*06:02'),('DRB1_15_01','HLA-DRA*01:01~HLA-DRB1*15:01')]:self.assertEqual(m['presenter'](value,spec,decl),wanted)
        for declared in (set(),decl|{'HLA-DRA*01:02~HLA-DRB1*15:01'}):
            with self.assertRaises(ValueError):m['presenter']('DRB1_15_01',spec,declared)
        with self.assertRaises(ValueError):m['convert'](text.replace('# Context type: none','# Context type: full'),spec,decl)
        with self.assertRaises(ValueError):m['convert'](text.replace('\t\tDRB1_15_01','\tAAAAAAAAAAAA\tDRB1_15_01'),spec,decl)
    def test_mhcflurry_genotype_or_best_allele_not_broadcast(self):
        s=next(x for x in SPECS if x['category']=='BA');d=ROOT/'converters'/s['id'];m=runpy.run_path(str(d/'converter.py'));t=(d/'input-X.tsv').read_text()
        with self.assertRaises(ValueError):m['convert'](t.replace('HLA-A*02:01','"HLA-A*02:01,HLA-B*07:02"'),s,set())
    def test_immuneapp_multiple_sample_groups_fail(self):
        s=next(x for x in SPECS if x['family']=='ImmuneApp');d=ROOT/'converters'/s['id'];m=runpy.run_path(str(d/'converter.py'));t=(d/'input-X.tsv').read_text();t=t.replace('synthetic-group','different',1)
        with self.assertRaises(ValueError):m['convert'](t,s,set())

if __name__=='__main__':unittest.main()
