#!/usr/bin/env python3
"""Test: er staan geen privégegevens (huisadres) in de repo of op de gepubliceerde pagina's.

  python3 tests/no-private-data.py            # zelftest + alle bestanden van de repo
  python3 tests/no-private-data.py --online   # ook de pagina's die nu online staan

Gebruikt ~/.studio-sedillo/blocklist.txt als die bestaat (in GitHub Actions het geheim
PRIVATE_BLOCKLIST). Zonder lijst draait alleen de zelftest en volgt een waarschuwing.
Het echte werk zit in tools/no-private-data.py.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOL = [sys.executable, str(ROOT / 'tools' / 'no-private-data.py')]
ONLINE = ['https://jmldewaal-sedillo.github.io/studio-sedillo/']

runs = [['--selftest'], [] + [a for a in sys.argv[1:] if a == '--ci']]
if '--online' in sys.argv:
    runs += [['--online', url] for url in ONLINE]
failed = 0
for args in runs:
    failed += subprocess.run(TOOL + args, cwd=ROOT).returncode != 0
print('✅ no-private-data: in orde.' if not failed else f'❌ no-private-data: {failed} controle(s) mislukt.')
sys.exit(1 if failed else 0)
