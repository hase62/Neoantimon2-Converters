"""Data-only expansion hygiene. Never import or execute converter scripts."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from build_index import build,validate_expected
from prepare_pages import prepare

class ExpansionMetadataTests(unittest.TestCase):
    def test_nine_distinct_new_identities_eight_families(self):
        specs=json.loads((ROOT/'tools/converter_specs.json').read_text())
        self.assertEqual(len(specs),9);self.assertEqual(len({x['id'] for x in specs}),9);self.assertEqual(len({x['family'] for x in specs}),8)
        self.assertEqual({x['category'] for x in specs},{'BA','EL','IM'})
    def test_every_fixture_and_metadata_are_explicit_and_checksum_pinned(self):
        research=json.loads((ROOT/'UPSTREAM-RESEARCH.json').read_text())
        for x in research['candidates']:
            if x['feasibility']!='IMPLEMENTED':continue
            d=ROOT/'converters'/x['converter_id'];m=json.loads((d/'metadata.json').read_text())
            self.assertEqual(m['sha256'],hashlib.sha256((d/'converter.py').read_bytes()).hexdigest())
            self.assertEqual(x['fixture_provenance'],'SCHEMA_FAITHFUL_SYNTHETIC_FIXTURE');self.assertFalse(x['fixtures_executed_predictor']);self.assertEqual(x['model_version'],'')
            self.assertEqual(x['input_sha256'],hashlib.sha256((d/'input-X.tsv').read_bytes()).hexdigest());self.assertEqual(x['expected_sha256'],hashlib.sha256((d/'expected.tsv').read_bytes()).hexdigest())
            self.assertIn('SCHEMA_FAITHFUL_SYNTHETIC_FIXTURE',(d/'README.md').read_text());self.assertTrue((d/'LICENSE.txt').is_file());self.assertTrue((d/'NOTICE.txt').is_file());validate_expected(d/'expected.tsv')
    def test_pages_includes_only_explicit_new_static_guides(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)/'registry';shutil.copytree(ROOT,base,ignore=shutil.ignore_patterns('.git','__pycache__'))
            out=prepare(base,Path(t)/'site')
            for f in ('CATALOG.md','EXTERNAL-QUICKSTART.md','UPSTREAM-RESEARCH.json'):self.assertEqual((out/f).read_bytes(),(ROOT/f).read_bytes())
            self.assertFalse((out/'tools').exists());self.assertFalse((out/'tests').exists())
    def test_new_static_guide_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)/'registry';shutil.copytree(ROOT,base,ignore=shutil.ignore_patterns('.git','__pycache__'))
            (base/'CATALOG.md').unlink();(base/'CATALOG.md').symlink_to(ROOT/'CATALOG.md')
            with self.assertRaisesRegex(ValueError,'unsafe'):prepare(base,Path(t)/'site')
    def test_index_rebuild_is_deterministic_existing_registration_retained(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)/'registry';shutil.copytree(ROOT,base,ignore=shutil.ignore_patterns('.git','__pycache__'))
            a=build(base);first=(base/'index.json').read_bytes();b=build(base)
            self.assertEqual(a,b);self.assertEqual(first,(base/'index.json').read_bytes());self.assertEqual(len(a),10)
            old=next(x for x in a if x['id']=='synthetic-example@1.0.0');self.assertEqual(old['sha256'],'ff2f3c4351df4bc6cfd91719a64edc2adf300f26425cbc19e0c66d20b5a5d8fb')
    def test_ci_remains_data_only_no_new_execution_discovery(self):
        text=(ROOT/'.github/workflows/validate.yml').read_text()
        self.assertIn('trusted/build_index.py',text);self.assertNotIn('converter_checks.py',text)
        pages=(ROOT/'.github/workflows/pages.yml').read_text();self.assertIn('python3 -m unittest discover -s tests -v',pages)
        self.assertFalse((ROOT/'tests/test_converters.py').exists())

if __name__=='__main__':unittest.main()
