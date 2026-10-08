import calendar
from datetime import date

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from states import Application
from database import (
    save_application,
    get_user_application_stats,
    get_user_applications,
    cancel_application,
    get_available_schedule,
    get_available_schedule_by_date,
    get_schedule_slot,
    book_schedule_slot,
)

from keyboard import inline_keyboard, profile_keyboard


router = Router()


# =========================================================
# МЕСЯЦЫ
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
# START
# =========================================================

@router.message(F.text == "/start")
async def start(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Здесь ты можешь оставить заявку или посмотреть расписание.",
        reply_markup=inline_keyboard
    )


# =========================================================
# MY ID
# =========================================================

@router.message(F.text == "/myid")
async def my_id(message: Message):
    await message.answer(
        f"🆔 Твой Telegram ID:\n{message.from_user.id}"
    )


# =========================================================
# PROFILE
# =========================================================

@router.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    total, active, completed = get_user_application_stats(
        callback.from_user.id
    )

    await callback.message.edit_text(
        "👤 Профиль\n\n"
        f"📨 Всего заявок: {total}\n"
        f"🟢 Активных: {active}\n"
        f"✅ Выполненных: {completed}",
        reply_markup=profile_keyboard
    )

    await callback.answer()


# =========================================================
# BACK TO MAIN MENU
# =========================================================

@router.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=inline_keyboard
    )

    await callback.answer()


# =========================================================
# MY APPLICATIONS
# =========================================================

@router.callback_query(F.data == "my_applications")
async def my_applications(callback: CallbackQuery):
    applications = get_user_applications(
        callback.from_user.id
    )

    if not applications:
        await callback.message.edit_text(
            "📨 У тебя пока нет заявок.",
            reply_markup=profile_keyboard
        )
        await callback.answer()
        return

    text = "📨 Твои заявки:\n\n"

    for application in applications:
        application_id = application[0]
        task = application[1]
        status = application[-1]

        if status == "new":
            status_text = "🟢 Новая"
        elif status == "completed":
            status_text = "✅ Выполнена"
        else:
            status_text = "❌ Отменена"

        text += (
            f"#{application_id}\n"
            f"📌 {task}\n"
            f"{status_text}\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=profile_keyboard
    )

    await callback.answer()


# =========================================================
# CANCEL COMMAND
# =========================================================

@router.message(F.text == "/cancel")
async def cancel_command(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "❌ Текущее действие отменено.",
        reply_markup=ReplyKeyboardRemove()
    )


# =========================================================
# START APPLICATION
# =========================================================

