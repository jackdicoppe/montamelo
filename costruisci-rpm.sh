#!/usr/bin/env bash
#
# Costruisce il pacchetto RPM a partire dalla cartella di lavoro.
#
#   ./costruisci-rpm.sh
#
# Alla fine stampa il percorso del pacchetto pronto da installare con dnf.
#
set -euo pipefail

NOME=montamelo
VERSIONE=$(grep -m1 '^Version:' "$NOME.spec" | awk '{print $2}')
DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD="$HOME/rpmbuild"

echo "Costruzione di $NOME $VERSIONE"

# La prima volta servono gli strumenti di packaging
for pacchetto in rpm-build rpmdevtools desktop-file-utils libappstream-glib; do
    rpm -q "$pacchetto" >/dev/null 2>&1 || {
        echo "Manca $pacchetto, lo installo"
        sudo dnf install -y "$pacchetto"
    }
done

rpmdev-setuptree

# Il sorgente viene impacchettato come se fosse scaricato da GitHub
STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT
mkdir -p "$STAGING/$NOME-$VERSIONE"
tar -c --exclude-vcs --exclude=__pycache__ --exclude='*.pyc' -C "$DIR" . \
    | tar -x -C "$STAGING/$NOME-$VERSIONE"
tar -czf "$BUILD/SOURCES/$NOME-$VERSIONE.tar.gz" -C "$STAGING" "$NOME-$VERSIONE"

cp "$DIR/$NOME.spec" "$BUILD/SPECS/"
rpmbuild -ba "$BUILD/SPECS/$NOME.spec"

PACCHETTO=$(find "$BUILD/RPMS" -name "$NOME-$VERSIONE-*.rpm" | head -n1)
echo
echo "Pacchetto pronto: $PACCHETTO"
echo "Installalo con:   sudo dnf install $PACCHETTO"
