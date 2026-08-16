#!/usr/bin/env python3
"""NSosyal B* -- offline demo. One local screen, three systems side by side.

Runs with networking disabled. That constraint drives two design choices:

  * No Gradio / Streamlit. Both fetch fonts and telemetry from CDNs at page
    load, so a "no network" demo built on them fails the moment it is actually
    disconnected. This is stdlib http.server with inline CSS -- no dependency,
    no external asset, offline by construction.
  * HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE are set BEFORE transformers is
    imported, and every from_pretrained call points at a local directory. If an
    asset is missing the demo fails loudly at startup rather than hanging on a
    socket in front of an audience.

Usage:
    python demo/app.py --assets demo_assets [--port 8000] [--no-browser]
"""

import argparse
import html
import json
import os
import socketserver
import sys
import unicodedata
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Must precede the transformers import, not follow it.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import lexicon

MAX_CHARS = 4000          # hard cap on accepted input; longer is truncated
MAX_LEN = 128             # the token budget every reported number was measured at

STATE = {}                # models, tokenizer, lexicon, operating point


# --------------------------------------------------------------------------
# input hygiene
# --------------------------------------------------------------------------

def clean_input(raw):
    """Make any input safe to run, and say what was done to it.

    Returns (text, notes). Never raises: the demo has to survive an empty box,
    a pasted novel, an emoji wall and English, because all four will happen.
    """
    notes = []
    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        raw = str(raw)

    # Strip control characters (except tab/newline) -- pasted text from PDFs and
    # terminals carries them and they break the tokenizer's assumptions.
    cleaned = "".join(c for c in raw
                      if c in "\t\n" or not unicodedata.category(c).startswith("C"))
    if cleaned != raw:
        notes.append("removed control characters")

    cleaned = cleaned.strip()
    if len(cleaned) > MAX_CHARS:
        cleaned = cleaned[:MAX_CHARS]
        notes.append(f"truncated to {MAX_CHARS} characters")

    if not cleaned:
        return "", ["empty input -- nothing to classify"]

    # Text with no letters or digits at all (emoji only, punctuation only) is
    # accepted and classified, but flagged: the model has essentially nothing to
    # work with and its confidence should not be read as meaningful.
    if not any(c.isalnum() for c in cleaned):
        notes.append("no alphanumeric characters -- the model has no lexical "
                     "signal here and its confidence is not meaningful")
    return cleaned, notes


# --------------------------------------------------------------------------
# the three systems
# --------------------------------------------------------------------------

def keyword_decision(text, lex):
    """Matrix row 1: the frozen Day 1 lexicon with agglutination-aware roots.

    The decision comes from `lexicon.hit_root` itself -- the same function that
    tagged every slice in every phase. It takes the whole string and tokenises
    internally, so re-splitting the text here would quietly create a second,
    drifting copy of the matching rule.
    """
    decision = "OFF" if lexicon.hit_root(text, lex) else "NOT"

    # Display only. This mirrors hit_root's inner rule to show WHICH token fired,
    # and is never consulted for the decision above.
    hits = []
    for t in lexicon.tokens(text):
        for root in lex:
            if len(root) >= lexicon.MIN_ROOT_LEN and t.startswith(root):
                hits.append(f"{t} ← {root}")
                break
    return decision, hits


def model_decision(name, text):
    import torch

    tok, model = STATE["tokenizer"], STATE["models"][name]
    enc = tok([text], truncation=True, max_length=MAX_LEN,
              padding=True, return_tensors="pt")
    enc = {k: v.to(STATE["device"]) for k, v in enc.items()}
    with torch.no_grad():
        logits = model(**enc).logits[0]
        p_off = float(torch.softmax(logits, dim=-1)[1])
    return ("OFF" if p_off >= 0.5 else "NOT"), p_off


def classify(raw):
    """Everything the page shows for one input."""
    text, notes = clean_input(raw)
    if not text:
        return {"ok": False, "notes": notes, "text": ""}

    kw, hits = keyword_decision(text, STATE["lexicon"])
    out = {"ok": True, "text": text, "notes": notes,
           "n_chars": len(text), "n_tokens": len(STATE["tokenizer"].tokenize(text)),
           "systems": {"keyword": {"decision": kw, "confidence": None,
                                   "detail": ("lexicon roots matched: " + ", ".join(hits))
                                   if hits else "no lexicon root matched"}}}
    for name in ("raw", "1a1b_d"):
        d, p = model_decision(name, text)
        out["systems"][name] = {"decision": d, "confidence": p,
                                "detail": f"P(OFF) = {p:.4f}"}

    # Selective prediction uses the RAW model at the frozen phase-04 threshold.
    op = STATE["operating_point"]
    p = out["systems"]["raw"]["confidence"]
    conf = max(p, 1.0 - p)
    auto = conf >= op["threshold"]
    out["selective"] = {
        "confidence": conf,
        "threshold": op["threshold"],
        "route": "AUTO-RESOLVE" if auto else "DEFER TO REVIEW",
        "decision": out["systems"]["raw"]["decision"] if auto else None,
        "margin": conf - op["threshold"],
    }
    return out


