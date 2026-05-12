import asyncio
import subprocess
import os
import signal
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT_SCRIPT = os.path.join(PROJECT_DIR, "telegram_bot.py")
PID_FILE = os.path.join(PROJECT_DIR, ".bot.pid")


def _read_pid():
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except (ValueError, OSError):
        return None


def _write_pid(pid: int):
    with open(PID_FILE, "w") as f:
        f.write(str(pid))


def _remove_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_bot() -> str:
    pid = _read_pid()
    if pid and _process_exists(pid):
        return "Бот уже запущен (PID: {})".format(pid)

    if not os.path.exists(BOT_SCRIPT):
        return "Ошибка: telegram_bot.py не найден"

    log_file = open(os.path.join(PROJECT_DIR, ".bot.log"), "a")
    proc = subprocess.Popen(
        ["python", BOT_SCRIPT],
        cwd=PROJECT_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    _write_pid(proc.pid)
    time.sleep(1)

    if _process_exists(proc.pid):
        return "Бот запущен (PID: {})".format(proc.pid)
    else:
        _remove_pid()
        return "Ошибка: бот не запустился. Проверьте HM_BOT_TOKEN в .env"


def stop_bot() -> str:
    pid = _read_pid()
    if not pid:
        return "Бот не запущен"

    if not _process_exists(pid):
        _remove_pid()
        return "Бот не запущен (PID файл устарел)"

    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.3)
            if not _process_exists(pid):
                _remove_pid()
                return "Бот остановлен"
        os.kill(pid, signal.SIGKILL)
        _remove_pid()
        return "Бот принудительно остановлен (SIGKILL)"
    except OSError as e:
        _remove_pid()
        return "Ошибка при остановке: {}".format(e)


def _make_session():
    from config import Config
    import aiohttp
    proxy_url = Config.get_proxy_url()
    if proxy_url:
        from aiohttp_socks import ProxyConnector
        connector = ProxyConnector.from_url(proxy_url)
        return aiohttp.ClientSession(connector=connector)
    return aiohttp.ClientSession()


async def _fetch(url: str, timeout: int = 15):
    import aiohttp
    async with _make_session() as sess:
        async with sess.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            return resp.status, await resp.read()


def check_proxy() -> dict:
    from config import Config
    proxy_url = Config.get_proxy_url()
    if not proxy_url:
        return {"ok": False, "error": "Хост прокси не указан"}
    try:
        status, _ = asyncio.run(_fetch("https://api.telegram.org", 15))
        return {"ok": True, "proxy": proxy_url, "status": status}
    except Exception as e:
        msg = str(e).encode("utf-8", errors="replace").decode("utf-8")
        return {"ok": False, "error": msg}


def _check_telegram_api() -> dict:
    from config import Config
    token = Config.BOT_TOKEN
    if not token:
        return {"reachable": False, "error": "HM_BOT_TOKEN не задан"}
    try:
        import json
        url = f"https://api.telegram.org/bot{token}/getMe"
        status, body = asyncio.run(_fetch(url, 10))
        data = json.loads(body.decode())
        if data.get("ok"):
            bot_user = data["result"]
            return {"reachable": True, "username": bot_user.get("username", ""),
                    "first_name": bot_user.get("first_name", "")}
        return {"reachable": False, "error": data.get("description", "API error")}
    except Exception as e:
        msg = str(e).encode("utf-8", errors="replace").decode("utf-8")
        return {"reachable": False, "error": msg}

def status_bot() -> dict:
    pid = _read_pid()
    running = bool(pid and _process_exists(pid))
    if pid and not running:
        _remove_pid()
    health = _check_telegram_api()
    return {"running": running, "pid": pid if running else None,
            "script": BOT_SCRIPT, "health": health}
