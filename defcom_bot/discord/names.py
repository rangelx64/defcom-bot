import re
import unicodedata


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFD", str(value))
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = re.sub(r"[^a-z0-9\s-]", "", value.lower()).strip()
    return re.sub(r"-+", "-", re.sub(r"\s+", "-", value))[:100]
