"""Standard library registries and built-in package detection."""

from typing import Set

# Python 3.8 - 3.13 standard library modules
PYTHON_STDLIB: Set[str] = {
    "__future__", "_thread", "abc", "aifc", "argparse", "array", "ast", "asdl",
    "asyncio", "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
    "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb", "chunk",
    "cmath", "cmd", "code", "codecs", "codeop", "collections", "colorsys",
    "compileall", "concurrent", "configparser", "contextlib", "contextvars",
    "copy", "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses",
    "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis", "distutils",
    "doctest", "email", "encodings", "ensurepip", "enum", "errno", "faulthandler",
    "fcntl", "filecmp", "fileinput", "fnmatch", "formatter", "fractions",
    "ftplib", "functools", "gc", "getopt", "getpass", "gettext", "glob",
    "graphlib", "grp", "gzip", "hashlib", "heapq", "hmac", "html", "http",
    "idlelib", "imaplib", "imghdr", "imp", "importlib", "inspect", "io",
    "ipaddress", "itertools", "json", "keyword", "lib2to3", "linecache",
    "locale", "logging", "lzma", "mailbox", "mailcap", "marshal", "math",
    "mimetypes", "mmap", "modulefinder", "msilib", "msvcrt", "multiprocessing",
    "netrc", "nis", "nntplib", "numbers", "operator", "optparse", "os",
    "ossaudiodev", "parser", "pathlib", "pdb", "pickle", "pickletools",
    "pipes", "pkgutil", "platform", "plistlib", "poplib", "posix", "posixpath",
    "pprint", "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr",
    "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
    "selectors", "shelve", "shlex", "shutil", "signal", "site", "smtpd",
    "smtplib", "sndhdr", "socket", "socketserver", "spwd", "sqlite3", "ssl",
    "stat", "statistics", "string", "stringprep", "struct", "subprocess",
    "sunau", "symbol", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
    "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize", "tomllib",
    "trace", "traceback", "tracemalloc", "tty", "turtle", "turtledemo",
    "types", "typing", "unicodedata", "unittest", "urllib", "uu", "uuid",
    "venv", "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound",
    "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport",
    "zlib", "zoneinfo"
}

# Node.js Built-in Modules (including node: protocol equivalents)
NODE_STDLIB: Set[str] = {
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console",
    "constants", "crypto", "dgram", "diagnostics_channel", "dns", "domain",
    "events", "fs", "fs/promises", "http", "http2", "https", "inspector",
    "module", "net", "os", "path", "path/posix", "path/win32", "perf_hooks",
    "process", "punycode", "querystring", "readline", "readline/promises",
    "repl", "stream", "stream/consumers", "stream/promises", "stream/web",
    "string_decoder", "sys", "test", "timers", "timers/promises", "tls",
    "trace_events", "tty", "url", "util", "util/types", "v8", "vm", "wasi",
    "worker_threads", "zlib"
}

# Rust Standard & Core Crates
RUST_STDLIB: Set[str] = {
    "std", "core", "alloc", "proc_macro", "test"
}

# Go Standard Library Root Modules / Packages
GO_STDLIB_PREFIXES: Set[str] = {
    "archive", "bufio", "bytes", "compress", "container", "context", "crypto",
    "database", "debug", "embed", "encoding", "errors", "expvar", "flag",
    "fmt", "go", "hash", "html", "image", "index", "io", "log", "math",
    "mime", "net", "os", "path", "plugin", "reflect", "regexp", "runtime",
    "sort", "strconv", "strings", "sync", "syscall", "testing", "text",
    "time", "unicode", "unsafe"
}

# Common high-value packages frequently targeted by slopsquatting / hallucination
TOP_POPULAR_PYTHON: Set[str] = {
    "requests", "numpy", "pandas", "urllib3", "setuptools", "wheel", "pip",
    "typing_extensions", "certifi", "idna", "charset_normalizer", "six",
    "packaging", "boto3", "botocore", "s3transfer", "pytest", "pluggy",
    "iniconfig", "attrs", "pydantic", "pydantic_core", "fastapi", "uvicorn",
    "starlette", "sqlalchemy", "flask", "click", "jinja2", "markupsafe",
    "werkzeug", "scipy", "scikit-learn", "matplotlib", "torch", "torchvision",
    "transformers", "tqdm", "pyyaml", "huggingface_hub", "filelock",
    "fsspec", "regex", "safetensors", "tokenizers", "accelerate", "openai",
    "anthropic", "langchain", "httpx", "aiohttp", "yarl", "multidict",
    "frozenlist", "aiosignal", "async_timeout", "rich", "typer", "cryptography",
    "cffi", "pycparser", "psycopg2", "redis", "celery", "beautifulsoup4",
    "lxml", "pillow", "sympy", "networkx", "seaborn", "dotenv", "python-dotenv",
    "pydantic-settings", "anyio", "sniffio", "distro", "greenlet"
}

TOP_POPULAR_NPM: Set[str] = {
    "react", "react-dom", "vue", "next", "nuxt", "express", "lodash",
    "axios", "typescript", "chalk", "tslib", "commander", "debug",
    "fs-extra", "glob", "inquirer", "semver", "uuid", "yargs",
    "jest", "vitest", "esbuild", "webpack", "vite", "prettier",
    "eslint", "dotenv", "cors", "dayjs", "moment", "zod", "prisma",
    "tailwindcss", "postcss", "autoprefixer", "@types/node", "@types/react",
    "rxjs", "rxjs-compat", "clsx", "tailwind-merge", "lucide-react",
    "supertest", "nodemon", "rimraf", "cross-env", "dotenv-cli"
}


def is_stdlib(name: str, ecosystem: str) -> bool:
    """Check if a package name belongs to the ecosystem standard library."""
    name_clean = name.strip()
    if ecosystem == "python":
        # Extract top-level module (e.g. urllib.parse -> urllib)
        top = name_clean.split(".")[0].lower()
        return top in PYTHON_STDLIB
    elif ecosystem == "npm":
        if name_clean.startswith("node:"):
            return True
        return name_clean.lower() in NODE_STDLIB
    elif ecosystem == "cargo":
        return name_clean in RUST_STDLIB
    elif ecosystem == "go":
        top = name_clean.split("/")[0]
        return top in GO_STDLIB_PREFIXES
    return False
