import html as _html

from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import hbold
from aiogram.filters import Command

from data_access.repositories.user_repository import SQLAlchemyUserRepository
from data_access.repositories.transaction_repository import SQLAlchemyTransactionRepository
from data_access.repositories.budget_repository import SQLAlchemyBudgetRepository
from data_access.repositories.income_repository import SQLAlchemyIncomeSourceRepository
from services.financial_service import FinancialService
from services.auth_service import AuthService
from models.database import Category, User, Transaction
from utils.database_session import get_db
from utils.rate_limiter import login_limiter
from datetime import date as dt_date

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

def not_command(msg: Message) -> bool:
    return msg.text is None or not msg.text.startswith("/")

def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить транзакцию", callback_data="addtx")],
        [InlineKeyboardButton(text="📋 Транзакции", callback_data="tx")],
        [InlineKeyboardButton(text="📊 Отчёт за месяц", callback_data="report")],
        [InlineKeyboardButton(text="💰 Бюджеты", callback_data="budgets")],
        [InlineKeyboardButton(text="📥 Доходы", callback_data="incomes")],
    ])

def confirm_kb(confirm_cb: str, cancel_cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_cb),
            InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_cb),
        ]
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
        return await func(message)
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
        return await func(callback)
    return wrapper

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

async def _do_login(message: Message, tg_id: int, email: str, password: str) -> bool:
    if not login_limiter.is_allowed(f"bot_login:{tg_id}"):
        await message.answer("❌ Слишком много попыток входа. Попробуйте через 60 секунд.")
        return False
    repo = SQLAlchemyUserRepository()
    user = repo.get_by_email(email)
    if not user or not AuthService.verify_password(password, user.hashed_password):
        await message.answer("❌ Неверный email или пароль")
        return False
    if user.status != "active":
        await message.answer("❌ Аккаунт не активирован. Дождитесь подтверждения администратором.")
        return False
    sess = get_session(tg_id)
    sess["user_id"] = user.id
    sess["email"] = user.email
    sess["role"] = user.role
    sess["step"] = None
    login_limiter.reset(f"bot_login:{tg_id}")
    if user.telegram_id != str(tg_id):
        with get_db() as s:
            u = s.query(User).filter(User.id == user.id).first()
            if u:
                u.telegram_id = str(tg_id)
                s.commit()
    await message.answer(
        f"✅ Вы вошли как {hbold(user.email)}\n"
        f"Роль: {user.role}",
        reply_markup=menu_kb()
    )
    return True

@router.message(Command("login"))
async def handle_login(message: Message):
    tg_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) >= 3:
        _, email, password = parts
        await _do_login(message, tg_id, email, password)
        return
    if len(parts) == 2:
        _, email = parts
        sess = get_session(tg_id)
        sess["data"]["login_email"] = email
        sess["step"] = "login_password"
        await message.answer(f"Введите пароль для {hbold(email)}:")
        return
    await message.answer("Использование: /login email пароль\nИли: /login email (пароль будет запрошен отдельно)")

@router.message(lambda msg: not_command(msg) and user_sessions.get(msg.from_user.id, {}).get("step") == "login_password")
async def handle_login_password(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    email = sess["data"].get("login_email", "")
    password = message.text.strip()
    if not password:
        await message.answer("❌ Пароль не может быть пустым.")
        return
    await _do_login(message, tg_id, email, password)

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
        "/tx [месяц год] — Транзакции с фильтром и пагинацией\n"
        "/edittx [id] — Редактировать транзакцию\n"
        "/report [месяц год] — Отчёт\n"
        "/budgets — Мои бюджеты\n"
        "/incomes — Мои доходы\n"
        "/addcat — Создать категорию\n"
        "/delcat — Удалить категорию\n"
        "/process — Обработать регулярные платежи\n"
        "/help — Эта справка"
    )

# ─── /report ─────────────────────────────────────────────────────────

