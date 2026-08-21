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

from gi.repository import Adw, Gtk  # noqa: E402

APP_ID = "io.github.jackdicoppe.Montamelo"


class FinestraWizard(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Montamelo")
        self.set_default_size(520, 640)

        # Qui teniamo i dati raccolti nei vari passi
        self.dati = {}

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
    # Passo 2: credenziali
    # ------------------------------------------------------------------
    def pagina_credenziali(self):
        gruppo = Adw.PreferencesGroup(
            title="Credenziali",
            description="Verranno salvate in un file leggibile solo da root",
        )

        self.riga_utente = Adw.EntryRow(title="Utente")
        self.riga_password = Adw.PasswordEntryRow(title="Password")
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
