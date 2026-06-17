const tg = window.Telegram.WebApp;
const isTg = !!tg.initDataUnsafe?.user;

document.addEventListener('DOMContentLoaded', () => {
    tg.ready();
    tg.expand();
    tg.setHeaderColor('secondary_bg_color');
    tg.setBackgroundColor('bg_color');

    const userNameEl = document.getElementById('user-name');
    if (isTg && tg.initDataUnsafe.user) {
        userNameEl.textContent = tg.initDataUnsafe.user.first_name;
    } else {
        userNameEl.textContent = 'Preview';
    }

    document.getElementById('btn-close').addEventListener('click', () => {
        if (isTg) tg.close();
    });

    document.getElementById('btn-refresh').addEventListener('click', () => {
        updateAllData();
        if (isTg) tg.HapticFeedback.impactOccurred('light');
    });

    updateAllData();
});

async function updateAllData() {
    try {
        await Promise.all([
            fetchStatus(),
            fetchVersions(),
            fetchClients()
        ]);
        if (isTg) tg.HapticFeedback.notificationOccurred('success');
    } catch (e) {
        console.error('Update error:', e);
        if (isTg) tg.HapticFeedback.notificationOccurred('error');
    }
}


async function fetchStatus() {
    const content = document.getElementById('status-content');
    const badge = document.getElementById('main-status-badge');
    const dot = document.getElementById('main-status-dot');
    const text = document.getElementById('main-status-text');

    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        const statusStr = data.status || '';

        const lines = statusStr.split('\n').filter(l => l.trim());
        let allOnline = true;
        let html = '';

        lines.forEach(line => {
            const isOnline = line.toLowerCase().includes('online');
            if (!isOnline) allOnline = false;

            const parts = line.split(':');
            const name = parts[0]?.trim() || 'Unknown';
            const statusPart = parts.slice(1).join(':').trim();


            const pingMatch = statusPart.match(/\((\d+ms)\)/);
            const ping = pingMatch ? pingMatch[1] : '';

            html += `
                <div class="service-row">
                    <div class="service-name">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                        </svg>
                        ${escapeHtml(name)}
                    </div>
                    <span class="service-status ${isOnline ? 'ok' : 'err'}">
                        ${isOnline ? 'Online' : 'Offline'}${ping ? ' · ' + ping : ''}
                    </span>
                </div>
            `;
        });

        content.innerHTML = html;

        if (allOnline) {
            badge.className = 'status-badge online';
            text.textContent = 'Stable';
        } else {
            badge.className = 'status-badge offline';
            text.textContent = 'Issues';
        }
    } catch (e) {
        content.innerHTML = '<div class="error-text">Не удалось загрузить статус</div>';
        badge.className = 'status-badge offline';
        text.textContent = 'Error';
    }
}

async function fetchVersions() {
    const content = document.getElementById('versions-content');

    try {
        const res = await fetch('/api/versions');
        const data = await res.json();

        const stableTag = data.latest?.[0] || 'N/A';
        const stableUrl = data.latest?.[1] || '#';
        const preTag = data.pre?.[0] || 'N/A';
        const preUrl = data.pre?.[1] || '#';

        content.innerHTML = `
            <div class="version-box" onclick="${stableUrl !== '#' ? `tg.openLink('${stableUrl}')` : ''}">
                <div class="version-label">Stable</div>
                <div class="version-tag">${escapeHtml(stableTag)}</div>
            </div>
            <div class="version-box" onclick="${preUrl !== '#' ? `tg.openLink('${preUrl}')` : ''}">
                <div class="version-label">Pre-release</div>
                <div class="version-tag">${escapeHtml(preTag)}</div>
            </div>
        `;
    } catch (e) {
        content.innerHTML = '<div class="error-text">Не удалось загрузить версии</div>';
    }
}


async function fetchClients() {
    const content = document.getElementById('clients-content');
    const countEl = document.getElementById('client-count').querySelector('span');

    try {
        const res = await fetch('/api/clients');
        const data = await res.json();
        const raw = data.clients || '';

        const lines = raw.split('\n').filter(l => l.trim());
        let html = '';
        let totalClients = 0;

        lines.forEach(line => {
            const stripped = line.replace(/<[^>]*>/g, '').trim();
            if (!stripped) return;

            if (line.includes('<b>') && line.trim().endsWith(':')) {
                const categoryName = stripped.replace(':', '');
                html += `<div class="clients-section-title">${escapeHtml(categoryName)}</div>`;
            } else {
                const nameMatch = stripped.match(/^(.+?)\s*\(v/);
                const versionMatch = stripped.match(/\(v([\d.]+)\)/);
                const idMatch = stripped.match(/ID:\s*(\d+)/);

                const name = nameMatch ? nameMatch[1].trim() : stripped;
                const version = versionMatch ? 'v' + versionMatch[1] : '';
                const id = idMatch ? '#' + idMatch[1] : '';

                if (name) {
                    totalClients++;
                    html += `
                        <div class="client-item">
                            <span class="client-name">${escapeHtml(name)}</span>
                            <span class="client-meta">${escapeHtml(version)}${id ? ' · ' + escapeHtml(id) : ''}</span>
                        </div>
                    `;
                }
            }
        });

        content.innerHTML = html || '<div class="error-text">Нет доступных клиентов</div>';
        countEl.textContent = totalClients > 0 ? totalClients + ' шт.' : '...';
    } catch (e) {
        content.innerHTML = '<div class="error-text">Не удалось загрузить клиентов</div>';
    }
}


function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
