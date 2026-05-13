from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import hbold, hcode
from aiogram.filters import Command

from data_access.repositories.user_repository import SQLAlchemyUserRepository
from data_access.repositories.transaction_repository import SQLAlchemyTransactionRepository
from data_access.repositories.budget_repository import SQLAlchemyBudgetRepository
from data_access.repositories.income_repository import SQLAlchemyIncomeSourceRepository
from services.financial_service import FinancialService
from services.auth_service import AuthService
from models.database import Category, User
from utils.database_session import get_db

router = Router()

user_sessions: dict[int, dict] = {}

def get_session(tg_id: int) -> dict:
    if tg_id not in user_sessions:
        user_sessions[tg_id] = {"step": None, "data": {}}
    return user_sessions[tg_id]

def try_auto_login(tg_id: int, sess: dict) -> bool:
    if "user_id" in sess:
        return True
    with get_db() as s:
        user = s.query(User).filter(User.telegram_id == str(tg_id)).first()
        if user and user.status == "active":
            sess["user_id"] = user.id
            sess["email"] = user.email
            sess["role"] = user.role
            return True
    return False

def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить транзакцию", callback_data="addtx")],
        [InlineKeyboardButton(text="📋 Последние транзакции", callback_data="tx")],
        [InlineKeyboardButton(text="📊 Отчёт за месяц", callback_data="report")],
        [InlineKeyboardButton(text="💰 Бюджеты", callback_data="budgets")],
        [InlineKeyboardButton(text="📥 Доходы", callback_data="incomes")],
    ])

def auth_required(func):
    async def wrapper(message: Message, *args, **kwargs):
        tg_id = message.from_user.id
        sess = get_session(tg_id)
        if not try_auto_login(tg_id, sess):
            await message.answer(
                "❌ Требуется авторизация.\nИспользуйте /login email пароль"
            )
            return
        return await func(message, *args, **kwargs)
    return wrapper

def auth_required_cb(func):
    async def wrapper(callback: CallbackQuery, *args, **kwargs):
        tg_id = callback.from_user.id
        sess = get_session(tg_id)
        if not try_auto_login(tg_id, sess):
            await callback.message.answer(
                "❌ Требуется авторизация.\nИспользуйте /login email пароль"
            )
            await callback.answer()
            return
        return await func(callback, *args, **kwargs)
    return wrapper

# ─── /start ──────────────────────────────────────────────────────────

@router.message(Command("start"))
async def handle_start(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    if try_auto_login(tg_id, sess):
        user_info = f"Вы вошли как {hbold(sess['email'])}"
    else:
        user_info = "Используйте /login email пароль для входа"
    await message.answer(
        f"{hbold('🏠 HomeMoney Bot')}\n\n"
        f"{user_info}\n\n"
        "Выберите действие:",
        reply_markup=menu_kb()
    )

# ─── /login ──────────────────────────────────────────────────────────

@router.message(Command("login"))
async def handle_login(message: Message):
    tg_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /login email пароль")
        return
    _, email, password = parts
    repo = SQLAlchemyUserRepository()
    user = repo.get_by_email(email)
    if not user or not AuthService.verify_password(password, user.hashed_password):
        await message.answer("❌ Неверный email или пароль")
        return
    if user.status != "active":
        await message.answer("❌ Аккаунт не активирован. Дождитесь подтверждения администратором.")
        return
    sess = get_session(tg_id)
    sess["user_id"] = user.id
    sess["email"] = user.email
    sess["role"] = user.role
    if user.telegram_id != str(tg_id):
        with get_db() as s:
            u = s.query(type(user)).filter(type(user).id == user.id).first()
            if u:
                u.telegram_id = str(tg_id)
                s.commit()
    await message.answer(
        f"✅ Вы вошли как {hbold(user.email)}\n"
        f"Роль: {user.role}",
        reply_markup=menu_kb()
    )

# ─── /logout ─────────────────────────────────────────────────────────

@router.message(Command("logout"))
async def handle_logout(message: Message):
    tg_id = message.from_user.id
    if tg_id in user_sessions:
        del user_sessions[tg_id]
    await message.answer("🔓 Вы вышли из системы.")

# ─── /help ───────────────────────────────────────────────────────────

@router.message(Command("help"))
async def handle_help(message: Message):
    await message.answer(
        f"{hbold('📖 Доступные команды:')}\n\n"
        "/start — Главное меню\n"
        "/login email пароль — Войти\n"
        "/logout — Выйти\n"
        "/addtx — Добавить транзакцию\n"
        "/tx — Последние транзакции\n"
        "/report месяц год — Отчёт (пример: /report 5 2026)\n"
        "/budgets — Мои бюджеты\n"
        "/incomes — Мои доходы\n"
        "/help — Эта справка"
    )

# ─── /addtx ──────────────────────────────────────────────────────────

async def _cmd_addtx(tg_id: int, message: Message):
    sess = get_session(tg_id)
    sess["step"] = "select_category"
    sess["data"] = {}
    with get_db() as s:
        cats = s.query(Category).all()
    if not cats:
        await message.answer("❌ Нет категорий. Создайте их через веб-интерфейс.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c.icon or '📁'} {c.name}", callback_data=f"txcat:{c.id}")]
        for c in cats
    ])
    await message.answer("Выберите категорию:", reply_markup=kb)

