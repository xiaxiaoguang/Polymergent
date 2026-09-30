import ast
import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

# --- policy: edit these -------------------------------------------------
ALLOWED_ROOTS = [
    Path("/home/hcao5/workspace/datasets/polymer/data_lake").resolve(),
    Path("/home/hcao5/workspace/datasets/polymer/data_lake2").resolve(),
    Path("/home/hcao5/workspace/polymer").resolve()
]

# raw datasets, secrets, home, system
DENIED_ROOTS = [
    Path("/home/hcao5/workspace/datasets/polymer/data").resolve(),
    Path("/home/hcao5/workspace/datasets/polymer/raw").resolve(),
    Path("*/data/polymer").resolve(),
]

MAX_PATH_DEPTH_UP = 0  # reject any ".." that escapes ALLOWED_ROOTS

NETWORK_NAME_RE = re.compile(
    r"""(?ix)
    \b(
        requests|httpx|aiohttp|urllib|httplib|
        socket|ssl|ftplib|smtplib|poplib|imaplib|nntplib|telnetlib|
        websocket|paramiko|fabric|subprocess|multiprocessing|
        webbrowser|selenium
    )\b
    |
    \b(
        curl|wget|nc|ncat|netcat|ssh|scp|sftp|rsync|ftp|telnet|
        ping|nmap|dig|nslookup|whois
    )\b
    """
)

PATH_CALL_RE = re.compile(
    r"""(?x)
    (?:
        open\s*\( |
        Path\s*\( |
        pathlib\.Path\s*\( |
        os\.path\.(?:join|abspath|realpath|expanduser) |
        os\.(?:listdir|scandir|walk|remove|rmdir|mkdir|makedirs|replace|rename|stat|chmod) |
        shutil\.(?:copy|copy2|copytree|move|rmtree|disk_usage) |
        pandas\.read_\w+\s*\( |
        pd\.read_\w+\s*\( |
        numpy\.load\s*\( | np\.load\s*\( |
        h5py\.File\s*\( |
        scanpy\.read |
        anndata\.read
    )
    """
)

STRING_PATH_RE = re.compile(
    r"""(?x)
    ['"](
        (?:\.\./)+[^'"]+ |
        /[^'"]+ |
        ~[^'"]* |
        (?:raw_data|data/raw|datasets|secrets|\.env|id_rsa)[^'"]*
    )['"]
    """
)
# ------------------------------------------------------------------------

def _is_private_or_blocked_host(host: str) -> bool:
    if not host:
        return True
    host = host.lower().strip("[]")
    if host in {"localhost", "metadata.google.internal"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip == ipaddress.ip_address("169.254.169.254")
        )
    except ValueError:
        return host.endswith(".internal") or host.endswith(".local")

def _compact_execution_output(text: str) -> str:
    if not text:
        return text
    text = text.replace("\r\n", "\n").replace("\r", "\n")
            # collapse runs of spaces/tabs to one space
    text = re.sub(r"[ \t]+", " ", text)
            # drop leftover indent on each line
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
            # collapse 2+ blank lines to one newline (no empty gap)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def _path_allowed(raw: str) -> tuple[bool, str]:
    if not raw:
        return False, "empty path"
    expanded = os.path.expanduser(os.path.expandvars(raw))
    try:
        resolved = Path(expanded).resolve()
    except Exception as e:
        return False, f"cannot resolve {raw!r}: {e}"

    for denied in DENIED_ROOTS:
        try:
            if resolved == denied or denied in resolved.parents or resolved in denied.parents:
                # "resolved in denied.parents" is wrong for files; keep prefix check
                pass
        except Exception:
            pass
        try:
            resolved.relative_to(denied)
            return False, f"path {resolved} is under denied root {denied}"
        except ValueError:
            continue

    for allowed in ALLOWED_ROOTS:
        try:
            resolved.relative_to(allowed)
            return True, str(resolved)
        except ValueError:
            continue
    return False, f"path {resolved} is outside allowed roots {ALLOWED_ROOTS}"

def _collect_string_literals(code: str) -> list[str]:
    out = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                out.append(node.value)
    except SyntaxError:
        out.extend(m.group(1) for m in STRING_PATH_RE.finditer(code))
    out.extend(m.group(1) for m in STRING_PATH_RE.finditer(code))
    return out

def check_code_policy(code: str) -> list[str]:
    violations = []

    if NETWORK_NAME_RE.search(code):
        violations.append(
            "network or process APIs are blocked in execute(); "
            "use dedicated tools for web/API access"
        )

    # URL-looking strings
    for lit in _collect_string_literals(code):
        if "://" in lit:
            try:
                parsed = urlparse(lit)
            except Exception:
                violations.append(f"invalid URL {lit!r}")
                continue
            if parsed.hostname and _is_private_or_blocked_host(parsed.hostname):
                violations.append(f"blocked host {parsed.hostname}")

        looks_like_path = (
            lit.startswith(("/", "~", ".", ".."))
            or "/" in lit
            or lit.endswith((".csv", ".tsv", ".h5", ".h5ad", ".parquet", ".pkl", ".pt", ".npy", ".zip"))
        )
        if looks_like_path and len(lit) < 512:
            ok, msg = _path_allowed(lit)
            if not ok and any(tok in lit for tok in ("/", "..", "~", "raw", "data", "home", "etc")):
                violations.append(msg)

    return violations

def install_runtime_guards(allowed_roots: list[Path], denied_roots: list[Path]) -> None:
    """Best-effort in-process guards. Not a substitute for container network=none."""
    allowed = [p.resolve() for p in allowed_roots]
    denied = [p.resolve() for p in denied_roots]

    def _guard_path(path, mode="r"):
        ok, msg = _path_allowed(str(path))
        if not ok:
            raise PermissionError(f"filesystem policy: {msg}")
        return path

    builtin_open = __builtins__["open"] if isinstance(__builtins__, dict) else __builtins__.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(c in str(mode) for c in "rwxa+"):
            _guard_path(file, mode)
        return builtin_open(file, mode, *args, **kwargs)

    if isinstance(__builtins__, dict):
        __builtins__["open"] = guarded_open
    else:
        __builtins__.open = guarded_open

    _real_connect = socket.socket.connect

    def _blocked_connect(self, address):
        raise PermissionError(
            "network is disabled inside execute(); use a dedicated internet tool"
        )

    socket.socket.connect = _blocked_connect
    socket.socket.connect_ex = lambda *a, **k: (_ for _ in ()).throw(
        PermissionError("network is disabled inside execute()")
    )