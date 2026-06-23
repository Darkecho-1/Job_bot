import re

def sanitize_text(text: str, max_length: int = 1000) -> str:
    if not text:
        return ""
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    cleaned = ' '.join(cleaned.split())
    return cleaned[:max_length]