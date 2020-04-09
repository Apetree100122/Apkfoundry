# SPDX-License-Identifier: GPL-2.0-only
# Copyright (c) 2019 Max Rees
# See LICENSE for more information.
import configparser # ConfigParser
import enum         # Enum, IntFlag, unique
import functools    # partial
import logging      # Formatter, getLogger, StreamHandler
import os           # environ, pathsep
import pwd          # getpwuid
import subprocess   # check_call, check_output
import sys          # stderr, stdout
import datetime as dt # timezone
from pathlib import Path

SITE_CONF = Path("/etc/apkfoundry")
SITE_PACKAGE = Path(__file__).parent
LIBEXEC = (SITE_PACKAGE / "libexec").resolve()
if "PATH" in os.environ:
    os.environ["PATH"] = str(LIBEXEC) + os.pathsep + os.environ["PATH"]
else:
    os.environ["PATH"] = str(LIBEXEC)
HOME = Path("/var/lib/apkfoundry")

_LOGGER = logging.getLogger(__name__)

_ConfigParser = functools.partial(
    configparser.ConfigParser,
    interpolation=None,
    comment_prefixes=(";",),
    delimiters=("=",),
    inline_comment_prefixes=None,
    empty_lines_in_values=True,
    converters={
        "list": lambda s: s.strip().splitlines(),
        "path": Path,
    },
)

_DEFAULT_SITE_CONFIG = {
    "container": {
        "subid": "100000",
    },
    "setarch": {
    },
}

_DEFAULT_LOCAL_CONFIG = {
    "DEFAULT": {
        "key": "",
        "on_failure": "stop",
    },
}

class Colors(enum.Enum):
    NORMAL = "\033[1;0m"
    STRONG = "\033[1;1m"
    CRITICAL = ERROR = RED = "\033[1;31m"
    INFO = GREEN = "\033[1;32m"
    WARNING = YELLOW = "\033[1;33m"
    DEBUG = BLUE = "\033[1;34m"
    MAGENTA = "\033[1;35m"

    def __str__(self):
        return self.value

@enum.unique
class EStatus(enum.IntFlag):
    NEW = 1
    REJECT = 2
    START = 4
    DONE = 8
    ERROR = DONE | 16      # 24
    CANCEL = ERROR | 32    # 56
    SUCCESS = DONE | 64    # 72
    FAIL = ERROR | 128     # 152
    DEPFAIL = CANCEL | 256 # 312
    SKIP = DONE | 512      # 520

    def __str__(self):
        return self.name

def get_config(section=None):
    files = sorted(SITE_CONF.glob("*.ini"))

    config = _ConfigParser()
    config.BOOLEAN_STATES = {"true": True, "false": False}
    config.read_dict(_DEFAULT_SITE_CONFIG)
    config.read(files)

    if section:
        return config[section]

    return config

def rootid():
    return pwd.getpwnam("af-root")

def run(*argv, **kwargs):
    argv = [str(arg) for arg in argv]
    sys.stdout.flush()
    sys.stderr.flush()
    return subprocess.check_call(argv, encoding="utf-8", **kwargs)

def get_output(*argv, **kwargs):
    argv = [str(arg) for arg in argv]
    sys.stdout.flush()
    sys.stderr.flush()
    return subprocess.check_output(argv, encoding="utf-8", **kwargs)

class abuildLogFormatter(logging.Formatter):
    def __init__(self, fmt=None, color=True, time=False, sections=False, **kwargs):
        if not fmt:
            if time:
                fmt = "%(magenta)s%(asctime)s "
            else:
                fmt = ""
            fmt += "%(levelcolor)s%(prettylevel)s"
            fmt += "%(normal)s%(message)s"

        super().__init__(fmt, **kwargs)
        self.color = color
        self.sections = sections

    def format(self, record):
        if self.color:
            try:
                record.levelcolor = Colors[record.levelname]
                record.strong = Colors.STRONG
                record.normal = Colors.NORMAL
                record.magenta = Colors.MAGENTA
            except KeyError:
                record.levelcolor = ""
                record.strong = ""
                record.normal = ""
                record.magenta = ""
        else:
            record.levelcolor = ""
            record.strong = ""
            record.normal = ""
            record.magenta = ""

        if self.sections:
            sectionfmt = "section_%s:%s:%s\r\033[0K"
        else:
            # Discard arguments
            sectionfmt = "%.0s%.0s%.0s"

        if record.levelname == "INFO":
            record.prettylevel = ">>> "
        elif record.levelno == 25:
            record.prettylevel = "\t"
        elif record.levelno in (26, 27):
            record.prettylevel = ""
            msg = record.msg
            record.msg = sectionfmt
            if msg.strip():
                record.msg += "\n" if record.levelno == 27 else ""
                record.msg += f"{Colors.NORMAL}{Colors.STRONG}>>>"
                record.msg += f" {Colors.BLUE}{msg}{Colors.NORMAL}"
        else:
            record.prettylevel = f">>> {record.levelname}: "

        return super().format(record)

def init_logger(
        name,
        output=sys.stderr, level="INFO",
        color=False, time=False, sections=False):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler(output)
    formatter = abuildLogFormatter(color=color, time=time, sections=sections)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def msg2(logger, s, *args, **kwargs):
    if not logger or isinstance(logger, str):
        logger = logging.getLogger(logger)
    if isinstance(s, str):
        logger.log(25, s, *args, **kwargs)
    else:
        for i in s:
            logger.log(25, i, *args, **kwargs)

_sections = []
def section_start(logger, name, *args, **kwargs):
    if not logger or isinstance(logger, str):
        logger = logging.getLogger(logger)

    ts = str(int(dt.datetime.now().timestamp()))
    _sections.append((ts, name))

    logger.log(26, args[0], "start", ts, name, *args[1:], **kwargs)

def section_end(logger, *args, **kwargs):
    if not logger or isinstance(logger, str):
        logger = logging.getLogger(logger)

    if not args:
        args = [""]

    ts, name = _sections.pop()
    logger.log(27, args[0], "end", ts, name, *args[1:], **kwargs)

class CI_Env:
    prefix = "CUSTOM_ENV_"

    def __getitem__(self, key):
        return os.environ[self.prefix + key]

    def __setitem__(self, key, value):
        os.environ[self.prefix + key] = value

    def __delitem__(self, key):
        del os.environ[self.prefix + key]

    def __iter__(self):
        return [i for i in os.environ if i.startswith(self.prefix)]

    def __contains__(self, item):
        return self.prefix + item in os.environ
