import os
import uuid
import hashlib
from urllib.parse import urlencode


async def create_payment_link(amount: float, description: str, user_id: int, purpose: str, vacancy_id: int = None):
    if os.getenv("TEST_MODE") == "true":
        fake_payment_id = f"test_{uuid.uuid4().hex[:8]}"
        fake_url = f"https://t.me/{os.getenv('BOT_USERNAME')}?start=payment_success"
        return fake_url, fake_payment_id

    merchant_id = os.getenv("FREKASSA_MERCHANT_ID")
    secret_key = os.getenv("FREKASSA_SECRET_KEY")
    order_id = f"order_{user_id}_{int(os.times().system)}"

    params = {
        'm': merchant_id,
        'oa': str(amount),
        'o': order_id,
        's': hashlib.md5(f"{merchant_id}:{amount}:{secret_key}:{order_id}".encode()).hexdigest(),
        'currency': 'RUB',
        'description': description,
        'us_user_id': str(user_id),
        'us_purpose': purpose,
        'us_vacancy_id': str(vacancy_id) if vacancy_id else ''
    }
    payment_url = f"https://pay.freekassa.ru/?{urlencode(params)}"
    return payment_url, order_id