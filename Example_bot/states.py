from aiogram.fsm.state import State, StatesGroup


class Application(StatesGroup):
    name = State()
    task = State()
    phone = State()