# SPDX-License-Identifier: GPL-2.0-only
# Copyright (c) 2019-2020 Max Rees
# See LICENSE for more information.
import collections  # defaultdict
import configparser # ConfigParser
import logging      # getLogger
import os           # environ, pathsep
from pathlib import Path

VERSION = "0.6"

BWRAP = "bwrap.nosuid"
DEFAULT_ARCH = "x86_64"

_src = Path(__file__).parent.parent
_maybe_src = lambda x, y: (_src / x) if (_src / x).is_dir() else Path(y)
LIBEXECDIR = _maybe_src("libexec", "/usr/libexec/apkfoundry").resolve()
_path = os.environ.get("PATH")
os.environ["PATH"] = str(LIBEXECDIR) + (os.pathsep + _path if _path else "")

HOME = Path(os.environ["HOME"]).resolve()
SYSCONFDIR = Path(os.environ.get(
    "AF_CONFIG",
    Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "apkfoundry",
)).resolve(strict=False)
LOCALSTATEDIR = Path(os.environ.get(
    "AF_LOCAL",
    Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "apkfoundry",
)).resolve(strict=False)
CACHEDIR = Path(os.environ.get(
    "AF_CACHE",
    Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "apkfoundry",
)).resolve(strict=False)

ROOTFS_CACHE = CACHEDIR / "rootfs"

MOUNTS = {
    "aportsdir": "/af/aports",
    "builddir": "/af/build",
    "repodest": "/af/repos",
    "srcdest": "/af/distfiles",
}

_LOGGER = logging.getLogger(__name__)

def _config_map(s):
    d = {}
    for i in s.strip().splitlines():
        i = i.strip().split(maxsplit=1)
        d[i[0]] = i[1]
    return d

def _config_maplist(s):
    d = collections.defaultdict(list)
    for i in s.strip().splitlines():
        i = i.strip().split()
        d[i[0]].extend(i[1:])
    return d

def _ConfigParser(**kwargs):
    parser = configparser.ConfigParser(
        interpolation=None,
        comment_prefixes=(";",),
        delimiters=("=",),
        inline_comment_prefixes=None,
        empty_lines_in_values=True,
        converters={
            "list": lambda s: s.strip().splitlines(),
            "path": Path,
            "map": _config_map,
            "maplist": _config_maplist,
        },
        **kwargs,
    )
    parser.BOOLEAN_STATES = {"true": True, "false": False}
    return parser

_DEFAULT_SITE_CONFIG = {
    "container": {
        "subuid": "100000",
        "subgid": "100000",
    },
    "setarch": {
    },
}

_DEFAULT_PROJ_CONFIG = {
    "master": {
        # Required
        # rootfs.url.{arch} (str)
        # rootfs.sha256.{arch} (str)
        "repo.arch": "", # maplist
        "repo.default": "", # str
        # Optional
        "rootfs.exclude": "", # list
        "build.networking": "false",
        "build.on-failure": "stop", # str
        "build.only-changed-versions": "false", # bool
        "build.skip": "", # maplist
        "container.persistent-repodest": "false", # bool
        "deps.ignore": "", # maplist
        "deps.map": "", # map
    },
}

def site_conf(section=None):
    files = sorted(SYSCONFDIR.glob("*.ini"))

    config = _ConfigParser()
    config.read_dict(_DEFAULT_SITE_CONFIG)
    config.read(files)

    if section:
        return config[section]

    return config

def proj_conf(gitdir=None, section=None, overrides=None):
    if gitdir is None:
        gitdir = Path.cwd()
    files = sorted((Path(gitdir) / ".apkfoundry").glob("*.ini"))

    config = _ConfigParser(default_section="master")
    config.read_dict(_DEFAULT_PROJ_CONFIG)
    config.read(files)
    if overrides:
        config.read_dict({(section if section else "master"): overrides})

    if section:
        if section not in config:
            config.add_section(section)
        return config[section]

    return config
