async function loadDashboard() {
    try {
        var r = await fetch('/api/v1/transactions', { headers: authHeaders() });
        var d = await r.json();
        if (d.status === 'success') {
            document.getElementById('total-income').textContent = '+' + fmt(d.data.total_income) + ' RUB';
            document.getElementById('total-spent').textContent = '-' + fmt(d.data.total_spent) + ' RUB';
            document.getElementById('total-budgeted').textContent = fmt(d.data.total_budgeted) + ' RUB';
            document.getElementById('transactions-count').textContent = d.data.transactions_count;
            document.getElementById('total-savings').textContent = fmt(d.data.total_savings) + ' RUB';
            var tbody = document.getElementById('transactions-list');
            tbody.innerHTML = (d.data.recent_transactions || []).map(function(t) {
                var icon = t.type === 'income' ? '💰' : '💳';
                var cls = t.type === 'income' ? 'income' : 'expense';
                return '<tr><td>' + icon + ' ' + (t.category_icon || '📁') + ' ' + t.category_name +
                    '</td><td>' + (t.description || '—') +
                    '</td><td class="' + cls + '">' + (t.type === 'income' ? '+' : '-') + fmt(t.amount) + ' RUB</td></tr>';
            }).join('');
        }
    } catch(e) { console.error(e); }
}

document.addEventListener('DOMContentLoaded', loadDashboard);