@router.callback_query(F.data == "application")
async def start_application(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.clear()

    await state.set_state(Application.name)

    await callback.message.edit_text(
        "📝 Оформление заявки\n\n"
        "Как тебя зовут?"
    )

    await callback.answer()


# =========================================================
# APPLICATION — NAME
# =========================================================

@router.message(Application.name)
async def get_name(
    message: Message,
    state: FSMContext
):
    if not message.text:
        await message.answer(
            "❗ Пожалуйста, введи своё имя."
        )
        return

    name = message.text.strip()

    if not name:
        await message.answer(
            "❗ Пожалуйста, введи своё имя."
        )
        return

    await state.update_data(
        name=name
    )

    await state.set_state(
        Application.task
    )

    await message.answer(
        "📌 Опиши, что тебе нужно сделать."
    )


# =========================================================
# APPLICATION — TASK
# =========================================================

@router.message(Application.task)
async def get_task(
    message: Message,
    state: FSMContext
):
    if not message.text:
        await message.answer(
            "❗ Пожалуйста, опиши задачу."
        )
        return

    task = message.text.strip()

    if not task:
        await message.answer(
            "❗ Пожалуйста, опиши задачу."
        )
        return

    await state.update_data(
        task=task
    )

    await state.set_state(
        Application.date
    )

    today = date.today()

    await message.answer(
        "📅 Выбери удобную дату:",
        reply_markup=create_application_calendar(
            today.year,
            today.month
        )
    )


# =========================================================
# КАЛЕНДАРЬ ПРИ ОФОРМЛЕНИИ ЗАЯВКИ
# =========================================================

def create_application_calendar(
    year: int,
    month: int
):
    available_slots = get_available_schedule()

    available_dates = {
        slot[1]
        for slot in available_slots
    }

    keyboard = []

    keyboard.append([
        InlineKeyboardButton(
            text="◀️",
            callback_data=f"application_calendar_prev_{year}_{month}"
        ),
        InlineKeyboardButton(
            text=f"{MONTHS[month]} {year}",
            callback_data="application_calendar_ignore"
        ),
        InlineKeyboardButton(
            text="▶️",
            callback_data=f"application_calendar_next_{year}_{month}"
        )
    ])

    weekdays = [
        "Пн",
        "Вт",
        "Ср",
        "Чт",
        "Пт",
        "Сб",
        "Вс"
    ]

    keyboard.append([
        InlineKeyboardButton(
            text=day,
            callback_data="application_calendar_ignore"
        )
        for day in weekdays
    ])

    today = date.today()

    for week in calendar.monthcalendar(year, month):
        row = []

        for day in week:
            if day == 0:
                row.append(
                    InlineKeyboardButton(
                        text=" ",
                        callback_data="application_calendar_ignore"
                    )
                )
                continue

            selected_date = date(
                year,
                month,
                day
            )

            date_text = selected_date.strftime(
                "%d.%m.%Y"
            )

            if selected_date < today:
                button_text = "·"
                callback_data = "application_calendar_ignore"

            elif date_text not in available_dates:
                button_text = "·"
                callback_data = "application_calendar_ignore"

            else:
                button_text = str(day)
                callback_data = (
                    f"application_calendar_date_"
                    f"{year}_{month}_{day}"
                )

            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=callback_data
                )
            )

        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            text="📅 Сегодня",
            callback_data=(
                f"application_calendar_today_"
                f"{today.year}_{today.month}"
            )
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="application_cancel"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


# =========================================================
# КАЛЕНДАРЬ ЗАЯВКИ — НАЗАД
# =========================================================

@router.callback_query(
    F.data.startswith("application_calendar_prev_")
)
async def application_calendar_previous(
    callback: CallbackQuery,
    state: FSMContext
):
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
        reply_markup=create_application_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# КАЛЕНДАРЬ ЗАЯВКИ — ВПЕРЁД
# =========================================================

