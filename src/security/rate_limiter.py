import logging
import time
import uuid

from fastapi import Request, HTTPException, status, Depends
from redis.asyncio import Redis

from config.dependencies import optional_get_current_user_id, get_redis_client
from config.settings import BaseAppSettings, get_settings

logger = logging.getLogger(__name__)


async def rate_limit(
    request: Request,
    user_id: int | None = Depends(optional_get_current_user_id),
    settings: BaseAppSettings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client)
) -> None:
    """Rate limiter dependency that limits requests based on user authentication status.

    Args:
        request: The incoming FastAPI request.
        user_id: The ID of the authenticated user, or None if anonymous.
        settings: Application settings containing rate limit configurations.
        redis_client: The Redis client instance used for tracking requests.

    Raises:
        HTTPException: If the client has exceeded the allowed rate limit (HTTP 429).
    """
    RATE_LIMITS = {
        "anonymous": (
            settings.RATE_LIMIT_ANONYMOUS,
            settings.RATE_LIMIT_PERIOD
        ),
        "authenticated": (
            settings.RATE_LIMIT_AUTHENTICATED,
            settings.RATE_LIMIT_PERIOD
        ),
    }

    identity = str(user_id) if user_id is not None else request.client.host
    limit_type = "authenticated" if user_id is not None else "anonymous"

    limit, period = RATE_LIMITS[limit_type]
    key = f"rate_limit_{identity}"

    now = int(time.time())
    window_start = now - period

    try:
        await redis_client.zremrangebyscore(key, min=0, max=window_start)

        request_count = await redis_client.zcard(key)
        if request_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests"
            )

        member = f"{now}:{uuid.uuid4()}"
        await redis_client.zadd(key, {member: now})
        await redis_client.expire(key, period)
    except ConnectionError as e:
        logger.error("Redis connection error during rate limiting: %s", e)
        pass
