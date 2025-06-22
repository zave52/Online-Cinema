from fastapi import FastAPI

from routers import accounts, profiles

app = FastAPI(title="Online Cinema")

api_version_index = "/api/v1"

app.include_router(
    accounts.router, prefix=f"{api_version_index}/accounts", tags=["accounts"]
)
app.include_router(
    profiles.router, prefix=f"{api_version_index}/profiles", tags=["profiles"]
)
