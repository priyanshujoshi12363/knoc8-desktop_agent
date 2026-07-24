import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
from logger import get_logger
from settings import load_env, save_env

log = get_logger("settings-web")

# group, key, label, type, options, default, secret
FIELDS = [
    ("General", "KNOC8_LLM_PROVIDER", "LLM provider", "select",
     ["ollama", "anthropic", "openai"], "ollama", False),
    ("General", "KNOC8_WAKE_WORD", "Wake word", "text", None, "hey agent", False),
    ("General", "KNOC8_SERIAL_PORT", "ESP32 COM port", "text", None, "COM17", False),
    ("General", "KNOC8_SERIAL_BAUD", "Serial baud rate", "number", None, "921600", False),

    ("Ollama", "OLLAMA_API_KEY", "Ollama Cloud API key", "password", None, "", True),
    ("Ollama", "KNOC8_LLM_MODEL", "Ollama model", "model",
     ["minimax-m3", "minimax-m2.7", "minimax-m2.5", "glm-5.2", "glm-5.1",
      "kimi-k2.5", "kimi-k2.7-code", "deepseek-v4-pro", "deepseek-v4-flash",
      "nemotron-3-ultra", "nemotron-3-nano:30b", "mistral-large-3:675b",
      "gpt-oss:20b"], "minimax-m3", False),

    ("Anthropic (Claude)", "ANTHROPIC_API_KEY", "Anthropic API key", "password", None, "", True),
    ("Anthropic (Claude)", "KNOC8_ANTHROPIC_MODEL", "Claude model", "model",
     ["claude-opus-4-8", "claude-opus-4-7", "claude-sonnet-4-6",
      "claude-haiku-4-5", "claude-fable-5"], "claude-opus-4-8", False),

    ("OpenAI", "OPENAI_API_KEY", "OpenAI API key", "password", None, "", True),
    ("OpenAI", "KNOC8_OPENAI_MODEL", "OpenAI model", "model",
     ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4-turbo", "o1", "o1-mini",
      "o3-mini"], "gpt-4o", False),
    ("OpenAI", "OPENAI_BASE_URL", "OpenAI base URL (optional)", "text", None, "", False),

    ("Voice & Audio", "KNOC8_WHISPER_MODEL", "Whisper model (tiny/base/small)", "text", None, "base", False),
    ("Voice & Audio", "KNOC8_TTS_RATE", "Voice speed (words/min)", "number", None, "175", False),
    ("Voice & Audio", "KNOC8_MIC_THRESHOLD", "Mic sensitivity (lower = more sensitive)", "number", None, "300", False),
    ("Voice & Audio", "KNOC8_SILENCE_MS", "Silence that ends a command (ms)", "number", None, "1200", False),
    ("Voice & Audio", "KNOC8_NOISE_REDUCTION", "Noise cancellation (1 on / 0 off)", "text", None, "1", False),

    ("Browser", "KNOC8_CHROME_PROFILE", "Default Chrome profile (blank = ask)", "text", None, "", False),
]

_server: ThreadingHTTPServer | None = None
_MASK = "•••• saved"


def _schema_payload(values: dict[str, str]) -> list[dict]:
    out = []
    for group, key, label, ftype, options, default, secret in FIELDS:
        current = values.get(key, "")
        out.append({
            "group": group, "key": key, "label": label, "type": ftype,
            "options": options, "default": default, "secret": secret,
            "value": (_MASK if (secret and current) else current),
            "isSet": bool(current),
        })
    return out


def _apply(posted: dict[str, str]) -> None:
    values = load_env()
    for group, key, label, ftype, options, default, secret in FIELDS:
        if key not in posted:
            continue
        submitted = str(posted[key]).strip()
        if secret:
            if submitted and submitted != _MASK:
                values[key] = submitted
        else:
            if submitted:
                values[key] = submitted
            else:
                values.pop(key, None)
    save_env(values)
    log.info("Settings saved via web UI")


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/config"):
            self._send(200, json.dumps(_schema_payload(load_env())),
                       "application/json")
        else:
            self._send(200, PAGE)

    def do_POST(self):
        if not self.path.startswith("/api/config"):
            self._send(404, "not found")
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            _apply(json.loads(raw))
            self._send(200, json.dumps({"ok": True}), "application/json")
        except Exception as exc:
            self._send(400, json.dumps({"ok": False, "error": str(exc)}),
                       "application/json")


