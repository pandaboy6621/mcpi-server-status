import json, os, time
from flask import Flask, render_template_string, jsonify
import ping
import db

app = Flask(__name__)

HTML_LAYOUT = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>MCPI Server Status</title>
    <style>
        :root{
            --bg:#0f1720;
            --card:#0b1220;
            --muted:#9aa4b2;
            --accent:#34d399;
            --danger:#fb7185;
            --gradient-up: linear-gradient(180deg, #34d399 0%, #22c55e 100%);
            --gradient-down: linear-gradient(180deg, rgba(251, 113, 133, 0.4) 0%, rgba(251, 113, 133, 0.1) 100%);
        }
        
        @font-face {
            font-family: 'Mojangles'; 
            src: url('/static/fonts/molangles.ttf') format('truetype'); 
            font-weight: normal; font-style: normal; font-display: swap;
        }

        html,body{height:100%;margin:0;font-family:Inter,system-ui,sans-serif;background:linear-gradient(180deg,#061226 0%, #071a2a 100%);color:#e6eef6}
        .wrap{max-width:1100px;margin:32px auto;padding:20px}
        header{margin-bottom:24px}
        h1{font-size:24px;margin:0;font-family: 'Mojangles', sans-serif;}
        
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
        .card{background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:18px; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.3)}
        
        .row{display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px}
        .name{font-weight:600; font-family: 'Mojangles', monospace; font-size: 1.2rem; color:#fff}
        
        .status-badge{display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px}
        .dot{width:8px; height:8px; border-radius:50%}
        .online{color:var(--accent)}
        .online .dot{background:var(--accent); box-shadow:0 0 8px var(--accent)}
        .offline{color:var(--danger)}
        .offline .dot{background:var(--danger)}

        .details{font-size:13px; color:var(--muted); margin-bottom:12px; line-height:1.4}
        .details b{color:#cbd5e1}

        .hb-grid{display:flex; gap:2px; margin-top:10px; height:14px}
        .hb-seg{flex:1; height:100%; border-radius:1px; transition: transform 0.2s}
        .hb-seg:hover{transform: scaleY(1.3); z-index:10}
        .hb-seg.up{background: var(--gradient-up);}
        .hb-seg.down{background: var(--gradient-down);}
        
        .footer-meta{display:flex; justify-content:space-between; margin-top:12px; font-size:11px; color:var(--muted); border-top:1px solid rgba(255,255,255,0.05); padding-top:8px}
    </style>
</head>
<body>
    <div class="wrap">
        <header><h1>MCPI Server Status</h1></header>
        <main id="main"></main>
    </div>
    <script>
        function sToHms(s){
            if (!s || s<=0) return '0s';
            s = Math.floor(s);
            const h = Math.floor(s/3600); s%=3600;
            const m = Math.floor(s/60); const sec = s%60;
            return (h? h+'h ':'') + (m? m+'m ':'') + sec+'s';
        }

        async function refresh(){
            try {
                const [statusRes, historyRes] = await Promise.all([
                    fetch('/status.json'), fetch('/history.json')
                ]);
                const servers = await statusRes.json();
                const historyList = await historyRes.json();
                const historyMap = {};
                historyList.forEach(i => { historyMap[i.address] = i.buckets; });

                let html = '<div class="grid">';
                servers.forEach(s => {
                    const buckets = historyMap[s.address] || [];
                    let hbHtml = '';
                    buckets.forEach(val => {
                        hbHtml += `<span class="hb-seg ${val === 1 ? 'up' : 'down'}" title="${val === 1 ? 'Online' : 'Offline'}"></span>`;
                    });

                    html += `
                        <div class="card">
                            <div class="row">
                                <div class="name">${s.name || s.address}</div>
                                <div class="status-badge ${s.online ? 'online' : 'offline'}">
                                    <span class="dot"></span>${s.online ? 'Online' : 'Offline'}
                                </div>
                            </div>
                            <div class="details">
                                <div>Address: <b>${s.address}</b></div>
                                <div>Version: <b>${s.version || 'Unknown'}</b></div>
                            </div>
                            <div class="hb-grid">${hbHtml}</div>
                            <div class="footer-meta">
                                <span>24H HEARTBEAT</span>
                                <span>${s.online ? 'UPTIME: ' + sToHms(s.uptime_seconds) : 'LAST SEEN: ' + new Date(s.last_seen).toLocaleTimeString()}</span>
                            </div>
                        </div>`;
                });
                document.getElementById('main').innerHTML = html + '</div>';
            } catch (e) { console.error("Refresh failed", e); }
        }
        refresh();
        setInterval(refresh, 15000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_LAYOUT)

@app.route('/status.json')
def status_json():
    ping.run_ping() #
    if os.path.exists("status.json"):
        with open("status.json", "r") as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route('/history.json')
def history_json():
    now_ms = int(time.time() * 1000)
    since_ms = now_ms - (24 * 3600 * 1000)
    rows = db.fetch_history_since(since_ms) #

    buckets_count = 288 
    bucket_ms = 5 * 60 * 1000
    history_map = { (s["address"] if isinstance(s, dict) else s): [0] * buckets_count for s in ping.SERVERS } #

    for r in rows:
        addr = r.get('address')
        if addr in history_map:
            idx = int((r.get('recorded_at') - since_ms) / bucket_ms)
            if 0 <= idx < buckets_count and r.get('online'):
                history_map[addr][idx] = 1

    return jsonify([{'address': k, 'buckets': v} for k, v in history_map.items()])

if __name__ == "__main__":
    app.run(debug=True, port=5555)