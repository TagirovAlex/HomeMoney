var userId = null, curPage = 1, totalPages = 1, pageSize = 20;
var sortBy = 'id', sortDir = 'desc';

function pad2(n) { return n < 10 ? '0' + n : '' + n; }

function setPreset(type, offset) {
    var d = new Date();
    var y = d.getFullYear(), m = d.getMonth() + 1;
    var start, end;
    if (type === 'month') {
        var tm = m + (offset || 0);
        var ty = y;
        if (tm < 1) { tm = 12; ty--; }
        if (tm > 12) { tm = 1; ty++; }
        start = ty + '-' + pad2(tm) + '-01';
        var lastDay = new Date(ty, tm, 0).getDate();
        end = ty + '-' + pad2(tm) + '-' + pad2(lastDay);
    } else if (type === 'quarter') {
        var q = Math.floor((m - 1) / 3);
        var qStart = q * 3 + 1;
        start = y + '-' + pad2(qStart) + '-01';
        var qEnd = qStart + 2;
        var lastDay = new Date(y, qEnd, 0).getDate();
        end = y + '-' + pad2(qEnd) + '-' + pad2(lastDay);
    } else if (type === 'year') {
        start = y + '-01-01';
        end = y + '-12-31';
    } else {
        document.getElementById('f-start').value = '';
        document.getElementById('f-end').value = '';
        return;
    }
    document.getElementById('f-start').value = start;
    document.getElementById('f-end').value = end;
}

function setSort(col) {
    if (sortBy === col) { sortDir = sortDir === 'asc' ? 'desc' : 'asc'; }
    else { sortBy = col; sortDir = 'desc'; }
    loadTransactions();
}

function sortData(data) {
    return data.slice().sort(function(a, b) {
        var va = a[sortBy], vb = b[sortBy];
        if (typeof va === 'string') { va = va.toLowerCase(); vb = (vb || '').toLowerCase(); }
        if (va == null) va = '';
        if (vb == null) vb = '';
        if (va < vb) return sortDir === 'asc' ? -1 : 1;
        if (va > vb) return sortDir === 'asc' ? 1 : -1;
        return 0;
    });
}

function sortIcon(col) {
    if (sortBy !== col) return '';
    return sortDir === 'asc' ? ' ▲' : ' ▼';
}

function getUser() {
    if (window.__userId) { userId = window.__userId; return; }
    try { var u = JSON.parse(localStorage.getItem('user')); userId = u.user_id; } catch(e) { userId = null; }
}

async function loadCategoriesFilter() {
    var r = await fetch('/api/v1/categories', { headers: authHeaders() });
    var d = await r.json();
    if (d.status !== 'success') return;
    var sel = document.getElementById('f-category');
    sel.innerHTML = '<option value="">Все</option>' +
        d.data.map(function(c) { return '<option value="' + c.id + '">' + c.name + '</option>'; }).join('');
}

var _budgetsData = [];

async function loadCategories() {
    var r = await fetch('/api/v1/categories', { headers: authHeaders() });
    var d = await r.json();
    if (d.status !== 'success') return;
    var sel = document.getElementById('tx-category');
    sel.innerHTML = '<option value="">-- Выберите --</option>' +
        d.data.map(function(c) { return '<option value="' + c.id + '">' + (c.icon || '') + ' ' + c.name + '</option>'; }).join('');
    var br = await fetch('/api/v1/budgets', { headers: authHeaders() });
    var bd = await br.json();
    if (bd.status === 'success') _budgetsData = bd.data;
}

function txCategoryChanged() {
    var catId = parseInt(document.getElementById('tx-category').value);
    var el = document.getElementById('tx-budget-info');
    if (!catId) { el.textContent = ''; return; }
    var b = _budgetsData.find(function(x) { return x.category_id === catId; });
    el.textContent = b ? 'Бюджет по этой категории: ' + fmt(b.target_amount) + ' RUB' : 'Бюджет не задан';
}

