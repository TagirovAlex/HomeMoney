var MONTHS = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
var currentMonth, currentYear;
var allCategories = [], allBudgets = [];
var catMap = {};

function pad2(n) { return n < 10 ? '0' + n : '' + n; }

function init() {
    var d = new Date();
    currentMonth = d.getMonth() + 1;
    currentYear = d.getFullYear();
    updateMonthLabel();
    loadData();
}

function updateMonthLabel() {
    document.getElementById('month-label').textContent = MONTHS[currentMonth-1] + ' ' + currentYear;
}

function changeMonth(delta) {
    currentMonth += delta;
    if (currentMonth < 1) { currentMonth = 12; currentYear--; }
    if (currentMonth > 12) { currentMonth = 1; currentYear++; }
    updateMonthLabel();
    renderBudgets();
}

async function loadData() {
    var [catRes, budRes] = await Promise.all([
        fetch('/api/v1/categories', { headers: authHeaders() }),
        fetch('/api/v1/budgets', { headers: authHeaders() })
    ]);
    var catData = await catRes.json();
    if (catData.status === 'success') {
        allCategories = catData.data;
        catMap = {};
        allCategories.forEach(function(c) { catMap[c.id] = c; });
        var sel = document.getElementById('bg-category');
        sel.innerHTML = '<option value="">-- Выберите --</option>' +
            allCategories.map(function(c) { return '<option value="' + c.id + '">' + (c.icon || '📁') + ' ' + c.name + '</option>'; }).join('');
    }
    var budData = await budRes.json();
    if (budData.status === 'success') {
        allBudgets = budData.data;
    }
    renderBudgets();
}

function renderBudgets() {
    var templates = allBudgets.filter(function(b) { return b.is_template; });
    var overrides = allBudgets.filter(function(b) { return !b.is_template; });
    var monthOverrides = overrides.filter(function(b) { return b.month === currentMonth && b.year === currentYear; });

    var tplMap = {};
    templates.forEach(function(b) { tplMap[b.category_id] = b; });
    var ovrMap = {};
    monthOverrides.forEach(function(b) { ovrMap[b.category_id] = b; });

    var catIds = {};
    allBudgets.forEach(function(b) { catIds[b.category_id] = true; });
    var cats = allCategories.filter(function(c) { return catIds[c.id]; });
    cats.sort(function(a, b) { return (a.name || '').localeCompare(b.name || ''); });

    var html = '<section class="section"><h3>📋 Сводка на ' + MONTHS[currentMonth-1] + ' ' + currentYear + '</h3>';
    if (!cats.length && !templates.length && !monthOverrides.length) {
        html += '<p>Нет бюджетов. Создайте первый.</p></section>';
        document.getElementById('budgets-list').innerHTML = html;
        return;
    }

    html += '<div class="budget-grid"><div class="budget-grid-header">' +
        '<span class="bg-col-cat">Категория</span>' +
        '<span class="bg-col-tpl">Шаблон</span>' +
        '<span class="bg-col-month">' + MONTHS[currentMonth-1] + ' ' + currentYear + '</span>' +
        '<span class="bg-col-actions"></span>' +
        '</div>';

    cats.forEach(function(c) {
        var tpl = tplMap[c.id];
        var ovr = ovrMap[c.id];
        var tplAmount = tpl ? tpl.target_amount : null;
        var monthAmount = ovr ? ovr.target_amount : (tplAmount || null);
        var isOverride = ovr && (!tpl || ovr.target_amount !== tpl.target_amount);
        var icon = c.icon || '📁';

        html += '<div class="budget-grid-row' + (isOverride ? ' bg-override' : '') + '">';
        html += '<span class="bg-col-cat">' + icon + ' ' + c.name + '</span>';
        html += '<span class="bg-col-tpl">' + (tplAmount !== null ? fmt(tplAmount) : '—') + '</span>';
        html += '<span class="bg-col-month">' + (monthAmount !== null ? fmt(monthAmount) : '—') + '</span>';
        html += '<span class="bg-col-actions">';

        if (tpl) {
            html += '<button class="btn btn-secondary btn-sm" onclick="editBudget(' + tpl.id + ')" title="Редактировать шаблон">✏️</button>';
        } else {
            html += '<button class="btn btn-secondary btn-sm" onclick="addTemplate(' + c.id + ')" title="Добавить шаблон">📋</button>';
        }
        if (ovr) {
            html += '<button class="btn btn-secondary btn-sm" onclick="editBudget(' + ovr.id + ')" title="Редактировать">✏️</button>';
            html += '<button class="btn btn-secondary btn-sm" onclick="deleteBudget(' + ovr.id + ')" title="Удалить переопределение">❌</button>';
        } else if (tpl) {
            html += '<button class="btn btn-secondary btn-sm" onclick="addOverride(' + c.id + ',' + tpl.target_amount + ')" title="Переопределить на этот месяц">📝</button>';
        } else {
            html += '<button class="btn btn-secondary btn-sm" onclick="addOverride(' + c.id + ')" title="Добавить бюджет на месяц">➕</button>';
        }

        html += '</span></div>';
    });

    html += '</div></section>';

    document.getElementById('budgets-list').innerHTML = html;
}

