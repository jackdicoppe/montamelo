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

# Servono gli strumenti di packaging
for pacchetto in rpm-build rpmdevtools; do
    rpm -q "$pacchetto" >/dev/null 2>&1 || {
        echo "Manca $pacchetto, lo installo"
        sudo dnf install -y "$pacchetto"
    }
done

# Le dipendenze di build vengono lette dallo spec, cosi' non possono
# andare fuori sincrono con quanto dichiarato in BuildRequires
DIPENDENZE=$(rpmspec -q --buildrequires "$DIR/$NOME.spec" | awk '{print $1}')
if [[ -n "$DIPENDENZE" ]]; then
    echo "Dipendenze di build: $(echo "$DIPENDENZE" | tr '\n' ' ')"
    # shellcheck disable=SC2086
    sudo dnf install -y $DIPENDENZE
fi

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
if [[ -z "$PACCHETTO" ]]; then
    echo "Build fallita: nessun pacchetto prodotto." >&2
    exit 1
fi

echo
echo "Pacchetto pronto: $PACCHETTO"
echo "Installalo con:   sudo dnf install $PACCHETTO"
