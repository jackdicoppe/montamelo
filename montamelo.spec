%global appid io.github.jackdicoppe.Montamelo

Name:           montamelo
Version:        0.1.0
Release:        1%{?dist}
Summary:        Set up permanent SMB network shares
Summary(it):    Configura condivisioni di rete SMB permanenti

License:        GPL-3.0-or-later
URL:            https://github.com/jackdicoppe/montamelo
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  make
BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib

Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       polkit
# Servono per elencare le share e per montarle davvero
Requires:       samba-client
Requires:       cifs-utils

%description
Montamelo is a step-by-step assistant that turns an SMB network share into a
real directory on your system, available to every application including
sandboxed ones. It browses the shares published by a server, tests the
connection before writing anything, generates systemd mount units instead of
editing fstab, and stores credentials in a file readable only by root.

%description -l it
Montamelo è un assistente passo passo che trasforma una condivisione di rete
SMB in una cartella vera del sistema, accessibile a qualsiasi applicazione
comprese quelle in sandbox. Elenca le condivisioni pubblicate da un server,
verifica la connessione prima di scrivere, genera unit systemd invece di
modificare fstab e salva le credenziali in un file leggibile solo da root.

%prep
%autosetup

%build
# Niente da compilare: e' tutto Python

%install
%make_install PREFIX=%{_prefix}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{appid}.desktop
appstream-util validate-relax --nonet \
    %{buildroot}%{_datadir}/metainfo/%{appid}.metainfo.xml

%files
%license LICENSE
%doc README.md
%{_bindir}/montamelo
%{_datadir}/montamelo/
%dir %{_libexecdir}/montamelo
%attr(0755,root,root) %{_libexecdir}/montamelo/montamelo-helper
%{_datadir}/polkit-1/actions/%{appid}.policy
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/metainfo/%{appid}.metainfo.xml
%{_datadir}/icons/hicolor/*/apps/%{appid}.png

%changelog
* Sat Aug 22 2026 Mauro Caputi <jackdicoppe@users.noreply.github.com> - 0.1.0-1
- Prima versione
