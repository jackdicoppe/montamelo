#!/usr/bin/env python3
"""Montamelo - scheletro minimo.

Questa versione NON scrive nulla sul sistema: raccoglie i dati e
mostra alla fine la riga di mount che verrebbe generata.
Serve solo per prendere confidenza con GTK4 / libadwaita.
"""

import json
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

APP_ID = "io.github.jackdicoppe.Montamelo"


def trova_helper():
    """L'helper installato ha la precedenza; in sviluppo si usa quello locale."""
    candidati = [
        "/usr/libexec/montamelo/montamelo-helper",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "montamelo-helper"),
    ]
    for percorso in candidati:
        if os.path.exists(percorso):
            return percorso
    return candidati[0]


PERCORSO_HELPER = trova_helper()


class FinestraWizard(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Montamelo")
        self.set_default_size(520, 640)

        # Qui teniamo i dati raccolti nei vari passi
        self.dati = {}
        # Credenziali usate per la ricerca delle share, riproposte al passo 2
        self.credenziali_temp = {}

        self.nav = Adw.NavigationView()
        self.set_content(self.nav)
        self.nav.push(self.pagina_server())

    # ------------------------------------------------------------------
    # Helper: costruisce una pagina del wizard con header bar e contenuto
    # ------------------------------------------------------------------
    def _pagina(self, titolo, tag, widget_contenuto):
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.append(widget_contenuto)

        scroll.set_child(box)
        toolbar.set_content(scroll)

        return Adw.NavigationPage(child=toolbar, title=titolo, tag=tag)

    def _bottone_avanti(self, etichetta, callback):
        btn = Gtk.Button(label=etichetta)
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.connect("clicked", callback)
        return btn

    # ------------------------------------------------------------------
    # Passo 1: server e share
    # ------------------------------------------------------------------
    def pagina_server(self):
        gruppo = Adw.PreferencesGroup(
            title="Server di rete",
            description="Indica il server SMB e la cartella condivisa",
        )

        self.riga_server = Adw.EntryRow(title="Server (IP o hostname)")

        self.bottone_sfoglia = Gtk.Button(label="Sfoglia")
        self.bottone_sfoglia.set_valign(Gtk.Align.CENTER)
        self.bottone_sfoglia.add_css_class("flat")
        self.bottone_sfoglia.connect("clicked", self.on_sfoglia)
        self.riga_server.add_suffix(self.bottone_sfoglia)

        self.riga_share = Adw.EntryRow(title="Nome della share")
        self.riga_mount = Adw.EntryRow(title="Punto di mount")
        self.riga_mount.set_text("/mnt/nas")

        gruppo.add(self.riga_server)
        gruppo.add(self.riga_share)
        gruppo.add(self.riga_mount)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.append(gruppo)
        box.append(self._bottone_avanti("Avanti", self.on_avanti_server))

        return self._pagina("1. Server", "server", box)

    def on_avanti_server(self, _button):
        self.dati["server"] = self.riga_server.get_text().strip()
        self.dati["share"] = self.riga_share.get_text().strip()
        self.dati["mount"] = self.riga_mount.get_text().strip()

        if not self.dati["server"] or not self.dati["share"]:
            self.avviso("Server e nome della share sono obbligatori.")
            return

        self.nav.push(self.pagina_credenziali())

    # ------------------------------------------------------------------
    # Sfoglia: chiede le credenziali e interroga il server con smbclient
    # ------------------------------------------------------------------
    def on_sfoglia(self, _button):
        server = self.riga_server.get_text().strip()
        if not server:
            self.avviso("Inserisci prima l'indirizzo del server.")
            return

        riga_anonimo = Adw.SwitchRow(
            title="Accesso anonimo",
            subtitle="Prova senza credenziali",
        )
        riga_utente = Adw.EntryRow(title="Utente")
        riga_utente.set_text(self.credenziali_temp.get("utente", ""))
        riga_password = Adw.PasswordEntryRow(title="Password")

        gruppo = Adw.PreferencesGroup()
        gruppo.add(riga_anonimo)
        gruppo.add(riga_utente)
        gruppo.add(riga_password)

        dialogo = Adw.AlertDialog(
            heading=f"Connessione a {server}",
            body="Credenziali per leggere l'elenco delle condivisioni",
        )
        dialogo.set_extra_child(gruppo)
        dialogo.add_response("annulla", "Annulla")
        dialogo.add_response("elenca", "Elenca")
        dialogo.set_response_appearance("elenca", Adw.ResponseAppearance.SUGGESTED)
        dialogo.set_default_response("elenca")
        dialogo.connect(
            "response",
            self.on_risposta_credenziali,
            server,
            riga_utente,
            riga_password,
            riga_anonimo,
        )
        dialogo.present(self)

    def on_risposta_credenziali(
        self, _dialogo, risposta, server, riga_utente, riga_password, riga_anonimo
    ):
        if risposta != "elenca":
            return

        anonimo = riga_anonimo.get_active()
        utente = riga_utente.get_text().strip()
        password = riga_password.get_text()

        if not anonimo:
            self.credenziali_temp = {"utente": utente, "password": password}

        self.elenca_share(server, utente, password, anonimo)

    def elenca_share(self, server, utente, password, anonimo):
        # -g produce un output a campi separati da |, molto più facile
        # da leggere rispetto alla tabella pensata per gli umani.
        argv = ["smbclient", "-L", f"//{server}", "-g"]
        argv += ["-N"] if anonimo else ["-U", utente]

        self.bottone_sfoglia.set_sensitive(False)
        self.bottone_sfoglia.set_label("Ricerca…")

        avviato = self.esegui_smbclient(
            argv,
            None if anonimo else password,
            self.on_ricerca_completata,
            server,
        )
        if not avviato:
            self.ripristina_bottone_sfoglia()

    # ------------------------------------------------------------------
    # Esecuzione asincrona di smbclient, condivisa da tutti i passi
    # ------------------------------------------------------------------
    def esegui_smbclient(self, argv, password, callback, dati_utente):
        """Avvia smbclient in background. Ritorna False se non parte proprio."""
        launcher = Gio.SubprocessLauncher.new(
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
        )
        # LC_ALL=C: i messaggi di errore restano in inglese e prevedibili
        launcher.setenv("LC_ALL", "C", True)
        if password is not None:
            # La password passa dall'ambiente e mai dagli argomenti:
            # in argv sarebbe leggibile da chiunque con `ps aux`.
            launcher.setenv("PASSWD", password, True)

        try:
            processo = launcher.spawnv(argv)
        except GLib.Error as errore:
            self.avviso(
                "Impossibile eseguire smbclient. Installalo con:\n"
                "sudo dnf install samba-client\n\n"
                f"{errore.message}"
            )
            return False

        # Il processo gira in background: l'interfaccia resta reattiva.
        cancellabile = Gio.Cancellable()
        GLib.timeout_add_seconds(10, self.on_timeout_ricerca, cancellabile)
        processo.communicate_utf8_async(None, cancellabile, callback, dati_utente)
        return True

    def on_timeout_ricerca(self, cancellabile):
        cancellabile.cancel()
        return GLib.SOURCE_REMOVE

    def on_ricerca_completata(self, processo, risultato, server):
        self.ripristina_bottone_sfoglia()

        try:
            _ok, stdout, stderr = processo.communicate_utf8_finish(risultato)
        except GLib.Error as errore:
            self.avviso(
                "Ricerca non riuscita: il server non ha risposto entro "
                f"10 secondi.\n\n{errore.message}"
            )
            return

        if processo.get_exit_status() != 0:
            self.avviso(
                "Ricerca non riuscita.\n\n"
                f"{self.riassumi_errore(stderr)}"
            )
            return

        elenco = self.estrai_share(stdout)
        if not elenco:
            self.avviso(f"Nessuna condivisione utilizzabile trovata su {server}.")
            return

        self.mostra_elenco_share(elenco)

    @staticmethod
    def estrai_share(output):
        """Trasforma l'output di `smbclient -L -g` in una lista (nome, commento)."""
        elenco = []
        for riga in output.splitlines():
            campi = riga.split("|")
            if len(campi) < 2 or campi[0] != "Disk":
                continue
            nome = campi[1]
            if nome.endswith("$"):  # share amministrative: C$, ADMIN$, IPC$
                continue
            commento = campi[2].strip() if len(campi) > 2 else ""
            elenco.append((nome, commento))
        return elenco

    def mostra_elenco_share(self, elenco):
        lista = Gtk.ListBox()
        lista.add_css_class("boxed-list")
        lista.set_selection_mode(Gtk.SelectionMode.NONE)

        dialogo = Adw.AlertDialog(heading="Condivisioni disponibili")

        for nome, commento in elenco:
            riga = Adw.ActionRow(title=nome)
            if commento:
                riga.set_subtitle(commento)
            riga.set_activatable(True)
            riga.connect("activated", self.on_share_scelta, nome, dialogo)
            lista.append(riga)

        dialogo.set_extra_child(lista)
        dialogo.add_response("annulla", "Chiudi")
        dialogo.present(self)

    def on_share_scelta(self, _riga, nome, dialogo):
        self.riga_share.set_text(nome)
        if self.riga_mount.get_text().strip() in ("", "/mnt/nas"):
            self.riga_mount.set_text(f"/mnt/{nome.lower()}")
        dialogo.close()

    def ripristina_bottone_sfoglia(self):
        self.bottone_sfoglia.set_sensitive(True)
        self.bottone_sfoglia.set_label("Sfoglia")

    # ------------------------------------------------------------------
    # Passo 2: credenziali
    # ------------------------------------------------------------------
    def pagina_credenziali(self):
        gruppo = Adw.PreferencesGroup(
            title="Credenziali",
            description="Verranno salvate in un file leggibile solo da root",
        )

        self.riga_utente = Adw.EntryRow(title="Utente")
        self.riga_utente.set_text(self.credenziali_temp.get("utente", ""))
        self.riga_password = Adw.PasswordEntryRow(title="Password")
        self.riga_password.set_text(self.credenziali_temp.get("password", ""))
        self.riga_dominio = Adw.EntryRow(title="Dominio")
        self.riga_dominio.set_text("WORKGROUP")

        gruppo.add(self.riga_utente)
        gruppo.add(self.riga_password)
        gruppo.add(self.riga_dominio)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.append(gruppo)
        box.append(self._bottone_avanti("Avanti", self.on_avanti_credenziali))

        return self._pagina("2. Credenziali", "credenziali", box)

    def on_avanti_credenziali(self, _button):
        self.dati["utente"] = self.riga_utente.get_text().strip()
        self.dati["password"] = self.riga_password.get_text()
        self.dati["dominio"] = self.riga_dominio.get_text().strip()
        self.nav.push(self.pagina_verifica())

    # ------------------------------------------------------------------
    # Passo 3: verifica che la share sia davvero raggiungibile
    # ------------------------------------------------------------------
    def pagina_verifica(self):
        gruppo = Adw.PreferencesGroup(
            title="Verifica connessione",
            description=(
                "Controlla che la condivisione risponda con queste credenziali, "
                "prima di scrivere qualsiasi cosa sul sistema"
            ),
        )

        self.riga_esito = Adw.ActionRow(
            title="Non ancora verificata",
            subtitle=f"//{self.dati['server']}/{self.dati['share']}",
        )
        self.icona_esito = Gtk.Image.new_from_icon_name("dialog-question-symbolic")
        self.riga_esito.add_prefix(self.icona_esito)
        gruppo.add(self.riga_esito)

        self.bottone_verifica = Gtk.Button(label="Verifica adesso")
        self.bottone_verifica.add_css_class("pill")
        self.bottone_verifica.set_halign(Gtk.Align.CENTER)
        self.bottone_verifica.connect("clicked", self.on_verifica)

        self.bottone_avanti_verifica = self._bottone_avanti(
            "Avanti", self.on_avanti_verifica
        )
        self.bottone_avanti_verifica.set_sensitive(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.append(gruppo)
        box.append(self.bottone_verifica)
        box.append(self.bottone_avanti_verifica)

        return self._pagina("3. Verifica", "verifica", box)

    def on_verifica(self, _button):
        # -c 'ls' apre la share, elenca la radice ed esce: è il modo più
        # leggero per sapere se il mount vero funzionerebbe.
        argv = [
            "smbclient",
            f"//{self.dati['server']}/{self.dati['share']}",
            "-U",
            self.dati["utente"],
            "-W",
            self.dati["dominio"] or "WORKGROUP",
            "-c",
            "ls",
        ]

        self.bottone_verifica.set_sensitive(False)
        self.bottone_verifica.set_label("Verifica in corso…")
        self.aggiorna_esito("dialog-question-symbolic", "Verifica in corso…", "")

        avviato = self.esegui_smbclient(
            argv, self.dati["password"], self.on_verifica_completata, None
        )
        if not avviato:
            self.ripristina_bottone_verifica()

    def on_verifica_completata(self, processo, risultato, _dati):
        self.ripristina_bottone_verifica()

        try:
            _ok, _stdout, stderr = processo.communicate_utf8_finish(risultato)
        except GLib.Error:
            self.aggiorna_esito(
                "network-offline-symbolic",
                "Nessuna risposta",
                "Il server non ha risposto entro 10 secondi",
            )
            return

        if processo.get_exit_status() != 0:
            self.aggiorna_esito(
                "dialog-error-symbolic",
                "Connessione fallita",
                self.riassumi_errore(stderr),
            )
            return

        self.dati["verificata"] = True
        self.aggiorna_esito(
            "emblem-ok-symbolic",
            "Connessione riuscita",
            "La condivisione risponde con queste credenziali",
        )
        self.bottone_avanti_verifica.set_sensitive(True)

    @staticmethod
    def riassumi_errore(stderr):
        """Traduce gli errori più comuni di smbclient in qualcosa di leggibile."""
        testo = (stderr or "").strip()
        mappa = {
            "LOGON_FAILURE": "Utente o password errati",
            "ACCESS_DENIED": "Credenziali valide ma accesso negato alla share",
            "BAD_NETWORK_NAME": "La share non esiste su questo server",
            "CONNECTION_REFUSED": "Il server rifiuta la connessione (porta 445 chiusa?)",
            "HOST_UNREACHABLE": "Server irraggiungibile: controlla indirizzo e rete",
            "ACCOUNT_LOCKED_OUT": "Account bloccato sul server",
        }
        for codice, spiegazione in mappa.items():
            if codice in testo:
                return spiegazione
        return (
            testo.splitlines()[0]
            if testo
            else "La ricerca non ha prodotto risultati, controlla nome utente e password"
        )

    def aggiorna_esito(self, icona, titolo, sottotitolo):
        self.icona_esito.set_from_icon_name(icona)
        self.riga_esito.set_title(titolo)
        self.riga_esito.set_subtitle(sottotitolo)

    def ripristina_bottone_verifica(self):
        self.bottone_verifica.set_sensitive(True)
        self.bottone_verifica.set_label("Verifica adesso")

    def on_avanti_verifica(self, _button):
        self.nav.push(self.pagina_riepilogo())

    # ------------------------------------------------------------------
    # Passo 4: riepilogo reale, generato dall'helper, e installazione
    # ------------------------------------------------------------------
    def pagina_riepilogo(self):
        self.gruppo_file = Adw.PreferencesGroup(
            title="File che verranno creati",
            description="Nessuno di questi esiste ancora sul sistema",
        )
        self.riga_attesa = Adw.ActionRow(title="Generazione anteprima…")
        self.gruppo_file.add(self.riga_attesa)

        self.bottone_installa = Gtk.Button(label="Installa nel sistema")
        self.bottone_installa.add_css_class("suggested-action")
        self.bottone_installa.add_css_class("pill")
        self.bottone_installa.set_halign(Gtk.Align.CENTER)
        self.bottone_installa.set_sensitive(False)
        self.bottone_installa.connect("clicked", self.on_installa)

        nota = Gtk.Label(
            label=(
                "Verrà chiesta la password di amministratore: la scrittura "
                "avviene in un processo separato, l'interfaccia non gira mai "
                "con privilegi di root."
            )
        )
        nota.set_wrap(True)
        nota.set_justify(Gtk.Justification.CENTER)
        nota.add_css_class("dim-label")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.append(self.gruppo_file)
        box.append(self.bottone_installa)
        box.append(nota)

        pagina = self._pagina("4. Riepilogo", "riepilogo", box)
        # L'anteprima non richiede privilegi: la chiediamo subito all'helper
        self.esegui_helper("anteprima", False, self.on_anteprima_completata)
        return pagina

    def payload_helper(self):
        """Il documento JSON che l'helper riceve su stdin."""
        return {
            "server": self.dati["server"],
            "share": self.dati["share"],
            "mount": self.dati["mount"],
            "utente": self.dati["utente"],
            "password": self.dati["password"],
            "dominio": self.dati["dominio"] or "WORKGROUP",
            "uid": os.getuid(),
            "gid": os.getgid(),
        }

    def esegui_helper(self, azione, con_privilegi, callback):
        argv = [PERCORSO_HELPER, azione]
        if con_privilegi:
            # pkexec mostra il dialogo di autenticazione e riesegue l'helper
            # come root: l'interfaccia resta un normale processo utente.
            argv = ["pkexec"] + argv

        launcher = Gio.SubprocessLauncher.new(
            Gio.SubprocessFlags.STDIN_PIPE
            | Gio.SubprocessFlags.STDOUT_PIPE
            | Gio.SubprocessFlags.STDERR_PIPE
        )
        launcher.setenv("LC_ALL", "C", True)

        try:
            processo = launcher.spawnv(argv)
        except GLib.Error as errore:
            self.avviso(f"Impossibile avviare l'helper:\n\n{errore.message}")
            return False

        # I dati (password compresa) viaggiano su stdin, mai su argv.
        processo.communicate_utf8_async(
            json.dumps(self.payload_helper()), None, callback, None
        )
        return True

    @staticmethod
    def leggi_risposta(processo, risultato):
        """Ritorna (risposta_dict, errore_stringa)."""
        try:
            _ok, stdout, stderr = processo.communicate_utf8_finish(risultato)
        except GLib.Error as errore:
            return None, errore.message

        if not (stdout or "").strip():
            uscita = processo.get_exit_status()
            if uscita == 126:
                return None, "Autenticazione annullata."
            return None, (stderr or "").strip() or "L'helper non ha risposto."

        try:
            return json.loads(stdout), None
        except json.JSONDecodeError:
            return None, f"Risposta non leggibile dall'helper:\n\n{stdout[:400]}"

    def on_anteprima_completata(self, processo, risultato, _dati):
        risposta, errore = self.leggi_risposta(processo, risultato)
        if errore or not risposta.get("ok"):
            self.riga_attesa.set_title("Anteprima non riuscita")
            self.riga_attesa.set_subtitle(
                errore or "; ".join(risposta.get("messaggi", []))
            )
            return

        self.gruppo_file.remove(self.riga_attesa)
        for voce in risposta.get("file", {}).values():
            self.gruppo_file.add(self.riga_file(voce))
        self.bottone_installa.set_sensitive(True)

    @staticmethod
    def riga_file(voce):
        """Una riga espandibile che mostra il contenuto del file generato."""
        riga = Adw.ExpanderRow(
            title=os.path.basename(voce["percorso"]),
            subtitle=os.path.dirname(voce["percorso"]),
        )

        etichetta = Gtk.Label(label=voce["contenuto"].strip())
        etichetta.set_selectable(True)
        etichetta.set_xalign(0)
        etichetta.set_wrap(True)
        etichetta.add_css_class("monospace")
        etichetta.set_margin_top(12)
        etichetta.set_margin_bottom(12)
        etichetta.set_margin_start(12)
        etichetta.set_margin_end(12)

        contenuto = Adw.ActionRow()
        contenuto.set_child(etichetta)
        riga.add_row(contenuto)
        return riga

    def on_installa(self, _button):
        self.bottone_installa.set_sensitive(False)
        self.bottone_installa.set_label("Installazione in corso…")
        if not self.esegui_helper("installa", True, self.on_installa_completata):
            self.ripristina_bottone_installa()

    def on_installa_completata(self, processo, risultato, _dati):
        risposta, errore = self.leggi_risposta(processo, risultato)

        if errore or not risposta.get("ok"):
            self.ripristina_bottone_installa()
            self.avviso(
                "Installazione non riuscita.\n\n"
                + (errore or "\n".join(risposta.get("messaggi", [])))
            )
            return

        self.bottone_installa.set_label("Installato")
        self.mostra_esito_installazione(risposta.get("messaggi", []))

    def ripristina_bottone_installa(self):
        self.bottone_installa.set_sensitive(True)
        self.bottone_installa.set_label("Installa nel sistema")

    def mostra_esito_installazione(self, messaggi):
        dialogo = Adw.AlertDialog(
            heading="Condivisione configurata",
            body=(
                f"{self.dati['mount']} verrà montata automaticamente "
                "al primo accesso, anche dopo un riavvio."
            ),
        )

        lista = Gtk.ListBox()
        lista.add_css_class("boxed-list")
        lista.set_selection_mode(Gtk.SelectionMode.NONE)
        for messaggio in messaggi:
            lista.append(Adw.ActionRow(title=messaggio))

        dialogo.set_extra_child(lista)
        dialogo.add_response("chiudi", "Chiudi")
        dialogo.present(self)

    # ------------------------------------------------------------------
    def avviso(self, messaggio):
        dialogo = Adw.AlertDialog(heading="Attenzione", body=messaggio)
        dialogo.add_response("ok", "Ho capito")
        dialogo.present(self)


class Applicazione(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        finestra = self.props.active_window
        if not finestra:
            finestra = FinestraWizard(application=self)
        finestra.present()


def main():
    return Applicazione().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())