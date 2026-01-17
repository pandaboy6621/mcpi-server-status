import json, os
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# The HTML you provided (Paste it inside the triple quotes)
HTML_LAYOUT = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>MCPI Server Status</title>
    <style>
        :root{--bg:#0f1720;--card:#0b1220;--muted:#9aa4b2;--accent:#34d399;--danger:#fb7185}
        html,body{height:100%;margin:0;font-family:Inter,system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:linear-gradient(180deg,#061226 0%, #071a2a 100%);color:#e6eef6}
        .wrap{max-width:1000px;margin:32px auto;padding:20px}
        header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
        h1{font-size:20px;margin:0}
        .meta{font-size:13px;color:var(--muted)}
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}
        .card{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));padding:14px;border-radius:10px;box-shadow:0 2px 10px rgba(2,6,23,0.6)}
        .row{display:flex;align-items:center;gap:10px}
        .name{font-weight:600}
        .status{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
        .dot{width:10px;height:10px;border-radius:50%;background:gray;box-shadow:0 0 6px rgba(0,0,0,0.6)}
        .dot.online{background:var(--accent);box-shadow:0 0 10px rgba(52,211,153,0.2)}
        .dot.offline{background:var(--danger);opacity:0.9}
        .version{font-size:13px;color:var(--muted);margin-top:8px}
        .uptime{margin-top:12px;display:flex;flex-direction:column;gap:8px}
        .bar{height:10px;background:rgba(255,255,255,0.06);border-radius:999px;overflow:hidden}
        .bar > i{display:block;height:100%;width:0%;background:linear-gradient(90deg,var(--accent),#60a5fa);transition:width 800ms cubic-bezier(.2,.9,.2,1)}
        .hb{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
        .pulse{width:12px;height:12px;border-radius:50%;background:var(--accent);box-shadow:0 0 12px rgba(52,211,153,0.3);opacity:0;transform:scale(.8)}
        .pulse.heartbeat{animation:beat 1s infinite}
        @keyframes beat{0%{opacity:.3;transform:scale(.85)}50%{opacity:1;transform:scale(1.2)}100%{opacity:.35;transform:scale(.9)}}
        footer{margin-top:16px;color:var(--muted);font-size:13px;display:flex;justify-content:space-between}
        .empty{color:var(--muted);padding:20px;border-radius:8px;background:rgba(255,255,255,0.02);text-align:center}
    </style>
</head>
<body>
    <div class="wrap">
        <header>
            <div>
                <h1>MCPI Server Status</h1>
                <div class="meta">Auto-refresh every 10s • Shows online state, MCPI version, and uptime heartbeat</div>
            </div>
            <div class="meta" id="lastUpdated">Last update: —</div>
        </header>
        <main id="main"><div class="empty">Loading server status…</div></main>
        <footer>
            <div class="meta">Data source: status.json</div>
            <div class="meta">GitHub Copilot Style</div>
        </footer>
    </div>
    <script>
        // Use the exact JavaScript you provided
        const main = document.getElementById('main');
        const lastUpdatedEl = document.getElementById('lastUpdated');
        function sToHms(s){
            if (!s || s<=0) return '0s';
            s = Math.floor(s);
            const h = Math.floor(s/3600); s%=3600;
            const m = Math.floor(s/60); const sec = s%60;
            return (h? h+'h ':'') + (m? m+'m ':'') + sec+'s';
        }
        async function fetchStatus(){
            try{
                const res = await fetch('/status.json', {cache:'no-store'});
                return await res.json();
            }catch(e){ return null; }
        }
        function render(servers){
            if(!Array.isArray(servers) || servers.length===0){
                main.innerHTML = '<div class="empty">No servers found.</div>';
                return;
            }
            const grid = document.createElement('div');
            grid.className = 'grid';
            servers.forEach(s=>{
                const card = document.createElement('div'); card.className='card';
                const row = document.createElement('div'); row.className='row';
                const name = document.createElement('div'); name.className='name'; name.textContent = s.name || 'unknown';
                const statusWrap = document.createElement('div'); statusWrap.className='status';
                const dot = document.createElement('span'); dot.className='dot ' + (s.online ? 'online' : 'offline');
                const sttext = document.createElement('span'); sttext.textContent = s.online ? 'Online' : 'Offline';
                statusWrap.appendChild(dot); statusWrap.appendChild(sttext);
                row.appendChild(name); row.appendChild(statusWrap);
                card.appendChild(row);
                const ver = document.createElement('div'); ver.className='version';
                ver.textContent = 'Version: ' + (s.version || '—');
                card.appendChild(ver);
                const up = document.createElement('div'); up.className='uptime';
                const hb = document.createElement('div'); hb.className='hb';
                const pulse = document.createElement('span'); pulse.className='pulse' + (s.online ? ' heartbeat' : '');
                const uptText = document.createElement('span'); uptText.textContent = s.online ? ('Uptime: '+ sToHms(s.uptime_seconds)) : (s.last_seen ? ('Last seen: '+ new Date(s.last_seen).toLocaleString()) : 'Uptime: —');
                hb.appendChild(pulse); hb.appendChild(uptText);
                up.appendChild(hb);
                const barWrap = document.createElement('div'); barWrap.className='bar';
                const barInner = document.createElement('i');
                const pct = Math.min(100, Math.round(( (s.uptime_seconds||0) / (24*3600) ) * 100));
                barInner.style.width = (s.online ? pct : 0) + '%';
                barWrap.appendChild(barInner);
                up.appendChild(barWrap);
                card.appendChild(up);
                grid.appendChild(card);
            });
            main.innerHTML = '';
            main.appendChild(grid);
        }
        async function refresh(){
            const data = await fetchStatus();
            lastUpdatedEl.textContent = 'Last update: ' + new Date().toLocaleString();
            render(data);
        }
        refresh();
        setInterval(refresh, 10000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_LAYOUT)

@app.route('/status.json')
def status_json():
    # This reads the file created by ping.py and returns it to the browser
    if os.path.exists("status.json"):
        with open("status.json", "r") as f:
            data = json.load(f)
        return jsonify(data)
    return jsonify([])

if __name__ == "__main__":
    app.run(debug=True, port=5000)