from fastapi import FastAPI

from routers import accounts, profiles, movies, shopping_cart, orders, payments

app = FastAPI(title="Online Cinema")

api_version_index = "/api/v1"

app.include_router(
    accounts.router, prefix=f"{api_version_index}/accounts", tags=["accounts"]
)
app.include_router(
    profiles.router, prefix=f"{api_version_index}/profiles", tags=["profiles"]
)
app.include_router(
    movies.router, prefix=f"{api_version_index}/cinema", tags=["cinema"]
)
app.include_router(
    shopping_cart.router,
    prefix=f"{api_version_index}/ecommerce",
    tags=["ecommerce"]
)
app.include_router(
    orders.router,
    prefix=f"{api_version_index}",
    tags=["ecommerce"]
)
app.include_router(
    payments.router,
    prefix=f"{api_version_index}",
    tags=["ecommerce"]
)
