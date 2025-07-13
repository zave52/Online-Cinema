from fastapi import FastAPI, Depends
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer
from fastapi.responses import HTMLResponse

from config.dependencies import get_current_user
from database.models.accounts import UserModel
from routers import (
    accounts,
    profiles,
    movies,
    shopping_cart,
    orders,
    payments,
    directors,
    comments,
    genres,
    likes,
    stars,
    rates,
    favorites
)

security = HTTPBearer(auto_error=False)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with OpenAPI documentation.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Online Cinema API",
        description="""
        # Online Cinema API Documentation

        ## Overview
        This API provides comprehensive functionality for an online cinema platform, including user management, movie catalog, shopping cart, orders, and payment processing.

        ## Features
        - **User Management**: Registration, authentication, profile management
        - **Movie Catalog**: Browse movies, view details, search and filter
        - **Shopping Cart**: Add/remove movies, manage cart contents
        - **Orders**: Create and manage movie purchases
        - **Payments**: Secure payment processing with Stripe integration
        - **Admin Functions**: User management and system administration

        ## Authentication
        The API uses JWT (JSON Web Tokens) for authentication. Most endpoints require a valid access token in the Authorization header.

        ## Error Handling
        The API returns standardized error responses with appropriate HTTP status codes and detailed error messages.

        ## Versioning
        This is version 1.0 of the API. All endpoints are prefixed with `/api/v1/`.
        """,
        version="1.0.0",
        contact={
            "name": "Zakhar Savchyn",
            "email": "zakhar.savchyn.dev@gmail.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            }
        ],
        docs_url=None,
        redoc_url=None,
    )

    api_version_index = "/api/v1"

    app.include_router(
        accounts.router,
        prefix=f"{api_version_index}/accounts",
        tags=["accounts"]
    )
    app.include_router(
        profiles.router,
        prefix=f"{api_version_index}/profiles",
        tags=["profiles"]
    )
    app.include_router(
        directors.router,
        prefix=f"{api_version_index}/cinema",
        tags=["directors"]
    )
    app.include_router(
        comments.router,
        prefix=f"{api_version_index}/cinema",
        tags=["comments"]
    )
    app.include_router(
        favorites.router,
        prefix=f"{api_version_index}/cinema",
        tags=["favorites"]
    )
    app.include_router(
        genres.router,
        prefix=f"{api_version_index}/cinema",
        tags=["genres"]
    )
    app.include_router(
        likes.router,
        prefix=f"{api_version_index}/cinema",
        tags=["likes"]
    )
    app.include_router(
        rates.router,
        prefix=f"{api_version_index}/cinema",
        tags=["rates"]
    )
    app.include_router(
        stars.router,
        prefix=f"{api_version_index}/cinema",
        tags=["stars"]
    )
    app.include_router(
        movies.router,
        prefix=f"{api_version_index}/cinema",
        tags=["movies"]
    )
    app.include_router(
        shopping_cart.router,
        prefix=f"{api_version_index}/ecommerce",
        tags=["cart"]
    )
    app.include_router(
        orders.router,
        prefix=f"{api_version_index}/ecommerce",
        tags=["orders"]
    )
    app.include_router(
        payments.router,
        prefix=f"{api_version_index}/ecommerce",
        tags=["payments"]
    )

    return app


app = create_app()


def custom_openapi():
    """Generate custom OpenAPI schema with security definitions and detailed documentation.

    Returns:
        dict: Custom OpenAPI schema
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from login endpoint"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/docs", include_in_schema=False)
async def get_swagger_documentation(
    authorized: UserModel = Depends(get_current_user)
) -> HTMLResponse:
    """Get Swagger UI documentation with access control.

    Args:
        authorized: Authentication verification result

    Returns:
        HTMLResponse: Swagger UI HTML page
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(
    authorized: UserModel = Depends(get_current_user)
) -> HTMLResponse:
    """Get ReDoc documentation with access control.

    Args:
        authorized: Authentication verification result

    Returns:
        HTMLResponse: ReDoc HTML page
    """
    return get_redoc_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
    )


@app.get(
    "/health",
    tags=["system"],
    summary="Health Check",
    description="Check if the API is running and healthy",
    response_description="API health status",
    responses={
        200: {
            "description": "API is healthy and operational",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "version": "1.0.0",
                        "timestamp": "2025-01-01T00:00:00Z"
                    }
                }
            }
        }
    }
)
async def health_check():
    """Check API health status.

    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    }