@router.message(Command("addtx"))
@auth_required
async def cmd_addtx(message: Message):
    await _cmd_addtx(message.from_user.id, message)

@router.callback_query(lambda c: c.data and c.data.startswith("txcat:"))
async def cb_tx_select_category(callback: CallbackQuery):
    tg_id = callback.from_user.id
    cat_id = int(callback.data.split(":")[1])
    sess = get_session(tg_id)
    sess["data"]["category_id"] = cat_id
    with get_db() as s:
        cat = s.query(Category).filter(Category.id == cat_id).first()
    sess["data"]["category_name"] = cat.name if cat else f"ID:{cat_id}"
    sess["step"] = "select_type"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Расход", callback_data="txtype:expense")],
        [InlineKeyboardButton(text="💰 Доход", callback_data="txtype:income")],
    ])
    await callback.message.edit_text(
        f"Категория: {hbold(sess['data']['category_name'])}\n"
        "Выберите тип:",
        reply_markup=kb,
    )
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("txtype:"))
async def cb_tx_select_type(callback: CallbackQuery):
    tg_id = callback.from_user.id
    tx_type = callback.data.split(":")[1]
    sess = get_session(tg_id)
    sess["data"]["type"] = tx_type
    sess["step"] = "enter_amount"
    await callback.message.edit_text(
        f"Категория: {hbold(sess['data']['category_name'])}\n"
        f"Тип: {'💰 Доход' if tx_type == 'income' else '💳 Расход'}\n"
        "Введите сумму числом:"
    )
    await callback.answer()