async def _cmd_report(tg_id: int, message: Message):
    sess = get_session(tg_id)
    today = dt_date.today()
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
                    f"{icon} {_html.escape(item['name'])}: {spent:.2f} / {budget:.2f} ({sign}{diff:.2f})"
                )
        await message.answer("\n".join(lines), reply_markup=menu_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {_html.escape(str(e))}")

@router.message(Command("report"))
@auth_required
async def cmd_report(message: Message):
    await _cmd_report(message.from_user.id, message)

# ─── /budgets ────────────────────────────────────────────────────────

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
            lines.append(f"{info['icon']} {_html.escape(info['name'])}: {b.target_amount:.2f} RUB")
        await message.answer("\n".join(lines), reply_markup=menu_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {_html.escape(str(e))}")

@router.message(Command("budgets"))
@auth_required
async def cmd_budgets(message: Message):
    await _cmd_budgets(message.from_user.id, message)

# ─── /incomes ────────────────────────────────────────────────────────

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
        for src in srcs:
            info = cats.get(src.category_id, {"name": f"ID:{src.category_id}", "icon": "📁"})
            next_d = src.next_date.strftime("%d.%m.%Y") if src.next_date else "—"
            active = "✅" if src.is_active else "⛔"
            lines.append(
                f"{active} {info['icon']} {_html.escape(src.name)} | {src.amount:.2f} RUB | "
                f"Кажд. {src.period} | След.: {next_d}"
            )
        await message.answer("\n".join(lines), reply_markup=menu_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {_html.escape(str(e))}")

@router.message(Command("incomes"))
@auth_required
async def cmd_incomes(message: Message):
    await _cmd_incomes(message.from_user.id, message)

# ─── /addtx ──────────────────────────────────────────────────────────

async def _cmd_addtx(tg_id: int, message: Message):
    sess = get_session(tg_id)
    sess["step"] = "select_category"
    sess["data"] = {}
    with get_db() as s:
        cats = s.query(Category).all()
    if not cats:
        await message.answer("❌ Нет категорий. Создайте их через веб-интерфейс или /addcat.")
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
    sess["data"]["type"] = cat.type if cat else "expense"
    sess["step"] = "enter_amount"
    type_label = "💰 Доход" if sess["data"]["type"] == "income" else "💳 Расход"
    await callback.message.edit_text(
        f"Категория: {hbold(_html.escape(sess['data']['category_name']))} ({type_label})\n"
        "Введите сумму числом:"
    )
    await callback.answer()

@router.message(lambda msg: not_command(msg) and user_sessions.get(msg.from_user.id, {}).get("step") == "enter_amount")
async def tx_enter_amount(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("❌ Введите число, например 1500")
        return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть положительным числом")
        return
    sess["data"]["amount"] = amount
    sess["step"] = "enter_desc"
    await message.answer("Введите описание (или отправьте «-» для пустого):")

@router.message(lambda msg: not_command(msg) and user_sessions.get(msg.from_user.id, {}).get("step") == "enter_desc")
async def tx_enter_desc(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    desc = message.text.strip()
    if desc == "-":
        desc = ""
    sess["data"]["description"] = desc
    sess["step"] = "enter_date"
    await message.answer(
        "Введите дату транзакции в формате ДД.ММ.ГГГГ\n"
        "Или отправьте «-» для сегодняшней даты:"
    )

@router.message(lambda msg: not_command(msg) and user_sessions.get(msg.from_user.id, {}).get("step") == "enter_date")
async def tx_enter_date(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    raw = message.text.strip()
    if raw == "-":
        tx_date = dt_date.today()
    else:
        try:
            parts = raw.replace(".", " ").replace("/", " ").replace("-", " ").split()
            if len(parts) != 3:
                raise ValueError
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            tx_date = dt_date(y, m, d)
        except (ValueError, IndexError):
            await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ или отправьте «-»")
            return
    sess["data"]["date"] = tx_date
    try:
        tx_repo = SQLAlchemyTransactionRepository()
        fs = FinancialService(tx_repo, SQLAlchemyBudgetRepository())
        tx = fs.add_transaction(
            user_id=sess["user_id"],
            amount=sess["data"]["amount"],
            category_id=sess["data"]["category_id"],
            description=sess["data"]["description"],
            date=tx_date,
        )
        sess["step"] = None
        type_label = "💰 Доход" if sess["data"].get("type") == "income" else "💳 Расход"
        await message.answer(
            f"✅ Транзакция добавлена:\n"
            f"Категория: {hbold(_html.escape(sess['data']['category_name']))}\n"
            f"Сумма: {hbold('{:.2f}'.format(sess['data']['amount']))} RUB\n"
            f"Тип: {type_label}\n"
            f"Дата: {tx_date.strftime('%d.%m.%Y')}\n"
            f"Описание: {_html.escape(sess['data']['description'] or '—')}",
            reply_markup=menu_kb()
        )
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {_html.escape(str(e))}")
        sess["step"] = None
    except Exception as e:
        await message.answer(f"❌ Ошибка: {_html.escape(str(e))}")
        sess["step"] = None

# ─── /tx (pagination + month filter) ─────────────────────────────────

def _build_tx_keyboard(page: int, month: int, year: int, total_pages: int, txs: list):
    today = dt_date.today()
    all_mode = month == 0
    kb = []

    for t in txs[:5]:
        kb.append([
            InlineKeyboardButton(text=f"✏️ #{t['id']}", callback_data=f"tx_edit:{t['id']}"),
            InlineKeyboardButton(text=f"🗑 #{t['id']}", callback_data=f"tx_delete:{t['id']}"),
        ])

    if all_mode:
        nav_row = [InlineKeyboardButton(
            text=f"📅 К месяцу {today.month}/{today.year}",
            callback_data=f"tx_nav_month:{today.month}:{today.year}")]
        kb.append(nav_row)
    else:
        nav_row = []
        prev_m = month - 1
        prev_y = year
        if prev_m < 1:
            prev_m = 12; prev_y -= 1
        next_m = month + 1
        next_y = year
        if next_m > 12:
            next_m = 1; next_y += 1
        can_go_back = year > 2020 or (year == 2020 and month > 1)
        can_go_forward = year < today.year or (year == today.year and month < today.month)
        if can_go_back:
            nav_row.append(InlineKeyboardButton(
                text=f"◀️ {prev_m}/{prev_y}", callback_data=f"tx_nav_month:{prev_m}:{prev_y}"))
        nav_row.append(InlineKeyboardButton(text=f"📅 {month}/{year}", callback_data="tx_nav_current"))
        if can_go_forward:
            nav_row.append(InlineKeyboardButton(
                text=f"{next_m}/{next_y} ▶️", callback_data=f"tx_nav_month:{next_m}:{next_y}"))
        kb.append(nav_row)
        kb.append([InlineKeyboardButton(text="📋 Все транзакции", callback_data="tx_all")])

    page_row = []
    p_m = month
    p_y = year
    if page > 1:
        page_row.append(InlineKeyboardButton(
            text=f"◀️ {page-1}", callback_data=f"tx_page:{page-1}:{p_m}:{p_y}"))
    page_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="tx_nav_current"))
    if page < total_pages:
        page_row.append(InlineKeyboardButton(
            text=f"{page+1} ▶️", callback_data=f"tx_page:{page+1}:{p_m}:{p_y}"))
    kb.append(page_row)

    kb.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def _render_tx_page(callback: CallbackQuery, month: int, year: int, page: int):
    tg_id = callback.from_user.id
    sess = get_session(tg_id)
    all_mode = month == 0
    sm = None if all_mode else month
    sy = None if all_mode else year
    try:
        tx_repo = SQLAlchemyTransactionRepository()
        fs = FinancialService(tx_repo, SQLAlchemyBudgetRepository())
        result = fs.get_filtered_user_transactions(
            sess["user_id"], month=sm, year=sy, page=page, limit=5
        )
        txs = result.get("data", [])
        total = result.get("total", 0)
        total_pages = max(1, (total + 4) // 5)

        if not txs:
            label = "Все транзакции" if all_mode else f"{month}/{year}"
            await callback.message.edit_text(
                f"Нет транзакций ({label}).",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")]
                ])
            )
            await callback.answer()
            return

        label = "📋 Все транзакции" if all_mode else f"📋 Транзакции за {month}/{year}"
        lines = [f"{hbold(label)} (стр. {page}/{total_pages}, всего: {total})"]
        for t in txs:
            icon = "💰" if t.get("type") == "income" else "💳"
            cat_icon = t.get("category_icon") or "📁"
            lines.append(
                f"#{t['id']} {icon} {cat_icon} {_html.escape(t['category_name'])} | "
                f"{t['amount']:.2f} RUB | {(t['date'][:10] if t['date'] else '')} | {_html.escape(t['description'] or '—')}"
            )

        kb = _build_tx_keyboard(page, month, year, total_pages, txs)
        await callback.message.edit_text("\n".join(lines), reply_markup=kb)
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {_html.escape(str(e))}")
        await callback.answer()

async def _cmd_tx(tg_id: int, message: Message, page: int = 1, month: int = None, year: int = None):
    sess = get_session(tg_id)
    try:
        tx_repo = SQLAlchemyTransactionRepository()
        fs = FinancialService(tx_repo, SQLAlchemyBudgetRepository())
        result = fs.get_filtered_user_transactions(
            sess["user_id"], month=month, year=year, page=page, limit=5
        )
        txs = result.get("data", [])
        total = result.get("total", 0)
        total_pages = max(1, (total + 4) // 5)

        if not txs:
            label = f"{month}/{year}" if (month and year) else "Все транзакции"
            await message.answer(
                f"Нет транзакций ({label}).",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")]
                ])
            )
            return

        label = f"📋 Транзакции за {month}/{year}" if (month and year) else "📋 Все транзакции"
        lines = [f"{hbold(label)} (стр. {page}/{total_pages}, всего: {total})"]
        for t in txs:
            icon = "💰" if t.get("type") == "income" else "💳"
            cat_icon = t.get("category_icon") or "📁"
            lines.append(
                f"#{t['id']} {icon} {cat_icon} {_html.escape(t['category_name'])} | "
                f"{t['amount']:.2f} RUB | {(t['date'][:10] if t['date'] else '')} | {_html.escape(t['description'] or '—')}"
            )

        display_month = month or 0
        display_year = year or 0
        kb = _build_tx_keyboard(page, display_month, display_year, total_pages, txs)
        await message.answer("\n".join(lines), reply_markup=kb)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {_html.escape(str(e))}")

@router.message(Command("tx"))
@auth_required
async def cmd_tx(message: Message):
    parts = message.text.strip().split()
    if len(parts) >= 3:
        try:
            m = int(parts[1])
            y = int(parts[2])
            await _cmd_tx(message.from_user.id, message, month=m, year=y)
            return
        except ValueError:
            await message.answer("Неверный формат. Используй: /tx ММ ГГГГ (например: /tx 05 2026)")
            return
    await _cmd_tx(message.from_user.id, message)

@router.callback_query(lambda c: c.data and c.data.startswith("tx_page:"))
async def cb_tx_page(callback: CallbackQuery):
    _, page_s, m_s, y_s = callback.data.split(":")
    await _render_tx_page(callback, int(m_s), int(y_s), int(page_s))

@router.callback_query(lambda c: c.data and c.data.startswith("tx_nav_month:"))
async def cb_tx_nav_month(callback: CallbackQuery):
    _, m_s, y_s = callback.data.split(":")
    await _render_tx_page(callback, int(m_s), int(y_s), 1)

@router.callback_query(lambda c: c.data == "tx_all")
async def cb_tx_all(callback: CallbackQuery):
    await _render_tx_page(callback, 0, 0, 1)

# ─── /edittx ─────────────────────────────────────────────────────────

@router.message(Command("edittx"))
@auth_required
async def cmd_edittx(message: Message):
    tg_id = message.from_user.id
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Использование: /edittx [id_транзакции]")
        return
    try:
        tx_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID транзакции должен быть числом")
        return

    sess = get_session(tg_id)
    tx_repo = SQLAlchemyTransactionRepository()
    fs = FinancialService(tx_repo, SQLAlchemyBudgetRepository())
    txs = fs.get_user_transactions(sess["user_id"])
    tx_data = next((t for t in txs if t["id"] == tx_id), None)
    if not tx_data:
        await message.answer("❌ Транзакция не найдена")
        return

    sess["step"] = f"edit_amount:{tx_id}"
    sess["data"]["edit_tx_id"] = tx_id
    sess["data"]["edit_original"] = tx_data
    await message.answer(
        f"Редактирование транзакции #{tx_id}\n"
        f"Текущая сумма: {tx_data['amount']:.2f} RUB\n"
        "Введите новую сумму (или «-» для текущей):"
    )

@router.message(lambda msg: not_command(msg) and user_sessions.get(msg.from_user.id, {}).get("step", "").startswith("edit_amount:"))
async def edit_enter_amount(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    tx_id = int(sess["step"].split(":")[1])
    raw = message.text.strip()
    if raw == "-":
        amount = sess["data"]["edit_original"]["amount"]
    else:
        try:
            amount = float(raw.replace(",", "."))
        except ValueError:
            await message.answer("❌ Введите число")
            return
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительным числом")
            return
    sess["data"]["edit_amount"] = amount
    sess["step"] = f"edit_category:{tx_id}"
    with get_db() as s:
        cats = s.query(Category).all()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c.icon or '📁'} {c.name}", callback_data=f"editcat:{c.id}:{tx_id}")]
        for c in cats
    ])
    await message.answer(
        f"Сумма: {amount:.2f} RUB\n"
        "Выберите новую категорию (или нажмите текущую для её сохранения):",
        reply_markup=kb
    )

