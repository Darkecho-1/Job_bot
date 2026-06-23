from aiogram.fsm.state import StatesGroup, State

class WorkerRegistration(StatesGroup):
    waiting_contact = State()
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_patronymic = State()
    waiting_birth_date = State()
    waiting_location = State()
    waiting_work_type = State()

class EmployerRegistration(StatesGroup):
    waiting_contact = State()
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_patronymic = State()
    waiting_birth_date = State()