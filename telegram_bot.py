from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import Message
from config import Config


def _parse_allowed_users(raw: str) -> set[int]:
    if not raw or not raw.strip():
        return set()
    result = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result


async def main():
    token = Config.BOT_TOKEN
    if not token:
        print("ОШИБКА: HM_BOT_TOKEN не задан.")
        return

    proxy_url = Config.get_proxy_url()
    if proxy_url:
        session = AiohttpSession(proxy=proxy_url)
        bot = Bot(token=token, session=session)
        print(f"Бот через прокси: {proxy_url}")
    else:
        bot = Bot(token=token)
        print("Бот напрямую (без прокси)")

    allowed = _parse_allowed_users(Config.BOT_ALLOWED_USERS)
    if allowed:
        print(f"Принимаются сообщения только от ID: {allowed}")
    else:
        print("Принимаются сообщения от всех пользователей")

    dp = Dispatcher()

    if allowed:

        @dp.message.middleware()
        async def whitelist_mw(handler, event: Message, data: dict):
            if event.from_user and event.from_user.id not in allowed:
                await event.answer("Доступ запрещён. Ваш Telegram ID не авторизован.")
                return
            return await handler(event, data)

    from handlers.command_handlers import router
    dp.include_router(router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("Webhook удалён (если был).")
    except Exception as e:
        print(f"Предупреждение: не удалось удалить webhook — {e}")

    print("Telegram Bot запущен. Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