def launch(open_browser: bool = True) -> str:
    global _server
    url = f"http://127.0.0.1:{config.SETTINGS_PORT}"
    if _server is None:
        _server = ThreadingHTTPServer(("127.0.0.1", config.SETTINGS_PORT), _Handler)
        threading.Thread(target=_server.serve_forever, daemon=True).start()
        log.info("Settings web UI running at %s", url)
    if open_browser:
        webbrowser.open(url)
    return url


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Knoc8 Settings</title>
<style>
  :root{
    --bg:#0a0a0a; --panel:#141414; --panel2:#1c1c1c; --border:#2a2a2a;
    --text:#f5f5f5; --muted:#8a8a8a; --accent:#ffffff; --field:#101010;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:'Segoe UI',system-ui,-apple-system,sans-serif;line-height:1.5}
  header{position:sticky;top:0;background:rgba(10,10,10,.85);
    backdrop-filter:blur(10px);border-bottom:1px solid var(--border);
    padding:20px 32px;display:flex;align-items:center;justify-content:space-between;z-index:10}
  .brand{display:flex;align-items:center;gap:12px}
  .logo{width:34px;height:34px;border-radius:9px;background:var(--text);
    color:var(--bg);display:grid;place-items:center;font-weight:800;font-size:18px}
  h1{font-size:18px;margin:0;letter-spacing:.3px}
  .sub{font-size:12px;color:var(--muted)}
  main{max-width:820px;margin:0 auto;padding:32px}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:14px;
    margin-bottom:20px;overflow:hidden}
  .card h2{font-size:13px;text-transform:uppercase;letter-spacing:1.2px;
    color:var(--muted);margin:0;padding:16px 22px;border-bottom:1px solid var(--border);
    background:var(--panel2)}
  .row{display:flex;align-items:center;gap:20px;padding:16px 22px;
    border-bottom:1px solid var(--border)}
  .row:last-child{border-bottom:none}
  .row label{flex:0 0 46%;font-size:14px}
  .row .set{display:block;font-size:11px;color:var(--muted);margin-top:2px}
  input,select{flex:1;background:var(--field);border:1px solid var(--border);
    color:var(--text);padding:11px 13px;border-radius:9px;font-size:14px;outline:none;
    transition:border-color .15s,box-shadow .15s;min-width:0}
  input:focus,select:focus{border-color:#666;box-shadow:0 0 0 3px rgba(255,255,255,.06)}
  select,.combo{appearance:none;cursor:pointer;
    background-image:linear-gradient(45deg,transparent 50%,var(--muted) 50%),
      linear-gradient(135deg,var(--muted) 50%,transparent 50%);
    background-position:calc(100% - 18px) 50%,calc(100% - 13px) 50%;
    background-size:5px 5px,5px 5px;background-repeat:no-repeat;padding-right:34px}
  .combo{cursor:text}
  input::-webkit-calendar-picker-indicator{opacity:0;cursor:pointer}
  .bar{position:sticky;bottom:0;background:rgba(10,10,10,.9);backdrop-filter:blur(10px);
    border-top:1px solid var(--border);padding:16px 32px;display:flex;
    align-items:center;justify-content:space-between}
  .note{font-size:12px;color:var(--muted)}
  button{background:var(--text);color:var(--bg);border:none;padding:12px 26px;
    border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;
    transition:opacity .15s,transform .05s}
  button:hover{opacity:.88}button:active{transform:translateY(1px)}
  #toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%) translateY(20px);
    background:var(--panel2);border:1px solid var(--border);color:var(--text);
    padding:12px 22px;border-radius:10px;font-size:14px;opacity:0;pointer-events:none;
    transition:all .25s}
  #toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
  #toast.err{border-color:#5a2a2a}
</style>
</head>
<body>
<header>
  <div class="brand">
    <div class="logo">K</div>
    <div><h1>Knoc8 Settings</h1><div class="sub">Desktop Agent configuration</div></div>
  </div>
  <div class="sub">local &middot; 127.0.0.1</div>
</header>
<main id="app"></main>
<div class="bar">
  <span class="note">Changes apply on next restart (or replug the device).</span>
  <button id="save">Save changes</button>
</div>
<div id="toast"></div>
<script>
let FIELDS=[];
function el(t,a={},...k){const e=document.createElement(t);
  for(const[x,v]of Object.entries(a)){if(x==='class')e.className=v;else e.setAttribute(x,v);}
  for(const c of k)e.append(c);return e;}
async function load(){
  FIELDS=await(await fetch('/api/config')).json();
  const app=document.getElementById('app');app.innerHTML='';
  const groups=[...new Set(FIELDS.map(f=>f.group))];
  for(const g of groups){
    const card=el('div',{class:'card'});card.append(el('h2',{},g));
    for(const f of FIELDS.filter(x=>x.group===g)){
      const row=el('div',{class:'row'});
      const lab=el('label',{},f.label);
      if(f.secret)lab.append(el('span',{class:'set'},f.isSet?'A key is saved. Leave blank to keep it.':'Not set.'));
      row.append(lab);
      let inp;
      if(f.type==='select'){inp=el('select',{'data-key':f.key});
        for(const o of f.options){const op=el('option',{value:o},o);if(o===f.value)op.selected=true;inp.append(op);}}
      else if(f.type==='model'){
        const dlid=f.key+'-dl';
        inp=el('input',{'data-key':f.key,list:dlid,value:f.value,placeholder:f.default||'',class:'combo'});
        const dl=el('datalist',{id:dlid});
        for(const o of f.options)dl.append(el('option',{value:o}));
        row.append(inp);row.append(dl);card.append(row);continue;
      }
      else{inp=el('input',{'data-key':f.key,type:f.type==='password'?'password':(f.type==='number'?'number':'text'),
        value:f.secret?'':f.value,placeholder:f.secret?(f.isSet?'•••• saved':'paste key'):(f.default||'')});}
      row.append(inp);card.append(row);
    }
    app.append(card);
  }
}
function toast(msg,err){const t=document.getElementById('toast');t.textContent=msg;
  t.className='show'+(err?' err':'');setTimeout(()=>t.className='',2200);}
document.getElementById('save').onclick=async()=>{
  const body={};document.querySelectorAll('[data-key]').forEach(i=>{body[i.dataset.key]=i.value;});
  const r=await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j=await r.json();
  if(j.ok){toast('Settings saved ✓');load();}else{toast('Error: '+j.error,true);}
};
load();
</script>
</body>
</html>"""


if __name__ == "__main__":
    launch()
    print(f"Knoc8 settings at http://127.0.0.1:{config.SETTINGS_PORT}  (Ctrl+C to stop)")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
