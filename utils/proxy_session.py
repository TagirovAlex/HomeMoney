from typing import Optional


def _build_proxy_url(proxy_params: Optional[dict] = None) -> str:
    """Собирает socks5:// URL из dict параметров (для aiogram AiohttpSession)."""
    if not proxy_params:
        return ""
    host = proxy_params["host"]
    port = proxy_params["port"]
    username = proxy_params.get("username")
    password = proxy_params.get("password")
    auth = f"{username}:{password}@" if username and password else ""
    return f"socks5://{auth}{host}:{port}"


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
    """Создаёт AiohttpSession для aiogram.

    aiogram 3.26 принимает только proxy URL (строку), не connector.
    """
    from aiogram.client.session.aiohttp import AiohttpSession

    proxy_url = _build_proxy_url(proxy_params)
    if proxy_url:
        return AiohttpSession(proxy=proxy_url)
    return AiohttpSession()


def create_aiogram_bot(
    token: str,
    proxy_params: Optional[dict] = None,
    parse_mode: str = "HTML",
) -> "Bot":
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties

    session = create_aiogram_session(proxy_params)
    return Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=parse_mode),
    )


def create_aiohttp_session(proxy_params: Optional[dict] = None):
    """Создаёт aiohttp.ClientSession с SOCKS5 прокси через ProxyConnector."""
    import aiohttp

    connector = _build_connector(proxy_params)
    if connector:
        return aiohttp.ClientSession(connector=connector)
    return aiohttp.ClientSession()