@router.callback_query(
    F.data.startswith("application_calendar_next_")
)
async def application_calendar_next(
    callback: CallbackQuery,
    state: FSMContext
):
    year, month = map(
        int,
        callback.data.split("_")[-2:]
    )

    month += 1

    if month == 13:
        month = 1
        year += 1

    await callback.message.edit_reply_markup(
        reply_markup=create_application_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# КАЛЕНДАРЬ ЗАЯВКИ — СЕГОДНЯ
# =========================================================

@router.callback_query(
    F.data.startswith("application_calendar_today_")
)
async def application_calendar_today(
    callback: CallbackQuery,
    state: FSMContext
):
    today = date.today()

    await callback.message.edit_reply_markup(
        reply_markup=create_application_calendar(
            today.year,
            today.month
        )
    )

    await callback.answer()


# =========================================================
# КАЛЕНДАРЬ ЗАЯВКИ — ИГНОРИРОВАТЬ
# =========================================================

@router.callback_query(
    F.data == "application_calendar_ignore"
)
async def application_calendar_ignore(
    callback: CallbackQuery
):
    await callback.answer()


# =========================================================
# КАЛЕНДАРЬ ЗАЯВКИ — ВЫБОР ДАТЫ
# =========================================================

@router.callback_query(
    F.data.startswith("application_calendar_date_")
)
async def application_calendar_select_date(
    callback: CallbackQuery,
    state: FSMContext
):
    parts = callback.data.split("_")

    year = int(parts[-3])
    month = int(parts[-2])
    day = int(parts[-1])

    selected_date = date(
        year,
        month,
        day
    )

    if selected_date < date.today():
        await callback.answer(
            "❌ Эта дата уже прошла.",
            show_alert=True
        )
        return

    date_text = selected_date.strftime(
        "%d.%m.%Y"
    )

    available_slots = get_available_schedule_by_date(
        date_text
    )

    if not available_slots:
        await callback.answer(
            "❌ На эту дату больше нет свободного времени.",
            show_alert=True
        )

        await callback.message.edit_reply_markup(
            reply_markup=create_application_calendar(
                year,
                month
            )
        )

        return

    await state.update_data(
        date=date_text
    )

    buttons = []

    for slot in available_slots:
        slot_id = slot[0]
        slot_time = slot[2]

        buttons.append([
            InlineKeyboardButton(
                text=f"🟢 {slot_time}",
                callback_data=f"application_time:{slot_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад к календарю",
            callback_data=(
                f"application_back_to_calendar_"
                f"{year}_{month}"
            )
        )
    ])

    await callback.message.edit_text(
        f"📅 Дата: {date_text}\n\n"
        "🕐 Выбери свободное время:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


# =========================================================
# ВЕРНУТЬСЯ К КАЛЕНДАРЮ ПРИ ЗАЯВКЕ
# =========================================================

@router.callback_query(
    F.data.startswith("application_back_to_calendar_")
)
async def application_back_to_calendar(
    callback: CallbackQuery,
    state: FSMContext
):
    parts = callback.data.split("_")

    year = int(parts[-2])
    month = int(parts[-1])

    await state.set_state(
        Application.date
    )

    await callback.message.edit_text(
        "📅 Выбери удобную дату:",
        reply_markup=create_application_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# ОТМЕНА ОФОРМЛЕНИЯ ЗАЯВКИ
# =========================================================

@router.callback_query(F.data == "application_cancel")
async def application_cancel(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.clear()

    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=inline_keyboard
    )

    await callback.answer()


# =========================================================
# APPLICATION — TIME
# =========================================================

@router.callback_query(
    F.data.startswith("application_time:")
)
async def application_select_time(
    callback: CallbackQuery,
    state: FSMContext
):
    slot_id = int(
        callback.data.split(":", 1)[1]
    )

    slot = get_schedule_slot(
        slot_id
    )

    if not slot:
        await callback.answer(
            "❌ Это время больше недоступно.",
            show_alert=True
        )
        return

    if slot[3] != "available":
        await callback.answer(
            "❌ Это время уже заняли.",
            show_alert=True
        )
        return

    await state.update_data(
        time=slot[2],
        schedule_id=slot_id
    )

    await state.set_state(
        Application.phone
    )

    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Отправить контакт",
                    request_contact=True
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.edit_text(
        f"📅 Дата: {slot[1]}\n"
        f"🕐 Время: {slot[2]}\n\n"
        "📱 Отправь свой номер телефона."
    )

    await callback.message.answer(
        "Нажми кнопку, чтобы отправить контакт:",
        reply_markup=contact_keyboard
    )

    await callback.answer()


# =========================================================
# APPLICATION — PHONE
# =========================================================

@router.message(Application.phone)
async def get_phone(
    message: Message,
    state: FSMContext
):
    phone = None

    if message.contact:
        phone = message.contact.phone_number

    elif message.text:
        phone = message.text.strip()

    if not phone:
        await message.answer(
            "❗ Пожалуйста, отправь контакт кнопкой ниже "
            "или введи номер телефона вручную."
        )
        return

    data = await state.get_data()

    name = data.get("name")
    task = data.get("task")
    selected_date = data.get("date")
    selected_time = data.get("time")
    schedule_id = data.get("schedule_id")

    telegram_id = message.from_user.id

    if not schedule_id:
        await message.answer(
            "❌ Не удалось определить выбранное время.\n"
            "Попробуй оформить заявку заново.",
            reply_markup=ReplyKeyboardRemove()
        )

        await state.clear()
        return

    booked = book_schedule_slot(
        schedule_id,
        telegram_id
    )

    if not booked:
        await message.answer(
            "❌ К сожалению, это время только что заняли.\n\n"
            "Пожалуйста, выбери другое время.",
            reply_markup=ReplyKeyboardRemove()
        )

        await state.clear()
        return

    application_id = save_application(
        name,
        task,
        selected_date,
        selected_time,
        phone,
        telegram_id
    )

    from config import ADMIN_ID

    bot = message.bot

    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👀 Посмотреть заявку",
                    callback_data=f"application_{application_id}"
                )
            ]
        ]
    )

    await bot.send_message(
        ADMIN_ID,
        "📨 Новая заявка!\n\n"
        f"🆔 Заявка №{application_id}\n"
        f"👤 Имя: {name}\n"
        f"📌 Задача: {task}\n"
        f"📅 Дата: {selected_date}\n"
        f"🕐 Время: {selected_time}\n"
        f"📱 Телефон: {phone}",
        reply_markup=admin_keyboard
    )

    await message.answer(
        "✅ Заявка успешно оформлена!\n\n"
        f"📅 Дата: {selected_date}\n"
        f"🕐 Время: {selected_time}",
        reply_markup=ReplyKeyboardRemove()
    )

    await state.clear()


