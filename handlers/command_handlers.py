from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import hbold

router = Router()

user_state: dict = {}

@router.message(commands=["start"])
async def handle_start(message: Message):
    text = (
        f"{hbold('HomeMoney Bot')} - Ваш личный финансовый помощник.\n\n"
        "Выберите действие из меню ниже:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить транзакцию", callback_data="add_transaction_start")],
        [InlineKeyboardButton(text="Посмотреть сводку", callback_data="get_summary_menu")],
    ])
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "add_transaction_start")
async def start_add_transaction(callback: CallbackQuery):
    user_state["wizard"] = {"step": "select_category", "data": {}}
    categories = ["Продукты", "Аренда", "Транспорт", "Развлечения", "Зарплата"]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat, callback_data=f"select_category:{cat}")]
        for cat in categories
    ])
    await callback.message.edit_text("Выберите категорию:", reply_markup=keyboard)

@router.callback_query(lambda c: str(c.data).startswith("select_category:"))
async def select_category(callback: CallbackQuery):
    selected = callback.data.split(":")[1]
    user_state["wizard"]["data"]["category"] = selected
    user_state["wizard"]["step"] = "enter_amount"
    await callback.message.edit_text(
        f"Выбрана категория: {hbold(selected)}\n"
        "Введите сумму числом:"
    )

@router.message(lambda msg: user_state.get("wizard", {}).get("step") == "enter_amount")
async def enter_amount(message: Message):
    try:
        amount = float(message.text.replace(",", "."))
        category = user_state["wizard"]["data"]["category"]
        user_state["wizard"] = None
        await message.answer(
            f"Транзакция '{category}' на {hbold(f'{amount:.2f}')} добавлена."
        )
    except ValueError:
        await message.answer("Ошибка: введите число.")

@router.callback_query(lambda c: c.data == "get_summary_menu")
async def handle_summary(callback: CallbackQuery):
    await callback.message.edit_text("Функция сводки будет добавлена в следующей версии.")