@router.message(lambda msg: user_sessions.get(msg.from_user.id, {}).get("step") == "enter_amount")
async def tx_enter_amount(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("❌ Введите число, например 1500")
        return
    if amount <= 0 or amount > 100000:
        await message.answer("❌ Сумма должна быть от 0.01 до 100000")
        return
    sess["data"]["amount"] = amount
    sess["step"] = "enter_desc"
    await message.answer("Введите описание (или отправьте «-» для пустого):")

@router.message(lambda msg: user_sessions.get(msg.from_user.id, {}).get("step") == "enter_desc")
async def tx_enter_desc(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    desc = message.text.strip()
    if desc == "-":
        desc = ""
    sess["data"]["description"] = desc
    try:
        from datetime import date as dt_date
        tx_repo = SQLAlchemyTransactionRepository()
        fs = FinancialService(tx_repo, SQLAlchemyBudgetRepository())
        tx = fs.add_transaction(
            user_id=sess["user_id"],
            amount=sess["data"]["amount"],
            category_id=sess["data"]["category_id"],
            description=desc,
            date=dt_date.today(),
            tx_type=sess["data"].get("type", "expense"),
        )
        sess["step"] = None
        type_label = "💰 Доход" if sess["data"].get("type") == "income" else "💳 Расход"
        await message.answer(
            f"✅ Транзакция добавлена:\n"
            f"Категория: {hbold(sess['data']['category_name'])}\n"
            f"Сумма: {hbold(f"{sess['data']['amount']:.2f}")} RUB\n"
            f"Тип: {type_label}\n"
            f"Описание: {desc or '—'}",
            reply_markup=menu_kb()
        )
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {e}")
        sess["step"] = None
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        sess["step"] = None

# ─── Внутренние реализации (принимают tg_id явно) ───────────────────

async def _cmd_tx(tg_id: int, message: Message):
    sess = get_session(tg_id)
    try:
        tx_repo = SQLAlchemyTransactionRepository()
        fs = FinancialService(tx_repo, SQLAlchemyBudgetRepository())
        txs = fs.get_user_transactions(sess["user_id"])
        if not txs:
            await message.answer("Нет транзакций.", reply_markup=menu_kb())
            return
        lines = [f"{hbold('📋 Последние транзакции')}"] + [
            f"{'💰' if t.get('type') == 'income' else '💳'} {t['category_icon'] or '📁'} {t['category_name']} | "
            f"{t['amount']:.2f} RUB | {(t['date'][:10] if t['date'] else '')} | {t['description'] or '—'}"
            for t in txs[:10]
        ]
        chunks = ["\n".join(lines[i:i+5]) for i in range(0, len(lines), 5)]
        for chunk in chunks:
            await message.answer(chunk)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

async def _cmd_report(tg_id: int, message: Message):
    sess = get_session(tg_id)
    from datetime import date
    today = date.today()
    parts = message.text.strip().split()
    if len(parts) >= 3 and parts[0].startswith("/"):
        month = int(parts[1])
        year = int(parts[2])
    else:
        month = today.month
        year = today.year
    try:
        tx_repo = SQLAlchemyTransactionRepository()
        bg_repo = SQLAlchemyBudgetRepository()
        fs = FinancialService(tx_repo, bg_repo)
        report = fs.get_detailed_report(sess["user_id"], role=sess.get("role", "User"), month=month, year=year)
        summary = report.get("summary", {})
        total = summary.get("total_spent", 0)
        budgeted = summary.get("total_budgeted", 0)
        income = summary.get("total_income", 0)
        opening = summary.get("opening_balance", 0)
        closing = summary.get("closing_balance", 0)
        lines = [
            f"{hbold(f'📊 Отчёт за {month}/{year}')}",
            f"💰 Доходы: +{income:.2f} RUB",
            f"💳 Расходы: -{total:.2f} RUB",
            f"📊 Бюджет: {budgeted:.2f} RUB",
            f"Остаток на начало: {opening:.2f} RUB",
            f"Остаток на конец: {closing:.2f} RUB",
            ""
        ]
        detailed = report.get("detailed_spending", {})
        if detailed:
            for cat_id, item in detailed.items():
                icon = item.get("icon", "📁") or "📁"
                spent = item.get("spent", 0)
                budget = item.get("budget", 0)
                diff = budget - spent
                sign = "+" if diff >= 0 else ""
                lines.append(
                    f"{icon} {item['name']}: {spent:.2f} / {budget:.2f} ({sign}{diff:.2f})"
                )
        await message.answer("\n".join(lines), reply_markup=menu_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

async def _cmd_budgets(tg_id: int, message: Message):
    sess = get_session(tg_id)
    try:
        bg_repo = SQLAlchemyBudgetRepository()
        budgets = bg_repo.get_all_for_user(sess["user_id"])
        if not budgets:
            await message.answer("Нет бюджетов. Создайте через веб-интерфейс.", reply_markup=menu_kb())
            return
        with get_db() as s:
            cats = {c.id: {"name": c.name, "icon": c.icon or ""} for c in s.query(Category).all()}
        lines = [hbold("💰 Мои бюджеты")]
        for b in budgets:
            info = cats.get(b.category_id, {"name": f"ID:{b.category_id}", "icon": "📁"})
            lines.append(f"{info['icon']} {info['name']}: {b.target_amount:.2f} RUB")
        await message.answer("\n".join(lines), reply_markup=menu_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

async def _cmd_incomes(tg_id: int, message: Message):
    sess = get_session(tg_id)
    try:
        inc_repo = SQLAlchemyIncomeSourceRepository()
        srcs = inc_repo.get_by_user(sess["user_id"])
        if not srcs:
            await message.answer("Нет доходов. Создайте через веб-интерфейс.", reply_markup=menu_kb())
            return
        with get_db() as s:
            cats = {c.id: {"name": c.name, "icon": c.icon or ""} for c in s.query(Category).all()}
        lines = [hbold("📥 Мои доходы")]
        for s in srcs:
            info = cats.get(s.category_id, {"name": f"ID:{s.category_id}", "icon": "📁"})
            next_d = s.next_date.strftime("%d.%m.%Y") if s.next_date else "—"
            lines.append(
                f"{info['icon']} {s.name} | {s.amount:.2f} RUB | "
                f"Кажд. {s.period} | След.: {next_d}"
            )
        await message.answer("\n".join(lines), reply_markup=menu_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# ─── /tx ─────────────────────────────────────────────────────────────

@router.message(Command("tx"))
@auth_required
async def cmd_tx(message: Message):
    await _cmd_tx(message.from_user.id, message)

# ─── /report ─────────────────────────────────────────────────────────

@router.message(Command("report"))
@auth_required
async def cmd_report(message: Message):
    await _cmd_report(message.from_user.id, message)

# ─── /budgets ────────────────────────────────────────────────────────

@router.message(Command("budgets"))
@auth_required
async def cmd_budgets(message: Message):
    await _cmd_budgets(message.from_user.id, message)

# ─── /incomes ────────────────────────────────────────────────────────

@router.message(Command("incomes"))
@auth_required
async def cmd_incomes(message: Message):
    await _cmd_incomes(message.from_user.id, message)

# ─── Инлайн-кнопки ──────────────────────────────────────────────────

async def _ensure_auth(callback: CallbackQuery) -> int | None:
    tg_id = callback.from_user.id
    sess = get_session(tg_id)
    if not try_auto_login(tg_id, sess):
        await callback.message.answer(
            "❌ Требуется авторизация.\nИспользуйте /login email пароль"
        )
        await callback.answer()
        return None
    return tg_id

@router.callback_query(lambda c: c.data == "addtx")
async def cb_addtx(callback: CallbackQuery):
    tg_id = await _ensure_auth(callback)
    if tg_id is not None:
        await _cmd_addtx(tg_id, callback.message)
        await callback.answer()

@router.callback_query(lambda c: c.data == "tx")
async def cb_tx(callback: CallbackQuery):
    tg_id = await _ensure_auth(callback)
    if tg_id is not None:
        await _cmd_tx(tg_id, callback.message)
        await callback.answer()

@router.callback_query(lambda c: c.data == "report")
async def cb_report(callback: CallbackQuery):
    tg_id = await _ensure_auth(callback)
    if tg_id is not None:
        await _cmd_report(tg_id, callback.message)
        await callback.answer()

@router.callback_query(lambda c: c.data == "budgets")
async def cb_budgets(callback: CallbackQuery):
    tg_id = await _ensure_auth(callback)
    if tg_id is not None:
        await _cmd_budgets(tg_id, callback.message)
        await callback.answer()

@router.callback_query(lambda c: c.data == "incomes")
async def cb_incomes(callback: CallbackQuery):
    tg_id = await _ensure_auth(callback)
    if tg_id is not None:
        await _cmd_incomes(tg_id, callback.message)
        await callback.answer()
