from aiogram.fsm.state import State, StatesGroup


class Application(StatesGroup):
    name = State()
    task = State()
    date = State()
    time = State()
    phone = State()


class Schedule(StatesGroup):
    date = State()
    time = State()