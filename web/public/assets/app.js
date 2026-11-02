import { request, setToken, download } from './api.js';
const $ = (id) => document.getElementById(id);
const escape = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const money = (n) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(n);
const icon = (name, size = 18) => {
    const paths = {
        grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
        play: '<path d="m8 5 11 7-11 7Z"/>', check: '<path d="m5 12 4 4L19 6"/>',
        code: '<path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-14-2 18"/>',
        clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
        shield: '<path d="m12 3 8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
        sliders: '<path d="M4 7h16M4 17h16"/><circle cx="8" cy="7" r="2"/><circle cx="16" cy="17" r="2"/>',
        arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>', plus: '<path d="M12 5v14M5 12h14"/>',
        file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
        upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5"/>',
        lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
        bolt: '<path d="m13 2-9 12h7l-1 8 10-12h-7Z"/>',
        close: '<path d="m6 6 12 12M6 18 18 6"/>',
    };
    return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] ?? paths.file}</svg>`;
};
let runs = [], selected = null, config = null, budget = null;
let view = 'workbench', tab = 'timeline', connected = false, polling = false, modal = false;
let fingerprint = '';
const terminal = new Set(['VERIFIED', 'REJECTED', 'ERROR', 'BLOCKED', 'NOT_REPRODUCED', 'CANCELLED', 'BUDGET_EXCEEDED']);
function toast(message) { $('toast').textContent = message; $('toast').classList.add('visible'); setTimeout(() => $('toast').classList.remove('visible'), 5000); }
function statusClass(status) { return status === 'VERIFIED' ? 'green' : status === 'REJECTED' || status === 'ERROR' ? 'red' : terminal.has(status) ? 'amber' : 'blue'; }
function badge(status) { return `<span class="badge ${statusClass(status)}">${escape(status.replaceAll('_', ' '))}</span>`; }
function time(value) { return new Date(value).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }); }
function shell(content) {
    const titles = { workbench: 'Repair workbench', runs: 'Run history', evaluation: 'Pilot evaluation', settings: 'Workspace settings' };
    $('app').innerHTML = `<aside class="sidebar">
 <a class="brand" href="#" aria-label="ReproPatch home"><img src="/favicon.svg" width="34" height="34" alt=""><span>ReproPatch<small>Evidence-first engineering</small></span></a>
 <div class="workspace-label">WORKSPACE</div>
 <nav aria-label="Main navigation">${[['workbench', 'grid', 'Workbench'], ['runs', 'clock', 'Run history'], ['evaluation', 'shield', 'Evaluation'], ['settings', 'sliders', 'Settings']].map(([id, i, title]) => `<button class="nav-item ${view === id ? 'active' : ''}" data-view="${id}">${icon(i)}<span>${title}</span>${id === 'runs' ? `<span class="nav-count">${runs.length}</span>` : ''}</button>`).join('')}</nav>
 <div class="sidebar-note">${icon('shield', 22)}<strong>Proof before confidence.</strong><p>A passing reproduction test is not the same as a valid repair.</p></div>
 <div class="sidebar-foot"><span class="online-dot"></span>Single-operator workspace<small>Meta hackathon · Indie / Push the Frontier</small></div>
 </aside><div class="page"><header class="topbar"><div class="breadcrumb">Workspace <span>/</span> <strong>${titles[view]}</strong></div><div class="top-actions"><span class="provider">${icon('bolt', 14)} Muse Wonder</span><button class="avatar" id="access" title="Connect operator session">RP</button></div></header>
 <main>${content}</main><footer class="page-footer"><span>ReproPatch / 0.1.0</span><span>No automatic merge. No production access.</span></footer></div>`;
    document.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { view = b.dataset.view; render(); });
    $('access').onclick = showAuth;
    document.querySelector('.brand')?.addEventListener('click', e => { e.preventDefault(); view = 'workbench'; render(); });
}
function heading(title, description, action = '') {
    return `<div class="heading"><div><div class="eyebrow">REPRODUCE. FREEZE. REPAIR. VERIFY.</div><h1>${title}</h1><p>${description}</p></div>${action}</div>`;
}
function fixtureNotice() { if (selected?.mode === 'live' || (!selected && runs.some(r => r.mode === 'live')))
    return `<div class="notice">${icon('bolt')}<div><strong>LIVE — Meta Model API repair attempt</strong><span>Real model calls, isolated target code and independent checks. Failures remain visible.</span></div><span class="badge blue">LIVE</span></div>`; return `<div class="notice">${icon('shield')}<div><strong>Integration workspace — synthetic fixture</strong><span>Test the interface and verification pipeline. No Meta calls; not a model-performance result.</span></div><span class="badge neutral">NO API SPEND</span></div>`; }
function stats() { return `<div class="stats"><div class="stat"><span>Completed live attempts</span><strong>${runs.filter(r => r.mode === 'live' && terminal.has(r.status)).length || '—'}</strong><small>Recorded live attempts; fixtures excluded</small></div><div class="stat"><span>Test integrity</span><strong>SHA-256</strong><small>Freeze before code changes</small></div><div class="stat"><span>Model / provider</span><strong class="small-value">Muse Wonder</strong><small>${escape(config?.model ?? 'muse-wonder-1.0')}</small></div><div class="stat"><span>Ledger committed / pilot cap</span><strong>${money(budget?.committed_usd ?? 0)} <em>/ ${money(budget?.cap_usd ?? 24)}</em></strong><small>This workspace only, not account billing</small></div></div>`; }
function runList() { return `<section class="panel runs-panel"><div class="panel-heading"><h2>Recent runs</h2><span class="subtle">${runs.length}</span></div>${runs.length ? `<div class="run-list">${runs.map(r => `<button class="run-card ${selected?.id === r.id ? 'selected' : ''}" data-run="${r.id}"><div class="run-card-top"><span class="mono">${r.method} · ${r.id.slice(0, 7)}</span><span>${time(r.created_at)}</span></div><strong>${escape(r.title)}</strong><div class="run-card-foot">${badge(r.status)}<span class="fixture-tag">${escape(r.mode)}</span></div></button>`).join('')}</div>` : `<div class="empty-list">${icon('clock', 28)}<p>No runs yet</p><span>Start the fixture to inspect the pipeline.</span></div>`}<div class="list-bottom">Fixtures never enter pilot metrics.</div></section>`; }
function emptyDetail() { return `<section class="panel empty-detail"><div class="empty-symbol">${icon('code', 36)}</div><span class="eyebrow">YOUR FIRST REPAIR TRACE</span><h2>From “it looks fixed”<br>to evidence you can inspect.</h2><p>Run the synthetic pagination case to see reproduction, frozen tests, a patch and independent verification.</p><button class="primary" id="start-empty">${icon('play', 16)} Run W1 fixture</button><div class="empty-steps"><span>${icon('file', 15)} Report</span><span>${icon('arrow', 14)}</span><span>${icon('lock', 15)} Frozen test</span><span>${icon('arrow', 14)}</span><span>${icon('shield', 15)} Evidence</span></div></section>`; }
function pipeline() {
    const observed = new Set(selected?.events?.map(e => e.stage) ?? []);
    const finished = selected ? terminal.has(selected.status) : false;
    const stages = [['REPRODUCING', 'Reproduce'], ['FROZEN', selected?.method === 'W0' ? 'Optional test' : 'Freeze test'], ['PATCHING', 'Patch'], ['VERIFYING', 'Verify']];
    return `<div class="pipeline">${stages.map(([stage, title], i) => {
        const optional = stage === 'FROZEN' && selected?.method === 'W0' && !observed.has('FROZEN');
        const current = selected?.status === stage;
        const done = !optional && observed.has(stage) && (!current || finished);
        return `<div class="pipeline-step ${done ? 'done' : current ? 'current' : ''}"><span>${optional ? '—' : done ? icon('check', 13) : i + 1}</span><b>${title}</b></div>`;
    }).join('')}</div>`;
}
function timeline() { return `<div class="timeline">${selected?.events?.map(e => `<div class="event ${escape(e.kind)}"><div class="event-dot">${e.kind === 'success' ? icon('check', 11) : ''}</div><div class="event-body"><div class="event-meta"><span>${escape(e.stage)}</span><time>${time(e.at)}</time></div><p>${escape(e.message)}</p>${Object.keys(e.data).length ? `<details><summary>Inspect evidence</summary><pre>${escape(JSON.stringify(e.data, null, 2))}</pre></details>` : ''}</div></div>`).join('') ?? ''}</div>`; }
function patch() { return selected?.result?.patch ? `<div class="diff-title">${icon('code', 16)} ${selected.mode === 'live' ? 'Candidate source changes' : 'src/pagination.mjs'} <span class="badge neutral">${selected.mode === 'live' ? 'LIVE PATCH' : 'FIXTURE PATCH'}</span></div><pre class="diff">${selected.result.patch.split('\n').map(line => `<span class="${line.startsWith('+') ? 'added' : line.startsWith('-') ? 'removed' : ''}">${escape(line) || ' '}</span>`).join('')}</pre>` : `<div class="inline-empty">No patch artifact yet.</div>`; }
function evidence() { return `<div class="evidence-list">${selected?.artifacts?.map(a => `<div class="artifact-row">${icon('file', 24)}<div><strong>${escape(a.name)}</strong><small class="mono">SHA-256 ${a.sha256.slice(0, 18)}… · ${a.size} bytes</small></div><button class="secondary compact" data-download="${a.id}">Download</button></div>`).join('') || '<div class="inline-empty">No artifacts yet.</div>'}</div>`; }
function detail() {
    if (!selected)
        return emptyDetail();
    const r = selected;
    const result = r.result;
    return `<section class="panel detail"><div class="detail-heading"><div><div class="eyebrow">${r.method === 'W1' ? 'FROZEN-TEST PROTOCOL' : 'COMPETENT BASELINE'} <span class="muted">/ ${r.id.slice(0, 8)}</span></div><h2>${escape(r.title)}</h2><p>${escape(r.payload.expected_behavior)}</p></div>${badge(r.status)}</div>${pipeline()}
 ${result ? `<div class="verdict ${result.verified ? 'pass' : 'fail'}">${icon(result.verified ? 'shield' : 'close', 22)}<div><strong>${result.verified ? 'Verified against executed checks' : r.status === 'REJECTED' && (result.independent || result.evaluation?.independent) ? 'Rejected by independent checks' : r.status === 'REJECTED' ? 'Attempt ended without independent verification' : escape(r.status.replaceAll('_', ' '))}</strong><p>${result.independent ? `${result.independent.passed}/${result.independent.total} independent checks` : result.evaluation?.independent ? `Independent checks: ${result.evaluation.independent.passed ? 'passed' : 'failed'}` : 'Independent evaluation not completed'} · ${result.model_calls ?? 0} model calls · ${money(result.cost_usd ?? 0)}${result.reason ? ' · ' + escape(result.reason) : ''}</p></div></div>` : ''}
 <div class="detail-tabs">${[['timeline', 'Activity'], ['patch', 'Patch diff'], ['evidence', 'Evidence']].map(([id, title]) => `<button class="${tab === id ? 'active' : ''}" data-tab="${id}">${title}</button>`).join('')}<span>${terminal.has(r.status) ? 'Completed trace' : 'Polling worker'}</span></div>
 <div class="detail-content">${tab === 'timeline' ? timeline() : tab === 'patch' ? patch() : evidence()}</div>
 <div class="detail-footer"><span>${icon('lock', 14)} ${result?.frozen_test_sha256 ? 'Frozen test: ' + result.frozen_test_sha256.slice(0, 16) + '…' : 'No frozen test recorded'}</span>${!terminal.has(r.status) ? '<button class="secondary compact" id="cancel-run">Cancel run</button>' : `<span class="fixture-tag">${r.mode === 'fixture' ? 'Synthetic fixture · not a pilot result' : 'Live attempt · inspect executed checks'}</span>`}</div></section>`;
}
function workbench() { return heading('Repair workbench', 'A bug report is the starting point. A verified patch is the deliverable.', `<button class="primary" id="new-run">${icon('plus', 16)} New run</button>`) + fixtureNotice() + stats() + `<div class="workspace-grid">${runList()}${detail()}</div><section class="next-step"><div class="next-icon">${icon('bolt', 22)}</div><div><strong>Inspect real attempts alongside the labeled fixture.</strong><p>Compare W0/W1 results, recorded spend, frozen hashes and independent checks. Fixtures never count as live repairs.</p></div><button class="text-button" id="open-evaluation">Pilot plan ${icon('arrow', 16)}</button></section>`; }
function history() { return heading('Every run, with its evidence.', 'Failures stay in the record. Fixture results stay out of the benchmark.') + fixtureNotice() + `<div class="panel table-panel"><table><thead><tr><th>Run</th><th>Method</th><th>Source</th><th>Status</th><th>Time</th></tr></thead><tbody>${runs.map(r => `<tr data-run="${r.id}"><td><strong>${escape(r.title)}</strong><small class="mono">${r.id.slice(0, 10)}</small></td><td>${r.method}</td><td><span class="fixture-tag">${r.mode}</span></td><td>${badge(r.status)}</td><td>${time(r.created_at)}</td></tr>`).join('') || '<tr><td colspan="5" class="inline-empty">No runs recorded.</td></tr>'}</tbody></table></div>`; }
function evaluation() {
    const live = runs.filter(r => r.mode === 'live');
    const ids = [...new Set(live.map(r => r.case_id))];
    const cells = ids.map(id => { const cases = live.filter(r => r.case_id === id); const arm = (m) => { const rs = cases.filter(r => r.method === m); return rs.length ? rs.map(r => r.status).join(', ') : 'Not run'; }; return `<tr><td>${escape(id)}<small>${escape(cases[0].title)}</small></td><td>${escape(arm('W0'))} / ${escape(arm('W1'))}</td><td>${cases.filter(r => r.result?.false_success).length}</td><td>${cases.some(r => r.result?.evaluation) ? cases.reduce((n, r) => n + (r.result?.regressions ?? 0), 0) : 'Not evaluated'}</td><td>${cases.filter(r => r.status === 'NOT_REPRODUCED' || ['model_ended_without_candidate', 'turn_limit'].includes(r.result?.reason ?? '')).length} / ${cases.filter(r => ['ERROR', 'BLOCKED', 'BUDGET_EXCEEDED'].includes(r.status)).length}</td><td>${cases.reduce((n, r) => n + (r.result?.operator_interventions ?? 0), 0)}</td><td>${money(cases.reduce((n, r) => n + (r.result?.cost_usd ?? 0), 0))} / ${Math.round(cases.reduce((n, r) => n + (r.result?.duration_ms ?? 0), 0) / 1000)} s</td></tr>`; }).join('');
    return heading('Measure repairs. Not confidence.', 'Same model, tools, inputs and budget. Fixtures excluded.') + `<div class="notice amber-notice">${icon('clock')}<div><strong>${live.length ? 'Recorded live attempts: ' + live.length : 'Real-issue pilot: not measured'}</strong><span>${ids.length} distinct real cases. Errors, absten­tions and unsuccessful attempts remain in the record.</span></div><span class="badge amber">${live.length ? 'EXPLORATORY' : 'PENDING'}</span></div><div class="comparison-cards"><section class="panel compare-card"><span class="method-label">W0</span><h2>Competent baseline</h2><p>Reproduce, repair and test with Muse Wonder and the same tools.</p></section><section class="panel compare-card emphasis"><span class="method-label">W1</span><h2>ReproPatch protocol</h2><p>Confirm the correct failure, freeze its test, repair and verify independently.</p></section></div><div class="panel table-panel"><div class="panel-heading"><h2>Pilot result sheet</h2><span class="badge neutral">${live.length} LIVE ATTEMPTS</span></div><table><thead><tr><th>Case</th><th>Status W0 / W1</th><th>False successes</th><th>Regressions</th><th>Abstentions / errors</th><th>Human interventions</th><th>Cost / time</th></tr></thead><tbody>${cells || '<tr><td colspan="7">No live results recorded.</td></tr>'}</tbody></table></div><p class="footnote">Four cases measure feasibility, not statistical superiority. Independent results never feed back into the model. Cost covers this ledger only.</p>`;
}
function settingsView() { return heading('Workspace controls', 'A single-operator MVP with explicit boundaries.') + `<div class="settings-grid"><section class="panel settings-card"><h2>Meta Model API</h2><div class="key-value"><span>Model</span><code>${escape(config?.model ?? 'muse-wonder-1.0')}</code></div><div class="key-value"><span>Server-side key</span><b>Environment variable only</b></div><div class="key-value"><span>Live orchestration</span>${badge(config?.live_enabled ? 'LIVE' : 'BLOCKED')}</div><p>${escape(config?.reason ?? 'Connect to inspect configuration.')}</p><p class="footnote">Model usage and response IDs are recorded per live run. Fixture traces have zero model calls.</p></section><section class="panel settings-card"><h2>Budget controls</h2><div class="key-value"><span>Per model run</span><b>${money(config?.run_cap_usd ?? 3)}</b></div><div class="key-value"><span>Pilot ledger cap</span><b>${money(config?.batch_cap_usd ?? 24)}</b></div><div class="key-value"><span>Conservative accounting</span><b>No assumed cache discount</b></div><p>Reserve before each request. Stop on ambiguous billing. No silent retries or changes to the budget.</p></section><section class="panel settings-card"><h2>Execution boundary</h2><p>Untrusted repositories and model-generated commands must run in disposable sandboxes. The control plane does not execute them.</p><div class="chips"><span>Network denied</span><span>No credentials</span><span>Non-root</span><span>Resource limits</span></div></section><section class="panel settings-card"><h2>Repository & release</h2><p>Start private. Keep generated artifacts and secrets outside Git. Publish the selected submission only after a disclosure and secret review.</p><div class="chips"><span>No auto-merge</span><span>Hackathon-only work</span><span>Original commits</span></div></section></div>`; }
function bind() {
    $('new-run')?.addEventListener('click', showNewRun);
    $('start-empty')?.addEventListener('click', () => createFixture('W1'));
    $('open-evaluation')?.addEventListener('click', () => { view = 'evaluation'; render(); });
    document.querySelectorAll('[data-run]').forEach(b => b.onclick = async () => { try {
        selected = await request('/runs/' + b.dataset.run);
        view = 'workbench';
        tab = 'timeline';
        render();
    }
    catch (e) {
        toast(String(e));
    } });
    document.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => { tab = b.dataset.tab; render(); });
    document.querySelectorAll('[data-download]').forEach(b => b.onclick = () => { const a = selected?.artifacts?.find(a => a.id === b.dataset.download); if (a && selected)
        download(selected.id, a).catch(e => toast(String(e))); });
    $('cancel-run')?.addEventListener('click', async () => { if (selected) {
        await request('/runs/' + selected.id + '/cancel', { method: 'POST' });
        await refresh();
    } });
}
function render() { shell(view === 'workbench' ? workbench() : view === 'runs' ? history() : view === 'evaluation' ? evaluation() : settingsView()); bind(); }
async function refresh() {
    if (!connected || polling)
        return;
    polling = true;
    try {
        const [list, b] = await Promise.all([request('/runs'), request('/budget')]);
        runs = list.items;
        budget = b;
        if (selected)
            selected = await request('/runs/' + selected.id);
        const next = JSON.stringify([runs.map(r => [r.id, r.status]), selected?.events?.length, b]);
        if (next !== fingerprint && !modal) {
            fingerprint = next;
            render();
        }
    }
    catch (e) {
        toast(String(e));
    }
    finally {
        polling = false;
    }
}
function closeModal() { modal = false; $('overlay').innerHTML = ''; }
function showAuth() {
    modal = true;
    $('overlay').innerHTML = `<div class="modal-backdrop"><section class="modal auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title"><div class="modal-head"><img src="/favicon.svg" width="36" alt=""><button class="icon-button" id="close-modal" aria-label="Close">${icon('close')}</button></div><h2 id="auth-title">Connect your workspace</h2><p>Enter the operator token printed by the local setup script. This is not your Meta API key.</p><form id="auth-form"><label for="operator-token">Operator token</label><input id="operator-token" type="password" autocomplete="off" required placeholder="REPROPATCH_AUTH_TOKEN"><div class="form-error" id="auth-error"></div><button class="primary full" type="submit">Connect workspace ${icon('arrow', 16)}</button></form><small>Token stays in browser memory. Meta credentials stay on the backend.</small></section></div>`;
    $('close-modal').onclick = closeModal;
    $('auth-form').onsubmit = async (e) => { e.preventDefault(); setToken(($('operator-token')).value); try {
        config = await request('/config');
        connected = true;
        closeModal();
        await refresh();
        render();
    }
    catch (error) {
        $('auth-error').textContent = String(error);
    } };
    setTimeout(() => $('operator-token').focus(), 50);
}
async function createFixture(method, title, videoId) {
    if (!connected) {
        showAuth();
        return;
    }
    try {
        const payload = { case_id: 'pagination-fixture', method, mode: 'fixture', ...(title ? { title } : {}), ...(videoId ? { video_id: videoId } : {}) };
        selected = await request('/runs', { method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify(payload) });
        closeModal();
        view = 'workbench';
        tab = 'timeline';
        await refresh();
        render();
        toast('Fixture queued. No Meta calls will be made.');
    }
    catch (e) {
        toast(String(e));
    }
}
function showNewRun() {
    if (!connected) {
        showAuth();
        return;
    }
    modal = true;
    $('overlay').innerHTML = `<div class="modal-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="new-title"><div class="modal-head"><span class="eyebrow">NEW REPAIR RUN</span><button class="icon-button" id="close-modal" aria-label="Close">${icon('close')}</button></div><h2 id="new-title">Start with the evidence.</h2><p>Choose the labeled fixture or an accepted real case. Live execution sends the reviewed video to Meta and uses the server budget.</p><form id="run-form"><label for="case-choice">Approved case</label><select id="case-choice"><option value="pagination-fixture">FIXTURE — scripted pagination</option>${config?.live_enabled ? (config.live_cases ?? []).map(c => `<option value="${escape(c.case_id)}">LIVE — ${escape(c.title)}</option>`).join('') : ''}</select><label for="run-title">Bug report</label><input id="run-title" value="Active filter disappears on page 2" required maxlength="140"><label for="method">Execution protocol</label><select id="method"><option value="W1">W1 — ReproPatch frozen-test protocol</option><option value="W0">W0 — Competent baseline</option></select><label for="video">MP4 evidence — local for fixture; reviewed case video required for LIVE</label><label class="upload-zone" for="video">${icon('upload', 25)}<strong>Choose a screen recording</strong><span>MP4 · up to 50 MiB · no client data or credentials</span></label><input id="video" type="file" accept="video/mp4" class="file-input"><div id="video-name" class="footnote"></div><div class="inline-warning" id="mode-warning">${icon('shield', 16)} FIXTURE: scripted, no Meta calls.</div><button class="primary full" id="submit-run" type="submit">Run fixture ${icon('arrow', 16)}</button></form></section></div>`;
    $('close-modal').onclick = closeModal;
    $('case-choice').onchange = () => { const c = config?.live_cases?.find(c => c.case_id === $('case-choice').value); $('run-title').value = c?.title ?? 'Active filter disappears on page 2'; $('mode-warning').textContent = c ? 'LIVE: sends the reviewed video to Meta. Maximum $3 per run; no automatic retries.' : 'FIXTURE: scripted, no Meta calls.'; $('submit-run').textContent = c ? 'Run LIVE attempt' : 'Run fixture'; };
    $('video').onchange = () => { $('video-name').textContent = $('video').files?.[0]?.name ?? ''; };
    $('run-form').onsubmit = async (e) => {
        e.preventDefault();
        const button = $('submit-run');
        button.disabled = true;
        try {
            let vid;
            const file = $('video').files?.[0];
            if (file) {
                const form = new FormData();
                form.append('file', file);
                vid = (await request('/videos', { method: 'POST', body: form })).id;
            }
            const cid = $('case-choice').value;
            const method = $('method').value;
            if (cid === 'pagination-fixture')
                await createFixture(method, $('run-title').value, vid);
            else {
                if (!vid)
                    throw new Error('The reviewed MP4 for this case is required.');
                const c = config?.live_cases?.find(c => c.case_id === cid);
                if (!c)
                    throw new Error('Case is not approved.');
                selected = await request('/runs', { method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify({ case_id: cid, method, mode: 'live', title: c.title, expected_behavior: c.expected_behavior, video_id: vid }) });
                closeModal();
                view = 'workbench';
                await refresh();
                render();
                toast('LIVE attempt queued with server budget controls.');
            }
        }
        catch (error) {
            toast(String(error));
            button.disabled = false;
        }
    };
}
render();
showAuth();
setInterval(refresh, 1200);
