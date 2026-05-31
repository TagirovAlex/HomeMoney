async function loadPending() {
    var r = await fetch('/api/v1/users/pending', { headers: authHeaders() });
    var d = await r.json();
    var tbody = document.getElementById('pending-body');
    if (d.status !== 'success' || !d.data.length) { tbody.innerHTML = '<tr><td colspan="4">Нет заявок.</td></tr>'; return; }
    tbody.innerHTML = d.data.map(function(u) {
        return '<tr><td>' + u.id + '</td><td>' + u.email + '</td><td>' + (u.telegram_id || '') +
            '</td><td><button class="btn" onclick="approve(' + u.id + ')">Да</button> ' +
            '<button class="btn btn-secondary" onclick="reject(' + u.id + ')">Нет</button></td></tr>';
    }).join('');
}

async function approve(id) {
    var r = await fetch('/api/v1/users/' + id + '/approve', { method: 'POST', headers: authHeaders() });
    var d = await r.json();
    alert(d.message); loadPending(); loadUsers();
}

async function reject(id) {
    var r = await fetch('/api/v1/users/' + id + '/reject', { method: 'POST', headers: authHeaders() });
    var d = await r.json();
    alert(d.message); loadPending(); loadUsers();
}

async function setTelegram(userId) {
    var input = document.getElementById('tg-' + userId);
    var val = input.value.trim();
    var r = await fetch('/api/v1/users/' + userId + '/telegram', { method: 'PUT', headers: authHeaders(), body: JSON.stringify({telegram_id: val}) });
    var d = await r.json();
    alert(d.message); loadUsers();
}

async function loadUsers() {
    var r = await fetch('/api/v1/users', { headers: authHeaders() });
    var d = await r.json();
    var tbody = document.getElementById('users-body');
    if (d.status !== 'success') { tbody.innerHTML = '<tr><td colspan="6">' + d.message + '</td></tr>'; return; }
    tbody.innerHTML = d.data.map(function(u) {
        var tg = u.telegram_id || '';
        return '<tr><td>' + u.id + '</td><td>' + u.email + '</td><td>' + u.role + '</td><td>' + u.status +
            '</td><td><input id="tg-' + u.id + '" type="text" value="' + tg + '" class="input-wide"></td>' +
            '<td><button class="btn btn-secondary" onclick="setTelegram(' + u.id + ')">💾</button></td></tr>';
    }).join('');
}

