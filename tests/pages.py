#!/usr/bin/env python3
"""Test van de hoofdsite: startpagina, privacyverklaring en de pagina's van Sudoku Kids.

  python3 tests/pages.py

Start zelf een webserver op de map van de repo en bekijkt de pagina's in een echte browser
(Playwright). Controleert: geen fouten, geen verzoeken naar buiten, bedrijfsregel in de
footer, geen links naar een app-website of github.io, en voor de pagina's van Sudoku Kids
dezelfde opbouw in vijf talen met de verplichte onderdelen.
"""
import functools
import http.server
import json
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAIL = 'studio.sedillo@gmail.com'
LANGS = ('en', 'nl', 'es', 'pt', 'id')
GITHUB = 'https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement'
GOOGLE = 'https://policies.google.com/privacy'
passed = failed = 0


def check(name, ok, detail=''):
    global passed, failed
    if ok:
        passed += 1
        print(f'  ✅ {name}')
    else:
        failed += 1
        print(f'  ❌ {name}  {detail}')


class Handler(http.server.SimpleHTTPRequestHandler):
    """Zoals GitHub Pages: /privacy levert privacy.html."""
    def log_message(self, *args):
        pass

    def translate_path(self, path):
        found = super().translate_path(path)
        clean = found.split('?')[0]
        if not pathlib.Path(clean).exists() and pathlib.Path(clean + '.html').is_file():
            return clean + '.html'
        return found


