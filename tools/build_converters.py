"""Embed the reviewed runtime/spec into standalone scripts (core stages one file).
Default checks reproducibility. --write-new never overwrites an existing script.
Accepted version directories are immutable: use a new ID for later changes.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def expected(spec):
    return ('# Generated standalone adapter; see tools/build_converters.py and local README.\n'
            '# Independently authored; PolyForm Noncommercial 1.0.0; see LICENSE.txt/NOTICE.\n' +
            (ROOT / 'tools/converter_runtime.py').read_text() + '\nSPEC = ' + repr(spec) +
            "\n\nif __name__ == '__main__':\n    try:\n        main(SPEC)\n    except (ValueError, OSError, KeyError, csv.Error, json.JSONDecodeError) as error:\n        raise SystemExit('Conversion failed: ' + str(error))\n")

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-new',action='store_true');a=p.parse_args()
    for s in json.loads((ROOT/'tools/converter_specs.json').read_text()):
        target=ROOT/'converters'/s['id']/'converter.py';text=expected(s)
        if target.exists():
            if target.read_text()!=text:raise SystemExit('Source drift; create a new version: '+s['id'])
        elif a.write_new:
            target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
        else:raise SystemExit('Missing generated script: '+str(target))
    print('Standalone converter sources are reproducible')
