import os

from config.settings import Settings, DevelopmentSettings, BaseAppSettings


def get_settings() -> BaseAppSettings:
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "production":
        return Settings()
    return DevelopmentSettings()