# --------------------------------------------------------------------------
# page
# --------------------------------------------------------------------------

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font-family: ui-monospace, "Cascadia Mono", "DejaVu Sans Mono", monospace;
       margin: 0; padding: 1.5rem; line-height: 1.5;
       background: #fbfbfa; color: #1a1a1a; }
@media (prefers-color-scheme: dark) { body { background: #16181c; color: #e6e6e6; } }
main { max-width: 60rem; margin: 0 auto; }
h1 { font-size: 1.15rem; margin: 0 0 .25rem; }
.sub { opacity: .7; font-size: .8rem; margin-bottom: 1.25rem; }
textarea { width: 100%; min-height: 6rem; font: inherit; padding: .6rem;
           border: 1px solid #8886; border-radius: 4px; background: transparent;
           color: inherit; }
button { font: inherit; padding: .45rem 1.1rem; margin-top: .5rem; cursor: pointer;
         border: 1px solid #8886; border-radius: 4px; background: transparent;
         color: inherit; }
button:hover { border-color: currentColor; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .88rem; }
th, td { text-align: left; padding: .4rem .6rem; border-bottom: 1px solid #8883;
         vertical-align: top; }
th { font-weight: 600; opacity: .75; }
.OFF { font-weight: 700; }
.tag { display: inline-block; padding: .05rem .4rem; border: 1px solid currentColor;
       border-radius: 3px; font-size: .78rem; }
.route { padding: .7rem .9rem; border: 1px solid #8886; border-radius: 4px;
         margin: .75rem 0; font-size: .9rem; }
.notes { font-size: .82rem; opacity: .8; margin: .4rem 0; }
.ex { margin: .3rem 0; font-size: .84rem; }
.ex button { margin: 0 .5rem 0 0; padding: .15rem .5rem; font-size: .78rem; }
.fam { opacity: .65; font-size: .78rem; margin: .9rem 0 .3rem; }
footer { margin-top: 2rem; font-size: .78rem; opacity: .65; }
code { background: #8881; padding: 0 .25rem; border-radius: 3px; }
"""

JS = """
async function run(t) {
  if (t !== undefined) document.getElementById('inp').value = t;
  const r = document.getElementById('out');
  r.textContent = 'classifying...';
  try {
    const resp = await fetch('/api/classify', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: document.getElementById('inp').value})
    });
    r.innerHTML = await resp.text();
  } catch (e) { r.textContent = 'error: ' + e; }
}
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') run();
});
"""


def render_result(res):
    if not res["ok"]:
        return f"<p class='notes'>{html.escape(' / '.join(res['notes']))}</p>"

    rows = []
    label = {"keyword": "keyword filter",
             "raw": "BERTurk raw",
             "1a1b_d": "BERTurk +1a+1b+D"}
    for key in ("keyword", "raw", "1a1b_d"):
        s = res["systems"][key]
        conf = f"{s['confidence']:.4f}" if s["confidence"] is not None else "—"
        rows.append(
            f"<tr><td>{label[key]}</td>"
            f"<td class='{s['decision']}'><span class='tag'>{s['decision']}</span></td>"
            f"<td>{conf}</td><td>{html.escape(s['detail'])}</td></tr>")

    sel = res["selective"]
    verdict = (f"<b>{sel['route']}</b> &nbsp; as <b>{sel['decision']}</b>"
               if sel["decision"] else f"<b>{sel['route']}</b>")
    notes = (f"<p class='notes'>note: {html.escape(' / '.join(res['notes']))}</p>"
             if res["notes"] else "")

    return f"""
{notes}
<table>
  <tr><th>system</th><th>decision</th><th>P(OFF)</th><th>detail</th></tr>
  {''.join(rows)}
</table>
<div class='route'>
  Review layer at the 90.2%-coverage operating point &nbsp;&rarr;&nbsp; {verdict}<br>
  decision confidence max(p, 1-p) = <code>{sel['confidence']:.4f}</code>,
  threshold <code>{sel['threshold']:.4f}</code>,
  margin <code>{sel['margin']:+.4f}</code>
