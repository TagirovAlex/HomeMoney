var typeIcons = { deposit: '🏦', stocks: '📈', bonds: '📜', cash: '💵', other: '📦' };
var _reportData = null;
var _selectedCategoryId = null;

function pad2(n) { return n < 10 ? '0' + n : '' + n; }

function todayStr() { var d = new Date(); return d.getFullYear() + '-' + pad2(d.getMonth()+1) + '-' + pad2(d.getDate()); }

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
        document.getElementById('r-start').value = '';
        document.getElementById('r-end').value = '';
        return;
    }
    document.getElementById('r-start').value = start;
    document.getElementById('r-end').value = end;
}

async function loadCategories() {
    var r = await fetch('/api/v1/categories', { headers: authHeaders() });
    var d = await r.json();
    if (d.status !== 'success') return;
    var sel = document.getElementById('r-category');
    sel.innerHTML = '<option value="">Все категории</option>' +
        d.data.map(function(c) { return '<option value="' + c.id + '">' + (c.icon || '📁') + ' ' + c.name + '</option>'; }).join('');
}

async function loadReport(e) {
    if (e) e.preventDefault();
    var start = document.getElementById('r-start').value;
    var end = document.getElementById('r-end').value;
    if (!start || !end) { alert('Укажите период'); return; }
    var cat = document.getElementById('r-category').value;
    var showTx = document.getElementById('r-show-tx').checked;
    var params = 'start_date=' + start + '&end_date=' + end + '&_=' + Date.now();
    if (cat) params += '&category_id=' + cat;
    if (showTx) params += '&include_transactions=1';
    var r = await fetch('/api/v1/reports?' + params, { headers: authHeaders() });
    var d = await r.json();
    if (d.status !== 'success') { alert(d.message); return; }
    _reportData = d.data;

    var s = d.data.summary;
    document.getElementById('report-summary').innerHTML =
        '<div class="card"><span class="card-label">💰 Доходы</span><span class="card-value income">+' + fmt(s.total_income || 0) + ' RUB</span></div>' +
        '<div class="card"><span class="card-label">💳 Расходы</span><span class="card-value expense">-' + fmt(s.total_spent) + ' RUB</span></div>' +
        '<div class="card"><span class="card-label">📊 Бюджет</span><span class="card-value">' + fmt(s.total_budgeted) + ' RUB</span></div>';
    document.getElementById('report-balance').innerHTML =
        '<div class="card"><span class="card-label">Остаток на начало</span><span class="card-value">' + fmt(s.opening_balance || 0) + ' RUB</span></div>' +
        '<div class="card"><span class="card-label">Остаток на конец</span><span class="card-value">' + fmt(s.closing_balance || 0) + ' RUB</span></div>';
    var sv = d.data.savings;
    if (sv && sv.items && sv.items.length) {
        document.getElementById('report-savings').innerHTML =
            '<div class="card card-savings">' +
            '<span class="card-label">🏦 Накопления (всего: ' + fmt(sv.total) + ' RUB)</span><br>' +
            sv.items.map(function(x) {
                var ic = typeIcons[x.type] || '📦';
                return '<span class="report-tag">' + ic + ' ' + x.name + ': <strong>' + fmt(x.amount) + ' RUB</strong> (' + x.type_label + ')</span><br>';
            }).join('') +
            '</div>';
    } else {
        document.getElementById('report-savings').innerHTML = '';
    }

    var catSelected = document.getElementById('r-category').value;
    var catDetailSection = document.getElementById('category-detail-section');
    if (catSelected) {
        catDetailSection.style.display = 'none';
    } else {
        catDetailSection.style.display = '';
        var tbody = document.getElementById('report-table');
        var keys = Object.keys(d.data.detailed_spending || {});
        if (keys.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4">Нет расходов за выбранный период.</td></tr>';
        } else {
            tbody.innerHTML = keys.map(function(k) {
                var item = d.data.detailed_spending[k];
                var rem = fmt(item.budget - item.spent);
                var icon = item.icon || '📁';
                var txCount = (item.transactions || []).length;
                var detailLink = txCount ? ' <a href="#" onclick="event.preventDefault();showCategoryDetail(' + k + ',\'' + item.name.replace(/'/g,"\\'") + '\')">(' + txCount + ')</a>' : '';
                return '<tr><td>' + icon + ' ' + item.name + detailLink + '</td><td>' + fmt(item.spent) + '</td><td>' + fmt(item.budget) + '</td><td>' + rem + '</td></tr>';
            }).join('');
        }
    }

    var txs = d.data.transactions || [];
    var txSection = document.getElementById('tx-list-section');
    var txBody = document.getElementById('tx-list-table');
    if (txs.length) {
        txSection.classList.remove('hidden');
        document.getElementById('tx-list-title').textContent = '(' + txs.length + ' шт., всего: ' + fmt(txs.reduce(function(a,t){return a+t.amount;},0)) + ' RUB)';
        txBody.innerHTML = txs.map(function(t) {
            var tl = t.type === 'income' ? '💰 Доход' : '💳 Расход';
            return '<tr><td>' + t.id + '</td><td>' + (t.category_icon || '📁') + ' ' + t.category_name + '</td><td>' + fmt(t.amount) + '</td><td>' + t.description + '</td><td>' + (t.date ? t.date.slice(0,10) : '') + '</td><td>' + tl + '</td></tr>';
        }).join('');
    } else {
        txSection.classList.add('hidden');
    }
}

function showCategoryDetail(catId, catName) {
    _selectedCategoryId = catId;
    var catData = _reportData.detailed_spending[catId];
    if (!catData || !catData.transactions || !catData.transactions.length) {
        alert('Нет транзакций по этой категории за период');
        return;
    }
    var txs = catData.transactions;
    var html = '<div class="card card-detail">' +
        '<div class="card-detail-header">' +
        '<strong>' + (catData.icon || '📁') + ' ' + catName + '</strong>' +
        '<span>Всего: ' + fmt(catData.spent) + ' RUB</span>' +
        '<button class="btn btn-secondary" onclick="this.parentElement.parentElement.remove()">✕</button>' +
        '</div>' +
        '<table class="data-table"><thead><tr><th>ID</th><th>Сумма</th><th>Описание</th><th>Дата</th></tr></thead><tbody>' +
        txs.map(function(t) {
            return '<tr><td>' + t.id + '</td><td>' + fmt(t.amount) + '</td><td>' + t.description + '</td><td>' + (t.date ? t.date.slice(0,10) : '') + '</td></tr>';
        }).join('') +
        '</tbody></table></div>';
    var container = document.getElementById('cat-detail');
    if (!container) {
        container = document.createElement('div');
        container.id = 'cat-detail';
        container.className = 'mt-12';
        document.querySelector('.section').after(container);
    }
    container.innerHTML = html;
}

window.onload = function() {
    setPreset('month', 0);
    loadCategories();
    loadReport(null);
};