@router.callback_query(lambda c: c.data and c.data.startswith("editcat:"))
async def cb_edit_select_category(callback: CallbackQuery):
    tg_id = callback.from_user.id
    _, cat_id_s, tx_id_s = callback.data.split(":")
    cat_id = int(cat_id_s)
    tx_id = int(tx_id_s)
    sess = get_session(tg_id)
    sess["data"]["edit_category_id"] = cat_id
    sess["step"] = f"edit_desc:{tx_id}"
    with get_db() as s:
        cat = s.query(Category).filter(Category.id == cat_id).first()
        cat_name = cat.name if cat else f"ID:{cat_id}"
    sess["data"]["edit_category_name"] = cat_name
    await callback.message.edit_text(
        f"Категория: {_html.escape(cat_name)}\n"
        f"Текущее описание: {_html.escape(sess['data']['edit_original']['description'] or '—')}\n"
        "Введите новое описание (или «-» для текущего):"
    )
    await callback.answer()

@router.message(lambda msg: not_command(msg) and user_sessions.get(msg.from_user.id, {}).get("step", "").startswith("edit_desc:"))
async def edit_enter_desc(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    tx_id = int(sess["step"].split(":")[1])
    raw = message.text.strip()
    desc = sess["data"]["edit_original"]["description"] if raw == "-" else raw
    sess["data"]["edit_description"] = desc
    sess["step"] = f"edit_date:{tx_id}"
    await message.answer(
        f"Описание: {_html.escape(desc or '—')}\n"
        f"Текущая дата: {_html.escape(sess['data']['edit_original']['date'][:10] if sess['data']['edit_original']['date'] else '—')}\n"
        "Введите новую дату ДД.ММ.ГГГГ (или «-» для текущей):"
    )

@router.message(lambda msg: not_command(msg) and user_sessions.get(msg.from_user.id, {}).get("step", "").startswith("edit_date:"))
async def edit_enter_date(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    tx_id = int(sess["step"].split(":")[1])
    raw = message.text.strip()
    if raw == "-":
        tx_date = sess["data"]["edit_original"]["date"]
    else:
        try:
            parts = raw.replace(".", " ").replace("/", " ").replace("-", " ").split()
            if len(parts) != 3:
                raise ValueError
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            tx_date = dt_date(y, m, d).isoformat()
        except (ValueError, IndexError):
            await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ или «-»")
            return
    sess["data"]["edit_date"] = tx_date

    update_data = {
        "amount": sess["data"]["edit_amount"],
        "category_id": sess["data"]["edit_category_id"],
        "description": sess["data"]["edit_description"],
    }
    if tx_date:
        update_data["date"] = tx_date

    try:
        tx_repo = SQLAlchemyTransactionRepository()
        fs = FinancialService(tx_repo, SQLAlchemyBudgetRepository())
        fs.update_transaction(tx_id, sess["user_id"], update_data)
        sess["step"] = None
        await message.answer(
            f"✅ Транзакция #{tx_id} обновлена!",
            reply_markup=menu_kb()
        )
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {_html.escape(str(e))}")
        sess["step"] = None
    except Exception as e:
        await message.answer(f"❌ Ошибка: {_html.escape(str(e))}")
        sess["step"] = None

# ─── Delete tx from inline button ────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("tx_delete:"))
async def cb_tx_delete(callback: CallbackQuery):
    tg_id = await _ensure_auth(callback)
    if tg_id is None:
        return
    tx_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        f"🗑 Удалить транзакцию #{tx_id}?",
        reply_markup=confirm_kb(f"confirm_del_tx:{tx_id}", f"cancel_del_tx:{tx_id}")
    )
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("confirm_del_tx:"))
async def cb_confirm_del_tx(callback: CallbackQuery):
    tg_id = await _ensure_auth(callback)
    if tg_id is None:
        return
    tx_id = int(callback.data.split(":")[1])
    sess = get_session(tg_id)
    try:
        with get_db() as s:
            tx = s.query(Transaction).filter(
                Transaction.id == tx_id, Transaction.user_id == sess["user_id"]
            ).first()
            if tx:
                s.delete(tx)
                s.commit()
                await callback.message.edit_text(f"✅ Транзакция #{tx_id} удалена.")
            else:
                await callback.message.edit_text("❌ Транзакция не найдена.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {_html.escape(str(e))}")
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("cancel_del_tx:"))
async def cb_cancel_del_tx(callback: CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()

# ─── /tx edit inline button ──────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("tx_edit:"))
async def cb_tx_edit(callback: CallbackQuery):
    tg_id = await _ensure_auth(callback)
    if tg_id is None:
        return
    tx_id = int(callback.data.split(":")[1])
    sess = get_session(tg_id)
    tx_repo = SQLAlchemyTransactionRepository()
    fs = FinancialService(tx_repo, SQLAlchemyBudgetRepository())
    txs = fs.get_user_transactions(sess["user_id"])
    tx_data = next((t for t in txs if t["id"] == tx_id), None)
    if not tx_data:
        await callback.message.edit_text("❌ Транзакция не найдена.")
        await callback.answer()
        return

    sess["step"] = f"edit_amount:{tx_id}"
    sess["data"]["edit_tx_id"] = tx_id
    sess["data"]["edit_original"] = tx_data
    await callback.message.edit_text(
        f"Редактирование транзакции #{tx_id}\n"
        f"Текущая сумма: {tx_data['amount']:.2f} RUB\n"
        "Введите новую сумму (или «-» для текущей):"
    )
    await callback.answer()

# ─── /addcat ─────────────────────────────────────────────────────────

@router.message(Command("addcat"))
@auth_required
async def cmd_addcat(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    sess["step"] = "addcat_name"
    sess["data"] = {}
    await message.answer("Введите название новой категории:")

@router.message(lambda msg: not_command(msg) and user_sessions.get(msg.from_user.id, {}).get("step") == "addcat_name")
async def addcat_enter_name(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название не может быть пустым.")
        return
    sess["data"]["cat_name"] = name
    sess["step"] = "addcat_icon"
    await message.answer(
        f"Название: {_html.escape(name)}\n"
        "Введите emoji-иконку для категории (или «-» для стандартной):"
    )

@router.message(lambda msg: not_command(msg) and user_sessions.get(msg.from_user.id, {}).get("step") == "addcat_icon")
async def addcat_enter_icon(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    raw = message.text.strip()
    icon = raw if raw != "-" else ""
    sess["data"]["cat_icon"] = icon
    sess["step"] = "addcat_type"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Расход", callback_data="addcat_type:expense")],
        [InlineKeyboardButton(text="💰 Доход", callback_data="addcat_type:income")],
    ])
    await message.answer(
        f"Название: {_html.escape(sess['data']['cat_name'])}\n"
        f"Иконка: {_html.escape(icon or '📁')}\n"
        "Выберите тип категории:",
        reply_markup=kb
    )

@router.callback_query(lambda c: c.data and c.data.startswith("addcat_type:"))
async def cb_addcat_type(callback: CallbackQuery):
    tg_id = callback.from_user.id
    sess = get_session(tg_id)
    cat_type = callback.data.split(":")[1]
    try:
        with get_db() as s:
            existing = s.query(Category).filter(Category.name == sess["data"]["cat_name"]).first()
            if existing:
                await callback.message.edit_text(f"❌ Категория «{_html.escape(sess['data']['cat_name'])}» уже существует.")
                sess["step"] = None
                await callback.answer()
                return
            cat = Category(
                name=sess["data"]["cat_name"],
                icon=sess["data"]["cat_icon"],
                type=cat_type,
            )
            s.add(cat)
            s.commit()
            s.refresh(cat)
        type_label = "💰 Доход" if cat_type == "income" else "💳 Расход"
        await callback.message.edit_text(
            f"✅ Категория создана:\n"
            f"{cat.icon or '📁'} {_html.escape(cat.name)} ({type_label})",
            reply_markup=menu_kb()
        )
        sess["step"] = None
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {_html.escape(str(e))}")
    await callback.answer()

# ─── /delcat ─────────────────────────────────────────────────────────

@router.message(Command("delcat"))
@auth_required
async def cmd_delcat(message: Message):
    with get_db() as s:
        cats = s.query(Category).all()
    if not cats:
        await message.answer("Нет категорий для удаления.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{c.icon or '📁'} {c.name}",
            callback_data=f"delcat_confirm:{c.id}"
        )]
        for c in cats
    ])
    await message.answer("Выберите категорию для удаления:", reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("delcat_confirm:"))
