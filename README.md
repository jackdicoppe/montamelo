# Montamelo

*Configurazione guidata delle condivisioni di rete*

Applicazione GTK4 / libadwaita che guida passo passo nella configurazione
di un mount SMB permanente su Fedora: elenca le share pubblicate dal server,
verifica la connessione, genera le unit systemd e salva le credenziali in un
file leggibile solo da root.

A differenza del montaggio da file manager, il risultato è una cartella vera
del sistema: funziona con qualsiasi applicazione, script e backup, comprese
le app Flatpak in sandbox.

## Installazione

```bash
git clone https://github.com/jackdicoppe/montamelo.git
cd montamelo
./costruisci-rpm.sh
sudo dnf install ~/rpmbuild/RPMS/noarch/montamelo-*.rpm
```

Requisiti a runtime (installati automaticamente da dnf): `python3-gobject`,
`gtk4`, `libadwaita`, `polkit`, `samba-client`, `cifs-utils`.

## Sviluppo

```bash
python3 main.py                     # interfaccia, senza installare nulla
./installa-dev.sh                   # helper + policy in posizione, per le prove
./installa-dev.sh --rimuovi
make check                          # verifica sintassi
```

L'helper si collauda senza privilegi scrivendo in una radice alternativa:

```bash
echo '{"server":"nas","share":"dati","mount":"/mnt/dati","utente":"mauro","password":"x"}' \
  | ./montamelo-helper --root /tmp/prova installa
```

## Architettura

| Componente | Ruolo |
|---|---|
| `main.py` | interfaccia GTK4, gira come utente normale |
| `montamelo-helper` | unico pezzo che gira come root, via `pkexec` |
| `data/*.policy` | autorizzazione polkit dell'helper |

I dati, password compresa, passano fra i due processi su stdin in formato
JSON: non compaiono mai negli argomenti, dove sarebbero leggibili con `ps`.

## Roadmap

- [x] Wizard con ricerca delle share via `smbclient`
- [x] Verifica della connessione prima di scrivere
- [x] Helper privilegiato con polkit e validazione degli input
- [x] Unit systemd `.mount` + `.automount`
- [x] Segnalibro opzionale nel file manager
- [x] Packaging RPM
- [ ] Elenco e rimozione delle condivisioni già configurate
- [ ] Opzioni di mount configurabili (versione SMB, permessi, timeout)
- [ ] Repository COPR per l'installazione con `dnf`

## Licenza

GPL-3.0-or-later
