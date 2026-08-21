#!/usr/bin/env python3
"""Montamelo - scheletro minimo.

Questa versione NON scrive nulla sul sistema: raccoglie i dati e
mostra alla fine la riga di mount che verrebbe generata.
Serve solo per prendere confidenza con GTK4 / libadwaita.
"""

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

APP_ID = "io.github.jackdicoppe.Montamelo"


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

        launcher = Gio.SubprocessLauncher.new(
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
        )
        # LC_ALL=C: i messaggi di errore restano in inglese e prevedibili
        launcher.setenv("LC_ALL", "C", True)
        if not anonimo:
            # La password passa dall'ambiente e mai dagli argomenti:
            # in argv sarebbe leggibile da chiunque con `ps aux`.
            launcher.setenv("PASSWD", password, True)

        self.bottone_sfoglia.set_sensitive(False)
        self.bottone_sfoglia.set_label("Ricerca…")

        try:
            processo = launcher.spawnv(argv)
        except GLib.Error as errore:
            self.ripristina_bottone_sfoglia()
            self.avviso(
                "Impossibile eseguire smbclient. Installalo con:\n"
                "sudo dnf install samba-client\n\n"
                f"{errore.message}"
            )
            return

        # Il processo gira in background: l'interfaccia resta reattiva.
        cancellabile = Gio.Cancellable()
        GLib.timeout_add_seconds(10, self.on_timeout_ricerca, cancellabile)
        processo.communicate_utf8_async(
            None, cancellabile, self.on_ricerca_completata, server
        )

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
                "smbclient ha restituito un errore:\n\n"
                f"{(stderr or '').strip() or 'nessun dettaglio disponibile'}"
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
        self.nav.push(self.pagina_riepilogo())

    # ------------------------------------------------------------------
    # Passo 3: riepilogo (per ora si limita a mostrare la riga generata)
    # ------------------------------------------------------------------
    def pagina_riepilogo(self):
        riga_fstab = (
            "//{server}/{share} {mount} cifs "
            "credentials=/etc/samba/credentials/{nome},"
            "uid=1000,gid=1000,vers=3.0,"
            "_netdev,nofail,x-systemd.automount 0 0"
        ).format(
            server=self.dati["server"],
            share=self.dati["share"],
            mount=self.dati["mount"],
            nome=self.dati["share"].replace("/", "_"),
        )

        gruppo = Adw.PreferencesGroup(
            title="Riepilogo",
            description="Riga di mount che verrà generata",
        )

        etichetta = Gtk.Label(label=riga_fstab)
        etichetta.set_wrap(True)
        etichetta.set_selectable(True)
        etichetta.set_xalign(0)
        etichetta.add_css_class("monospace")
        etichetta.set_margin_top(12)
        etichetta.set_margin_bottom(12)
        etichetta.set_margin_start(12)
        etichetta.set_margin_end(12)

        contenitore = Gtk.Frame()
        contenitore.set_child(etichetta)
        gruppo.add(contenitore)

        nota = Gtk.Label(
            label="In questa versione non viene scritto nulla sul sistema."
        )
        nota.set_wrap(True)
        nota.add_css_class("dim-label")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.append(gruppo)
        box.append(nota)

        return self._pagina("3. Riepilogo", "riepilogo", box)

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