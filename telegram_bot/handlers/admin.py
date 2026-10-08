import calendar
from datetime import date, datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_ID
from database import (
    add_schedule_slot,
    complete_application,
    delete_application,
    delete_schedule_slot,
    get_application,
    get_applications,
    get_schedule_by_date,
    get_schedule_slot,
    release_schedule_slot,
    reopen_application,
)
from keyboard import admin_keyboard
from states import Schedule


router = Router()


# =========================================================
# MONTHS
# =========================================================

MONTHS = [
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь"
]


# =========================================================
# START ДЛЯ АДМИНА
# =========================================================

@router.message(
    F.text == "/start",
    F.from_user.id == ADMIN_ID
)
async def admin_start(message: Message):
    await message.answer(
        "⚙️ Админ-панель\n\n"
        "Ты вошёл как администратор.",
        reply_markup=admin_keyboard
    )


# =========================================================
# ПРОВЕРКА АДМИНА
# =========================================================

async def check_admin(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "У тебя нет доступа 😎",
            show_alert=True
        )
        return False

    return True


# =========================================================
# НАЗАД В АДМИН-ПАНЕЛЬ
# =========================================================

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not await check_admin(callback):
        return

    await callback.message.edit_text(
        "⚙️ Админ-панель\n\n"
        "Выбери действие:",
        reply_markup=admin_keyboard
    )

    await callback.answer()


# =========================================================
# ЗАЯВКИ
# =========================================================