async function loadTransactions() {
    getUser();
    if (!userId) return;
    var start = document.getElementById('f-start').value;
    var end = document.getElementById('f-end').value;
    if (!start || !end) { return; }
    var cat = document.getElementById('f-category').value;
    var url = '/api/v1/user/' + userId + '/transactions?start_date=' + start + '&end_date=' + end + '&category_id=' + cat + '&page=' + curPage + '&limit=' + pageSize;
    var r = await fetch(url, { headers: authHeaders() });
    var d = await r.json();
    var tbody = document.getElementById('tx-table');
    if (d.status !== 'success') { tbody.innerHTML = '<tr><td colspan="7">' + d.message + '</td></tr>'; return; }
    if (!d.data.length) { tbody.innerHTML = '<tr><td colspan="7">Нет транзакций</td></tr>'; return; }
    var sorted = sortData(d.data);
    tbody.innerHTML = sorted.map(function(tx) {
        var typeLabel = tx.type === 'income' ? '💰 Доход' : '💳 Расход';
        return '<tr><td>' + tx.id + '</td><td>' + (tx.category_icon || '📁') + ' ' + tx.category_name + '</td><td>' + fmt(tx.amount) + '</td><td>' + typeLabel + '</td><td>' + tx.description + '</td><td>' + (tx.date ? tx.date.slice(0, 10) : '') + '</td>' +
            '<td><button class="btn btn-secondary btn-icon" onclick="editTransaction(' + tx.id + ')">✏️</button>' +
            '<button class="btn btn-secondary" onclick="deleteTransaction(' + tx.id + ')">❌</button></td></tr>';
    }).join('');
    ['id','category_name','amount','type','description','date'].forEach(function(c) {
        document.getElementById('s-' + c).textContent = sortIcon(c);
    });
    totalPages = Math.ceil(d.total / d.limit) || 1;
    document.getElementById('pagination').style.display = 'block';
    document.getElementById('page-info').textContent = curPage + ' / ' + totalPages;
    document.getElementById('prev-page').disabled = curPage <= 1;
    document.getElementById('next-page').disabled = curPage >= totalPages;
}

function goPage(delta) {
    var np = curPage + delta;
    if (np < 1 || np > totalPages) return;
    curPage = np;
    loadTransactions();
}

function changeLimit() {
    pageSize = parseInt(document.getElementById('page-size').value);
    curPage = 1;
    loadTransactions();
}

function showAddForm() {
    document.getElementById('form-title').textContent = 'Новая транзакция';
    document.getElementById('tx-edit-id').value = '';
    document.getElementById('tx-submit').textContent = 'Сохранить';
    document.getElementById('tx-amount').value = '';
    document.getElementById('tx-category').value = '';
    document.getElementById('tx-desc').value = '';
    document.getElementById('tx-budget-info').textContent = '';
    setDefaultDate();
    document.getElementById('add-form').style.display = 'block';
}
function hideAddForm() { document.getElementById('add-form').style.display = 'none'; }

async function editTransaction(txId) {
    getUser();
    if (!userId) return;
    var r = await fetch('/api/v1/user/' + userId + '/transactions/' + txId, { headers: authHeaders() });
    var d = await r.json();
    if (d.status !== 'success') { alert(d.message); return; }
    var tx = d.data;
    document.getElementById('form-title').textContent = 'Редактировать транзакцию #' + txId;
    document.getElementById('tx-edit-id').value = txId;
    document.getElementById('tx-submit').textContent = '✏️ Обновить';
    document.getElementById('tx-amount').value = tx.amount;
    document.getElementById('tx-category').value = tx.category_id;
    document.getElementById('tx-desc').value = tx.description || '';
    document.getElementById('tx-date').value = tx.date ? tx.date.slice(0, 10) : '';
    txCategoryChanged();
    document.getElementById('add-form').style.display = 'block';
}

async function saveTransaction(e) {
    e.preventDefault();
    getUser();
    if (!userId) { alert('Ошибка авторизации'); return; }
    var editId = document.getElementById('tx-edit-id').value;
    var body = {
        amount: parseFloat(document.getElementById('tx-amount').value),
        category_id: parseInt(document.getElementById('tx-category').value),
        description: document.getElementById('tx-desc').value,
    };
    var dateVal = document.getElementById('tx-date').value;
    if (dateVal) body.date = dateVal;
    var url, method;
    if (editId) {
        url = '/api/v1/user/' + userId + '/transactions/' + editId;
        method = 'PUT';
    } else {
        url = '/api/v1/user/' + userId + '/create_transaction';
        method = 'POST';
    }
    var r = await fetch(url, { method: method, headers: authHeaders(), body: JSON.stringify(body) });
    var d = await r.json();
    alert(d.message || d.error);
    if (r.ok) { hideAddForm(); loadTransactions(); }
}

function setDefaultDate() {
    var d = new Date();
    var ds = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
    document.getElementById('tx-date').value = ds;
}

async function deleteTransaction(txId) {
    if (!confirm('Удалить транзакцию #' + txId + '?')) return;
    getUser();
    if (!userId) return;
    var r = await fetch('/api/v1/user/' + userId + '/transactions/' + txId, { method: 'DELETE', headers: authHeaders() });
    var d = await r.json();
    alert(d.message);
    if (r.ok) loadTransactions();
}

window.__pageInit = function(uid) {
    userId = uid;
    setPreset('month', 0);
    loadCategoriesFilter();
    loadCategories();
    setDefaultDate();
    pageSize = parseInt(document.getElementById('page-size').value);
    loadTransactions();
};
if (window.__userId) window.__pageInit(window.__userId);
