async function loadCategories() {
    var r = await fetch('/api/v1/categories', { headers: authHeaders() });
    var d = await r.json();
    var container = document.getElementById('categories-list');
    if (d.status !== 'success' || !d.data.length) {
        container.innerHTML = '<p>Нет категорий. Добавьте первую.</p>';
        return;
    }
    container.innerHTML = d.data.map(function(c) {
        return '<div class="card card-left">' +
            '<div class="flex-between">' +
            '<div><span class="card-label">' + (c.icon || '📁') + ' ' + c.name + '</span>' +
            (c.description ? '<br><span class="text-secondary fs-small">' + c.description + '</span>' : '') +
            '</div>' +
            '<div><button class="btn btn-secondary btn-icon" data-action="edit-category" data-id="' + c.id + '">✏️</button>' +
            '<button class="btn btn-secondary" data-action="delete-category" data-id="' + c.id + '">❌</button></div>' +
            '</div></div>';
    }).join('');
}

function showAddForm() {
    document.getElementById('form-title').textContent = 'Новая категория';
    document.getElementById('form-submit').textContent = 'Сохранить';
    document.getElementById('cat-id').value = '';
    document.getElementById('cat-name').value = '';
    document.getElementById('cat-icon').value = '📁';
    document.getElementById('cat-desc').value = '';
    document.getElementById('add-form').style.display = 'block';
}

function hideAddForm() {
    document.getElementById('add-form').style.display = 'none';
}

async function saveCategory(e) {
    e.preventDefault();
    var id = document.getElementById('cat-id').value;
    var body = {
        name: document.getElementById('cat-name').value,
        icon: document.getElementById('cat-icon').value || '📁',
        description: document.getElementById('cat-desc').value,
    };
    var url = id ? '/api/v1/categories/' + id : '/api/v1/categories';
    var method = id ? 'PUT' : 'POST';
    var r = await fetch(url, { method: method, headers: authHeaders(), body: JSON.stringify(body) });
    var d = await r.json();
    alert(d.message || d.error);
    if (r.ok) { hideAddForm(); loadCategories(); }
}

async function editCategory(id) {
    var r = await fetch('/api/v1/categories', { headers: authHeaders() });
    var d = await r.json();
    if (d.status !== 'success') return;
    var cat = null;
    d.data.forEach(function(c) { if (c.id === id) cat = c; });
    if (!cat) return;
    document.getElementById('form-title').textContent = 'Редактировать: ' + cat.name;
    document.getElementById('form-submit').textContent = 'Обновить';
    document.getElementById('cat-id').value = cat.id;
    document.getElementById('cat-name').value = cat.name;
    document.getElementById('cat-icon').value = cat.icon || '📁';
    document.getElementById('cat-desc').value = cat.description || '';
    document.getElementById('add-form').style.display = 'block';
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
    document.getElementById('cat-add-btn').addEventListener('click', showAddForm);
    document.getElementById('cat-cancel-btn').addEventListener('click', hideAddForm);

    document.getElementById('categories-list').addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action]');
        if (!btn) return;
        var id = parseInt(btn.getAttribute('data-id'));
        if (btn.getAttribute('data-action') === 'edit-category') editCategory(id);
        else if (btn.getAttribute('data-action') === 'delete-category') deleteCategory(id);
    });
});
