from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


# =========================================================
# ADMIN KEYBOARD
# =========================================================

admin_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📨 Заявки",
                callback_data="applications"
            )
        ],
        [
            InlineKeyboardButton(
                text="📅 Расписание",
                callback_data="schedule"
            )
        ]
    ]
)


# =========================================================
# PROFILE KEYBOARD
# =========================================================

profile_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📨 Мои заявки",
                callback_data="my_applications"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back"
            )
        ]
    ]
)


# =========================================================
# USER MAIN KEYBOARD
# =========================================================

inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👤 Профиль",
                callback_data="profile"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Оставить заявку",
                callback_data="application"
            )
        ],
        [
            InlineKeyboardButton(
                text="📅 Расписание",
                callback_data="user_schedule"
            )
        ]
    ]
)


# =========================================================
# PHONE KEYBOARD
# =========================================================

phone_keyboard = ReplyKeyboardMarkup(
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