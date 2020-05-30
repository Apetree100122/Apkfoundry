# vi: noet
DESTDIR = target
PREFIX = usr
DOCDIR = $(PREFIX)/share/doc/apkfoundry
LIBEXECDIR = $(PREFIX)/libexec/apkfoundry
export DOCDIR LIBEXECDIR

BWRAP = bwrap.nosuid
DEFAULT_ARCH = $(shell apk --print-arch)

PYTHON = python3
PYLINT = pylint
SETUP.PY = $(PYTHON) src/setup.py

C_TARGETS = \
	libexec/af-req-root \
	libexec/af-su

TEST_ARGS = -q
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
	$(CC) $(CFLAGS) -Wall -Wextra -fPIE $(LDFLAGS) -static-pie -o $@ $<

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

.PHONY: check
check: quickstart
	@tests/run-tests.sh $(TEST_ARGS) $(TEST_TARGETS)

.PHONY: paths
paths: configure
	@printf 'PATH: LIBEXECDIR = "%s"\n' '$(LIBEXECDIR)'
	@sed -i \
		-e '/^LIBEXECDIR = /s@= .*@= "/$(LIBEXECDIR)"@' \
		apkfoundry/__init__.py

.PHONY: install
install: paths all
	$(SETUP.PY) install \
		--root="$(DESTDIR)" \
		--prefix="/$(PREFIX)"

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
