#!/bin/sh -e
# vi:noet
. /usr/share/abuild/functions.sh
. "$AF_LIBEXEC/af-functions"

if [ -d "$AF_AFTERDIR" ]; then
	cd "$REPODEST"

	package_key="$AF_AFTERDIR/test@example.org"
	if [ -e "$package_key" ]; then
		af_resign_files "$package_key"
	else
		warning "Could not find '$package_key'"
	fi

	rsync_key="$AF_AFTERDIR/rsync.key"
	rsync_dest=example.org:rsync-test
	export RSYNC_RSH="
		ssh
		-l test
		-i '$rsync_key'
		-o 'IdentitiesOnly yes'
	"
	if [ -e "$rsync_key" ]; then
		$SUDO_APK add openssh-client rsync
		af_sync_files "$rsync_dest"
	else
		warning "Could not find '$rsync_key'"
	fi
fi
