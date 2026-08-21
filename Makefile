PREFIX  ?= /usr
DESTDIR ?=
APPID    = io.github.jackdicoppe.Montamelo

BINDIR     = $(DESTDIR)$(PREFIX)/bin
LIBEXECDIR = $(DESTDIR)$(PREFIX)/libexec/montamelo
DATADIR    = $(DESTDIR)$(PREFIX)/share
APPDIR     = $(DATADIR)/montamelo
ICONDIR    = $(DATADIR)/icons/hicolor

.PHONY: all install uninstall check

all:
	@echo "Niente da compilare: e' tutto Python. Usa 'make install'."

install:
	# Codice dell'interfaccia
	install -Dm644 main.py $(APPDIR)/main.py

	# Lanciatore in PATH
	install -d $(BINDIR)
	printf '#!/bin/sh\nexec python3 $(PREFIX)/share/montamelo/main.py "$$@"\n' \
		> $(BINDIR)/montamelo
	chmod 755 $(BINDIR)/montamelo

	# Helper privilegiato: eseguibile da tutti, scrivibile solo da root
	install -Dm755 montamelo-helper $(LIBEXECDIR)/montamelo-helper

	# Autorizzazione polkit
	install -Dm644 data/$(APPID).policy \
		$(DATADIR)/polkit-1/actions/$(APPID).policy

	# Voce di menu e metadati
	install -Dm644 data/$(APPID).desktop $(DATADIR)/applications/$(APPID).desktop
	install -Dm644 data/$(APPID).metainfo.xml \
		$(DATADIR)/metainfo/$(APPID).metainfo.xml

	# Icone
	for dim in 48 64 128 256 512; do \
		install -Dm644 data/icons/$$dim.png \
			$(ICONDIR)/$${dim}x$${dim}/apps/$(APPID).png; \
	done

uninstall:
	rm -f $(BINDIR)/montamelo
	rm -rf $(APPDIR) $(LIBEXECDIR)
	rm -f $(DATADIR)/polkit-1/actions/$(APPID).policy
	rm -f $(DATADIR)/applications/$(APPID).desktop
	rm -f $(DATADIR)/metainfo/$(APPID).metainfo.xml
	for dim in 48 64 128 256 512; do \
		rm -f $(ICONDIR)/$${dim}x$${dim}/apps/$(APPID).png; \
	done

check:
	python3 -m py_compile main.py montamelo-helper
	@echo "Sintassi Python corretta."
