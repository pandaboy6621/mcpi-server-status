(() => {
    'use strict';

    const REFRESH_MS = 15000;
    const $ = (id) => document.getElementById(id);

    const ICONS = {
        copy: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 1H4a2 2 0 0 0-2 2v14h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h11v14z"/></svg>',
        check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>',
    };

    // Server names come straight from UDP replies, so treat every value as untrusted.
    const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[c]);

    const safeUrl = (url) => {
        if (!url) return null;
        try {
            const u = new URL(url);
            return ['http:', 'https:'].includes(u.protocol) ? u.href : null;
        } catch { return null; }
    };

    function duration(seconds) {
        let s = Math.max(0, Math.floor(seconds || 0));
        const d = Math.floor(s / 86400); s %= 86400;
        const h = Math.floor(s / 3600); s %= 3600;
        const m = Math.floor(s / 60); s %= 60;
        if (d) return `${d}d ${h}h`;
        if (h) return `${h}h ${m}m`;
        if (m) return `${m}m`;
        return `${s}s`;
    }

    function ago(ms, now) {
        if (!ms) return 'never';
        const diff = Math.max(0, (now - ms) / 1000);
        if (diff < 45) return 'just now';
        if (diff < 86400 * 30) return `${duration(diff)} ago`;
        return new Date(ms).toLocaleDateString(undefined, { dateStyle: 'medium' });
    }

    const clock = (ms) => new Date(ms).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    function heartbeat(history, now) {
        const buckets = history?.buckets || new Array(96).fill(null);
        const since = history?.since ?? now - 96 * 15 * 60000;
        const size = history?.bucket_ms ?? 15 * 60000;
        let up = 0, known = 0;
        const segs = buckets.map((v, i) => {
            const from = since + i * size;
            const label = v === 1 ? 'Online' : v === 0 ? 'Offline' : 'No data';
            if (v !== null) { known++; if (v === 1) up++; }
            const cls = v === 1 ? 'up' : v === 0 ? 'down' : '';
            return `<span class="hb-seg ${cls}" title="${clock(from)}–${clock(from + size)}: ${label}"></span>`;
        }).join('');
        const pct = known ? `${Math.round((up / known) * 1000) / 10}%` : '—';
        return { segs, pct };
    }

    function card(s, history, now) {
        const online = !!s.online;
        const name = s.name || s.address;
        const hb = heartbeat(history, now);
        const site = safeUrl(s.website) || (s.show_link ? safeUrl(`http://${s.address.split(':')[0]}`) : null);
        const players = online && s.players !== null && s.players !== undefined
            ? `<dt>Players</dt><dd>${esc(s.players)} online</dd>` : '';

        return `
        <article class="card ${online ? '' : 'is-offline'}">
            <div class="card-head">
                <div class="name dim">${esc(name)}</div>
                <span class="pill ${online ? 'online' : 'offline'}"><span class="dot"></span>${online ? 'Online' : 'Offline'}</span>
            </div>
            <dl class="details dim">
                <dt>Address</dt>
                <dd>
                    <span class="addr">${esc(s.address)}</span>
                    <button class="icon-btn copy-btn" type="button" data-copy="${esc(s.address)}"
                        title="Copy address" aria-label="Copy address ${esc(s.address)}">${ICONS.copy}</button>
                </dd>
                <dt>Version</dt><dd>${esc(s.version || 'Unknown')}</dd>
                ${players}
                ${site ? `<dt>Website</dt><dd><a href="${esc(site)}" target="_blank" rel="noopener noreferrer">${esc(new URL(site).hostname)} ↗</a></dd>` : ''}
            </dl>
            <div class="hb dim" role="img" aria-label="24 hour uptime ${hb.pct}">${hb.segs}</div>
            <div class="hb-axis dim"><span>24h ago</span><span>now</span></div>
            <div class="card-foot">
                <span>24h uptime <b>${hb.pct}</b></span>
                <span>${online ? `Up for <b>${duration(s.uptime_seconds)}</b>` : `Last seen <b>${esc(ago(s.last_seen, now))}</b>`}</span>
            </div>
        </article>`;
    }

    function setBanner(text, kind = '') {
        const el = $('banner');
        el.hidden = !text;
        el.textContent = text || '';
        el.className = `banner ${kind}`;
    }

    let toastTimer;
    function toast(msg) {
        const el = $('toast');
        el.textContent = msg;
        el.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => el.classList.remove('show'), 1800);
    }

    // Poll quickly while waiting for the first check after startup.
    let soonTimer;
    function scheduleSoon() {
        clearTimeout(soonTimer);
        soonTimer = setTimeout(refresh, 2000);
    }

    let inFlight = false;
    async function refresh() {
        if (inFlight) return;
        inFlight = true;
        const btn = $('refresh-btn');
        btn.classList.add('spinning');
        try {
            const [statusRes, historyRes] = await Promise.all([
                fetch('status.json', { cache: 'no-store' }),
                fetch('history.json', { cache: 'no-store' }),
            ]);
            if (!statusRes.ok) throw new Error(`status.json returned ${statusRes.status}`);
            const status = await statusRes.json();
            const hist = historyRes.ok ? await historyRes.json() : { servers: [] };
            const now = status.server_time || Date.now();

            const byAddr = {};
            (hist.servers || []).forEach((h) => {
                byAddr[h.address] = { ...h, since: hist.since, bucket_ms: hist.bucket_ms };
            });

            const servers = status.servers || [];
            const main = $('main');
            main.innerHTML = servers.length
                ? servers.map((s) => card(s, byAddr[s.address], now)).join('')
                : '<div class="empty">No results yet. The first check runs a few seconds after startup.</div>';
            main.setAttribute('aria-busy', 'false');

            const online = servers.filter((s) => s.online);
            const players = online.reduce((n, s) => n + (Number(s.players) || 0), 0);
            $('summary').innerHTML = servers.length ? `
                <span class="chip"><b>${online.length}</b> / ${servers.length} online</span>
                <span class="chip"><b>${players}</b> player${players === 1 ? '' : 's'}</span>` : '';

            const checked = status.checked_at;
            const started = status.checker_started_at;
            const staleAfter = (status.interval || 30) * 4 * 1000;
            const firstCheckPending = !checked || (started && checked < started);
            if (firstCheckPending && (!started || now - started < staleAfter)) {
                // App just started: the results on screen (if any) are from the previous run.
                setBanner(checked
                    ? `Checking servers… Showing results from ${ago(checked, now)} until the first check finishes.`
                    : 'Checking servers… Results will appear in a few seconds.');
                scheduleSoon();
            } else if (now - checked > staleAfter) {
                setBanner(started
                    ? `The status checker hasn't finished a check since ${ago(checked, now)}. Look at the terminal running app.py for errors.`
                    : `The status checker hasn't run since ${ago(checked, now)}, so this data may be out of date. Start it with "python app.py" (or "python ping.py --loop").`);
            } else {
                setBanner('');
            }
            $('last-updated').textContent = checked
                ? `Last checked ${new Date(checked).toLocaleString()}`
                : 'Not checked yet';
        } catch (err) {
            console.error('Refresh failed', err);
            setBanner("Can't reach the status server. Retrying automatically…", 'error');
        } finally {
            btn.classList.remove('spinning');
            inFlight = false;
        }
    }

    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('.copy-btn');
        if (!btn) return;
        try {
            await navigator.clipboard.writeText(btn.dataset.copy);
            btn.innerHTML = ICONS.check;
            btn.classList.add('copied');
            toast(`Copied ${btn.dataset.copy}`);
            setTimeout(() => { btn.innerHTML = ICONS.copy; btn.classList.remove('copied'); }, 1500);
        } catch {
            toast('Copy failed: select the address manually');
        }
    });

    $('refresh-btn').addEventListener('click', refresh);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
    setInterval(() => { if (!document.hidden) refresh(); }, REFRESH_MS);
    refresh();
})();
