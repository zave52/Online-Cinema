import asyncio
from functools import wraps
from typing import Any, Callable, Coroutine

from celery.app import Celery

from config.settings import CelerySettings

settings = CelerySettings()

celery_app = Celery("fastapi_celery_app")

celery_app.config_from_object(settings, namespace="CELERY")
celery_app.autodiscover_tasks()


def async_task(*args: Any, **kwargs: Any):
    """Decorator to convert async functions to Celery tasks.
    
    This decorator wraps async functions and converts them to synchronous
    Celery tasks using AsyncToSync, allowing async functions to be used
    as background tasks.
    
    Args:
        *args: Positional arguments to pass to the Celery task decorator.
        **kwargs: Keyword arguments to pass to the Celery task decorator.
        
    Returns:
        Callable: Decorated function that can be used as a Celery task.
    """

    def _decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @celery_app.task(*args, **kwargs)
        @wraps(func)
        def _decorated(*args, **kwargs) -> Any:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(func(*args, **kwargs))
            finally:
                loop.close()

        return _decorated

    return _decorator
