var MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
var MONTHS_SHORT = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
var currentMonth, currentYear;
var allCategories = [], allBudgets = [];
var catMap = {};

function pad2(n) { return n < 10 ? '0' + n : '' + n; }

function populateSelect(id, values) {
    var sel = document.getElementById(id);
    sel.innerHTML = values.map(function(v) { return '<option value="' + v.value + '">' + v.label + '</option>'; }).join('');
}

function populateMonthSelects() {
    var months = [];
    for (var i = 1; i <= 12; i++) months.push({ value: i, label: MONTHS[i-1] });
    populateSelect('bg-month', months);
    populateSelect('bg-period-from-month', months);
    populateSelect('bg-period-to-month', months);
    var year = new Date().getFullYear();
    var years = [];
    for (var y = year - 1; y <= year + 5; y++) years.push({ value: y, label: y });
    populateSelect('bg-year', years);
    populateSelect('bg-period-from-year', years);
    populateSelect('bg-period-to-year', years);
}

function init() {
    var d = new Date();
    currentMonth = d.getMonth() + 1;
    currentYear = d.getFullYear();
    populateMonthSelects();
    updateMonthLabel();
    loadData();
}

function updateMonthLabel() {
    document.getElementById('month-label').textContent = MONTHS_SHORT[currentMonth-1] + ' ' + currentYear;
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

function getBudgetType() {
    var radios = document.getElementsByName('bg-type');
    for (var i = 0; i < radios.length; i++) {
        if (radios[i].checked) return radios[i].value;
    }
    return 'template';
}

function onBudgetTypeChange() {
    var t = getBudgetType();
    document.getElementById('bg-month-fields').style.display = t === 'month' ? '' : 'none';
    document.getElementById('bg-period-fields').style.display = t === 'period' ? '' : 'none';
    if (t === 'month') {
        document.getElementById('bg-month').value = currentMonth;
        document.getElementById('bg-year').value = currentYear;
    }
    if (t === 'period') {
        document.getElementById('bg-period-from-month').value = currentMonth;
        document.getElementById('bg-period-from-year').value = currentYear;
        document.getElementById('bg-period-to-month').value = currentMonth;
        document.getElementById('bg-period-to-year').value = currentYear;
    }
}

function renderBudgets() {
    var templates = allBudgets.filter(function(b) { return b.is_template; });
    var monthOverrides = allBudgets.filter(function(b) {
        return !b.is_template && !b.period_end_month && b.month === currentMonth && b.year === currentYear;
    });
    var periodBudgets = allBudgets.filter(function(b) {
        return b.period_end_month && b.month && b.year;
    }).filter(function(b) {
        var start = b.year * 12 + b.month;
        var end = b.period_end_year * 12 + b.period_end_month;
        var target = currentYear * 12 + currentMonth;
        return start <= target && target <= end;
    });

    var tplMap = {};
    templates.forEach(function(b) { tplMap[b.category_id] = b; });
    var ovrMap = {};
    monthOverrides.forEach(function(b) { ovrMap[b.category_id] = b; });
    var perMap = {};
    periodBudgets.forEach(function(b) { perMap[b.category_id] = b; });

    var catIds = {};
    allBudgets.forEach(function(b) { catIds[b.category_id] = true; });
    var cats = allCategories.filter(function(c) { return catIds[c.id]; });
    cats.sort(function(a, b) { return (a.name || '').localeCompare(b.name || ''); });

    var html = '<section class="section"><h3>📋 Сводка на ' + MONTHS_SHORT[currentMonth-1] + ' ' + currentYear + '</h3>';
    if (!cats.length && !templates.length && !monthOverrides.length && !periodBudgets.length) {
        html += '<p>Нет бюджетов. Создайте первый.</p></section>';
        document.getElementById('budgets-list').innerHTML = html;
        return;
    }

    html += '<div class="budget-grid"><div class="budget-grid-header">' +
        '<span class="bg-col-cat">Категория</span>' +
        '<span class="bg-col-tpl">Шаблон</span>' +
        '<span class="bg-col-month">' + MONTHS_SHORT[currentMonth-1] + ' ' + currentYear + '</span>' +
        '<span class="bg-col-actions"></span>' +
        '</div>';

    cats.forEach(function(c) {
        var tpl = tplMap[c.id];
        var ovr = ovrMap[c.id];
        var per = perMap[c.id];
        var tplAmount = tpl ? tpl.target_amount : null;
        var monthAmount = ovr ? ovr.target_amount : (per ? per.target_amount : (tplAmount || null));
        var isOverride = !!(ovr || per);
        var icon = c.icon || '📁';

        html += '<div class="budget-grid-row' + (isOverride ? ' bg-override' : '') + '">';
        html += '<span class="bg-col-cat">' + icon + ' ' + c.name + '</span>';
        html += '<span class="bg-col-tpl">' + (tplAmount !== null ? fmt(tplAmount) : (per ? '📅' : '—')) + '</span>';
        html += '<span class="bg-col-month">' + (monthAmount !== null ? fmt(monthAmount) : '—') + '</span>';
        html += '<span class="bg-col-actions">';

        if (tpl) {
            html += '<button class="btn btn-secondary btn-sm" data-action="edit-budget" data-id="' + tpl.id + '" title="Редактировать шаблон">✏️</button>';
        } else {
            html += '<button class="btn btn-secondary btn-sm" data-action="add-template" data-id="' + c.id + '" title="Добавить шаблон">📋</button>';
        }
        var budgetForEdit = ovr || per || tpl;
        if (budgetForEdit) {
            html += '<button class="btn btn-secondary btn-sm" data-action="delete-budget" data-id="' + budgetForEdit.id + '" title="Удалить">❌</button>';
        }
        if (!per && tpl) {
            html += '<button class="btn btn-secondary btn-sm" data-action="add-override" data-cat="' + c.id + '" data-amount="' + tpl.target_amount + '" title="Переопределить на этот месяц">📝</button>';
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
    document.getElementById('bg-month').value = currentMonth;
    document.getElementById('bg-year').value = currentYear;
    clearAllRadios();
    document.querySelector('input[name="bg-type"][value="template"]').checked = true;
    document.getElementById('bg-month-fields').style.display = 'none';
    document.getElementById('bg-period-fields').style.display = 'none';
    document.getElementById('add-form-title').textContent = 'Новый бюджет';
    document.getElementById('bg-submit').textContent = 'Сохранить';
    document.getElementById('add-form').style.display = 'block';
}

function clearAllRadios() {
    var radios = document.getElementsByName('bg-type');
    for (var i = 0; i < radios.length; i++) radios[i].checked = false;
}

function hideAddForm() {
    document.getElementById('add-form').style.display = 'none';
}

function editBudget(id) {
    var b = allBudgets.find(function(x) { return x.id === id; });
    if (!b) return;
    document.getElementById('bg-edit-id').value = id;
    document.getElementById('bg-category').value = b.category_id;
    document.getElementById('bg-amount').value = b.target_amount;
    clearAllRadios();

    if (b.is_template) {
        document.querySelector('input[name="bg-type"][value="template"]').checked = true;
        document.getElementById('bg-month-fields').style.display = 'none';
        document.getElementById('bg-period-fields').style.display = 'none';
    } else if (b.period_end_month) {
        document.querySelector('input[name="bg-type"][value="period"]').checked = true;
        document.getElementById('bg-month-fields').style.display = 'none';
        document.getElementById('bg-period-fields').style.display = '';
        document.getElementById('bg-period-from-month').value = b.month;
        document.getElementById('bg-period-from-year').value = b.year;
        document.getElementById('bg-period-to-month').value = b.period_end_month;
        document.getElementById('bg-period-to-year').value = b.period_end_year;
    } else {
        document.querySelector('input[name="bg-type"][value="month"]').checked = true;
        document.getElementById('bg-month-fields').style.display = '';
        document.getElementById('bg-period-fields').style.display = 'none';
        document.getElementById('bg-month').value = b.month || currentMonth;
        document.getElementById('bg-year').value = b.year || currentYear;
    }

    document.getElementById('add-form-title').textContent = 'Редактировать бюджет';
    document.getElementById('bg-submit').textContent = '✏️';
    document.getElementById('add-form').style.display = 'block';
}

function addTemplate(catId) {
    document.getElementById('bg-edit-id').value = '';
    document.getElementById('bg-category').value = catId;
    document.getElementById('bg-amount').value = '';
    clearAllRadios();
    document.querySelector('input[name="bg-type"][value="template"]').checked = true;
    document.getElementById('bg-month-fields').style.display = 'none';
    document.getElementById('bg-period-fields').style.display = 'none';
    document.getElementById('add-form-title').textContent = 'Новый шаблон';
    document.getElementById('bg-submit').textContent = 'Сохранить';
    document.getElementById('add-form').style.display = 'block';
}

function addOverride(catId, suggestedAmount) {
    document.getElementById('bg-edit-id').value = '';
    document.getElementById('bg-category').value = catId;
    document.getElementById('bg-amount').value = suggestedAmount || '';
    clearAllRadios();
    document.querySelector('input[name="bg-type"][value="month"]').checked = true;
    document.getElementById('bg-month').value = currentMonth;
    document.getElementById('bg-year').value = currentYear;
    document.getElementById('bg-month-fields').style.display = '';
    document.getElementById('bg-period-fields').style.display = 'none';
    document.getElementById('add-form-title').textContent = 'Бюджет на ' + MONTHS_SHORT[currentMonth-1] + ' ' + currentYear;
    document.getElementById('bg-submit').textContent = 'Сохранить';
    document.getElementById('add-form').style.display = 'block';
}

async function saveBudget(e) {
    e.preventDefault();
    var editId = document.getElementById('bg-edit-id').value;
    var catId = parseInt(document.getElementById('bg-category').value);
    var amount = parseFloat(document.getElementById('bg-amount').value);
    var type = getBudgetType();
    var body = { category_id: catId, target_amount: amount };

    if (type === 'month') {
        body.month = parseInt(document.getElementById('bg-month').value);
        body.year = parseInt(document.getElementById('bg-year').value);
    } else if (type === 'period') {
        body.month = parseInt(document.getElementById('bg-period-from-month').value);
        body.year = parseInt(document.getElementById('bg-period-from-year').value);
        body.period_end_month = parseInt(document.getElementById('bg-period-to-month').value);
        body.period_end_year = parseInt(document.getElementById('bg-period-to-year').value);
    }

    var url = editId ? '/api/v1/budgets/' + editId : '/api/v1/budgets';
    var method = editId ? 'PUT' : 'POST';

    if (editId) {
        body.category_id = catId;
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
    if (!confirm('Копировать переопределения из ' + MONTHS_SHORT[prevMonth-1] + ' ' + prevYear + ' в ' + MONTHS_SHORT[currentMonth-1] + ' ' + currentYear + '?')) return;
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

document.addEventListener('DOMContentLoaded', function() {
    init();

    document.getElementById('bg-form').addEventListener('submit', saveBudget);
    document.getElementById('bg-add-btn').addEventListener('click', showAddForm);
    document.getElementById('bg-cancel-btn').addEventListener('click', hideAddForm);
    document.getElementById('bg-prev-btn').addEventListener('click', function() { changeMonth(-1); });
    document.getElementById('bg-next-btn').addEventListener('click', function() { changeMonth(1); });
    document.getElementById('copy-btn').addEventListener('click', copyFromPrev);

    document.querySelector('.radio-group').addEventListener('change', function(e) {
        if (e.target.name === 'bg-type') onBudgetTypeChange();
    });

    document.getElementById('budgets-list').addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action]');
        if (!btn) return;
        var action = btn.getAttribute('data-action');
        var id = parseInt(btn.getAttribute('data-id'));
        if (action === 'edit-budget') editBudget(id);
        else if (action === 'delete-budget') deleteBudget(id);
        else if (action === 'add-template') addTemplate(id);
        else if (action === 'add-override') addOverride(parseInt(btn.getAttribute('data-cat')), parseFloat(btn.getAttribute('data-amount')));
    });
});
