from aiogram.fsm.state import StatesGroup, State

class CreateVacancy(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_work_type = State()
    waiting_location_city = State()
    waiting_location_address = State()
    waiting_salary_min = State()
    waiting_salary_max = State()
    waiting_requirements = State()
    waiting_responsibilities = State()