async def cb_delcat_confirm(callback: CallbackQuery):
    cat_id = int(callback.data.split(":")[1])
    with get_db() as s:
        cat = s.query(Category).filter(Category.id == cat_id).first()
        if not cat:
            await callback.message.edit_text("❌ Категория не найдена.")
            await callback.answer()
            return
        name = cat.name
    await callback.message.edit_text(
        f"🗑 Удалить категорию «{_html.escape(name)}»?\n"
        "Все связанные транзакции и бюджеты останутся.",
        reply_markup=confirm_kb(f"confirm_del_cat:{cat_id}", "cancel_del_cat")
    )
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("confirm_del_cat:"))
async def cb_confirm_del_cat(callback: CallbackQuery):
    cat_id = int(callback.data.split(":")[1])
    try:
        with get_db() as s:
            cat = s.query(Category).filter(Category.id == cat_id).first()
            if not cat:
                await callback.message.edit_text("❌ Категория не найдена.")
                await callback.answer()
                return
            from models.database import Transaction, Budget, IncomeSource
            tx_count = s.query(Transaction).filter(Transaction.category_id == cat_id).count()
            bg_count = s.query(Budget).filter(Budget.category_id == cat_id).count()
            inc_count = s.query(IncomeSource).filter(IncomeSource.category_id == cat_id).count()
            if tx_count > 0 or bg_count > 0 or inc_count > 0:
                refs = []
                if tx_count: refs.append(f"транзакции ({tx_count})")
                if bg_count: refs.append(f"бюджеты ({bg_count})")
                if inc_count: refs.append(f"доходы ({inc_count})")
                await callback.message.edit_text(
                    f"❌ Нельзя удалить категорию «{_html.escape(cat.name)}»: есть связанные записи: {', '.join(refs)}.",
                    reply_markup=menu_kb()
                )
                await callback.answer()
                return
            s.delete(cat)
            s.commit()
            await callback.message.edit_text(f"✅ Категория «{_html.escape(cat.name)}» удалена.", reply_markup=menu_kb())
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {_html.escape(str(e))}")
    await callback.answer()

