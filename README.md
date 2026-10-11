# Studio Sedillo – hoofdsite

De website van Studio Sedillo: de spellen, contact en de algemene privacyverklaring.
Vanilla HTML/CSS/JS, geen build-stap, geen externe bestanden, geen cookies.

| | |
|---|---|
| Live | https://studiosedillo.com (na het instellen van DNS; tot dan https://jmldewaal-sedillo.github.io/studio-sedillo/) |
| Hosting | GitHub Pages vanaf `main` |
| Talen | Engels en Nederlands (`data-en` / `data-nl` op elk element, wissel in `site.js`) |

## Bestanden

| Bestand | Wat |
|---|---|
| `index.html` | Spellen en contact |
| `privacy.html` | Algemene privacyverklaring (bereikbaar als `/privacy`) |
| `404.html` | Pagina niet gevonden |
| `style.css`, `site.js`, `logo.svg` | Opmaak, taalwissel, logo |
| `apps/` | Een icoon per spel |
| `CNAME` | Het eigen domein. Wordt pas toegevoegd als DNS klaar is, anders stuurt GitHub bezoekers naar een adres dat nog niet bestaat |

## Een spel toevoegen

Kopieer een `<article class="app">` in `index.html`, zet het icoon in `apps/`, en voeg het
spel toe aan de lijst in `privacy.html`. De volledige werkwijze voor een nieuwe app
(subdomein, DNS, repo, testversie, assetlinks) staat in de Sudoku-repo:
`docs/studio-sedillo.md`.

## Privégegevens (adres) buiten de site houden

Het adres van Studio Sedillo staat nergens op deze site en hoort ook nooit in deze repo.
`tools/install-hooks.sh` zet een pre-commit hook aan die elke commit controleert tegen
`~/.studio-sedillo/blocklist.txt` (buiten de repo). `python3 tests/no-private-data.py`
controleert alle bestanden; met `--online` ook de gepubliceerde pagina's. Uitleg:
`docs/bedrijf.md` in de repo `sudoku-kids`.
