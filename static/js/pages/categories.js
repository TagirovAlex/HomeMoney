async function loadCategories() {
    var r = await fetch('/api/v1/categories', { headers: authHeaders() });
    var d = await r.json();
    var tbody = document.getElementById('categories-body');
    if (d.status !== 'success') { tbody.innerHTML = '<tr><td colspan="5">' + d.message + '</td></tr>'; return; }
    tbody.innerHTML = d.data.map(function(c) {
        var icon = c.icon || '📁';
        var typeLabel = c.type === 'income' ? '💰 Доход' : '💳 Расход';
        var safe = JSON.stringify([c.id, c.name, c.icon || '', c.description || '', c.type]);
        return '<tr><td>' + c.id + '</td><td class="cell-icon">' + icon + '</td><td>' + c.name.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</td><td>' + typeLabel + '</td>' +
            '<td><button class="btn btn-secondary btn-icon" data-cat=\'' + safe + '\' onclick="editCategory(this)">✏️</button>' +
            '<button class="btn btn-secondary" onclick="deleteCategory(' + c.id + ')">❌</button></td></tr>';
    }).join('');
}

async function addCategory(e) {
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

function editCategory(btn) {
    var data = JSON.parse(btn.getAttribute('data-cat'));
    document.getElementById('cat-edit-id').value = data[0];
    document.getElementById('cat-name').value = data[1];
    document.getElementById('cat-icon').value = data[2];
    document.getElementById('cat-desc').value = data[3];
    document.getElementById('cat-type').value = data[4] || 'expense';
    document.getElementById('cat-submit').textContent = '✏️';
}

async function deleteCategory(id) {
    if (!confirm('Удалить категорию?')) return;
    var r = await fetch('/api/v1/categories/' + id, { method: 'DELETE', headers: authHeaders() });
    var d = await r.json();
    alert(d.message); loadCategories();
}

window.onload = function() { loadCategories(); };
