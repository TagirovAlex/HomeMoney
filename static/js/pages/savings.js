async function loadSavings() {
    var r = await fetch('/api/v1/savings', { headers: authHeaders() });
    var d = await r.json();
    var container = document.getElementById('savings-list');
    if (d.status !== 'success' || !d.data.length) {
        container.innerHTML = '<p>Нет накоплений. Добавьте первое.</p>';
        return;
    }
    var icons = { deposit: '🏦', stocks: '📈', bonds: '📜', cash: '💵', other: '📦' };
    container.innerHTML = d.data.map(function(s) {
        var icon = icons[s.type] || '📦';
        var typeLabel = { deposit: 'Депозит', stocks: 'Акции', bonds: 'Облигации', cash: 'Наличные', other: 'Другое' }[s.type] || s.type;
        return '<div class="card card-left">' +
            '<div class="flex-between">' +
            '<div><span class="card-label">' + icon + ' ' + s.name + '</span><br>' +
            '<span class="text-secondary fs-small">' + typeLabel + '</span><br>' +
            '<span class="card-value card-value-sm">' + fmt(s.amount) + ' RUB</span>' +
            (s.description ? '<br><span class="text-secondary fs-small">' + s.description + '</span>' : '') +
            '</div>' +
            '<div><button class="btn btn-secondary btn-icon" onclick="editSaving(' + s.id + ')">✏️</button>' +
            '<button class="btn btn-secondary" onclick="deleteSaving(' + s.id + ')">❌</button></div>' +
            '</div></div>';
    }).join('');
}

function showAddForm() {
    document.getElementById('form-title').textContent = 'Новое накопление';
    document.getElementById('form-submit').textContent = 'Сохранить';
    document.getElementById('saving-id').value = '';
    document.getElementById('saving-name').value = '';
    document.getElementById('saving-amount').value = '0';
    document.getElementById('saving-type').value = 'deposit';
    document.getElementById('saving-desc').value = '';
    document.getElementById('add-form').style.display = 'block';
}

function hideAddForm() {
    document.getElementById('add-form').style.display = 'none';
}

async function saveSaving(e) {
    e.preventDefault();
    var id = document.getElementById('saving-id').value;
    var body = {
        name: document.getElementById('saving-name').value,
        amount: parseFloat(document.getElementById('saving-amount').value) || 0,
        type: document.getElementById('saving-type').value,
        description: document.getElementById('saving-desc').value,
    };
    var url = id ? '/api/v1/savings/' + id : '/api/v1/savings';
    var method = id ? 'PUT' : 'POST';
    var r = await fetch(url, { method: method, headers: authHeaders(), body: JSON.stringify(body) });
    var d = await r.json();
    alert(d.message || d.error);
    if (r.ok) { hideAddForm(); loadSavings(); }
}

async function editSaving(id) {
    var r = await fetch('/api/v1/savings', { headers: authHeaders() });
    var d = await r.json();
    if (d.status !== 'success') return;
    var src = null;
    d.data.forEach(function(s) { if (s.id === id) src = s; });
    if (!src) return;
    document.getElementById('form-title').textContent = 'Редактировать: ' + src.name;
    document.getElementById('form-submit').textContent = 'Обновить';
    document.getElementById('saving-id').value = src.id;
    document.getElementById('saving-name').value = src.name;
    document.getElementById('saving-amount').value = src.amount;
    document.getElementById('saving-type').value = src.type || 'deposit';
    document.getElementById('saving-desc').value = src.description || '';
    document.getElementById('add-form').style.display = 'block';
}

async function deleteSaving(id) {
    if (!confirm('Удалить это накопление?')) return;
    var r = await fetch('/api/v1/savings/' + id, { method: 'DELETE', headers: authHeaders() });
    var d = await r.json();
    alert(d.message); loadSavings();
}

window.onload = loadSavings;
