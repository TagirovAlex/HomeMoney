async function loadCategories() {
    var r = await fetch('/api/v1/categories', { headers: authHeaders() });
    var d = await r.json();
    var tbody = document.getElementById('categories-body');
    if (d.status !== 'success' || !d.data.length) {
        tbody.innerHTML = '<tr><td colspan="5">Нет категорий. Добавьте первую.</td></tr>';
        return;
    }
    tbody.innerHTML = d.data.map(function(c) {
        var icon = c.icon || '📁';
        var typeLabel = c.type === 'income' ? '💰 Доход' : '💳 Расход';
        return '<tr><td>' + c.id + '</td><td class="cell-icon">' + icon + '</td><td>' + c.name + '</td><td>' + typeLabel + '</td>' +
            '<td><button class="btn btn-secondary btn-icon" data-action="edit-category" data-id="' + c.id + '" data-name="' + c.name.replace(/"/g,'&quot;') + '" data-icon="' + (c.icon||'') + '" data-desc="' + (c.description||'').replace(/"/g,'&quot;') + '" data-type="' + c.type + '">✏️</button>' +
            '<button class="btn btn-secondary" data-action="delete-category" data-id="' + c.id + '">❌</button></td></tr>';
    }).join('');
}

async function saveCategory(e) {
    e.preventDefault();
    var editId = document.getElementById('cat-edit-id').value;
    var body = {
        name: document.getElementById('cat-name').value,
        icon: document.getElementById('cat-icon').value || '📁',
        description: document.getElementById('cat-desc').value,
        type: document.getElementById('cat-type').value,
    };
    var url = editId ? '/api/v1/categories/' + editId : '/api/v1/categories';
    var method = editId ? 'PUT' : 'POST';
    var r = await fetch(url, { method: method, headers: authHeaders(), body: JSON.stringify(body) });
    var d = await r.json();
    alert(d.message || d.error);
    if (r.ok) {
        document.getElementById('cat-name').value = '';
        document.getElementById('cat-icon').value = '';
        document.getElementById('cat-desc').value = '';
        document.getElementById('cat-type').value = 'expense';
        document.getElementById('cat-edit-id').value = '';
        document.getElementById('cat-submit').textContent = '+';
        loadCategories();
    }
}

function editCategory(id, name, icon, desc, type) {
    document.getElementById('cat-edit-id').value = id;
    document.getElementById('cat-name').value = name;
    document.getElementById('cat-icon').value = icon;
    document.getElementById('cat-desc').value = desc;
    document.getElementById('cat-type').value = type || 'expense';
    document.getElementById('cat-submit').textContent = '✏️';
}

async function deleteCategory(id) {
    if (!confirm('Удалить категорию? Расходы с этой категорией останутся.')) return;
    var r = await fetch('/api/v1/categories/' + id, { method: 'DELETE', headers: authHeaders() });
    var d = await r.json();
    alert(d.message); loadCategories();
}

document.addEventListener('DOMContentLoaded', function() {
    loadCategories();

    document.getElementById('cat-form').addEventListener('submit', saveCategory);

    document.getElementById('categories-body').addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action]');
        if (!btn) return;
        var id = parseInt(btn.getAttribute('data-id'));
        if (btn.getAttribute('data-action') === 'edit-category') {
            editCategory(id, btn.getAttribute('data-name'), btn.getAttribute('data-icon'), btn.getAttribute('data-desc'), btn.getAttribute('data-type'));
        } else if (btn.getAttribute('data-action') === 'delete-category') {
            deleteCategory(id);
        }
    });
});
