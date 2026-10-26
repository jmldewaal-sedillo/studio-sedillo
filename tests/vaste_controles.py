#!/usr/bin/env python3
"""Vaste controles van de hoofdsite (Apps/CLAUDE.md, sectie 11.7a), naast tests/pages.py.

  python3 tests/vaste_controles.py

Controleert op index, over, privacy, credits en de 404-pagina:
  - toegankelijkheid volgens WCAG 2.1 AA met axe-core, in het Engels en het Nederlands;
  - een strenge Content-Security-Policy, geen inline scripts of style-attributen;
  - de pagina's zijn ook zonder JavaScript leesbaar (de Engelse tekst staat in de HTML);
  - de taal wordt pas onthouden na een klik op EN of NL;
  - een skiplink naar de inhoud, en de 404-pagina met footer en werkende links.
De map sudoku-kids/ komt uit de app zelf en wordt getest in tests/pages.py.

axe-core komt uit Apps/studio-sedillo-app-template/node_modules (npm install daar), of uit $AXE.
"""
import functools
import http.server
import os
import pathlib
import re
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ('index.html', 'over.html', 'privacy.html', 'credits.html', '404.html')
AXE = pathlib.Path(os.environ.get('AXE', ROOT.parent / 'studio-sedillo-app-template' / 'node_modules' / 'axe-core' / 'axe.min.js'))
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
    """Zoals GitHub Pages: /privacy levert privacy.html, en wat niet bestaat krijgt 404.html."""
    def log_message(self, *args):
        pass

    def translate_path(self, path):
        found = super().translate_path(path)
        clean = found.split('?')[0]
        if not pathlib.Path(clean).exists() and pathlib.Path(clean + '.html').is_file():
            return clean + '.html'
        return found

    def send_error(self, code, message=None, explain=None):
        if code != 404:
            return super().send_error(code, message, explain)
        body = (ROOT / '404.html').read_bytes()
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    print('Bron: CSP, geen inline scripts of stijlen')
    for name in PAGES:
        html = (ROOT / name).read_text()
        csp = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', html)
        check(f'{name}: strenge CSP en referrer, geen inline script of style-attribuut',
              bool(csp) and "default-src 'self'" in csp.group(1) and 'unsafe' not in csp.group(1)
              and '<meta name="referrer"' in html and not re.search(r'<script>|<script(?![^>]*\ssrc=)[^>]*>', html)
              and not re.search(r'\sstyle="|\son[a-z]+="', html), csp.group(1) if csp else 'geen CSP')

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    with sync_playwright() as p:
        browser = p.chromium.launch()

        print('Toegankelijkheid (axe-core, WCAG 2.1 AA)')
        if not AXE.is_file():
            check('axe-core gevonden', False, f'{AXE} ontbreekt: npm install in studio-sedillo-app-template, of zet $AXE')
        else:
            # Alleen voor het injecteren van axe: in deze browser telt de CSP van de pagina niet.
            ctx = browser.new_context(viewport={'width': 360, 'height': 740}, bypass_csp=True)
            page = ctx.new_page()
            for lang in ('en', 'nl'):
                for name in ('', 'over', 'privacy', 'credits', 'bestaat-niet'):
                    page.goto(f'{url}{name}?lang={lang}')
                    page.add_script_tag(path=str(AXE))
                    found = page.evaluate('''async () => (await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] }))
                        .violations.map(v => v.id + ': ' + v.nodes.map(n => n.target.join(' ')).slice(0, 3).join(', '))''')
                    check(f'/{name or ""} ({lang}): geen toegankelijkheidsproblemen', not found, found)
            # Bewijs dat de controle iets vindt.
            page.goto(url)
            page.evaluate('''() => { const b = document.createElement('button'); document.querySelector('main').append(b);
                                     const p = document.createElement('p'); p.textContent = 'grijs'; p.style.color = '#ddd'; document.querySelector('main').append(p); }''')
            page.add_script_tag(path=str(AXE))
            ids = page.evaluate("async () => (await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa'] })).violations.map(v => v.id)")
            check('de controle werkt echt: knop zonder naam en te weinig contrast gevonden', 'button-name' in ids and 'color-contrast' in ids, ids)
            ctx.close()

        print('Zonder JavaScript')
        ctx = browser.new_context(viewport={'width': 360, 'height': 740}, java_script_enabled=False)
        page = ctx.new_page()
        for name in ('', 'over', 'privacy', 'credits'):
            page.goto(url + name)
            empty = page.evaluate('[...document.querySelectorAll("[data-en]")].filter(e => !e.textContent.trim()).map(e => e.tagName + ": " + e.dataset.en.slice(0, 40))')
            check(f'/{name}: elke tekst staat in de HTML (niets leeg zonder JavaScript)', not empty, empty)
        page.goto(url + 'privacy')
        text = page.evaluate('document.querySelector("main").textContent')
        check('privacyverklaring zonder JavaScript: verantwoordelijke, grondslag van serverlogs en e-mail, rechten',
              'KvK 42122276' in text and text.count('Article 6(1)(f)') == 2 and 'Autoriteit Persoonsgegevens' in text, text[:200])
        ctx.close()

        print('Taal, skiplink en 404')
        ctx = browser.new_context(viewport={'width': 360, 'height': 740})
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        # De 404-pagina zelf geeft status 404 (Chrome meldt dat in de console); wel fout: een ontbrekend bestand.
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and '404 (Not Found)' not in m.text else None)
        page.on('response', lambda r: errors.append(f'{r.status} {r.url}') if r.status >= 400 and r.request.resource_type != 'document' else None)
        page.goto(url + '?lang=nl')
        check('?lang=nl toont Nederlands maar slaat niets op', page.evaluate('document.documentElement.lang') == 'nl' and page.evaluate('localStorage.length') == 0)
        page.click('.langs button[data-lang="en"]')
        check('na een klik op EN wordt de keuze onthouden', page.evaluate('localStorage.getItem("studioSedillo_lang")') == 'en')
        page.goto(url + 'over')
        check('de keuze geldt ook op de volgende pagina', page.evaluate('document.documentElement.lang') == 'en')
        page.keyboard.press('Tab')
        check('eerste Tab: skiplink naar de inhoud', page.evaluate('document.activeElement.className') == 'skip' and page.evaluate('document.activeElement.getAttribute("href")') == '#main')
        page.goto(url + 'bestaat/niet/hier')
        links = page.evaluate('[...document.querySelectorAll(".foot-links a")].map(a => a.getAttribute("href"))')
        check('404 (ook diep in een map): opmaak geladen, footer met KvK en links naar alle pagina\'s',
              page.evaluate('getComputedStyle(document.body).backgroundColor') == 'rgb(251, 248, 244)'
              and 'KvK 42122276' in page.evaluate('document.querySelector("footer").textContent')
              and links == ['/', '/over', '/privacy', '/credits'], links)
        page.click('.foot-links a[href="/privacy"]')
        check('vanaf de 404-pagina werkt een link', page.evaluate('document.querySelector("h1").textContent') == 'Privacy policy')
        check('geen fouten in de console (ook geen CSP-meldingen)', not errors, errors)
        ctx.close()
        browser.close()
    server.shutdown()
    print(f'\n{"✅" if not failed else "❌"} {passed}/{passed + failed} controles geslaagd.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
