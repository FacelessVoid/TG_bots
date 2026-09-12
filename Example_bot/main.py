from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
from database import (
    save_application,
    get_applications,
    get_application,
    delete_application,
    complete_application,
    reopen_application
)

load_dotenv()


class Application(StatesGroup):
    name = State()
    task = State()
    phone = State()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if BOT_TOKEN is None or ADMIN_ID is None:
    raise ValueError("Не найдены BOT_TOKEN или ADMIN_ID в .env")

bot = Bot(token=BOT_TOKEN)
ADMIN_ID = int(ADMIN_ID)
dp = Dispatcher(storage=MemoryStorage())

admin_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📨 Заявки",
                callback_data="applications"
            )
        ]
    ]
)

applications_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="admin_back"
            )
        ]
    ]
)

@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выбери действие:",
        reply_markup=admin_keyboard
    )

    await callback.answer()


@dp.callback_query(F.data == "applications")
async def applications(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У тебя нет доступа 😎", show_alert=True)
        return

    apps = get_applications()

    keyboard = []

    for app in apps:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🆔 Заявка №{app[0]} — {app[1]}",
                callback_data=f"application_{app[0]}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="admin_back"
        )
    ])

    applications_keyboard = InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )

    if not apps:
        text = "📨 Заявки\n\nПока заявок нет."
    else:
        text = "📨 Заявки\n\n"

        for app in apps:
            text += (
                f"🆔 Заявка №{app[0]}\n"
                f"👤 Имя: {app[1]}\n"
                f"📝 Задача: {app[2]}\n"
                f"📞 Телефон: {app[3]}\n\n"
            )

    await callback.message.edit_text(
        text,
        reply_markup=applications_keyboard
    )

    await callback.answer()

@dp.callback_query(F.data.startswith("application_"))
async def application_details(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У тебя нет доступа 😎", show_alert=True)
        return

    application_id = int(callback.data.split("_")[1])

    app = get_application(application_id)

    if app[4] == "completed":
        action_button = InlineKeyboardButton(
            text="↩️ Вернуть в работу",
            callback_data=f"reopen_{application_id}"
        )
    else:
        action_button = InlineKeyboardButton(
            text="✅ Выполнено",
            callback_data=f"complete_{application_id}"
        )

    application_actions = InlineKeyboardMarkup(
        inline_keyboard=[
            [action_button],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"delete_{application_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="applications"
                )
            ]
        ]
    )
    if app[4] == "new":
        status = "🟡 Новая"
    else:
        status = "🟢 Выполнена"

    await callback.message.edit_text(
        f"📨 Заявка №{app[0]}\n\n"
        f"👤 Имя: {app[1]}\n"
        f"📝 Задача: {app[2]}\n"
        f"📞 Телефон: {app[3]}\n"
        f"📌 Статус: {status}",
        reply_markup=application_actions
    )

    await callback.answer()

@dp.callback_query(F.data.startswith("complete_"))
async def complete_application_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У тебя нет доступа 😎", show_alert=True)
        return

    application_id = int(callback.data.split("_")[1])

    complete_application(application_id)

    app = get_application(application_id)

    await callback.message.edit_text(
        f"📨 Заявка №{app[0]}\n\n"
        f"👤 Имя: {app[1]}\n"
        f"📝 Задача: {app[2]}\n"
        f"📞 Телефон: {app[3]}\n"
        f"📌 Статус: 🟢 Выполнена",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🗑 Удалить",
                        callback_data=f"delete_{application_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="applications"
                    )
                ]
            ]
        )
    )

    await callback.answer("Заявка выполнена ✅")

@dp.callback_query(F.data.startswith("reopen_"))
async def reopen_application_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У тебя нет доступа 😎", show_alert=True)
        return

    application_id = int(callback.data.split("_")[1])

    reopen_application(application_id)

    await callback.answer("Заявка снова в работе 🔄")

    await application_details(callback)

@dp.callback_query(F.data.startswith("delete_"))
async def delete_application_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У тебя нет доступа 😎", show_alert=True)
        return

    application_id = int(callback.data.split("_")[1])

    confirmation_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Да, удалить",
                    callback_data=f"confirm_delete_{application_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"application_{application_id}"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "⚠️ Ты точно хочешь удалить эту заявку?\n\n"
        "Это действие нельзя будет отменить.",
        reply_markup=confirmation_keyboard
    )
    await callback.answer()

    apps = get_applications()

    keyboard = []

    for app in apps:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🆔 Заявка №{app[0]} — {app[1]} {'🟢' if app[4] == 'completed' else '🟡'}",
                callback_data=f"application_{app[0]}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="admin_back"
        )
    ])

    applications_keyboard = InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )

    if not apps:
        text = "📨 Заявки\n\nПока заявок нет."
    else:
        text = "📨 Заявки\n\n"

        for app in apps:
            text += (
                f"🆔 Заявка №{app[0]}\n"
                f"👤 Имя: {app[1]}\n"
                f"📝 Задача: {app[2]}\n"
                f"📞 Телефон: {app[3]}\n\n"
            )


profile_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back"
            )
        ]
    ]
)
inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Показать профиль",
                callback_data="profile"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Оставить заявку",
                callback_data="application"
            )
        ]
    ]
)

@dp.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_application(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У тебя нет доступа 😎", show_alert=True)
        return

    application_id = int(callback.data.split("_")[2])

    delete_application(application_id)

    await callback.answer("Заявка удалена ✅")
    await applications(callback)

@dp.message(CommandStart())
async def start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Выбери действие:",
            reply_markup=admin_keyboard
        )
    else:
        await message.answer(
            "Выбери действие:",
            reply_markup=inline_keyboard
        )

@dp.message(F.text == "/myid")
async def my_id(message: Message):
    await message.answer(f"Твой Telegram ID: {message.from_user.id}")

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У тебя нет доступа 😎", show_alert=True)
        return

    await callback.message.edit_text(
        "⚙️ Админ-панель\n\n"
        "Ты вошёл как администратор.",
        reply_markup=admin_keyboard
    )

    await callback.answer()

@dp.message(Command("cancel"))
async def cancel_application(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "❌ Оформление заявки отменено.",
        reply_markup=inline_keyboard
    )

async def main():
    await dp.start_polling(bot)

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    await callback.message.edit_text(
        "👤 Твой профиль\n\n"
        "Имя: Артём\n"
        "Уровень: 1\n"
        "Опыт: 0 XP",
        reply_markup=profile_keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "application")
async def application(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Application.name)

    cancel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel_application"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "📝 Отлично! Давай оформим заявку.\n\n"
        "Напиши своё имя:",
        reply_markup=cancel_keyboard
    )

    await callback.answer()

@dp.callback_query(F.data == "cancel_application")
async def cancel_application_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.clear()

    await callback.message.edit_text(
        "❌ Оформление заявки отменено.",
        reply_markup=inline_keyboard
    )

    await callback.answer()

@dp.message(Application.name)
async def get_name(message: Message, state: FSMContext):

    await state.update_data(name=message.text)

    await state.set_state(Application.task)

    await message.answer(
        "Отлично! 👍\n\n"
        "Теперь напиши, что тебе нужно:"
    )

@dp.message(Application.task)
async def get_task(message: Message, state: FSMContext):
    await state.update_data(task=message.text)

    await state.set_state(Application.phone)

    phone_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Отправить мой номер",
                    request_contact=True
                )
            ],
            [
                KeyboardButton(
                    text="❌ Отмена"
                )
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "Понял 👍\n\n"
        "Нажми кнопку ниже, чтобы отправить свой номер:",
        reply_markup=phone_keyboard
    )

@dp.message(Application.phone, F.text == "❌ Отмена")
async def cancel_phone(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "❌ Оформление заявки отменено.",
        reply_markup=inline_keyboard
    )


@dp.message(Application.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number

    await state.update_data(phone=phone)

    data = await state.get_data()

    save_application(
        data["name"],
        data["task"],
        data["phone"]
    )

    await bot.send_message(
        ADMIN_ID,
        f"📨 Новая заявка!\n\n"
        f"Имя: {data['name']}\n"
        f"Задача: {data['task']}\n"
        f"Телефон: {data['phone']}"
    )

    await state.clear()

    await message.answer(
        "Заявка успешно отправлена! ✅",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выбери действие:",
        reply_markup=inline_keyboard
    )
    await callback.answer()


if __name__ == "__main__":
    asyncio.run(main())