function showAddForm() {
    document.getElementById('bg-edit-id').value = '';
    document.getElementById('bg-category').value = '';
    document.getElementById('bg-amount').value = '';
    document.getElementById('bg-is-template').checked = true;
    document.getElementById('bg-month').value = currentMonth;
    document.getElementById('bg-year').value = currentYear;
    document.getElementById('add-form-title').textContent = 'Новый бюджет';
    document.getElementById('bg-submit').textContent = 'Сохранить';
    document.getElementById('bg-month-picker').style.display = 'none';
    document.getElementById('add-form').style.display = 'block';
}

function hideAddForm() {
    document.getElementById('add-form').style.display = 'none';
}

function toggleMonthPicker() {
    var isTpl = document.getElementById('bg-is-template').checked;
    document.getElementById('bg-month-picker').style.display = isTpl ? 'none' : '';
    if (!isTpl) {
        document.getElementById('bg-month').value = currentMonth;
        document.getElementById('bg-year').value = currentYear;
    }
}

function editBudget(id) {
    var b = allBudgets.find(function(x) { return x.id === id; });
    if (!b) return;
    document.getElementById('bg-edit-id').value = id;
    document.getElementById('bg-category').value = b.category_id;
    document.getElementById('bg-amount').value = b.target_amount;
    var isTpl = b.is_template;
    document.getElementById('bg-is-template').checked = isTpl;
    if (isTpl) {
        document.getElementById('bg-month-picker').style.display = 'none';
    } else {
        document.getElementById('bg-month').value = b.month;
        document.getElementById('bg-year').value = b.year;
        document.getElementById('bg-month-picker').style.display = '';
    }
    document.getElementById('add-form-title').textContent = 'Редактировать бюджет';
    document.getElementById('bg-submit').textContent = '✏️';
    document.getElementById('add-form').style.display = 'block';
}

function addTemplate(catId) {
    document.getElementById('bg-edit-id').value = '';
    document.getElementById('bg-category').value = catId;
    document.getElementById('bg-amount').value = '';
    document.getElementById('bg-is-template').checked = true;
    document.getElementById('bg-month-picker').style.display = 'none';
    document.getElementById('add-form-title').textContent = 'Новый шаблон';
    document.getElementById('bg-submit').textContent = 'Сохранить';
    document.getElementById('add-form').style.display = 'block';
}

function addOverride(catId, suggestedAmount) {
    document.getElementById('bg-edit-id').value = '';
    document.getElementById('bg-category').value = catId;
    document.getElementById('bg-amount').value = suggestedAmount || '';
    document.getElementById('bg-is-template').checked = false;
    document.getElementById('bg-month').value = currentMonth;
    document.getElementById('bg-year').value = currentYear;
    document.getElementById('bg-month-picker').style.display = '';
    document.getElementById('add-form-title').textContent = 'Бюджет на ' + MONTHS[currentMonth-1] + ' ' + currentYear;
    document.getElementById('bg-submit').textContent = 'Сохранить';
    document.getElementById('add-form').style.display = 'block';
}

async function saveBudget(e) {
    e.preventDefault();
    var editId = document.getElementById('bg-edit-id').value;
    var catId = parseInt(document.getElementById('bg-category').value);
    var amount = parseFloat(document.getElementById('bg-amount').value);
    var isTpl = document.getElementById('bg-is-template').checked;

    var body = { category_id: catId, target_amount: amount };
    if (!isTpl) {
        body.month = parseInt(document.getElementById('bg-month').value);
        body.year = parseInt(document.getElementById('bg-year').value);
    }

    var url = editId ? '/api/v1/budgets/' + editId : '/api/v1/budgets';
    var method = editId ? 'PUT' : 'POST';

    if (editId) {
        var b = allBudgets.find(function(x) { return x.id === parseInt(editId); });
        if (b) body = { target_amount: amount };
    }

    var r = await fetch(url, { method: method, headers: authHeaders(), body: JSON.stringify(body) });
    var d = await r.json();
    alert(d.message || d.error);
    if (r.ok) {
        hideAddForm();
        loadData();
    }
}

async function deleteBudget(id) {
    if (!confirm('Удалить бюджет?')) return;
    var r = await fetch('/api/v1/budgets/' + id, { method: 'DELETE', headers: authHeaders() });
    var d = await r.json();
    alert(d.message);
    loadData();
}

async function copyFromPrev() {
    var prevMonth = currentMonth - 1;
    var prevYear = currentYear;
    if (prevMonth < 1) { prevMonth = 12; prevYear--; }
    if (!confirm('Копировать переопределения из ' + MONTHS[prevMonth-1] + ' ' + prevYear + ' в ' + MONTHS[currentMonth-1] + ' ' + currentYear + '?')) return;
    var r = await fetch('/api/v1/budgets/copy', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
            from_month: prevMonth,
            from_year: prevYear,
            to_month: currentMonth,
            to_year: currentYear
        })
    });
    var d = await r.json();
    alert(d.message);
    if (r.ok) loadData();
}

init();