from aiogram import Bot, F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import ADMIN_ID
from database import (
    complete_application,
    delete_application,
    get_application,
    get_applications,
    reopen_application,
)
from keyboard import admin_keyboard


router = Router()


# =========================
# Назад из списка заявок
# =========================

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "У тебя нет доступа 😎",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "Выбери действие:",
        reply_markup=admin_keyboard
    )

    await callback.answer()


# =========================
# Админ-панель
# =========================

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "У тебя нет доступа 😎",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "⚙️ Админ-панель\n\n"
        "Ты вошёл как администратор.",
        reply_markup=admin_keyboard
    )

    await callback.answer()


# =========================
# Список заявок
# =========================

@router.callback_query(F.data == "applications")
async def applications(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "У тебя нет доступа 😎",
            show_alert=True
        )
        return

    apps = get_applications()

    if not apps:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="admin_back"
                    )
                ]
            ]
        )

        await callback.message.edit_text(
            "📨 Заявки\n\n"
            "Пока заявок нет.",
            reply_markup=keyboard
        )

        await callback.answer()
        return

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

    await callback.message.edit_text(
        "📨 Заявки",
        reply_markup=applications_keyboard
    )

    await callback.answer()


# =========================
# Информация о заявке
# =========================

@router.callback_query(F.data.startswith("application_"))
async def application_details(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "У тебя нет доступа 😎",
            show_alert=True
        )
        return

    application_id = int(
        callback.data.split("_")[1]
    )

    app = get_application(application_id)

    if not app:
        await callback.answer(
            "Заявка не найдена.",
            show_alert=True
        )
        return

    application_id = app[0]
    name = app[1]
    task = app[2]
    phone = app[3]
    status = app[4]
    telegram_id = app[5]

    if status == "completed":
        status_text = "🟢 Выполнена"

        action_button = InlineKeyboardButton(
            text="↩️ Вернуть в работу",
            callback_data=f"reopen_{application_id}"
        )

    elif status == "cancelled":
        status_text = "🔴 Отменена"

        action_button = InlineKeyboardButton(
            text="↩️ Вернуть в работу",
            callback_data=f"reopen_{application_id}"
        )

    else:
        status_text = "🟡 В работе"

        action_button = InlineKeyboardButton(
            text="✅ Выполнено",
            callback_data=f"complete_{application_id}"
        )

    keyboard_buttons = []

    if telegram_id:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="💬 Написать клиенту",
                url=f"tg://user?id={telegram_id}"
            )
        ])

    keyboard_buttons.extend([
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
    ])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=keyboard_buttons
    )

    telegram_text = (
        f"💬 Telegram ID: {telegram_id}"
        if telegram_id
        else "💬 Telegram ID: неизвестен"
    )

    text = (
        f"📨 Заявка №{application_id}\n\n"
        f"👤 Имя: {name}\n"
        f"📝 Задача: {task}\n"
        f"📞 Телефон: {phone}\n"
        f"{telegram_text}\n"
        f"📌 Статус: {status_text}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )

    await callback.answer()


# =========================
# Выполнить заявку
# =========================

@router.callback_query(F.data.startswith("complete_"))
async def complete_application_handler(
    callback: CallbackQuery,
    bot: Bot
):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "У тебя нет доступа 😎",
            show_alert=True
        )
        return

    application_id = int(
        callback.data.split("_")[1]
    )

    app = get_application(application_id)

    if not app:
        await callback.answer(
            "Заявка не найдена.",
            show_alert=True
        )
        return

    telegram_id = app[5]

    complete_application(application_id)

    if telegram_id:
        try:
            await bot.send_message(
                telegram_id,
                f"✅ Заявка №{application_id} выполнена!\n\n"
                "Спасибо за обращение. Если тебе понадобится "
                "что-то ещё — можешь оставить новую заявку."
            )
        except Exception:
            pass

    await callback.answer(
        "Заявка выполнена ✅"
    )

    await application_details(callback)


# =========================
# Вернуть заявку в работу
# =========================

@router.callback_query(F.data.startswith("reopen_"))
async def reopen_application_handler(
    callback: CallbackQuery,
    bot: Bot
):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "У тебя нет доступа 😎",
            show_alert=True
        )
        return

    application_id = int(
        callback.data.split("_")[1]
    )

    app = get_application(application_id)

    if not app:
        await callback.answer(
            "Заявка не найдена.",
            show_alert=True
        )
        return

    telegram_id = app[5]

    reopen_application(application_id)

    if telegram_id:
        try:
            await bot.send_message(
                telegram_id,
                f"🟡 Заявка №{application_id} снова в работе!\n\n"
                "Мы продолжили работу над твоей заявкой."
            )
        except Exception:
            pass

    await callback.answer(
        "Заявка возвращена в работу ↩️"
    )

    await application_details(callback)


# =========================
# Удаление заявки
# =========================

@router.callback_query(F.data.startswith("delete_"))
async def delete_application_handler(
    callback: CallbackQuery
):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "У тебя нет доступа 😎",
            show_alert=True
        )
        return

    application_id = int(
        callback.data.split("_")[1]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Да, удалить",
                    callback_data=f"confirm_delete_{application_id}"
                )
            ],
            [
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
        reply_markup=keyboard
    )

    await callback.answer()


# =========================
# Подтверждение удаления
# =========================

@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_application(
    callback: CallbackQuery
):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "У тебя нет доступа 😎",
            show_alert=True
        )
        return

    application_id = int(
        callback.data.split("_")[2]
    )

    delete_application(application_id)

    await callback.answer(
        "Заявка удалена ✅"
    )

    await applications(callback)