from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from config import Config


async def main():
    token = Config.BOT_TOKEN
    if not token:
        print("ОШИБКА: HM_BOT_TOKEN не задан. Укажите токен в .env или переменной окружения.")
        return

    proxy_url = Config.BOT_PROXY_URL
    if proxy_url:
        from aiohttp_socks import ProxyConnector
        connector = ProxyConnector.from_url(proxy_url)
        session = AiohttpSession(connector=connector)
        bot = Bot(token=token, session=session)
        print(f"Бот запущен через прокси: {proxy_url}")
    else:
        bot = Bot(token=token)
        print("Бот запущен напрямую (без прокси)")

    dp = Dispatcher()

    from handlers.command_handlers import router
    dp.include_router(router)

    print("Telegram Bot запущен. Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