@router.callback_query(F.data == "applications")
async def applications(callback: CallbackQuery):
    if not await check_admin(callback):
        return

    apps = get_applications()

    if not apps:
        await callback.message.edit_text(
            "📨 Заявки\n\n"
            "Пока заявок нет.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Назад",
                            callback_data="admin_back"
                        )
                    ]
                ]
            )
        )

        await callback.answer()
        return

    buttons = []

    for app in apps:
        application_id = app[0]
        name = app[1]
        status = app[4]

        if status == "completed":
            status_text = "🟢"
        elif status == "cancelled":
            status_text = "🔴"
        else:
            status_text = "🟡"

        buttons.append([
            InlineKeyboardButton(
                text=f"{status_text} Заявка №{application_id} — {name}",
                callback_data=f"application_{application_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="admin_back"
        )
    ])

    await callback.message.edit_text(
        "📨 Заявки",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


# =========================================================
# ИНФОРМАЦИЯ О ЗАЯВКЕ
# =========================================================

@router.callback_query(F.data.regexp(r"^application_\d+$"))
async def application_details(callback: CallbackQuery):
    if not await check_admin(callback):
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

    (
        application_id,
        name,
        task,
        application_date,
        application_time,
        phone,
        status,
        telegram_id
    ) = app

    if status == "completed":
        status_text = "🟢 Выполнена"

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

    buttons = [
        [
            action_button
        ],
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

    text = (
        f"📨 Заявка №{application_id}\n\n"
        f"👤 Имя: {name}\n"
        f"📝 Задача: {task}\n"
        f"📅 Дата: {application_date or 'не выбрана'}\n"
        f"🕐 Время: {application_time or 'не выбрано'}\n"
        f"📞 Телефон: {phone}\n\n"
        f"📌 Статус: {status_text}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


# =========================================================
# ВЫПОЛНИТЬ ЗАЯВКУ
# =========================================================

@router.callback_query(F.data.startswith("complete_"))
async def complete_application_handler(
    callback: CallbackQuery,
    bot: Bot
):
    if not await check_admin(callback):
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

    telegram_id = app[7]

    complete_application(application_id)

    if telegram_id:
        try:
            await bot.send_message(
                telegram_id,
                f"✅ Заявка №{application_id} выполнена!\n\n"
                "Спасибо за обращение."
            )
        except Exception:
            pass

    await callback.answer(
        "Заявка выполнена ✅"
    )

    await application_details(callback)


# =========================================================
# ВЕРНУТЬ ЗАЯВКУ
# =========================================================

@router.callback_query(F.data.startswith("reopen_"))
async def reopen_application_handler(
    callback: CallbackQuery,
    bot: Bot
):
    if not await check_admin(callback):
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

    telegram_id = app[7]

    reopen_application(application_id)

    if telegram_id:
        try:
            await bot.send_message(
                telegram_id,
                f"🟡 Заявка №{application_id} снова в работе!"
            )
        except Exception:
            pass

    await callback.answer(
        "Заявка возвращена в работу ↩️"
    )

    await application_details(callback)


# =========================================================
# УДАЛЕНИЕ ЗАЯВКИ
# =========================================================

@router.callback_query(F.data.regexp(r"^delete_\d+$"))
async def delete_application_handler(
    callback: CallbackQuery
):
    if not await check_admin(callback):
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


# =========================================================
# ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ ЗАЯВКИ
# =========================================================

@router.callback_query(
    F.data.regexp(r"^confirm_delete_\d+$")
)
async def confirm_delete_application(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    application_id = int(
        callback.data.split("_")[2]
    )

    delete_application(application_id)

    await callback.answer(
        "Заявка удалена ✅"
    )

    await applications(callback)


# =========================================================
# РАСПИСАНИЕ
# =========================================================

@router.callback_query(F.data == "schedule")
async def schedule(callback: CallbackQuery):
    if not await check_admin(callback):
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить время",
                    callback_data="schedule_add"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Посмотреть расписание",
                    callback_data="schedule_view"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="admin_back"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "📅 Расписание\n\n"
        "Что хочешь сделать?",
        reply_markup=keyboard
    )

    await callback.answer()


# =========================================================
# ДОБАВЛЕНИЕ В РАСПИСАНИЕ
# =========================================================

@router.callback_query(F.data == "schedule_add")
async def schedule_add(
    callback: CallbackQuery,
    state: FSMContext
):
    if not await check_admin(callback):
        return

    await state.set_state(Schedule.date)

    today = date.today()

    await callback.message.edit_text(
        "📅 Выбери дату:",
        reply_markup=create_calendar(
            today.year,
            today.month
        )
    )

    await callback.answer()


# =========================================================
# КАЛЕНДАРЬ ДОБАВЛЕНИЯ
# =========================================================

def create_calendar(year: int, month: int):
    keyboard = []

    keyboard.append([
        InlineKeyboardButton(
            text="◀️",
            callback_data=f"calendar_prev_{year}_{month}"
        ),
        InlineKeyboardButton(
            text=f"{MONTHS[month]} {year}",
            callback_data="calendar_ignore"
        ),
        InlineKeyboardButton(
            text="▶️",
            callback_data=f"calendar_next_{year}_{month}"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text=day,
            callback_data="calendar_ignore"
        )
        for day in [
            "Пн",
            "Вт",
            "Ср",
            "Чт",
            "Пт",
            "Сб",
            "Вс"
        ]
    ])

    today = date.today()

    for week in calendar.monthcalendar(year, month):
        row = []

        for day in week:
            if day == 0:
                row.append(
                    InlineKeyboardButton(
                        text=" ",
                        callback_data="calendar_ignore"
                    )
                )
                continue

            selected_date = date(
                year,
                month,
                day
            )

            if selected_date < today:
                text = "·"
                callback = "calendar_ignore"
            else:
                text = str(day)
                callback = (
                    f"calendar_date_{year}_{month}_{day}"
                )

            row.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=callback
                )
            )

        keyboard.append(row)

    # Кнопку "Сегодня" специально не добавляем.
    # Текущий месяц и так открывается автоматически.

    keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="schedule"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


# =========================================================
# КАЛЕНДАРЬ — НАЗАД
# =========================================================

@router.callback_query(F.data.startswith("calendar_prev_"))
async def calendar_previous(
    callback: CallbackQuery,
    state: FSMContext
):
    if not await check_admin(callback):
        return

    _, _, year, month = callback.data.split("_")

    year = int(year)
    month = int(month)

    month -= 1

    today = date.today()

    if month == 0:
        month = 12
        year -= 1

    if (year, month) < (today.year, today.month):
        year = today.year
        month = today.month

    await callback.message.edit_reply_markup(
        reply_markup=create_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# КАЛЕНДАРЬ — ВПЕРЁД
# =========================================================

@router.callback_query(F.data.startswith("calendar_next_"))
async def calendar_next(
    callback: CallbackQuery,
    state: FSMContext
):
    if not await check_admin(callback):
        return

    _, _, year, month = callback.data.split("_")

    year = int(year)
    month = int(month)

    month += 1

    if month == 13:
        month = 1
        year += 1

    await callback.message.edit_reply_markup(
        reply_markup=create_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# КАЛЕНДАРЬ — СЕГОДНЯ
#
# Оставляем обработчик для совместимости со старыми
# сообщениями Telegram, но новые календари эту кнопку
# больше не создают.
# =========================================================

@router.callback_query(F.data.startswith("calendar_today_"))
async def calendar_today(
    callback: CallbackQuery,
    state: FSMContext
):
    if not await check_admin(callback):
        return

    today = date.today()

    await callback.message.edit_reply_markup(
        reply_markup=create_calendar(
            today.year,
            today.month
        )
    )

    await callback.answer()


# =========================================================
# ВЫБОР ДАТЫ ДЛЯ ДОБАВЛЕНИЯ
# =========================================================

@router.callback_query(F.data.startswith("calendar_date_"))
async def calendar_select_date(
    callback: CallbackQuery,
    state: FSMContext
):
    if not await check_admin(callback):
        return

    _, _, year, month, day = callback.data.split("_")

    selected_date = date(
        int(year),
        int(month),
        int(day)
    )

    if selected_date < date.today():
        await callback.answer(
            "Эта дата уже прошла.",
            show_alert=True
        )
        return

    await state.update_data(
        date=selected_date.strftime("%d.%m.%Y")
    )

    await state.set_state(
        Schedule.time
    )

    await callback.message.edit_text(
        f"📅 Дата: {selected_date.strftime('%d.%m.%Y')}\n\n"
        "🕐 Введи время в формате HH:MM.\n\n"
        "Например: 15:30"
    )

    await callback.answer()


# =========================================================
# ИГНОРИРОВАТЬ
# =========================================================

@router.callback_query(F.data == "calendar_ignore")
async def calendar_ignore(callback: CallbackQuery):
    await callback.answer()


# =========================================================
# СОХРАНЕНИЕ ВРЕМЕНИ
# =========================================================

@router.message(Schedule.time)
async def schedule_time(
    message: Message,
    state: FSMContext
):
    if message.from_user.id != ADMIN_ID:
        return

    if not message.text:
        await message.answer(
            "❌ Введи время текстом.\n\n"
            "Например: 15:30"
        )
        return

    try:
        selected_time = datetime.strptime(
            message.text.strip(),
            "%H:%M"
        ).strftime("%H:%M")

    except ValueError:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Введи время так: 15:30"
        )
        return

    data = await state.get_data()
    selected_date = data.get("date")

    if not selected_date:
        await state.clear()

        await message.answer(
            "❌ Не удалось определить дату.\n\n"
            "Попробуй ещё раз."
        )
        return

    slot_id = add_schedule_slot(
        selected_date,
        selected_time
    )

    if not slot_id:
        await message.answer(
            "❌ Такое время на эту дату уже существует.\n\n"
            "Выбери другую дату или время."
        )
        return

    await state.clear()

    await message.answer(
        "✅ Время добавлено!\n\n"
        f"📅 {selected_date}\n"
        f"🕐 {selected_time}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Добавить ещё",
                        callback_data="schedule_add"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Посмотреть расписание",
                        callback_data="schedule_view"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ В расписание",
                        callback_data="schedule"
                    )
                ]
            ]
        )
    )


