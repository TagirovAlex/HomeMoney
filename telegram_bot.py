from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from config import Config
from utils.proxy_session import create_aiogram_bot


def _parse_allowed_users(raw: str) -> set[int]:
    if not raw or not raw.strip():
        return set()
    result = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result


def _check_whitelist(event_from_user, allowed: set[int]) -> bool:
    if not allowed:
        return True
    return bool(event_from_user and event_from_user.id in allowed)


async def main():
    token = Config.BOT_TOKEN
    if not token:
        print("ОШИБКА: HM_BOT_TOKEN не задан.")
        return

    proxy_params = Config.get_proxy_params()
    bot = create_aiogram_bot(token, proxy_params)
    if proxy_params:
        safe_host = proxy_params["host"]
        safe_port = proxy_params["port"]
        print(f"Бот через прокси: socks5://***:***@{safe_host}:{safe_port}")
    else:
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
            if not _check_whitelist(event.from_user, allowed):
                await event.answer("Доступ запрещён. Ваш Telegram ID не авторизован.")
                return
            return await handler(event, data)

        @dp.callback_query.middleware()
        async def whitelist_cb_mw(handler, event: CallbackQuery, data: dict):
            if not _check_whitelist(event.from_user, allowed):
                await event.answer("Доступ запрещён.", show_alert=True)
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
