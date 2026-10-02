"""Answer the audit sheet in a browser, one question at a time (answers are saved on every click).

Usage: audit_ui.py [PORT]      then open http://127.0.0.1:PORT
Reads data/audit/audit_facts.csv (never the key file), writes data/audit/answers.csv
(id, answer, note, time). Already answered rows are skipped on restart; Back changes an answer.
"""
import csv, json, os, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS = os.path.join(ROOT, "data/audit/audit_facts.csv")
ANSWERS = os.path.join(ROOT, "data/audit/answers.csv")
ROWS = list(csv.DictReader(open(FACTS, newline="")))
ANS = {}
if os.path.exists(ANSWERS):
    ANS = {r["id"]: r for r in csv.DictReader(open(ANSWERS, newline=""))}


def save():
    tmp = ANSWERS + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "answer", "note", "time"])
        for r in ROWS:
            a = ANS.get(r["id"])
            if a:
                w.writerow([a["id"], a["answer"], a["note"], a["time"]])
    os.replace(tmp, ANSWERS)


def docs_link(cls):
    # package segments become folders, nested classes keep their dot: a.b.C$D -> a/b/C.D
    outer, _, inner = cls.partition("$")
    parts = outer.split(".")
    path = "/".join(parts[:-1] + [parts[-1] + ("." + inner.replace("$", ".") if inner else "")])
    return "https://developer.android.com/reference/" + path


def row_json(i):
    r = ROWS[i]
    a = ANS.get(r["id"], {})
    return {"index": i, "total": len(ROWS), "answered": len(ANS), "id": r["id"], "class": r["class"],
            "signature": r["signature"], "from": r["from"], "to": r["to"], "docs": docs_link(r["class"]),
            "answer": a.get("answer", ""), "note": a.get("note", "")}


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit questions</title><style>
:root{--bg:#fff;--fg:#1a1a1a;--mut:#666;--card:#f4f5f7;--line:#d6d8dc;--yes:#0b6b3a;--no:#a1262b;--unsure:#444}
@media(prefers-color-scheme:dark){:root{--bg:#15171a;--fg:#ececec;--mut:#9aa0a6;--card:#202328;--line:#3a3f46;--yes:#2e9e62;--no:#d4575c;--unsure:#8a9099}}
body{background:var(--bg);color:var(--fg);font:18px/1.5 system-ui,sans-serif;margin:0}
main{max-width:760px;margin:0 auto;padding:20px 16px 60px}
.bar{height:8px;background:var(--card);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:var(--yes)}
.small{color:var(--mut);font-size:15px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
code{font:15px ui-monospace,monospace;word-break:break-all}
.q{font-size:21px;margin:8px 0}.q b{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:0 6px}
.btns{display:flex;gap:12px;margin:18px 0}
button{flex:1;font:700 22px system-ui;padding:20px 8px;border:0;border-radius:10px;color:#fff;cursor:pointer}
#yes{background:var(--yes)}#no{background:var(--no)}#unsure{background:var(--unsure);font-size:17px;flex:.6}
.nav{display:flex;justify-content:space-between;align-items:center}
.nav button{flex:none;font:16px system-ui;padding:8px 14px;background:var(--card);color:var(--fg);border:1px solid var(--line)}
input{width:100%;box-sizing:border-box;font:16px system-ui;padding:8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
a{color:inherit}
</style></head><body><main>
<div class="small" id="prog"></div><div class="bar"><i id="fill" style="width:0"></i></div>
<div class="card"><div class="small">Method</div><div><code id="cls"></code></div><div><code id="sig"></code></div></div>
<div class="q">Suppose <b id="from"></b> holds a <b>secret</b> before this method runs.</div>
<div class="q">After the method finishes, does <b id="to"></b> hold that secret, or anything taken or built from it?</div>
<div class="small">Say YES if the secret could end up inside it, including inside its fields, its contents, or anything read out of it.
Say NO if the method cannot pass the secret there. "The receiver object (this)" means the object the method is called on. <a id="docs" target="_blank" rel="noopener">Open the documentation</a> if you need it.</div>
<div class="btns"><button id="yes">YES (Y)</button><button id="no">NO (N)</button><button id="unsure">NOT SURE (U)</button></div>
<input id="note" placeholder="Optional note">
<div class="nav" style="margin-top:14px"><button id="back">&larr; Back</button><span class="small" id="cur"></span><button id="next">Skip &rarr;</button></div>
<div class="small" style="margin-top:20px">Keys: Y = yes, N = no, U = not sure, Backspace = back. Every answer is saved right away.</div>
</main><script>
let i=0,row=null;const $=id=>document.getElementById(id);
async function load(k){const r=await fetch('/api/row?i='+k);if(!r.ok){return}row=await r.json();i=row.index;
$('cls').textContent=row.class;$('sig').textContent=row.signature;$('from').textContent=row.from;$('to').textContent=row.to;
$('docs').href=row.docs;$('note').value=row.note;
$('prog').textContent=row.answered+' of '+row.total+' answered';$('fill').style.width=(100*row.answered/row.total)+'%';
$('cur').textContent='question '+(i+1)+(row.answer?' (answered: '+row.answer+')':'');}
async function answer(a){if(!row)return;await fetch('/api/answer',{method:'POST',body:JSON.stringify({id:row.id,answer:a,note:$('note').value})});
if(i+1<row.total){await load(i+1)}else{await load(i);$('cur').textContent='last question saved. All done?'}}
$('yes').onclick=()=>answer('yes');$('no').onclick=()=>answer('no');$('unsure').onclick=()=>answer('unsure');
$('back').onclick=()=>load(Math.max(0,i-1));$('next').onclick=()=>load(Math.min(row.total-1,i+1));
document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT')return;const k=e.key.toLowerCase();
if(k==='y')answer('yes');else if(k==='n')answer('no');else if(k==='u')answer('unsure');else if(e.key==='Backspace'){e.preventDefault();load(Math.max(0,i-1))}});
fetch('/api/first').then(r=>r.json()).then(j=>load(j.index));
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/":
            self._send(200, PAGE, "text/html")
        elif path == "/api/first":
            first = next((k for k, r in enumerate(ROWS) if r["id"] not in ANS), len(ROWS) - 1)
            self._send(200, json.dumps({"index": first}))
        elif path == "/api/row":
            try:
                k = int(dict(p.split("=") for p in query.split("&"))["i"])
                self._send(200, json.dumps(row_json(k)))
            except Exception:
                self._send(400, "{}")
        else:
            self._send(404, "{}")

    def do_POST(self):
        if self.path != "/api/answer":
            return self._send(404, "{}")
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if d["answer"] in ("yes", "no", "unsure") and d["id"] in {r["id"] for r in ROWS}:
            ANS[d["id"]] = {"id": d["id"], "answer": d["answer"], "note": d.get("note", ""),
                            "time": time.strftime("%Y-%m-%d %H:%M:%S")}
            save()
            self._send(200, "{}")
        else:
            self._send(400, "{}")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print("open http://127.0.0.1:%d  (%d questions, %d already answered)" % (port, len(ROWS), len(ANS)), flush=True)
    HTTPServer(("127.0.0.1", port), H).serve_forever()