# =========================================================
# ПРОСМОТР РАСПИСАНИЯ — КАЛЕНДАРЬ
# =========================================================

@router.callback_query(F.data == "schedule_view")
async def schedule_view(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    today = date.today()

    await callback.message.edit_text(
        "📋 Расписание\n\n"
        "Выбери дату:",
        reply_markup=create_schedule_view_calendar(
            today.year,
            today.month
        )
    )

    await callback.answer()


# =========================================================
# КАЛЕНДАРЬ ПРОСМОТРА
# =========================================================

def create_schedule_view_calendar(
    year: int,
    month: int
):
    keyboard = []

    keyboard.append([
        InlineKeyboardButton(
            text="◀️",
            callback_data=f"schedule_view_prev_{year}_{month}"
        ),
        InlineKeyboardButton(
            text=f"{MONTHS[month]} {year}",
            callback_data="schedule_view_ignore"
        ),
        InlineKeyboardButton(
            text="▶️",
            callback_data=f"schedule_view_next_{year}_{month}"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text=day,
            callback_data="schedule_view_ignore"
        )
        for day in [
            "Пн",
            "Вт",
            "Ср",
            "Чт",
            "Пт",
            "Сб",
            "Вс"
        ]
    ])

    today = date.today()

    for week in calendar.monthcalendar(year, month):
        row = []

        for day in week:
            if day == 0:
                row.append(
                    InlineKeyboardButton(
                        text=" ",
                        callback_data="schedule_view_ignore"
                    )
                )
                continue

            selected_date = date(
                year,
                month,
                day
            )

            if selected_date < today:
                text = "·"
                callback = "schedule_view_ignore"
            else:
                text = str(day)
                callback = (
                    f"schedule_view_date_"
                    f"{year}_{month}_{day}"
                )

            row.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=callback
                )
            )

        keyboard.append(row)

    # Кнопку "Сегодня" специально не добавляем.

    keyboard.append([
        InlineKeyboardButton(
            text="➕ Добавить время",
            callback_data="schedule_add"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="schedule"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


# =========================================================
# ПРОСМОТР — НАЗАД
# =========================================================

@router.callback_query(F.data.startswith("schedule_view_prev_"))
async def schedule_view_previous(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    year, month = map(
        int,
        callback.data.split("_")[-2:]
    )

    month -= 1

    today = date.today()

    if month == 0:
        month = 12
        year -= 1

    if (year, month) < (today.year, today.month):
        year = today.year
        month = today.month

    await callback.message.edit_reply_markup(
        reply_markup=create_schedule_view_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# ПРОСМОТР — ВПЕРЁД
# =========================================================

@router.callback_query(F.data.startswith("schedule_view_next_"))
async def schedule_view_next(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    year, month = map(
        int,
        callback.data.split("_")[-2:]
    )

    month += 1

    if month == 13:
        month = 1
        year += 1

    await callback.message.edit_reply_markup(
        reply_markup=create_schedule_view_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# ПРОСМОТР — СЕГОДНЯ
#
# Оставляем обработчик для старых сообщений Telegram.
# Новые календари эту кнопку больше не создают.
# =========================================================

@router.callback_query(F.data.startswith("schedule_view_today_"))
async def schedule_view_today(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    today = date.today()

    await callback.message.edit_reply_markup(
        reply_markup=create_schedule_view_calendar(
            today.year,
            today.month
        )
    )

    await callback.answer()


# =========================================================
# ПРОСМОТР — ИГНОРИРОВАТЬ
# =========================================================

@router.callback_query(F.data == "schedule_view_ignore")
async def schedule_view_ignore(
    callback: CallbackQuery
):
    await callback.answer()


# =========================================================
# ПРОСМОТР — ВЫБОР ДАТЫ
# =========================================================

@router.callback_query(F.data.startswith("schedule_view_date_"))
async def schedule_view_date(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    parts = callback.data.split("_")

    year = int(parts[-3])
    month = int(parts[-2])
    day = int(parts[-1])

    selected_date = date(
        year,
        month,
        day
    )

    date_text = selected_date.strftime(
        "%d.%m.%Y"
    )

    slots = get_schedule_by_date(
        date_text
    )

    if not slots:
        buttons = [
            [
                InlineKeyboardButton(
                    text="➕ Добавить время",
                    callback_data="schedule_add"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К календарю",
                    callback_data=(
                        f"schedule_view_back_"
                        f"{year}_{month}"
                    )
                )
            ]
        ]

        await callback.message.edit_text(
            f"📅 {date_text}\n\n"
            "На эту дату пока нет времени.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=buttons
            )
        )

        await callback.answer()
        return

    buttons = []

    for slot in slots:
        slot_id = slot[0]
        slot_time = slot[2]
        status = slot[3]

        if status == "booked":
            status_text = "🔴"
        else:
            status_text = "🟢"

        buttons.append([
            InlineKeyboardButton(
                text=f"{status_text} {slot_time}",
                callback_data=f"schedule_slot_{slot_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="➕ Добавить время",
            callback_data="schedule_add"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ К календарю",
            callback_data=(
                f"schedule_view_back_"
                f"{year}_{month}"
            )
        )
    ])

    await callback.message.edit_text(
        f"📅 {date_text}\n\n"
        "🟢 — свободно\n"
        "🔴 — занято",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


# =========================================================
# ВОЗВРАТ К КАЛЕНДАРЮ ПРОСМОТРА
# =========================================================

@router.callback_query(
    F.data.startswith("schedule_view_back_")
)
async def schedule_view_back(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    parts = callback.data.split("_")

    try:
        # НОВЫЙ ФОРМАТ:
        # schedule_view_back_2026_10
        if (
            len(parts) >= 5
            and parts[-2].isdigit()
            and parts[-1].isdigit()
        ):
            year = int(parts[-2])
            month = int(parts[-1])

        # СТАРЫЙ ФОРМАТ:
        # schedule_view_back_date_08.10.2026
        elif (
            len(parts) >= 5
            and parts[-2] == "date"
        ):
            slot_date = parts[-1]

            selected_date = datetime.strptime(
                slot_date,
                "%d.%m.%Y"
            ).date()

            year = selected_date.year
            month = selected_date.month

        else:
            await callback.answer(
                "Не удалось определить дату.",
                show_alert=True
            )
            return

    except (ValueError, IndexError):
        await callback.answer(
            "Ошибка при обработке даты.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "📋 Расписание\n\n"
        "Выбери дату:",
        reply_markup=create_schedule_view_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# ИНФОРМАЦИЯ О СЛОТЕ
# =========================================================

@router.callback_query(F.data.startswith("schedule_slot_"))
async def schedule_slot_details(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    slot_id = int(
        callback.data.split("_")[2]
    )

    slot = get_schedule_slot(slot_id)

    if not slot:
        await callback.answer(
            "Слот не найден.",
            show_alert=True
        )
        return

    (
        slot_id,
        slot_date,
        slot_time,
        status,
        telegram_id
    ) = slot

    if status == "booked":
        status_text = "🔴 Занято"
    else:
        status_text = "🟢 Свободно"

    buttons = []

    if status == "booked":
        buttons.append([
            InlineKeyboardButton(
                text="🟢 Освободить",
                callback_data=f"release_slot_{slot_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"delete_slot_{slot_id}"
        )
    ])

    try:
        slot_date_object = datetime.strptime(
            slot_date,
            "%d.%m.%Y"
        ).date()

        back_callback = (
            f"schedule_view_date_"
            f"{slot_date_object.year}_"
            f"{slot_date_object.month}_"
            f"{slot_date_object.day}"
        )

    except ValueError:
        back_callback = "schedule_view"

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=back_callback
        )
    ])

    text = (
        "📅 Информация о времени\n\n"
        f"Дата: {slot_date}\n"
        f"Время: {slot_time}\n"
        f"Статус: {status_text}"
    )

    if telegram_id:
        text += f"\n👤 Telegram ID: {telegram_id}"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


# =========================================================
# ОСВОБОДИТЬ СЛОТ
# =========================================================

@router.callback_query(F.data.startswith("release_slot_"))
async def release_slot(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    slot_id = int(
        callback.data.split("_")[2]
    )

    slot = get_schedule_slot(slot_id)

    if not slot:
        await callback.answer(
            "Слот уже удалён.",
            show_alert=True
        )
        return

    release_schedule_slot(slot_id)

    await callback.answer(
        "Время снова свободно 🟢"
    )

    await schedule_slot_details(callback)


# =========================================================
# УДАЛЕНИЕ СЛОТА — ПОДТВЕРЖДЕНИЕ
# =========================================================

@router.callback_query(F.data.startswith("delete_slot_"))
async def delete_slot(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    slot_id = int(
        callback.data.split("_")[2]
    )

    slot = get_schedule_slot(slot_id)

    if not slot:
        await callback.answer(
            "Слот уже удалён.",
            show_alert=True
        )
        return

    # Нельзя удалять занятое время, пока оно связано
    # с заявкой пользователя.
    if slot[3] == "booked":
        await callback.answer(
            "Сначала освободи это время.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "⚠️ Удалить это время?\n\n"
        f"📅 {slot[1]}\n"
        f"🕐 {slot[2]}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🗑 Да, удалить",
                        callback_data=f"confirm_delete_slot_{slot_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отмена",
                        callback_data=f"schedule_slot_{slot_id}"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# =========================================================
# ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ СЛОТА
# =========================================================

@router.callback_query(
    F.data.startswith("confirm_delete_slot_")
)
async def confirm_delete_slot(
    callback: CallbackQuery
):
    if not await check_admin(callback):
        return

    slot_id = int(
        callback.data.split("_")[3]
    )

    # Получаем слот ДО удаления, чтобы после удаления
    # знать, на какую дату вернуть администратора.
    slot = get_schedule_slot(slot_id)

    if not slot:
        await callback.answer(
            "Это время уже удалено.",
            show_alert=True
        )
        return

    slot_date = slot[1]

    try:
        slot_date_object = datetime.strptime(
            slot_date,
            "%d.%m.%Y"
        ).date()

    except ValueError:
        await callback.answer(
            "Ошибка в дате слота.",
            show_alert=True
        )
        return

    delete_schedule_slot(slot_id)

    # Проверяем БД после удаления.
    deleted_slot = get_schedule_slot(slot_id)

    if deleted_slot:
        await callback.answer(
            "Не удалось удалить время.",
            show_alert=True
        )
        return

    await callback.answer(
        "Время удалено 🗑"
    )

    # Возвращаемся не в общий календарь, а сразу
    # на ту же дату и показываем актуальный список времени.
    date_text = slot_date_object.strftime("%d.%m.%Y")

    slots = get_schedule_by_date(date_text)

    if not slots:
        await callback.message.edit_text(
            f"📅 {date_text}\n\nНа эту дату больше нет времени.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Добавить время",
                            callback_data="schedule_add"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ К календарю",
                            callback_data=(
                                f"schedule_view_back_"
                                f"{slot_date_object.year}_"
                                f"{slot_date_object.month}"
                            )
                        )
                    ]
                ]
            )
        )
        return

    buttons = []

    for current_slot in slots:
        current_slot_id = current_slot[0]
        current_slot_time = current_slot[2]
        current_status = current_slot[3]

        if current_status == "booked":
            status_text = "🔴"
        else:
            status_text = "🟢"

        buttons.append([
            InlineKeyboardButton(
                text=f"{status_text} {current_slot_time}",
                callback_data=f"schedule_slot_{current_slot_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="➕ Добавить время",
            callback_data="schedule_add"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ К календарю",
            callback_data=(
                f"schedule_view_back_"
                f"{slot_date_object.year}_"
                f"{slot_date_object.month}"
            )
        )
    ])

    await callback.message.edit_text(
        f"📅 {date_text}\n\n"
        "🟢 — свободно\n"
        "🔴 — занято",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )