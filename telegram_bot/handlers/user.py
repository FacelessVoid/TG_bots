from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import ADMIN_ID
from database import (
    cancel_application,
    get_user_application_stats,
    get_user_applications,
    save_application,
)
from keyboard import inline_keyboard, profile_keyboard
from states import Application


router = Router()


# =========================
# /start
# =========================

@router.message(CommandStart())
async def start(message: Message):
    if message.from_user.id == ADMIN_ID:
        from keyboard import admin_keyboard

        await message.answer(
            "Выбери действие:",
            reply_markup=admin_keyboard
        )
    else:
        await message.answer(
            "Выбери действие:",
            reply_markup=inline_keyboard
        )


# =========================
# /myid
# =========================

@router.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(
        f"Твой Telegram ID: {message.from_user.id}"
    )


# =========================
# /cancel
# =========================

@router.message(Command("cancel"))
async def cancel(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "❌ Оформление заявки отменено.",
        reply_markup=inline_keyboard
    )


# =========================
# Профиль
# =========================

@router.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = callback.from_user

    total, new, completed = get_user_application_stats(
        user.id
    )

    if user.username:
        telegram = f"@{user.username}"
    else:
        telegram = "Не указан"

    await callback.message.edit_text(
        "👤 Твой профиль\n\n"
        f"Имя: {user.full_name}\n"
        f"Telegram: {telegram}\n"
        f"ID: {user.id}\n\n"
        "📊 Статистика\n"
        f"📨 Заявок отправлено: {total}\n"
        f"🟡 В работе: {new}\n"
        f"🟢 Выполнено: {completed}",
        reply_markup=profile_keyboard
    )

    await callback.answer()


# =========================
# Мои заявки
# =========================

@router.callback_query(F.data == "my_applications")
async def my_applications(callback: CallbackQuery):
    user_id = callback.from_user.id

    applications = get_user_applications(user_id)

    if not applications:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="profile"
                    )
                ]
            ]
        )

        await callback.message.edit_text(
            "📨 Мои заявки\n\n"
            "У тебя пока нет заявок.",
            reply_markup=keyboard
        )

        await callback.answer()
        return

    keyboard = []

    for application_id, task, status in applications:
        if status == "new":
            status_text = "🟡 В работе"
        elif status == "completed":
            status_text = "🟢 Выполнена"
        else:
            status_text = "🔴 Отменена"

        keyboard.append([
            InlineKeyboardButton(
                text=f"🆔 №{application_id} — {status_text}",
                callback_data=f"my_application_{application_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="profile"
        )
    ])

    await callback.message.edit_text(
        "📨 Мои заявки\n\n"
        "Выбери заявку:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )

    await callback.answer()


# =========================
# Информация о моей заявке
# =========================

@router.callback_query(F.data.startswith("my_application_"))
async def my_application_details(callback: CallbackQuery):
    application_id = int(
        callback.data.split("_")[2]
    )

    user_id = callback.from_user.id

    applications = get_user_applications(user_id)

    application = None

    for item in applications:
        if item[0] == application_id:
            application = item
            break

    if not application:
        await callback.answer(
            "Заявка не найдена.",
            show_alert=True
        )
        return

    application_id, task, status = application

    if status == "new":
        status_text = "🟡 В работе"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Отменить заявку",
                        callback_data=f"confirm_cancel_{application_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="my_applications"
                    )
                ]
            ]
        )

    elif status == "completed":
        status_text = "🟢 Выполнена"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="my_applications"
                    )
                ]
            ]
        )

    else:
        status_text = "🔴 Отменена"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="my_applications"
                    )
                ]
            ]
        )

    await callback.message.edit_text(
        f"📨 Заявка №{application_id}\n\n"
        f"📝 Задача:\n{task}\n\n"
        f"📌 Статус: {status_text}",
        reply_markup=keyboard
    )

    await callback.answer()

# =========================
# Отмена моей заявки
# =========================

