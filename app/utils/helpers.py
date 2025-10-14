import json
from typing import Any
from fastapi.responses import Response

def safe_json(payload: Any, status_code: int = 200) -> Response:
    """
    Возвращает строго валидный JSON (без NaN/Infinity), чтобы jq и строгие клиенты не падали.
    """
    return Response(
        content=json.dumps(payload, ensure_ascii=False, allow_nan=False, default=str),
        media_type="application/json",
        status_code=status_code,
    )