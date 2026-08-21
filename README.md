# Montamelo

*Configurazione guidata delle condivisioni di rete*

Applicazione GTK4 / libadwaita che guida passo passo nella configurazione
di un mount SMB permanente su Fedora: cartella di mount, file credenziali
protetto, unit systemd (o entry fstab) e test della connessione.

> **Stato: work in progress.** La versione attuale è solo uno scheletro
> dell'interfaccia: raccoglie i dati e mostra la riga di mount che verrebbe
> generata, senza scrivere nulla sul sistema.

## Requisiti

Su Fedora Workstation:

```bash
sudo dnf install python3-gobject gtk4 libadwaita cifs-utils
```

## Esecuzione

```bash
git clone https://github.com/jackdicoppe/montamelo.git
cd montamelo
python3 main.py
```

## Roadmap

- [x] Scheletro del wizard (server, credenziali, riepilogo)
- [ ] Test della connessione con `smbclient` prima di salvare
- [ ] Helper privilegiato invocato via `pkexec` + policy polkit
- [ ] Scrittura del file credenziali in `/etc/samba/credentials` (0600, root)
- [ ] Generazione unit systemd `.mount` + `.automount`
- [ ] Gestione dei contesti SELinux
- [ ] Elenco e rimozione dei mount già configurati
- [ ] Override Flatpak per dare accesso al mount alle app in sandbox
- [ ] Packaging RPM e repository COPR

## Licenza

GPL-3.0-or-later
