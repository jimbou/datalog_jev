"""Ask a model through a locally logged-in coding CLI instead of an HTTP API.

BACKEND=claude  Claude Code headless (`claude -p`): our system prompt replaces Claude Code's, no tools, one turn.
BACKEND=codex   Codex (`codex exec`): read-only sandbox, the system text is prepended to the prompt.
Neither CLI exposes the sampling temperature, so answers are not forced to be deterministic (the API runs used 0).
Calls run in an empty directory so no project context is picked up. Returns the model's text answer.
"""
import json, os, shutil, subprocess, tempfile, threading

WORKDIR = tempfile.mkdtemp(prefix="cli_llm_")
PROXY = os.path.expanduser("~/ai-proxy/with-proxy")
PREFIX = [PROXY] if os.path.exists(PROXY) else []


def _bin(name):  # ~/.local/bin on the PKU server; elsewhere (e.g. a Claude Code cloud session) whatever is on PATH
    p = os.path.expanduser("~/.local/bin/" + name)
    return p if os.path.exists(p) else shutil.which(name) or p


CLAUDE, CODEX = os.environ.get("CLAUDE_BIN") or _bin("claude"), _bin("codex")
_LAST = threading.local()


def last_cost():
    """API-equivalent cost (total_cost_usd) of this thread's last Claude Code call; 0 for Codex, which reports none."""
    return getattr(_LAST, "cost", 0.0)


def chat(backend, model, system, user, timeout=300):
    if backend == "claude":
        cmd = PREFIX + [CLAUDE, "-p", user, "--model", model, "--system-prompt", system,
                        "--tools", "", "--output-format", "json", "--max-turns", "1"]
        out = subprocess.run(cmd, cwd=WORKDIR, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        d = json.loads(out.stdout)
        _LAST.cost = d.get("total_cost_usd") or 0.0
        if d.get("is_error"):
            raise RuntimeError("claude: %s" % d.get("result"))
        return d["result"]
    if backend == "codex":
        with tempfile.NamedTemporaryFile("r", suffix=".txt", dir=WORKDIR) as last:
            cmd = PREFIX + [CODEX, "exec", "--skip-git-repo-check", "--sandbox", "read-only",
                            "-m", model, "--output-last-message", last.name, system + "\n\n" + user]
            out = subprocess.run(cmd, cwd=WORKDIR, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            text = open(last.name).read()
            if out.returncode or not text.strip():
                raise RuntimeError("codex rc=%d: %s" % (out.returncode, out.stderr[-300:]))
            return text
    raise ValueError("unknown backend %r" % backend)
