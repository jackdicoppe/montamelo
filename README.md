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

Lo script di build installa da solo, se mancano, gli strumenti di packaging
(`rpm-build`, `rpmdevtools`) e le dipendenze dichiarate nello spec
(`make`, `python3-devel`, `desktop-file-utils`, `libappstream-glib`).

Le dipendenze a runtime le installa `dnf` insieme al pacchetto:
`python3-gobject`, `gtk4`, `libadwaita`, `polkit`, `samba-client`,
`cifs-utils`.

## Disinstallazione

```bash
sudo dnf remove montamelo
```

**Le condivisioni già configurate restano attive**, ed è voluto:
disinstallare l'applicazione non deve far sparire un mount usato da script o
backup. Per rimuoverne una, prima di disinstallare, usa l'helper indicando
gli stessi dati con cui l'avevi creata:

```bash
echo '{"server":"192.168.1.10","share":"sharename","mount":"/where/you/mountit","utente":"username"}' \
  | sudo /usr/libexec/montamelo/montamelo-helper rimuovi
```

Disattiva l'automount, cancella le unit systemd e il file credenziali, e
rimuove la cartella di mount se è vuota. Il segnalibro nel file manager, se
l'avevi aggiunto, va tolto a mano dalla barra laterale di Nautilus oppure
con:

```bash
sed -i '\|^file:///mnt/garden |d' ~/.config/gtk-3.0/bookmarks
```

Se hai disinstallato il pacchetto prima di rimuovere una condivisione, puoi
sempre farlo a mano:

```bash
sudo systemctl disable --now mnt-garden.automount
sudo rm /etc/systemd/system/mnt-garden.{mount,automount}
sudo rm /etc/samba/credentials/montamelo-192.168.1.10-garden
sudo systemctl daemon-reload
```

Il nome delle unit deriva dal punto di mount: `/mnt/garden` diventa
`mnt-garden`.

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

Con `--root` i file finiscono sotto la cartella indicata e i comandi
`systemctl` non vengono eseguiti: si può verificare tutto senza toccare il
sistema e senza `sudo`.

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
- [ ] Elenco e rimozione delle condivisioni già configurate dall'interfaccia
- [ ] Opzioni di mount configurabili (versione SMB, permessi, timeout)
- [ ] Repository COPR per l'installazione con `dnf`

## Licenza

GPL-3.0-or-later