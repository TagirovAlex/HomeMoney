"""
SOCKS5 Proxy Session Helper
============================
Утилита для создания HTTP-сессий с поддержкой SOCKS5 прокси.
Используется для Telegram-бота (aiogram) и HTTP-запросов (aiohttp).

Поддерживает:
- aiogram AiohttpSession с SOCKS5 прокси
- aiohttp ClientSession с SOCKS5 прокси (ProxyConnector)
- Автоматический fallback на прямое соединение, если прокси не указан

Зависимости (requirements.txt):
    aiogram>=3.0
    aiohttp-socks>=0.8

Пример использования:
    from utils.proxy_session import create_aiogram_bot, create_aiohttp_session

    # Aiogram бот через прокси
    bot = create_aiogram_bot(token, proxy_url="socks5://user:pass@host:1080")
    await bot.send_message(chat_id, "Hello")

    # Aiogram без прокси
    bot = create_aiogram_bot(token)

    # Aiohttp сессия через прокси (один запрос)
    async with create_aiohttp_session(proxy_url) as session:
        async with session.get("https://api.telegram.org") as resp:
            print(resp.status)

    # Aiohttp сессия напрямую
    async with create_aiohttp_session() as session:
        ...
"""

from typing import Optional


def create_aiogram_session(proxy_url: Optional[str] = None):
    """Создаёт AiohttpSession для aiogram с поддержкой SOCKS5 прокси.

    Args:
        proxy_url: URL прокси вида socks5://[user:pass@]host:port
                  Если None или пустая строка — сессия без прокси.

    Returns:
        AiohttpSession — передаётся в Bot(session=...)
    """
    from aiogram.client.session.aiohttp import AiohttpSession

    if proxy_url:
        return AiohttpSession(proxy=proxy_url)
    return AiohttpSession()


def create_aiogram_bot(
    token: str,
    proxy_url: Optional[str] = None,
    parse_mode: str = "HTML",
) -> "Bot":
    """Создаёт Bot для aiogram с поддержкой SOCKS5 прокси.

    Args:
        token: Токен Telegram-бота (полученный у BotFather).
        proxy_url: URL прокси вида socks5://[user:pass@]host:port
                  Если None или пустая строка — прямое соединение.
        parse_mode: Режим форматирования сообщений (по умолчанию HTML).

    Returns:
        Bot из aiogram, готовый к использованию.

    Пример:
        bot = create_aiogram_bot("123:abc", "socks5://user:pass@127.0.0.1:1080")
        await bot.send_message(chat_id, "<b>Hello</b>")
    """
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties

    session = create_aiogram_session(proxy_url)
    return Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=parse_mode),
    )


def create_aiohttp_session(proxy_url: Optional[str] = None):
    """Создаёт aiohttp.ClientSession с SOCKS5 прокси через ProxyConnector.

    Args:
        proxy_url: URL прокси вида socks5://[user:pass@]host:port
                  Если None или пустая строка — сессия без прокси.

    Returns:
        aiohttp.ClientSession — использовать с 'async with'.

    Пример:
        async with create_aiohttp_session(proxy_url) as session:
            async with session.get("https://example.com") as resp:
                ...
    """
    import aiohttp

    if not proxy_url:
        return aiohttp.ClientSession()

    from aiohttp_socks import ProxyConnector

    connector = ProxyConnector.from_url(proxy_url)
    return aiohttp.ClientSession(connector=connector)
