from functools import wraps
from typing import Any, Callable, Coroutine

from celery.app import Celery
from asgiref.sync import AsyncToSync

from config.settings import CelerySettings

settings = CelerySettings()

celery_app = Celery("fastapi_celery_app")

celery_app.config_from_object(settings, namespace="CELERY")
celery_app.autodiscover_tasks()


def async_task(*args: Any, **kwargs: Any):
    def _decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        sync_call = AsyncToSync(func)

        @celery_app.task(*args, **kwargs)
        @wraps(func)
        def _decorated(*args, **kwargs) -> Any:
            return sync_call(*args, **kwargs)

        return _decorated

    return _decorator
