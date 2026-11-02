let token = '';
export function setToken(value) { token = value; }
export async function request(path, options = {}) {
    const headers = new Headers(options.headers);
    headers.set('Authorization', 'Bearer ' + token);
    if (options.body && !(options.body instanceof FormData))
        headers.set('Content-Type', 'application/json');
    const response = await fetch('/api' + path, { ...options, headers });
    if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
            const data = await response.json();
            detail = typeof data.detail === 'string' ? data.detail : detail;
        }
        catch { /* retain status */ }
        throw new Error(detail);
    }
    return response.json();
}
export async function download(runId, artifact) {
    const response = await fetch(`/api/runs/${runId}/artifacts/${artifact.id}`, { headers: { Authorization: 'Bearer ' + token } });
    if (!response.ok)
        throw new Error('Artifact download failed');
    const url = URL.createObjectURL(await response.blob());
    const a = document.createElement('a');
    a.href = url;
    a.download = artifact.name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
