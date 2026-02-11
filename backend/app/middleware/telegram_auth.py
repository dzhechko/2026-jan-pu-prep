"""Telegram Mini App initData validation.

Implements the official Telegram WebApp data verification algorithm:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, unquote

from fastapi import HTTPException, status


def validate_init_data(
    init_data_raw: str,
    bot_token: str,
    max_age_seconds: int = 300,
) -> dict:
    """Validate Telegram Mini App ``initData`` and return parsed fields.

    Parameters
    ----------
    init_data_raw:
        The raw query-string exactly as received from ``Telegram.WebApp.initData``.
    bot_token:
        The bot token issued by BotFather.
    max_age_seconds:
        Maximum allowed age of ``auth_date`` in seconds (default 5 min).

    Returns
    -------
    dict
        Parsed initData fields including the ``user`` object (already
        JSON-decoded).

    Raises
    ------
    HTTPException
        401 if the hash is missing, invalid, or the data is too old.
    """
    # 1. Parse the query string into individual key=value pairs
    parsed = parse_qs(init_data_raw, keep_blank_values=True)

    # Flatten single-value lists
    data: dict[str, str] = {k: v[0] for k, v in parsed.items()}

    # 2. Extract the hash sent by Telegram
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing hash in initData",
        )

    # 3. Build the data-check-string: sorted "key=value" pairs joined by "\n"
    data_check_parts = sorted(f"{k}={v}" for k, v in data.items())
    data_check_string = "\n".join(data_check_parts)

    # 4. Compute HMAC-SHA256
    #    secret_key = HMAC_SHA256("WebAppData", bot_token)
    #    hash       = HMAC_SHA256(secret_key, data_check_string)
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # 5. Constant-time comparison
    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid initData signature",
        )

    # 6. Check auth_date freshness
    auth_date_str = data.get("auth_date")
    if not auth_date_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing auth_date in initData",
        )

    try:
        auth_date = int(auth_date_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth_date value",
        )

    if time.time() - auth_date > max_age_seconds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData has expired",
        )

    # 7. Decode the user JSON object if present
    user_raw = data.get("user")
    if user_raw:
        try:
            data["user"] = json.loads(unquote(user_raw))
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user JSON in initData",
            )

    # Re-attach hash so callers can see the original value if needed
    data["hash"] = received_hash

    return data
