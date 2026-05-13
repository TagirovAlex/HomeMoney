from typing import Optional


def _build_connector(proxy_params: Optional[dict] = None):
    """Создаёт aiohttp ProxyConnector из отдельных параметров прокси."""
    if not proxy_params:
        return None
    from aiohttp_socks import ProxyConnector, ProxyType
    return ProxyConnector(
        host=proxy_params["host"],
        port=proxy_params["port"],
        username=proxy_params.get("username"),
        password=proxy_params.get("password"),
        proxy_type=ProxyType.SOCKS5,
    )


def create_aiogram_session(proxy_params: Optional[dict] = None):
    """Создаёт AiohttpSession для aiogram с поддержкой SOCKS5 прокси.

    Args:
        proxy_params: dict с ключами host, port, username, password
                     (из Config.get_proxy_params()). Если None — без прокси.
    """
    from aiogram.client.session.aiohttp import AiohttpSession

    connector = _build_connector(proxy_params)
    if connector:
        return AiohttpSession(connector=connector)
    return AiohttpSession()


def create_aiogram_bot(
    token: str,
    proxy_params: Optional[dict] = None,
    parse_mode: str = "HTML",
) -> "Bot":
    """Создаёт Bot для aiogram с поддержкой SOCKS5 прокси.

    Args:
        token: Токен Telegram-бота.
        proxy_params: dict из Config.get_proxy_params() или None для прямого соединения.
        parse_mode: Режим форматирования сообщений (по умолчанию HTML).
    """
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties

    session = create_aiogram_session(proxy_params)
    return Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=parse_mode),
    )


def create_aiohttp_session(proxy_params: Optional[dict] = None):
    """Создаёт aiohttp.ClientSession с SOCKS5 прокси через ProxyConnector.

    Args:
        proxy_params: dict из Config.get_proxy_params() или None для прямого соединения.
    """
    import aiohttp

    connector = _build_connector(proxy_params)
    if connector:
        return aiohttp.ClientSession(connector=connector)
    return aiohttp.ClientSession()
