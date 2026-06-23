import aiohttp
from typing import Dict

async def get_city_from_coords(lat: float, lon: float) -> Dict[str, str]:
    async with aiohttp.ClientSession() as session:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&addressdetails=1"
        headers = {"User-Agent": "JobBot/1.0"}
        try:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                address = data.get("address", {})
                city = address.get("city") or address.get("town") or address.get("village") or "Не определен"
                district = address.get("state_district") or address.get("county") or ""
                return {"city": city, "district": district}
        except Exception:
            return {"city": "Москва", "district": "Центральный"}