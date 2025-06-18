from fastapi import FastAPI

from routers.accounts import router

app = FastAPI(title="Online Cinema")

api_version_index = "/api/v1"

app.include_router(
    router, prefix=f"{api_version_index}/accounts", tags=["accounts"]
)
