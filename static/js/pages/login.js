var isLogin = true;

function toggleAuthMode() {
    isLogin = !isLogin;
    document.getElementById('auth-title').textContent = isLogin ? 'Вход' : 'Регистрация';
    document.getElementById('auth-submit').textContent = isLogin ? 'Войти' : 'Зарегистрироваться';
    document.getElementById('auth-switch-text').textContent = isLogin ? 'Нет аккаунта?' : 'Уже есть аккаунт?';
    document.getElementById('auth-switch-link').textContent = isLogin ? 'Зарегистрироваться' : 'Войти';
    document.getElementById('auth-error').style.display = 'none';
}

async function handleAuth(e) {
    e.preventDefault();
    var email = document.getElementById('auth-email').value;
    var password = document.getElementById('auth-password').value;
    var endpoint = isLogin ? '/api/v1/login' : '/api/v1/register';
    var errEl = document.getElementById('auth-error');

    try {
        var r = await fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: email, password: password})
        });
        var d = await r.json();
        if (d.status === 'success') {
            window.location.href = '/';
        } else {
            errEl.textContent = d.message;
            errEl.style.display = 'block';
        }
    } catch(e) {
        errEl.textContent = 'Ошибка соединения';
        errEl.style.display = 'block';
    }
    return false;
}