@router.callback_query(
    F.data.startswith("cancel_my_application_")
)
@router.callback_query(
    F.data.startswith("confirm_cancel_")
)
@router.callback_query(
    F.data.startswith("cancel_my_application_")
)
async def cancel_my_application(
    callback: CallbackQuery,
    bot: Bot
):
    application_id = int(
        callback.data.replace(
            "cancel_my_application_",
            ""
        )
    )

    success = cancel_application(
        application_id,
        callback.from_user.id
    )

    if not success:
        await callback.answer(
            "Эту заявку уже нельзя отменить.",
            show_alert=True
        )
        return

    # Кнопка для открытия заявки у администратора
    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📨 Открыть заявку",
                    callback_data=f"application_{application_id}"
                )
            ]
        ]
    )

    # Уведомляем администратора
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🔴 Клиент отменил заявку №{application_id}.\n\n"
            f"👤 Клиент: {callback.from_user.full_name}\n"
            f"💬 Telegram ID: {callback.from_user.id}",
            reply_markup=admin_keyboard
        )
    except Exception:
        pass

    # Сразу показываем отменённую заявку пользователю
    await callback.message.edit_text(
        f"📨 Заявка №{application_id}\n\n"
        f"📌 Статус: 🔴 Отменена",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="my_applications"
                    )
                ]
            ]
        )
    )

    await callback.answer(
        "Заявка отменена 🔴"
    )

async def cancel_my_application(
    callback: CallbackQuery,
    bot: Bot
):
    application_id = int(
        callback.data.split("_")[3]
    )

    success = cancel_application(
        application_id,
        callback.from_user.id
    )

    if not success:
        await callback.answer(
            "Эту заявку уже нельзя отменить.",
            show_alert=True
        )
        return

    # Кнопка для открытия заявки у администратора
    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📨 Открыть заявку",
                    callback_data=f"application_{application_id}"
                )
            ]
        ]
    )

    # Уведомляем администратора
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🔴 Клиент отменил заявку №{application_id}.\n\n"
            f"👤 Клиент: {callback.from_user.full_name}\n"
            f"💬 Telegram ID: {callback.from_user.id}",
            reply_markup=admin_keyboard
        )
    except Exception:
        pass

    # Сразу обновляем экран клиента
    await callback.message.edit_text(
        f"📨 Заявка №{application_id}\n\n"
        f"📌 Статус: 🔴 Отменена",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="my_applications"
                    )
                ]
            ]
        )
    )

    await callback.answer(
        "Заявка отменена 🔴"
    )


# =========================
# Назад
# =========================

@router.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выбери действие:",
        reply_markup=inline_keyboard
    )

    await callback.answer()


# =========================
# Начало оформления заявки
# =========================

@router.callback_query(F.data == "application")
async def application(
    callback: CallbackQuery,
    state: FSMContext
):
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


# =========================
# Получение имени
# =========================

@router.message(Application.name)
async def get_name(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        name=message.text
    )

    await state.set_state(
        Application.task
    )

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

    await message.answer(
        "Отлично! 👍\n\n"
        "Теперь напиши, что тебе нужно:",
        reply_markup=cancel_keyboard
    )


# =========================
# Получение задачи
# =========================

@router.message(Application.task)
async def get_task(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        task=message.text
    )

    await state.set_state(
        Application.phone
    )

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
        "Теперь отправь свой номер телефона:",
        reply_markup=phone_keyboard
    )


# =========================
# Отмена на этапе телефона
# =========================

@router.message(
    Application.phone,
    F.text == "❌ Отмена"
)
async def cancel_phone(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "❌ Оформление заявки отменено.",
        reply_markup=ReplyKeyboardRemove()
    )

    await message.answer(
        "Выбери действие:",
        reply_markup=inline_keyboard
    )


# =========================
# Получение телефона
# =========================

@router.message(
    Application.phone,
    F.contact
)
@router.message(
    Application.phone,
    F.contact
)
async def get_phone(
    message: Message,
    state: FSMContext,
    bot: Bot
):
    phone = message.contact.phone_number

    await state.update_data(
        phone=phone
    )

    data = await state.get_data()

    application_id = save_application(
        data["name"],
        data["task"],
        data["phone"],
        message.from_user.id
    )

    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📨 Открыть заявку",
                    callback_data=f"application_{application_id}"
                )
            ]
        ]
    )

    await bot.send_message(
        ADMIN_ID,
        "📨 Новая заявка!\n\n"
        f"🆔 Заявка №{application_id}\n"
        f"👤 Имя: {data['name']}\n"
        f"📝 Задача: {data['task']}\n"
        f"📞 Телефон: {data['phone']}",
        reply_markup=admin_keyboard
    )

    await state.clear()

    await message.answer(
        "Заявка успешно отправлена! ✅",
        reply_markup=ReplyKeyboardRemove()
    )

    await message.answer(
        "Выбери действие:",
        reply_markup=inline_keyboard
    )

# =========================
# Отмена заявки через inline-кнопку
# =========================

@router.callback_query(
    F.data == "cancel_application"
)
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