# =========================================================
# ПОЛЬЗОВАТЕЛЬСКОЕ РАСПИСАНИЕ
# =========================================================

def create_user_schedule_calendar(
    year: int,
    month: int
):
    available_slots = get_available_schedule()

    available_dates = {
        slot[1]
        for slot in available_slots
    }

    keyboard = []

    keyboard.append([
        InlineKeyboardButton(
            text="◀️",
            callback_data=f"user_calendar_prev_{year}_{month}"
        ),
        InlineKeyboardButton(
            text=f"{MONTHS[month]} {year}",
            callback_data="user_calendar_ignore"
        ),
        InlineKeyboardButton(
            text="▶️",
            callback_data=f"user_calendar_next_{year}_{month}"
        )
    ])

    weekdays = [
        "Пн",
        "Вт",
        "Ср",
        "Чт",
        "Пт",
        "Сб",
        "Вс"
    ]

    keyboard.append([
        InlineKeyboardButton(
            text=day,
            callback_data="user_calendar_ignore"
        )
        for day in weekdays
    ])

    today = date.today()

    for week in calendar.monthcalendar(year, month):
        row = []

        for day in week:
            if day == 0:
                row.append(
                    InlineKeyboardButton(
                        text=" ",
                        callback_data="user_calendar_ignore"
                    )
                )
                continue

            selected_date = date(
                year,
                month,
                day
            )

            date_text = selected_date.strftime(
                "%d.%m.%Y"
            )

            if selected_date < today:
                button_text = "·"
                callback_data = "user_calendar_ignore"

            elif date_text not in available_dates:
                button_text = "·"
                callback_data = "user_calendar_ignore"

            else:
                button_text = str(day)
                callback_data = (
                    f"user_calendar_date_"
                    f"{year}_{month}_{day}"
                )

            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=callback_data
                )
            )

        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            text="📅 Сегодня",
            callback_data=(
                f"user_calendar_today_"
                f"{today.year}_{today.month}"
            )
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


# =========================================================
# USER SCHEDULE
# =========================================================