async function loadCategories() {
    var r = await fetch('/api/v1/categories', { headers: authHeaders() });
    var d = await r.json();
    var tbody = document.getElementById('categories-body');
    if (d.status !== 'success') { tbody.innerHTML = '<tr><td colspan="4">' + d.message + '</td></tr>'; return; }
    tbody.innerHTML = d.data.map(function(c) {
        var icon = c.icon || '📁';
        var typeLabel = c.type === 'income' ? '💰 Доход' : '💳 Расход';
        return '<tr><td>' + c.id + '</td><td class="cell-icon">' + icon + '</td><td>' + c.name + '</td><td>' + typeLabel + '</td>' +
            '<td><button class="btn btn-secondary btn-icon" onclick="editCat(' + c.id + ',\'' + c.name.replace(/'/g,"\\'") + '\',\'' + (c.icon||'') + '\',\'' + (c.description||'').replace(/'/g,"\\'") + '\',\'' + c.type + '\')">✏️</button>' +
            '<button class="btn btn-secondary" onclick="deleteCategory(' + c.id + ')">❌</button></td></tr>';
    }).join('');
}

async function addCat(e) {
    e.preventDefault();
    var editId = document.getElementById('cat-edit-id').value;
    var body = {
        name: document.getElementById('cat-name').value,
        description: document.getElementById('cat-desc').value,
        icon: document.getElementById('cat-icon').value,
        type: document.getElementById('cat-type').value,
    };
    var url = editId ? '/api/v1/categories/' + editId : '/api/v1/categories';
    var method = editId ? 'PUT' : 'POST';
    var r = await fetch(url, { method: method, headers: authHeaders(), body: JSON.stringify(body) });
    var d = await r.json();
    alert(d.message || JSON.stringify(d));
    if (r.ok) {
        document.getElementById('cat-name').value = '';
        document.getElementById('cat-desc').value = '';
        document.getElementById('cat-icon').value = '';
        document.getElementById('cat-type').value = 'expense';
        document.getElementById('cat-edit-id').value = '';
        document.getElementById('cat-submit').textContent = '+';
        loadCategories();
    }
}

function editCat(id, name, icon, desc, type) {
    document.getElementById('cat-edit-id').value = id;
    document.getElementById('cat-name').value = name;
    document.getElementById('cat-icon').value = icon;
    document.getElementById('cat-desc').value = desc;
    document.getElementById('cat-type').value = type || 'expense';
    document.getElementById('cat-submit').textContent = '✏️';
}

async function deleteCategory(id) {
    if (!confirm('Удалить категорию?')) return;
    var r = await fetch('/api/v1/categories/' + id, { method: 'DELETE', headers: authHeaders() });
    var d = await r.json();
    alert(d.message); loadCategories();
}

async function loadSettings() {
    var r = await fetch('/api/v1/admin/settings', { headers: authHeaders() });
    var d = await r.json();
    if (d.status !== 'success') return;
    var tk = document.getElementById('cfg-bot-token');
    tk.value = d.data.HM_BOT_TOKEN || '';
    tk.placeholder = d.data.HM_BOT_TOKEN_SET ? '******** (задан)' : 'не задан';
    document.getElementById('cfg-proxy-host').value = d.data.HM_BOT_PROXY_HOST || '';
    document.getElementById('cfg-proxy-port').value = d.data.HM_BOT_PROXY_PORT || '';
    document.getElementById('cfg-proxy-user').value = d.data.HM_BOT_PROXY_USERNAME || '';
    var pw = document.getElementById('cfg-proxy-pass');
    pw.value = d.data.HM_BOT_PROXY_PASSWORD || '';
    pw.placeholder = d.data.HM_BOT_PROXY_PASSWORD_SET ? '******** (задан)' : 'не задан';
    document.getElementById('cfg-bot-users').value = d.data.HM_BOT_ALLOWED_USERS || '';
    document.getElementById('cfg-debug').value = d.data.HM_DEBUG || 'false';
    document.getElementById('cfg-dashboard-limit').value = d.data.HM_DASHBOARD_TX_LIMIT || '5';
}

async function saveBotSettings(e) {
    e.preventDefault();
    var body = {
        HM_BOT_TOKEN: document.getElementById('cfg-bot-token').value,
        HM_BOT_PROXY_HOST: document.getElementById('cfg-proxy-host').value,
        HM_BOT_PROXY_PORT: document.getElementById('cfg-proxy-port').value,
        HM_BOT_PROXY_USERNAME: document.getElementById('cfg-proxy-user').value,
        HM_BOT_PROXY_PASSWORD: document.getElementById('cfg-proxy-pass').value,
        HM_BOT_ALLOWED_USERS: document.getElementById('cfg-bot-users').value,
        HM_DEBUG: document.getElementById('cfg-debug').value,
        HM_DASHBOARD_TX_LIMIT: document.getElementById('cfg-dashboard-limit').value,
    };
    var r = await fetch('/api/v1/admin/settings', { method: 'PUT', headers: authHeaders(), body: JSON.stringify(body) });
    var d = await r.json();
    document.getElementById('settings-result').textContent = d.message || JSON.stringify(d);
}

async function loadBotStatus() {
    try {
        var r = await fetch('/api/v1/admin/bot/status', { headers: authHeaders() });
        var d = await r.json();
        var el = document.getElementById('bot-status-text');
        if (d.status === 'success' && d.data && d.data.running) {
            el.textContent = '✅ запущен (PID: ' + d.data.pid + ')';
        } else {
            el.textContent = '⏹ остановлен';
        }
        var hel = document.getElementById('bot-health-text');
        var health = d.data && d.data.health ? d.data.health : {};
        if (health.reachable) {
            hel.innerHTML = '✅ Online — @' + (health.username || '') + ' (' + (health.first_name || '') + ')';
        } else {
            hel.innerHTML = '❌ ' + (health.error || 'недоступен');
        }
    } catch (e) {
        document.getElementById('bot-status-text').textContent = '❌ ошибка загрузки';
    }
}

async function checkProxy() {
    var el = document.getElementById('proxy-check-result');
    el.textContent = '⏳ проверка...';
    try {
        var r = await fetch('/api/v1/admin/bot/check-proxy', { method: 'POST', headers: authHeaders() });
        var d = await r.json();
        var data = d.data || {};
        if (data.ok) {
            el.innerHTML = '✅ ' + data.proxy + ' — OK';
        } else {
            el.innerHTML = '❌ ' + (data.error || 'ошибка подключения');
        }
    } catch (e) {
        el.textContent = '❌ ' + e.message;
    }
}

async function botStart() {
    var out = document.getElementById('bot-result');
    out.textContent = '⏳ Запуск...';
    try {
        var r = await fetch('/api/v1/admin/bot/start', { method: 'POST', headers: authHeaders() });
        var d = await r.json();
        out.textContent = d.message;
        loadBotStatus();
    } catch (e) {
        out.textContent = '❌ Ошибка: ' + e.message;
    }
}

async function botStop() {
    var out = document.getElementById('bot-result');
    out.textContent = '⏳ Остановка...';
    try {
        var r = await fetch('/api/v1/admin/bot/stop', { method: 'POST', headers: authHeaders() });
        var d = await r.json();
        out.textContent = d.message;
        loadBotStatus();
    } catch (e) {
        out.textContent = '❌ Ошибка: ' + e.message;
    }
}

async function backup(type) {
    var out = document.getElementById('backup-result');
    out.textContent = '⏳ Создание бэкапа...';
    try {
        var r = await fetch('/api/v1/backup?type=' + type, { headers: authHeaders() });
        var d = await r.json();
        out.textContent = d.message;
    } catch (e) {
        out.textContent = '❌ Ошибка: ' + e.message;
    }
}

window.onload = function() {
    loadPending().catch(function() {});
    loadUsers().catch(function() {});
    loadCategories().catch(function() {});
    loadSettings().catch(function() {});
    loadBotStatus().catch(function() {});
};