</div>
<p class='notes'>{res['n_chars']} characters, {res['n_tokens']} wordpiece tokens
(model sees the first {MAX_LEN}).</p>
"""


def render_page():
    ex = []
    for fam in ("implicit offense, no profanity token",
                "profanity token present, no offensive act"):
        ex.append(f"<div class='fam'>{html.escape(fam)}</div>")
        for e in STATE["examples"]:
            if e["family"] != fam:
                continue
            t = html.escape(e["text"]).replace("'", "&#39;")
            js = json.dumps(e["text"])
            ex.append(
                f"<div class='ex'><button onclick='run({html.escape(js)})'>"
                f"{e['phase02_tag']}</button>"
                f"<span class='tag'>gold {e['gold']}</span> {t}</div>")

    op = STATE["operating_point"]
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NSosyal B* — offline demo</title><style>{CSS}</style></head><body><main>
<h1>NSosyal B* — Turkish offensive language, three systems side by side</h1>
<div class="sub">Runs fully offline. Local checkpoints only, no network calls.
Device: {STATE['device']}.</div>

<textarea id="inp" placeholder="Türkçe bir metin yapıştırın…"></textarea><br>
<button onclick="run()">Classify (Ctrl+Enter)</button>
<div id="out"></div>

<h2 style="font-size:.95rem;margin-top:2rem">Examples from our analysed rows</h2>
<div class="sub">Real dev rows from the phase 02 failure analysis, with the
function tag we assigned. Both error directions are represented.</div>
{''.join(ex)}

<footer>
Review layer: raw BERTurk, confidence threshold <code>{op['threshold']:.4f}</code>,
selected on the dev calibration half in phase 04 and never re-derived.
On the official test set it achieved {op['test_coverage']:.1%} coverage at
{op['test_macro_f1']:.4f} macro-F1 / {op['test_error_rate']:.2%} error,
concentrating errors {op['test_capture_lift']:.2f}&times; in the deferred queue.<br>
Gold labels follow Çöltekin's annotation convention, adopted as given; nothing was relabelled.
</footer>
</main><script>{JS}</script></body></html>"""


# --------------------------------------------------------------------------
# server
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *a):        # keep the console readable
        pass

    def _send(self, body, ctype="text/html; charset=utf-8", code=200):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(render_page())
        else:
            self._send("<p>not found</p>", code=404)

    def do_POST(self):
        if self.path != "/api/classify":
            return self._send("<p>not found</p>", code=404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
            res = classify(payload.get("text", ""))
            self._send(render_result(res))
        except Exception as e:
            # A malformed request must never take the server down mid-demo.
            self._send(f"<p class='notes'>could not classify: "
                       f"{html.escape(type(e).__name__)}: {html.escape(str(e))}</p>")


class Server(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True     # so a second cold start is not blocked by TIME_WAIT


def load_assets(assets):
    import torch
    from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

    assets = Path(assets)
    missing = [p for p in ("tokenizer", "checkpoints/raw.pt",
                           "checkpoints/1a1b_d.pt", "lexicon/karaliste.txt",
                           "operating_point.json")
               if not (assets / p).exists()]
    if missing:
        sys.exit(f"ABORT: asset bundle at {assets} is incomplete: {missing}\n"
                 "Run demo/build_assets.py once on a machine with network.")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"loading assets from {assets} (device: {device}) ...")

    tok = AutoTokenizer.from_pretrained(assets / "tokenizer", local_files_only=True)
    cfg = AutoConfig.from_pretrained(assets / "tokenizer", local_files_only=True)
    models = {}
    for name in ("raw", "1a1b_d"):
        m = AutoModelForSequenceClassification.from_config(cfg)
        state = torch.load(assets / "checkpoints" / f"{name}.pt",
                           map_location=device, weights_only=False)
        m.load_state_dict(state["model"])
        m.to(device).eval()
        models[name] = m
        print(f"  {name:<8} loaded (dev macro-F1 {state.get('dev_macro_f1'):.4f})")

    STATE.update(
        tokenizer=tok, models=models, device=device,
        lexicon=lexicon.load_lexicon(assets / "lexicon" / "karaliste.txt"),
        operating_point=json.loads((assets / "operating_point.json").read_text(encoding="utf-8")),
        examples=json.loads((Path(__file__).parent / "examples.json").read_text(encoding="utf-8")),
    )
    print(f"  lexicon  {len(STATE['lexicon']):,} entries")
    print(f"  examples {len(STATE['examples'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default=None)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--selftest", action="store_true",
                    help="classify the hostile inputs and exit; no server")
    args = ap.parse_args()

    load_assets(args.assets or Path(__file__).resolve().parents[1] / "demo_assets")

    if args.selftest:
        cases = [("empty", ""), ("spaces", "     "), ("emoji", "🔥🔥🔥😀"),
                 ("english", "This is a perfectly ordinary English sentence."),
                 ("very long", "çok uzun bir metin " * 900),
                 ("control chars", "merhaba\x00\x07 dünya"),
                 ("single char", "a"), ("punctuation", "!!!???..."),
                 ("turkish caps", "İIıi ŞĞÜÖÇ"), ("newlines", "bir\niki\nüç")]
        for label, text in cases:
            r = classify(text)
            if r["ok"]:
                s = r["systems"]
                print(f"  {label:<14} kw={s['keyword']['decision']} "
                      f"raw={s['raw']['decision']}({s['raw']['confidence']:.3f}) "
                      f"def={s['1a1b_d']['decision']} -> {r['selective']['route']}")
            else:
                print(f"  {label:<14} rejected: {r['notes']}")
        print("\nselftest OK -- no exceptions")
        return

    with Server((args.host, args.port), Handler) as httpd:
        url = f"http://{args.host}:{args.port}/"
        print("\n" + "=" * 64)
        print(f"  NSosyal B* demo -> {url}")
        print("  offline: HF_HUB_OFFLINE=1, no external assets, no CDN")
        print("  Ctrl+C to stop")
        print("=" * 64)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopping ...")
        finally:
            httpd.shutdown()


if __name__ == "__main__":
    main()