@router.callback_query(F.data == "user_schedule")
async def user_schedule(
    callback: CallbackQuery
):
    available_slots = get_available_schedule()

    if not available_slots:
        await callback.message.edit_text(
            "😔 Сейчас нет свободных записей.\n\n"
            "Попробуй зайти позже.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Назад",
                            callback_data="back"
                        )
                    ]
                ]
            )
        )

        await callback.answer()
        return

    today = date.today()

    await callback.message.edit_text(
        "📅 Свободное расписание\n\n"
        "Выбери дату:",
        reply_markup=create_user_schedule_calendar(
            today.year,
            today.month
        )
    )

    await callback.answer()


# =========================================================
# USER CALENDAR — НАЗАД
# =========================================================

@router.callback_query(
    F.data.startswith("user_calendar_prev_")
)
async def user_calendar_previous(
    callback: CallbackQuery
):
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
        reply_markup=create_user_schedule_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# USER CALENDAR — ВПЕРЁД
# =========================================================

@router.callback_query(
    F.data.startswith("user_calendar_next_")
)
async def user_calendar_next(
    callback: CallbackQuery
):
    year, month = map(
        int,
        callback.data.split("_")[-2:]
    )

    month += 1

    if month == 13:
        month = 1
        year += 1

    await callback.message.edit_reply_markup(
        reply_markup=create_user_schedule_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# USER CALENDAR — СЕГОДНЯ
# =========================================================

@router.callback_query(
    F.data.startswith("user_calendar_today_")
)
async def user_calendar_today(
    callback: CallbackQuery
):
    today = date.today()

    await callback.message.edit_reply_markup(
        reply_markup=create_user_schedule_calendar(
            today.year,
            today.month
        )
    )

    await callback.answer()


# =========================================================
# USER CALENDAR — ИГНОРИРОВАТЬ
# =========================================================

@router.callback_query(
    F.data == "user_calendar_ignore"
)
async def user_calendar_ignore(
    callback: CallbackQuery
):
    await callback.answer()


# =========================================================
# USER CALENDAR — ВЫБОР ДАТЫ
# =========================================================

@router.callback_query(
    F.data.startswith("user_calendar_date_")
)
async def user_calendar_select_date(
    callback: CallbackQuery
):
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

    available_slots = get_available_schedule_by_date(
        date_text
    )

    if not available_slots:
        await callback.answer(
            "❌ На эту дату больше нет свободного времени.",
            show_alert=True
        )
        return

    buttons = []

    for slot in available_slots:
        slot_id = slot[0]
        slot_time = slot[2]

        buttons.append([
            InlineKeyboardButton(
                text=f"🟢 {slot_time}",
                callback_data=f"user_time:{slot_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад к календарю",
            callback_data=(
                f"user_back_to_calendar_"
                f"{year}_{month}"
            )
        )
    ])

    await callback.message.edit_text(
        f"📅 {date_text}\n\n"
        "🟢 Свободное время:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


# =========================================================
# USER SCHEDULE — НАЗАД К КАЛЕНДАРЮ
# =========================================================

@router.callback_query(
    F.data.startswith("user_back_to_calendar_")
)
async def user_back_to_calendar(
    callback: CallbackQuery
):
    year, month = map(
        int,
        callback.data.split("_")[-2:]
    )

    await callback.message.edit_text(
        "📅 Свободное расписание\n\n"
        "Выбери дату:",
        reply_markup=create_user_schedule_calendar(
            year,
            month
        )
    )

    await callback.answer()


# =========================================================
# USER SCHEDULE — TIME
# =========================================================

@router.callback_query(
    F.data.startswith("user_time:")
)
async def user_select_time(
    callback: CallbackQuery
):
    slot_id = int(
        callback.data.split(":", 1)[1]
    )

    slot = get_schedule_slot(
        slot_id
    )

    if not slot:
        await callback.answer(
            "❌ Время не найдено.",
            show_alert=True
        )
        return

    if slot[3] != "available":
        await callback.answer(
            "🔴 Это время уже занято.",
            show_alert=True
        )
        return

    await callback.answer(
        f"🟢 {slot[1]} в {slot[2]} свободно."
    )