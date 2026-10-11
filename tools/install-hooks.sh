#!/usr/bin/env bash
# Zet het vangnet tegen privégegevens aan in deze kopie van de repo:
#
#   tools/install-hooks.sh
#
# Daarna controleert git elke commit (inhoud, bestandsnamen en het commitbericht) tegen
# ~/.studio-sedillo/blocklist.txt en weigert de commit bij een treffer. De lijst staat
# buiten alle repo's; bestaat hij nog niet, dan maakt dit script hem aan met een
# voorbeeldregel. Hooks zitten in .git en gaan niet mee met een push of een clone:
# draai dit dus één keer per kopie van de repo. Uitleg: tools/no-private-data.py.
set -euo pipefail

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
HOOKS="$(git -C "$ROOT" rev-parse --absolute-git-dir)/hooks"
LIST="$HOME/.studio-sedillo/blocklist.txt"
MARK="# studio-sedillo: no-private-data"

if [ ! -f "$LIST" ]; then
  mkdir -p "$(dirname "$LIST")"
  chmod 700 "$(dirname "$LIST")"
  cat > "$LIST" <<'EOF'
# Privégegevens die nooit in een repo of online mogen komen.
# Eén patroon per regel. Hoofdletters en spaties maken niet uit:
# "1234 AB" vindt ook "1234ab". Regels die met # beginnen tellen niet.
# Zet hier je straatnaam (zonder huisnummer is genoeg) en je postcode.
# Dit bestand staat buiten alle repo's. Deel het met niemand.
Voorbeeldstraat
EOF
  chmod 600 "$LIST"
  echo "Lijst aangemaakt: $LIST (vul je eigen straatnaam en postcode in)."
fi

mkdir -p "$HOOKS"
# Een kopie in .git/hooks, zodat de controle ook werkt op een branch waar tools/ nog niet bestaat.
cp "$ROOT/tools/no-private-data.py" "$HOOKS/no-private-data.py"

install_hook() {   # naam, argumenten
  local file="$HOOKS/$1"
  if [ -f "$file" ] && ! grep -q "$MARK" "$file"; then
    echo "Er staat al een andere $1-hook; die laat ik staan. Voeg deze regel er zelf aan toe:"
    echo "  python3 \"$HOOKS/no-private-data.py\" $2 || exit 1"
    return
  fi
  printf '#!/bin/sh\n%s\nexec python3 "%s/no-private-data.py" %s\n' "$MARK" "$HOOKS" "$2" > "$file"
  chmod +x "$file"
  echo "Hook gezet: $1"
}
install_hook pre-commit '--staged'
install_hook commit-msg '--message "$1"'