def main():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 360, 'height': 740})
        errors, outside = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.on('request', lambda r: outside.append(r.url) if not r.url.startswith(url) else None)
        js = page.evaluate

        print('Hoofdsite')
        for lang, soon in (('en', 'Coming soon'), ('nl', 'Binnenkort')):
            page.goto(url + '?lang=' + lang)
            hrefs = js('[...document.querySelectorAll("a")].map(a => a.getAttribute("href"))')
            check(f'startpagina ({lang}): spellen staan er als "{soon}", zonder links naar een app-website of github.io',
                  js('[...document.querySelectorAll(".app .tag")].map(t => t.textContent)') == [soon, soon] and
                  js('document.querySelectorAll(".app a").length') == 0 and
                  not [h for h in hrefs if 'github.io' in h or 'studiosedillo.com' in h], hrefs)
            check(f'startpagina ({lang}): contact en footer met KvK-nummer, land en e-mailadres',
                  MAIL in js('document.querySelector("main").textContent') and
                  js('document.querySelector("footer").textContent').strip().startswith('© 2026 Studio Sedillo · KvK 42122276 · '))
        for lang, word in (('en', 'Responsible for your data: Studio Sedillo (sole proprietorship), KvK 42122276'), ('nl', 'Verantwoordelijke: Studio Sedillo (eenmanszaak), KvK 42122276, Nederland')):
            page.goto(url + 'privacy?lang=' + lang)
            text = js('document.querySelector("main").textContent')
            check(f'privacyverklaring van de site ({lang}): verantwoordelijke, Gmail, grondslag, Data Privacy Framework, links naar de pagina\'s van Sudoku Kids',
                  word in text and 'Gmail' in text and 'Data Privacy Framework' in text and '6' in text and
                  js('[...document.querySelectorAll("main a")].map(a => a.getAttribute("href")).filter(h => h.startsWith("sudoku-kids/")).join()') == 'sudoku-kids/privacy,sudoku-kids/delete')
        for lang, facts in (('en', ['Studio Sedillo', 'Sole proprietorship (eenmanszaak)', '42122276', 'the Netherlands', MAIL]),
                            ('nl', ['Studio Sedillo', 'Eenmanszaak', '42122276', 'Nederland', MAIL])):
            page.goto(url + 'over?lang=' + lang)
            check(f'/over ({lang}): bedrijfsgegevens (naam, rechtsvorm, KvK, land, e-mail), past op een telefoon',
                  js('[...document.querySelectorAll(".facts dd")].map(d => d.textContent)') == facts and
                  js('document.documentElement.scrollWidth <= innerWidth'), js('[...document.querySelectorAll(".facts dd")].map(d => d.textContent)'))
            page.goto(url + 'credits?lang=' + lang)
            check(f'/credits ({lang}): site, spellen en auteursrecht',
                  js('document.querySelectorAll("main h2").length') == 3 and 'Studio Sedillo' in js('document.querySelector("main").textContent'))
        for name in ('', 'over', 'privacy', 'credits'):
            page.goto(url + name)
            links = js('[...document.querySelectorAll(".foot-links a")].map(a => a.getAttribute("href"))')
            want = {'./', 'over', 'privacy', 'credits'} - {name or './'}
            check(f'footer van /{name}: links naar de andere pagina\'s ({", ".join(sorted(want))})', set(links) == want, links)

        print('Sudoku Kids: privacy en gegevens verwijderen')
        for name, sections, title in (('privacy', 12, 'Privacyverklaring'), ('delete', 5, 'Gegevens verwijderen')):
            page.goto(url + 'sudoku-kids/' + name + '?lang=nl')
            check(f'/sudoku-kids/{name} (zonder .html, zoals op GitHub Pages) opent in de gevraagde taal',
                  js('document.querySelector("#policy h1").textContent') == title and js('document.documentElement.lang') == 'nl')
            shape = {}
            for code in LANGS:
                page.click(f'#langs button[data-lang="{code}"]')
                foot = js('document.getElementById("company").textContent')
                shape[code] = [js('document.querySelectorAll("#policy h2").length'), js('document.querySelectorAll("#policy li").length'),
                               js(f'document.querySelectorAll(\'#policy a[href="mailto:{MAIL}"]\').length') >= 1,
                               'Studio Sedillo' in js('document.getElementById("policy").textContent'),
                               foot.startswith('© 2026 Studio Sedillo · KvK 42122276 · ') and foot.endswith(' · ' + MAIL),
                               js('document.querySelector(\'#langs button[aria-pressed="true"]\').dataset.lang') == code,
                               js('document.documentElement.scrollWidth <= innerWidth')]
            check(f'{name} in 5 talen: zelfde opbouw ({sections} onderdelen), contactadres, footer met KvK-nummer en land, past op een telefoon',
                  len({json.dumps(v) for v in shape.values()}) == 1 and shape['en'][0] == sections and all(shape['en'][2:]), shape)
        page.goto(url + 'sudoku-kids/privacy')
        legal = {}
        for code in LANGS:
            page.click(f'#langs button[data-lang="{code}"]')
            text = js('document.getElementById("policy").textContent')
            legal[code] = ['Studio Sedillo (' in text and 'KvK 42122276' in text, 'Gmail' in text and 'Google Play' in text, 'Data Privacy Framework' in text,
                           '6' in text and any(w in text for w in ('GDPR', 'AVG', 'RGPD')),
                           js('[...document.querySelectorAll("#policy a")].map(a => a.getAttribute("href")).filter(h => /^https:/.test(h)).sort().join()'),
                           js('document.querySelector("#policy a[href^=\\"delete?lang=\\"]") !== null'), '11' in js('document.querySelector(".updated").textContent') and '2026' in js('document.querySelector(".updated").textContent')]
        check('privacyverklaring Sudoku Kids in 5 talen: verantwoordelijke met KvK-nummer, Gmail, Google Play, Data Privacy Framework, grondslag, links naar GitHub en Google, link naar de verwijderpagina, datum',
              all(v == [True, True, True, True, f'{GITHUB},{GOOGLE},{GOOGLE}', True, True] for v in legal.values()), legal)
        page.goto(url + 'sudoku-kids/privacy?lang=nl')
        heads = js('[...document.querySelectorAll("#policy h2")].map(h => h.textContent)')
        check('verplichte onderdelen in de Nederlandse verklaring',
              heads == ['Wie is verantwoordelijk', 'In het kort', 'Wat er wordt bewaard, en waar', 'Wat de app niet doet', 'Delen met anderen', 'Als je ons mailt',
                        'Gegevens buiten de EU', 'Hoe lang gegevens bewaard blijven', 'Hoe je gegevens verwijdert', 'Je rechten (AVG)', 'Kinderen en ouders', 'Wijzigingen'], heads)
        page.click('#policy a[href^="delete"]')
        page.wait_for_url('**/sudoku-kids/delete?lang=nl')
        check('de link naar de verwijderpagina houdt de taal vast', js('document.querySelector("#policy h1").textContent') == 'Gegevens verwijderen')
        page.click('#other')
        page.wait_for_url('**/sudoku-kids/privacy?lang=nl')
        check('en de link in de footer gaat terug naar de privacyverklaring', js('document.querySelector("#policy h1").textContent') == 'Privacyverklaring')
        adres = [f.name for f in (ROOT / 'sudoku-kids').glob('*.html') if 'github.io' in f.read_text() or 'sudokukids.studiosedillo' in f.read_text()]
        check('geen verwijzing naar github.io of een app-subdomein in de pagina\'s', not adres, adres)
        check('geen fouten in de console', not errors, errors)
        check('geen enkel verzoek naar een ander adres', not outside, outside)
        browser.close()
    server.shutdown()
    print(f'\n{"✅" if not failed else "❌"} {passed}/{passed + failed} controles geslaagd.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