@router.callback_query(lambda c: c.data == "cancel_del_cat")
async def cb_cancel_del_cat(callback: CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено.", reply_markup=menu_kb())
    await callback.answer()

# ─── /process ────────────────────────────────────────────────────────

@router.message(Command("process"))
@auth_required
async def cmd_process(message: Message):
    tg_id = message.from_user.id
    sess = get_session(tg_id)
    try:
        tx_repo = SQLAlchemyTransactionRepository()
        bg_repo = SQLAlchemyBudgetRepository()
        inc_repo = SQLAlchemyIncomeSourceRepository()
        fs = FinancialService(tx_repo, bg_repo, inc_repo)
        result = fs.process_regular_payments(sess["user_id"])
        processed = result.get("processed", 0)
        errors = result.get("errors", [])
        lines = [f"✅ Обработано регулярных платежей: {processed}"]
        if errors:
            lines.append(f"❌ Ошибки ({len(errors)}):")
            for e in errors:
                lines.append(f"  • {_html.escape(e)}")
        await message.answer("\n".join(lines), reply_markup=menu_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {_html.escape(str(e))}")

# ─── Инлайн-кнопки меню ─────────────────────────────────────────────

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

@router.callback_query(lambda c: c.data == "menu")
async def cb_menu(callback: CallbackQuery):
    tg_id = callback.from_user.id
    sess = get_session(tg_id)
    try_auto_login(tg_id, sess)
    email = sess.get("email", "неизвестный")
    await callback.message.edit_text(
        f"{hbold('🏠 HomeMoney Bot')}\n\n"
        f"Вы вошли как {hbold(email)}\n\n"
        "Выберите действие:",
        reply_markup=menu_kb()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "tx_nav_current")
async def cb_tx_nav_current(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(lambda c: True)
async def cb_fallback(callback: CallbackQuery):
    await callback.answer()
