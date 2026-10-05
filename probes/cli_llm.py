"""Ask a model through a locally logged-in coding CLI instead of an HTTP API.

BACKEND=claude  Claude Code headless (`claude -p`): our system prompt replaces Claude Code's, no tools, one turn.
BACKEND=codex   Codex (`codex exec`): read-only sandbox, the system text is prepended to the prompt.
Neither CLI exposes the sampling temperature, so answers are not forced to be deterministic (the API runs used 0).
Calls run in an empty directory so no project context is picked up. Returns the model's text answer.
"""
import json, os, subprocess, tempfile

WORKDIR = tempfile.mkdtemp(prefix="cli_llm_")
PROXY = os.path.expanduser("~/ai-proxy/with-proxy")
PREFIX = [PROXY] if os.path.exists(PROXY) else []


def chat(backend, model, system, user, timeout=300):
    if backend == "claude":
        cmd = PREFIX + [os.path.expanduser("~/.local/bin/claude"), "-p", user, "--model", model, "--system-prompt", system,
                        "--tools", "", "--output-format", "json", "--max-turns", "1"]
        out = subprocess.run(cmd, cwd=WORKDIR, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        d = json.loads(out.stdout)
        if d.get("is_error"):
            raise RuntimeError("claude: %s" % d.get("result"))
        return d["result"]
    if backend == "codex":
        with tempfile.NamedTemporaryFile("r", suffix=".txt", dir=WORKDIR) as last:
            cmd = PREFIX + [os.path.expanduser("~/.local/bin/codex"), "exec", "--skip-git-repo-check", "--sandbox", "read-only",
                            "-m", model, "--output-last-message", last.name, system + "\n\n" + user]
            out = subprocess.run(cmd, cwd=WORKDIR, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            text = open(last.name).read()
            if out.returncode or not text.strip():
                raise RuntimeError("codex rc=%d: %s" % (out.returncode, out.stderr[-300:]))
            return text
    raise ValueError("unknown backend %r" % backend)
