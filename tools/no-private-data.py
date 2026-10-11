#!/usr/bin/env python3
"""Vangnet: privégegevens (zoals een huisadres) mogen nooit in een repo of online komen.

De patronen staan NIET in een repo maar in ~/.studio-sedillo/blocklist.txt: één patroon
per regel, lege regels en regels die met # beginnen tellen niet. Vergelijken gaat zonder
op hoofdletters en spaties te letten ("1234 AB" vindt ook "1234ab"). In GitHub Actions
komt dezelfde lijst uit het geheim PRIVATE_BLOCKLIST.

  tools/no-private-data.py              alle bestanden van de repo (de standaard)
  tools/no-private-data.py --staged     alleen wat klaarstaat voor een commit (pre-commit hook)
  tools/no-private-data.py --message F  de tekst van een commitbericht (commit-msg hook)
  tools/no-private-data.py --history    de hele git-geschiedenis, alle branches
  tools/no-private-data.py --online URL de gepubliceerde pagina's op dat adres
  tools/no-private-data.py --dir MAP    alle bestanden in een map (ook buiten git)
  tools/no-private-data.py --selftest   bewijst dat een treffer echt gevonden wordt
  --ci                                  zonder lijst: waarschuwing voor GitHub Actions

Bij een treffer: exitcode 1, met bestand en regelnummer. Het patroon zelf wordt nooit
getoond (alleen het regelnummer in de lijst), zodat het ook niet in een log belandt.
Zonder lijst: waarschuwing en exitcode 0. Dit bestand staat gelijk in de Sudoku-repo en
in studio-sedillo; pas ze samen aan.
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.request

LIST = pathlib.Path(os.environ.get('STUDIO_SEDILLO_BLOCKLIST', '~/.studio-sedillo/blocklist.txt')).expanduser()
EXAMPLE = 'voorbeeldstraat'          # de voorbeeldregel uit het nieuwe bestand telt niet mee
MIN_LENGTH = 4                       # korter geeft overal valse treffers
SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}


def squash(text):
    return re.sub(r'\s+', '', text).lower()


def patterns():
    """[(regelnummer in de lijst, patroon zonder spaties in kleine letters)], en waar de lijst vandaan komt."""
    if os.environ.get('PRIVATE_BLOCKLIST', '').strip():
        raw, source = os.environ['PRIVATE_BLOCKLIST'], 'het geheim PRIVATE_BLOCKLIST'
    elif LIST.is_file():
        raw, source = LIST.read_text(errors='ignore'), str(LIST)
    else:
        return [], None
    found = []
    for number, line in enumerate(raw.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if len(squash(line)) < MIN_LENGTH:
            print(f'  let op: regel {number} van de lijst is korter dan {MIN_LENGTH} tekens en wordt overgeslagen')
            continue
        if EXAMPLE in squash(line):
            continue                 # de voorbeeldregel is geen echt patroon
        found.append((number, squash(line)))
    return found, source


def hits_in(text, pats):
    """[(regelnummer in de tekst, regelnummer in de lijst)]"""
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        flat = squash(line)
        out += [(number, n) for n, p in pats if p in flat]
    return out


def git(*args):
    return subprocess.run(['git', *args], capture_output=True, check=True).stdout


def report(where, found):
    for line, pattern in found:
        print(f'  TREFFER  {where}:{line}  (patroon op regel {pattern} van de lijst)')
    return len(found)


def check_tree(pats, folder=None):
    total = 0
    if folder is None:
        names = [n for n in git('ls-files', '-z').decode().split('\0') if n]
        names += [n for n in git('ls-files', '-z', '--others', '--exclude-standard').decode().split('\0') if n]
        paths = [pathlib.Path(n) for n in names]
    else:
        paths = [p for p in pathlib.Path(folder).rglob('*') if p.is_file() and not SKIP_DIRS & set(p.parts)]
    for path in paths:
        if not path.is_file():
            continue
        total += report(str(path) + ' (bestandsnaam)', [(0, n) for _, n in hits_in(str(path), pats)])
        total += report(str(path), hits_in(path.read_bytes().decode('utf-8', 'ignore'), pats))
    print(f'  {len(paths)} bestanden bekeken')
    return total


def check_staged(pats):
    total = 0
    names = [n for n in git('diff', '--cached', '--name-only', '-z', '--diff-filter=ACMR').decode().split('\0') if n]
    for name in names:
        total += report(name + ' (bestandsnaam)', [(0, n) for _, n in hits_in(name, pats)])
        total += report(name, hits_in(git('show', ':' + name).decode('utf-8', 'ignore'), pats))
    return total


def check_history(pats):
    """Elke toegevoegde of verwijderde regel in elke commit van elke branch, plus de commitberichten."""
    total, commit, name, seen = 0, '?', '?', set()
    log = subprocess.Popen(['git', 'log', '--all', '-p', '--no-color', '--format=%x01%h %ad %s', '--date=short'],
                           stdout=subprocess.PIPE)
    commits = 0
    for raw in log.stdout:
        line = raw.decode('utf-8', 'ignore').rstrip('\n')
        if line.startswith('\x01'):
            commit, name, commits = line[1:], '(commitbericht)', commits + 1
        elif line.startswith('+++ b/') or line.startswith('--- a/'):
            name = line[6:]
            continue
        elif not (line.startswith('+') or line.startswith('-')):
            continue
        flat = squash(line)
        for n, p in pats:
            if p in flat and (commit, name, n) not in seen:
                seen.add((commit, name, n))
                print(f'  TREFFER  commit {commit[:60]}  bestand {name}  (patroon op regel {n} van de lijst)')
                total += 1
    log.wait()
    print(f'  {commits} commits bekeken (alle branches)')
    return total


def check_online(pats, base):
    base = base.rstrip('/') + '/'
    pages = ['', 'privacy.html', 'delete.html', 'verwijderen.html', 'privacy', 'delete', '404.html', 'manifest.json']
    sw = pathlib.Path('sw.js')
    if sw.is_file():
        pages += [a[2:] for a in re.findall(r"'(\./[^']+)'", sw.read_text()) if a != './']
    total, seen = 0, 0
    for page in dict.fromkeys(pages):
        if re.search(r'\.(png|jpg|svg|ico|mp3|woff2?)$', page):
            continue
        try:
            with urllib.request.urlopen(base + page, timeout=20) as answer:
                text = answer.read().decode('utf-8', 'ignore')
        except Exception:
            continue                 # de pagina bestaat (nog) niet op dit adres
        seen += 1
        total += report(base + page, hits_in(text, pats))
    print(f'  {seen} pagina\'s opgehaald van {base}')
    return total


def selftest():
    """Een verzonnen patroon moet gevonden worden, ook met andere hoofdletters en spaties; schone tekst niet."""
    pats = [(1, squash('Kanariestraat 12')), (2, squash('9999 ZZ'))]
    with tempfile.TemporaryDirectory() as folder:
        (pathlib.Path(folder) / 'schoon.html').write_text('<p>Studio Sedillo, Nederland</p>')
        clean = check_tree(pats, folder)
        (pathlib.Path(folder) / 'lek.html').write_text('<p>Bezoek ons:\n  kanarieSTRAAT   12, 9999zz Ergens</p>')
        dirty = check_tree(pats, folder)
    ok = clean == 0 and dirty == 2
    print('✅ zelftest: een treffer wordt gevonden, schone tekst niet' if ok else f'❌ zelftest mislukt ({clean}, {dirty})')
    return 0 if ok else 1


def main(argv):
    if '--selftest' in argv:
        return selftest()
    pats, source = patterns()
    if not pats:
        why = f'{LIST} bestaat niet' if source is None else f'{source} bevat nog geen eigen patronen (alleen de voorbeeldregel of niets)'
        if '--ci' in argv:
            print(f'::warning::Controle op privégegevens overgeslagen: het geheim PRIVATE_BLOCKLIST ontbreekt ({why}).')
        else:
            print(f'⚠️  Controle op privégegevens overgeslagen: {why}.')
        return 0
    if '--staged' in argv:
        total, what = check_staged(pats), 'deze commit'
    elif '--message' in argv:
        name = argv[argv.index('--message') + 1]
        total, what = report('commitbericht', hits_in(pathlib.Path(name).read_text(errors='ignore'), pats)), 'het commitbericht'
    elif '--history' in argv:
        total, what = check_history(pats), 'de git-geschiedenis'
    elif '--online' in argv:
        total, what = check_online(pats, argv[argv.index('--online') + 1]), 'de gepubliceerde pagina\'s'
    elif '--dir' in argv:
        total, what = check_tree(pats, argv[argv.index('--dir') + 1]), 'de map'
    else:
        total, what = check_tree(pats), 'de bestanden van de repo'
    if total:
        print(f'❌ {total} treffer(s) in {what}: er staat iets in dat op de lijst met privégegevens staat. Haal het weg en probeer opnieuw.')
        return 1
    print(f'✅ Geen privégegevens gevonden in {what} ({len(pats)} patronen uit {source}).')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
