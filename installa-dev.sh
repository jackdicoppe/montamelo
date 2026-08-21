#!/usr/bin/env bash
#
# Installa helper e policy polkit nelle posizioni di sistema.
# Da usare SOLO nella macchina virtuale di prova, finche' non c'e' l'RPM.
#
#   ./installa-dev.sh            installa
#   ./installa-dev.sh --rimuovi  disinstalla
#
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER=/usr/libexec/montamelo/montamelo-helper
POLICY=/usr/share/polkit-1/actions/io.github.jackdicoppe.Montamelo.policy

if [[ "${1:-}" == "--rimuovi" ]]; then
    sudo rm -f "$HELPER" "$POLICY"
    sudo rmdir --ignore-fail-on-non-empty /usr/libexec/montamelo
    echo "Rimossi helper e policy."
    exit 0
fi

# L'helper deve appartenere a root: pkexec lo esegue con i privilegi massimi,
# quindi un file scrivibile dall'utente sarebbe un buco di sicurezza.
sudo install -D -o root -g root -m 0755 "$DIR/montamelo-helper" "$HELPER"
sudo install -D -o root -g root -m 0644 \
    "$DIR/data/io.github.jackdicoppe.Montamelo.policy" "$POLICY"

echo "Installati:"
echo "  $HELPER"
echo "  $POLICY"
echo
echo "Ora lancia l'interfaccia con:  python3 $DIR/main.py"
