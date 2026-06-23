from database.crud import get_active_vacancies, get_user_by_telegram_id
from typing import List
from database.models import Vacancy

async def find_matching_vacancies(telegram_id: int) -> List[Vacancy]:
    worker = await get_user_by_telegram_id(telegram_id)
    if not worker:
        return []
    all_vacancies = await get_active_vacancies()
    matched = []
    for vac in all_vacancies:
        if worker.preferred_work_type != "both":
            if vac.work_type != worker.preferred_work_type:
                continue
        if vac.work_type == "physical":
            if worker.city and vac.location_city:
                if worker.city.lower() != vac.location_city.lower():
                    continue
        matched.append(vac)
        if len(matched) >= 20:
            break
    return matched