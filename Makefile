# vi: noet
DESTDIR = target
PREFIX = usr
DOCDIR = $(PREFIX)/share/doc/apkfoundry
LIBEXECDIR = $(PREFIX)/libexec/apkfoundry
LOCALSTATEDIR = var/lib/apkfoundry
SYSCONFDIR = etc/apkfoundry
export DOCDIR LIBEXECDIR SYSCONFDIR

BWRAP = bwrap.nosuid
DEFAULT_ARCH = $(shell apk --print-arch)

PYTHON = python3
PYLINT = pylint
SETUP.PY = $(PYTHON) src/setup.py

C_TARGETS = \
	libexec/af-req-root \
	libexec/af-su

TEST_TARGETS = \
	tests/*.test

CLEAN_TARGETS = \
	$(C_TARGETS) \
	MANIFEST \
	apkfoundry.egg-info \
	build \
	dist \
	target \
	tests/tmp \
	var

LINT_TARGETS = \
	apkfoundry \
	bin/af-buildrepo \
	bin/af-chroot \
	bin/af-depgraph \
	bin/af-mkchroot \
	bin/af-rmchroot \
	libexec/gl-run

.PHONY: all
all: libexec
	$(SETUP.PY) build

libexec/%: src/%.c
	$(CC) $(CFLAGS) -Wall -Wextra -fPIE -static-pie $(LDFLAGS) -o $@ $<

libexec: $(C_TARGETS)

.PHONY: configure
configure:
	@printf 'CONF: BWRAP = "%s"\n' '$(BWRAP)'
	@printf 'CONF: DEFAULT_ARCH = "%s"\n' '$(DEFAULT_ARCH)'
	@sed -i \
		-e '/^BWRAP = /s@= .*@= "$(BWRAP)"@' \
		-e '/^DEFAULT_ARCH = /s@= .*@= "$(DEFAULT_ARCH)"@' \
		apkfoundry/__init__.py

.PHONY: quickstart
quickstart: configure libexec
	mkdir -p var/build
	mkdir -p var/apk-cache var/rootfs-cache var/src-cache

.PHONY: check
check: quickstart
	@tests/run-tests.sh -q $(TEST_TARGETS)

.PHONY: paths
paths: configure
	@printf 'PATH: LIBEXECDIR = "%s"\n' '$(LIBEXECDIR)'
	@printf 'PATH: LOCALSTATEDIR = "%s"\n' '$(LOCALSTATEDIR)'
	@printf 'PATH: SYSCONFDIR = "%s"\n' '$(SYSCONFDIR)'
	@sed -i \
		-e '/^LIBEXECDIR = /s@= .*@= "/$(LIBEXECDIR)"@' \
		-e '/^LOCALSTATEDIR = /s@= .*@= "/$(LOCALSTATEDIR)"@' \
		-e '/^SYSCONFDIR = /s@= .*@= "/$(SYSCONFDIR)"@' \
		apkfoundry/__init__.py

.PHONY: install
install: paths all
	$(SETUP.PY) install \
		--root="$(DESTDIR)" \
		--prefix="/$(PREFIX)"
	chmod 2755 "$(DESTDIR)/$(SYSCONFDIR)"
	-chgrp apkfoundry "$(DESTDIR)/$(SYSCONFDIR)"
	mkdir -p "$(DESTDIR)/$(LOCALSTATEDIR)"
	chmod 2770 "$(DESTDIR)/$(LOCALSTATEDIR)"
	-chgrp apkfoundry "$(DESTDIR)/$(LOCALSTATEDIR)"
	mkdir "$(DESTDIR)/$(LOCALSTATEDIR)/build"
	chmod 770 "$(DESTDIR)/$(LOCALSTATEDIR)/build"
	-chgrp apkfoundry "$(DESTDIR)/$(LOCALSTATEDIR)/build"
	mkdir "$(DESTDIR)/$(LOCALSTATEDIR)/apk-cache"
	chmod 775 "$(DESTDIR)/$(LOCALSTATEDIR)/apk-cache"
	-chgrp apkfoundry "$(DESTDIR)/$(LOCALSTATEDIR)/apk-cache"
	mkdir "$(DESTDIR)/$(LOCALSTATEDIR)/rootfs-cache"
	chmod 775 "$(DESTDIR)/$(LOCALSTATEDIR)/rootfs-cache"
	-chgrp apkfoundry "$(DESTDIR)/$(LOCALSTATEDIR)/rootfs-cache"
	mkdir "$(DESTDIR)/$(LOCALSTATEDIR)/src-cache"
	chmod 775 "$(DESTDIR)/$(LOCALSTATEDIR)/src-cache"
	-chgrp apkfoundry "$(DESTDIR)/$(LOCALSTATEDIR)/src-cache"

.PHONY: clean
clean:
	rm -rf $(CLEAN_TARGETS)

.PHONY: dist
dist: clean
	$(SETUP.PY) sdist -u root -g root -t src/MANIFEST.in

.PHONY: lint
lint: $(LINT_TARGETS)
	-$(PYLINT) --rcfile src/pylintrc $?

.PHONY: setup
setup:
	@$(SETUP.PY) $(SETUP_ARGS)
