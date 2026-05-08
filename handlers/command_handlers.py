from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from typing import List

router = Router()

# Состояние пользователя (имитация хранилища для многошагового процесса)
# В реальном боте это должен быть User State (например, из Redis/Postgres)
user_state: dict = {} 

# --- Обработчик /start ---
@router.message(commands=["start"])
async def handle_start(message: Message):
    """Обрабатывает команду /start и показывает меню."""
    from aiogram.utils.markdown import hbold, hitalic
    text = (
        f"{hbold('💰 HomeMoney Bot')} - Ваш личный финансовый помощник.\n\n"
        "Выберите действие из меню ниже:",
    )
    await message.answer(text)

# --- Обработчик CallbackQuery для Главного Меню ---
@router.callback_query(lambda c: c.data == "main_menu")
async def handle_main_menu(callback: CallbackQuery):
    """Обрабатывает нажатие на главное меню и показывает опции."""
    from aiogram import classmethod
    
    # Определяем кнопки главного меню
    inline_keyboard = [
        [InlineKeyboardButton(text="➕ Добавить транзакцию", callback_data="add_transaction_start")],
        [InlineKeyboardButton(text="📊 Посмотреть сводку месяца", callback_data="get_summary_menu")],
        [InlineKeyboardButton(text="⚙️ Настройки/Помощь", callback_data="help_menu")],
    ]
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard))

# --- Мастер добавления транзакции (Wizard) ---
@router.callback_query(lambda c: c.data == "add_transaction_start")
async def start_add_transaction(callback: CallbackQuery):
    """Начинает процесс добавления транзакции, запрашивая категорию."""
    # 1. Устанавливаем состояние пользователя (текущий шаг = выбор категории)
    user_state["wizard"] = {"step": "select_category", "data": {}}
    
    # Список всех доступных категорий для выбора
    categories = ["Продукты", "Аренда", "Транспорт", "Развлечения", "Зарплата"] 

    inline_keyboard = [
        [InlineKeyboardButton(text=cat, callback_data="select_category:" + cat) for cat in categories]
    ]
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard))


# --- Шаг 1: Выбор Категории (Обработчик выбора категории) ---
@router.callback_query(lambda c: str(c.data).startswith("select_category:"))
async def select_category(callback: CallbackQuery):
    """Переходит к следующему шагу мастера - ввод суммы."""
    selected_category = callback.data.split(":")[1]
    # 1. Сохраняем выбранную категорию в состояние пользователя
    user_state["wizard"]["data"]["category"] = selected_category
    user_state["wizard"]["step"] = "enter_amount"

    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="✅ Готово к следующему шагу", callback_data="next_step")]], resize_keyboard=True))
    await callback.message.answer("Отлично, выбранная категория: *{}*.\nТеперь укажите сумму расхода (числовое значение).".format(hbold(selected_category)))


# --- Шаг 2: Ввод суммы и завершение процесса ---
@router.callback_query(lambda c: c.data == "next_step")
async def enter_amount_and_submit(callback: CallbackQuery):
    """Обрабатывает финальные данные и вызывает сервис добавления транзакции."""
    # Получаем текущее состояние пользователя (должна быть сумма от текста, но для примера оставим заглушку)
    if not user_state.get("wizard") or user_state["wizard"]["step"] != "enter_amount":
        await callback.message.answer("Ошибка: Не удалось определить шаг.")
        return

    # Имитация получения суммы (В реальном боте это пришло бы из Message, а не CallbackQuery)
    # Для простоты используем фиксированное значение для демонстрации логики
    amount_text = "120.50" 
    try:
        amount = float(amount_text)

        # Получаем данные из состояния (текущая категория)
        category = user_state["wizard"]["data"]["category"]
        description = "Транзакция добавлена через бота."

        # Вызываем бизнес-логику сервиса!
        # В реальном боте здесь нужно передавать UserID, который взят из context.from_user
        # Имитация user_id=1 и вызов:
        # transaction = await financial_service.add_transaction(user_id=1, amount=amount, category_id="...")
        
        await callback.message.answer(
            f"✅ Успех! Транзакция '{category}' на сумму {hbold(float(amount)):.2f} успешно добавлена.\n"
            "Теперь вы можете добавить следующую транзакцию."
        )

    except Exception as e:
        await callback.message.answer(f"❌ Произошла ошибка при записи данных в систему: {e}")
    finally:
        # Очистка состояния пользователя после успешной операции
        user_state["wizard"] = None
