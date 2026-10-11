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
