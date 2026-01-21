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
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@mdi/font@7.4.47/css/materialdesignicons.min.css">
    <style>
        :root{
            --bg:#0f1720;
            --card:#0b1220;
            --muted:#9aa4b2;
            --accent:#34d399;
            --info:#60a5fa;
            --danger:#fb7185;
            --gradient-up: linear-gradient(180deg, #34d399 0%, #22c55e 100%);
            --gradient-down: linear-gradient(180deg, rgba(251, 113, 133, 0.4) 0%, rgba(251, 113, 133, 0.1) 100%);
        }
        
        @font-face {
            font-family: 'Mojangles'; 
            src: url('/static/fonts/mojangles.ttf') format('truetype'); 
            font-weight: normal; font-style: normal; font-display: swap;
        }

        html,body{height:100%;margin:0;font-family:Inter,system-ui,sans-serif;background:linear-gradient(180deg,#061226 0%, #071a2a 100%);color:#e6eef6}
        .wrap{max-width:1100px;margin:32px auto;padding:20px}
        header{margin-bottom:24px}
        h1{font-size:24px;margin:0;font-family: 'Mojangles', sans-serif;}
        
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
        .card{background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:18px; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.3); transition: opacity 0.3s, filter 0.3s;}
        .card.is-offline .name, 
        .card.is-offline .details, 
        .card.is-offline .hb-grid, 
        .card.is-offline .footer-meta {
            opacity: 0.5;
            filter: grayscale(1);
        }
        
        .row{display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px}
        .name{font-weight:600; font-family: 'Mojangles', monospace; font-size: 1.2rem; color:#fff}
        .subtitle{font-size: 0.95rem; color: var(--info); margin-top: -2px; margin-bottom: 8px; font-weight: 500;}
        
        .status-badge{display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px}
        .dot{width:8px; height:8px; border-radius:50%}
        .online{color:var(--accent)}
        .online .dot{background:var(--accent); box-shadow:0 0 8px var(--accent)}
        .offline{color:var(--danger)}
        .offline .dot{background:var(--danger)}

        .details{font-size:13px; color:var(--muted); margin-bottom:12px; line-height:1.4}
        .details b{color:#cbd5e1}

        .hb-grid{display:flex; gap:1px; margin-top:10px; height:12px; width:100%;}
        .hb-seg{flex:1; height:100%; border-radius:1px; transition: transform 0.2s; min-width:1px;}
        .hb-seg:hover{transform: scaleY(1.3); z-index:10}
        .hb-seg.up{background: var(--gradient-up);}
        .hb-seg.down{background: rgba(255,255,255,0.08);}
        
        .footer-meta{display:flex; justify-content:space-between; margin-top:12px; font-size:11px; color:var(--muted); border-top:1px solid rgba(255,255,255,0.05); padding-top:8px}

        .address-link {
            text-decoration: none;
            color: inherit;
            transition: color 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .address-link:hover {
            color: #6366f1; /* Indigo-ish color */
        }
        .address-link .mdi {
            font-size: 14px;
            opacity: 0.8;
        }
        
        #last-updated {
            text-align: left;
            margin-top: 40px;
            padding-bottom: 40px;
            font-size: 13px;
            color: var(--muted);
            border-top: 1px solid rgba(255,255,255,0.05);
            padding-top: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        #refresh-btn {
            cursor: pointer;
            font-size: 16px;
            transition: transform 0.3s ease;
        }
        #refresh-btn:hover {
            color: #fff;
        }
        #refresh-btn.spinning {
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        #loading {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-family: 'Mojangles', sans-serif;
            font-size: 2.5rem;
            color: #d946ef; /* Magenta/Purple */
            z-index: 1000;
            text-shadow: 0 0 20px rgba(217, 70, 239, 0.3);
        }

        .dots::after {
            content: '';
            animation: dots 1.5s steps(4, end) infinite;
        }

        @keyframes dots {
            0%, 20% { content: ''; }
            40% { content: '.'; }
            60% { content: '..'; }
            80% { content: '...'; }
        }
    </style>
</head>
<body>
    <div id="loading">loading<span class="dots"></span></div>
    <div class="wrap">
        <header><h1>MCPI Server Status</h1></header>
        <main id="main"></main>
        <div id="last-updated"></div>
    </div>
    <script>
        function sToHms(s){
            if (!s || s<=0) return '0s';
            s = Math.floor(s);
            const d = Math.floor(s/86400);
            const h = Math.floor((s%86400)/3600);
            const m = Math.floor((s%3600)/60);
            const sec = s%60;
            
            if (d > 0) {
                return d + 'd ' + (h ? h + 'h ' : '') + m + 'm';
            }
            return (h? h+'h ':'') + (m? m+'m ':'') + sec+'s';
        }

        function timeAgo(ms){
            if (!ms) return 'NEVER';
            const diff = Math.floor((Date.now() - ms) / 1000);
            if (diff < 0) return 'Just now';
            if (diff < 60) return diff + 's ago';
            if (diff < 3600) return Math.floor(diff/60) + 'm ago';
            if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
            const d = new Date(ms);
            return d.toLocaleString();
        }

        async function refresh(manual = false){
            if (manual) {
                document.getElementById('refresh-btn')?.classList.add('spinning');
            }
            try {
                const [statusRes, historyRes] = await Promise.all([
                    fetch('/status.json'), fetch('/history.json')
                ]);
                const data = await statusRes.json();
                const servers = data.servers;
                const lastUpdatedTs = data.last_updated;

                const historyList = await historyRes.json();
                const historyMap = {};
                historyList.forEach(i => { historyMap[i.address] = i.buckets; });

                let html = '<div class="grid">';
                servers.forEach(s => {
                    const buckets = historyMap[s.address] || new Array(96).fill(0);
                    let hbHtml = '';
                    buckets.forEach(val => {
                        hbHtml += `<span class="hb-seg ${val === 1 ? 'up' : 'down'}" title="${val === 1 ? 'Online' : 'Offline'}"></span>`;
                    });
                    const upCount = buckets.reduce((acc, v) => acc + (v === 1 ? 1 : 0), 0);
                    const uptimePct = buckets.length ? Math.round((upCount / buckets.length) * 100) : 0;

                    html += `
                        <div class="card ${s.online ? '' : 'is-offline'}">
                            <div class="row">
                                <div class="name">${s.name || s.address}</div>
                                <div class="status-badge ${s.online ? 'online' : 'offline'}">
                                    <span class="dot"></span>${s.online ? 'Online' : 'Offline'}
                                </div>
                            </div>
                            ${s.players !== undefined && s.players !== null ? `<div class="subtitle">${s.players} online</div>` : ''}
                            <div class="details">
                                <div>Address: <b>${s.show_link ? `<a href="http://${s.address}" target="_blank" class="address-link">${s.address} <span class="mdi mdi-open-in-new"></span></a>` : s.address}</b></div>
                                <div>Version: <b>${s.version || 'Unknown'}</b></div>
                            </div>
                            <div class="hb-grid">${hbHtml}</div>
                            <div class="footer-meta">
                                <span>24H HEARTBEAT (${uptimePct}%)</span>
                                <span>${s.online ? 'UPTIME: ' + sToHms(s.uptime_seconds) : 'LAST SEEN: ' + timeAgo(s.last_seen)}</span>
                            </div>
                        </div>`;
                });
                document.getElementById('main').innerHTML = html + '</div>';
                
                if (lastUpdatedTs) {
                    const d = new Date(lastUpdatedTs);
                    document.getElementById('last-updated').innerHTML = `
                        last refresh: ${d.toLocaleString()} 
                        <span id="refresh-btn" class="mdi mdi-refresh" onclick="refresh(true)" title="Manual Refresh"></span>
                    `;
                }

                // Hide loading screen after first data load
                const loader = document.getElementById('loading');
                if (loader) loader.style.display = 'none';
                document.getElementById('refresh-btn')?.classList.remove('spinning');
            } catch (e) { 
                console.error("Refresh failed", e);
                document.getElementById('refresh-btn')?.classList.remove('spinning');
            }
        }

        refresh();
        setInterval(() => refresh(false), 15000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_LAYOUT)

@app.route('/status.json')
def status_json():
    ping.run_ping() 
    if os.path.exists("status.json"):
        mtime = os.path.getmtime("status.json")
        with open("status.json", "r") as f:
            return jsonify({
                "servers": json.load(f),
                "last_updated": int(mtime * 1000)
            })
    return jsonify({"servers": [], "last_updated": 0})

@app.route('/history.json')
def history_json():
    now_ms = int(time.time() * 1000)
    since_ms = now_ms - (24 * 3600 * 1000)
    rows = db.fetch_history_since(since_ms)

    buckets_count = 96 
    bucket_ms = 15 * 60 * 1000
    history_map = { (s["address"] if isinstance(s, dict) else s): [0] * buckets_count for s in ping.SERVERS }

    for r in rows:
        addr = r.get('address')
        if addr in history_map:
            idx = int((r.get('recorded_at') - since_ms) / bucket_ms)
            if 0 <= idx < buckets_count and r.get('online'):
                history_map[addr][idx] = 1

    return jsonify([{'address': k, 'buckets': v} for k, v in history_map.items()])

if __name__ == "__main__":
    # Disable the reloader so only one process writes the DB/file.
    app.run(debug=True, port=5555, use_reloader=False)