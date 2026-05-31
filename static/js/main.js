(function() {
    var btn = document.getElementById('theme-toggle');
    var html = document.documentElement;
    function initTheme() {
        var t = localStorage.getItem('theme');
        if (t) { html.setAttribute('data-theme', t); if (btn) btn.textContent = t === 'dark' ? '☀️' : '🌙'; }
        else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            localStorage.setItem('theme', 'dark'); html.setAttribute('data-theme', 'dark'); if (btn) btn.textContent = '☀️';
        }
    }
    if (btn) {
        btn.addEventListener('click', function() {
            var cur = html.getAttribute('data-theme') || 'light';
            var next = cur === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            btn.textContent = next === 'dark' ? '☀️' : '🌙';
        });
    }
    initTheme();

    window.fmt = function(n) { return (n || 0).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };

    window.getCookie = function(name) {
        var m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return m ? decodeURIComponent(m[2]) : '';
    };

    window.authHeaders = function() {
        var h = { 'Content-Type': 'application/json' };
        var csrf = getCookie('csrf_token');
        if (csrf) { h['X-CSRF-Token'] = csrf; }
        return h;
    };

    var userEmail = document.getElementById('user-email');
    var logoutBtn = document.getElementById('logout-btn');

    if (userEmail && logoutBtn) {
        fetch('/api/v1/me', { method: 'GET', headers: { 'Content-Type': 'application/json' } })
            .then(function(r) {
                if (!r.ok) { window.location.href = '/login'; return; }
                return r.json();
            })
            .then(function(d) {
                if (!d || d.status !== 'success') { window.location.href = '/login'; return; }
                var u = d.user;
                userEmail.textContent = u.email;
                userEmail.style.display = 'inline';
                logoutBtn.style.display = 'inline-block';
                window.__userId = u.user_id;
                try { localStorage.setItem('user', JSON.stringify(u)); } catch(e) {}
                if (window.__pageInit) window.__pageInit(u.user_id);
            })
            .catch(function() { window.location.href = '/login'; });

        logoutBtn.addEventListener('click', function() {
            fetch('/api/v1/logout', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
                .then(function() { window.location.href = '/login'; })
                .catch(function() { window.location.href = '/login'; });
        });
    }

    checkMobile();
    window.addEventListener('resize', checkMobile);
    function checkMobile() { document.documentElement.classList.toggle('mobile', window.innerWidth < 1024); }

    var navToggle = document.getElementById('nav-toggle');
    var mainNav = document.getElementById('main-nav');
    if (navToggle && mainNav) {
        navToggle.addEventListener('click', function() {
            mainNav.classList.toggle('nav-open');
        });
    }

    var links = document.querySelectorAll('.nav-link');
    var path = window.location.pathname;
    links.forEach(function(l) { if (l.getAttribute('href') === path) l.classList.add('active'); });
})();
