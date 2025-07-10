import asyncio
from typing import Sequence, Optional

from fastapi import (
    APIRouter,
    status,
    Depends,
    Query,
    HTTPException
)
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from config.dependencies import RoleChecker, get_current_user
from database import get_db
from database.models.accounts import (
    UserGroupEnum,
    UserModel,
    purchased_movies_association
)

from database.models.movies import (
    MovieModel,
    StarModel,
    DirectorModel,
    GenreModel,
    CertificationModel,
    CommentModel,
    LikeModel,
    FavoriteMovieModel,
    RateMovieModel
)
from database.models.shopping_cart import CartModel, CartItemModel
from schemas.movies import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieCreateResponseSchema,
    MovieCreateRequestSchema,
    MovieDetailSchema,
    MovieUpdateSchema,
    MessageResponseSchema
)

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


@router.get(
    "/movies/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="List movies",
    description="Browse the movie catalog with pagination, filtering, sorting, and search.",
    responses={
        200: {
            "description": "List of movies returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "movies": [
                            {
                                "id": 1,
                                "name": "The Shawshank Redemption",
                                "year": 1994,
                                "price": 9.99,
                                "imdb": 9.3,
                                "time": 142,
                                "genres": [{"id": 1, "name": "Drama"}],
                                "stars": [{"id": 1, "name": "Tim Robbins"}],
                                "directors": [
                                    {"id": 1, "name": "Frank Darabont"}]
                            },
                            {
                                "id": 2,
                                "name": "The Godfather",
                                "year": 1972,
                                "price": 9.99,
                                "imdb": 9.2,
                                "time": 175,
                                "genres": [{"id": 2, "name": "Crime"}],
                                "stars": [{"id": 2, "name": "Marlon Brando"}],
                                "directors": [
                                    {"id": 2, "name": "Francis Ford Coppola"}]
                            }
                        ],
                        "total_pages": 1,
                        "total_items": 2,
                        "prev_page": None,
                        "next_page": None
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "page"],
                                "msg": "ensure this value is greater than or equal to 1",
                                "type": "value_error.number.not_ge"
                            }
                        ]
                    }
                }
            }
        }
    },
)
async def get_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    imdb_min: Optional[int] = Query(None),
    genre: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> MovieListResponseSchema:
    """Retrieve a paginated list of movies with optional filters and sorting.

    Args:
        page (int): Page number for pagination.
        per_page (int): Number of movies per page.
        sort_by (Optional[str]): Field to sort by.
        search (Optional[str]): Search term for title, description, actor, or director.
        year_from (Optional[int]): Filter movies released from this year.
        year_to (Optional[int]): Filter movies released up to this year.
        imdb_min (Optional[int]): Minimum IMDb rating.
        genre (Optional[str]): Filter by genre name.
        db (AsyncSession): Database session.

    Returns:
        MovieListResponseSchema: Paginated list of movies.
    """
    base_filters = []

    if year_from:
        base_filters.append(MovieModel.year >= year_from)
    if year_to:
        base_filters.append(MovieModel.year <= year_to)
    if imdb_min:
        base_filters.append(MovieModel.imdb >= imdb_min)
    if genre:
        base_filters.append(
            MovieModel.genres.any(GenreModel.name.ilike(f"%{genre}%"))
        )

    if search:
        search_term = f"%{search}%"
        count_filters = base_filters + [
            or_(
                MovieModel.name.ilike(search_term),
                MovieModel.description.ilike(search_term),
                MovieModel.stars.any(StarModel.name.ilike(search_term)),
                MovieModel.directors.any(DirectorModel.name.ilike(search_term))
            )
        ]
        count_stmt = select(func.count(MovieModel.id.distinct())).where(
            *count_filters
        )
    else:
        count_stmt = select(func.count(MovieModel.id)).where(*base_filters)

    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return MovieListResponseSchema(movies=[], total_pages=0, total_items=0)

    stmt = select(MovieModel).options(
        selectinload(MovieModel.genres),
        selectinload(MovieModel.stars),
        selectinload(MovieModel.directors),
        selectinload(MovieModel.certification)
    )

    if search:
        stmt = stmt.join(MovieModel.stars).join(MovieModel.directors).distinct()
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                MovieModel.name.ilike(search_term),
                MovieModel.description.ilike(search_term),
                StarModel.name.ilike(search_term),
                DirectorModel.name.ilike(search_term)
            )
        )

    stmt = stmt.where(*base_filters)

    if sort_by:
        sort_field = sort_by.strip("-")
        allowed_sort_fields = ("year", "price", "imdb", "name", "time")
        if sort_field in allowed_sort_fields:
            column = getattr(MovieModel, sort_field)
            if sort_by.startswith("-"):
                stmt = stmt.order_by(desc(column))
            else:
                stmt = stmt.order_by(asc(column))

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    movies: Sequence[MovieModel] = result.scalars().all()

    movie_list = [MovieListItemSchema.model_validate(movie) for movie in movies]

    total_pages = (total_items + per_page - 1) // per_page

    return MovieListResponseSchema(
        movies=movie_list,
        prev_page=f"/cinema/movies/?page={page - 1}&per_page={per_page}{f'&sort_by={sort_by}' if sort_by else ''}{f'&search={search}' if search else ''}{f'&year_from={year_from}' if year_from else ''}{f'&year_to={year_to}' if year_to else ''}{f'&imdb_min={imdb_min}' if imdb_min else ''}{f'&genre={genre}' if genre else ''}" if page > 1 else None,
        next_page=f"/cinema/movies/?page={page + 1}&per_page={per_page}{f'&sort_by={sort_by}' if sort_by else ''}{f'&search={search}' if search else ''}{f'&year_from={year_from}' if year_from else ''}{f'&year_to={year_to}' if year_to else ''}{f'&imdb_min={imdb_min}' if imdb_min else ''}{f'&genre={genre}' if genre else ''}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/movies/purchased/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="List purchased movies",
    description="Get a paginated list of movies purchased by the current user.",
    responses={
        200: {
            "description": "List of purchased movies returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "movies": [
                            {
                                "id": 1,
                                "name": "The Shawshank Redemption",
                                "year": 1994,
                                "price": 9.99,
                                "imdb": 9.3,
                                "time": 142,
                                "genres": [{"id": 1, "name": "Drama"}],
                                "stars": [{"id": 1, "name": "Tim Robbins"}],
                                "directors": [
                                    {"id": 1, "name": "Frank Darabont"}]
                            }
                        ],
                        "total_pages": 1,
                        "total_items": 1,
                        "prev_page": None,
                        "next_page": None
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "page"],
                                "msg": "ensure this value is greater than or equal to 1",
                                "type": "value_error.number.not_ge"
                            }
                        ]
                    }
                }
            }
        }
    },
)
async def get_purchased_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MovieListResponseSchema:
    count_stmt = (
        select(func.count(MovieModel.id))
        .join(
            purchased_movies_association,
            MovieModel.id == purchased_movies_association.c.movie_id
        )
        .where(purchased_movies_association.c.user_id == user.id)
    )
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return MovieListResponseSchema(movies=[], total_pages=0, total_items=0)

    stmt = (
        select(MovieModel)
        .options(
            selectinload(MovieModel.genres),
            selectinload(MovieModel.stars),
            selectinload(MovieModel.directors),
            selectinload(MovieModel.certification)
        )
        .join(
            purchased_movies_association,
            MovieModel.id == purchased_movies_association.c.movie_id
        )
        .where(purchased_movies_association.c.user_id == user.id)
    )

    if sort_by:
        sort_field = sort_by.strip("-")
        allowed_sort_fields = ("year", "price", "imdb", "name", "time")
        if sort_field in allowed_sort_fields:
            column = getattr(MovieModel, sort_field)
            if sort_by.startswith("-"):
                stmt = stmt.order_by(desc(column))
            else:
                stmt = stmt.order_by(asc(column))

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    movies: Sequence[MovieModel] = result.scalars().all()

    movie_list = [MovieListItemSchema.model_validate(movie) for movie in movies]

    total_pages = (total_items + per_page - 1) // per_page

    return MovieListResponseSchema(
        movies=movie_list,
        prev_page=f"/cinema/movies/purchased/?page={page - 1}&per_page={per_page}{f'&sort_by={sort_by}' if sort_by else ''}" if page > 1 else None,
        next_page=f"/cinema/movies/purchased/?page={page + 1}&per_page={per_page}{f'&sort_by={sort_by}' if sort_by else ''}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/movies/{movie_id}/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK,
    summary="Get movie details",
    description="Retrieve detailed information about a specific movie by its ID.",
    responses={
        200: {
            "description": "Movie details returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "The Shawshank Redemption",
                        "description": "Two imprisoned men bond over a number of years...",
                        "year": 1994,
                        "price": 9.99,
                        "imdb": 9.3,
                        "time": 142,
                        "genres": [{"id": 1, "name": "Drama"}],
                        "stars": [{"id": 1, "name": "Tim Robbins"}],
                        "directors": [{"id": 1, "name": "Frank Darabont"}],
                        "certification": {"id": 1, "name": "R"},
                        "comments": [
                            {
                                "id": 1,
                                "text": "Amazing movie!",
                                "user": {"id": 1, "email": "user@example.com"},
                                "created_at": "2024-01-01T00:00:00Z"
                            }
                        ],
                        "likes_count": 150,
                        "favorites_count": 75,
                        "average_rating": 9.2
                    }
                }
            }
        },
        404: {
            "description": "Movie not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found"
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["path", "movie_id"],
                                "msg": "ensure this value is greater than 0",
                                "type": "value_error.number.not_gt"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_movie_by_id(
    movie_id: int,
    db: AsyncSession = Depends(get_db)
) -> MovieDetailSchema:
    """Retrieve detailed information about a specific movie by its ID.

    Args:
        movie_id (int): The ID of the movie to retrieve.
        db (AsyncSession): Database session dependency.

    Returns:
        MovieDetailSchema: Detailed information about the movie.
    """
    movie_stmt = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.certification),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
            joinedload(MovieModel.directors),
        )
        .where(MovieModel.id == movie_id)
    )
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    comments_stmt = (
        select(CommentModel)
        .where(CommentModel.movie_id == movie_id)
        .order_by(desc(CommentModel.created_at))
        .limit(10)
    )
    likes_stmt = (
        select(func.count(LikeModel.id))
        .where(LikeModel.movie_id == movie_id)
    )
    favorites_stmt = (
        select(func.count(FavoriteMovieModel.id))
        .where(FavoriteMovieModel.movie_id == movie_id)
    )
    avg_rating_stmt = (
        select(func.avg(RateMovieModel.rate))
        .where(RateMovieModel.movie_id == movie_id)
    )

    (
        comments_result,
        likes_result,
        favorites_result,
        avg_rating_result
    ) = await asyncio.gather(
        db.execute(comments_stmt),
        db.execute(likes_stmt),
        db.execute(favorites_stmt),
        db.execute(avg_rating_stmt),
    )

    recent_comments = comments_result.scalars().all()
    likes_count = likes_result.scalar_one()
    favorites_count = favorites_result.scalar_one()
    avg_rating = avg_rating_result.scalar_one() or 0.0

    movie_dict = {
        **movie.__dict__,
        "comments": recent_comments,
        "likes": likes_count,
        "favorites": favorites_count,
        "average_rating": avg_rating
    }

    return MovieDetailSchema.model_validate(movie_dict)


@router.post(
    "/movies/",
    response_model=MovieCreateResponseSchema,
    status_code=status.HTTP_201_CREATED,
    tags=["movies", "moderator"],
    summary="Create a new movie",
    description="Create a new movie entry. Only moderators and admins can perform this action.",
    responses={
        201: {
            "description": "Movie created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "The Shawshank Redemption",
                        "description": "Two imprisoned men bond over a number of years...",
                        "year": 1994,
                        "price": 9.99,
                        "imdb": 9.3,
                        "time": 142,
                        "genres": [{"id": 1, "name": "Drama"}],
                        "stars": [{"id": 1, "name": "Tim Robbins"}],
                        "directors": [{"id": 1, "name": "Frank Darabont"}],
                        "certification": {"id": 1, "name": "R"}
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Moderator or admin privileges required."
                    }
                }
            }
        },
        409: {
            "description": "Movie already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie with this name already exists."
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "name"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def create_movie(
    data: MovieCreateRequestSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> MovieCreateResponseSchema:
    """Create a new movie entry in the database.

    Args:
        data (MovieCreateRequestSchema): Data for the new movie.
        authorized: Dependency to check moderator/admin rights.
        db (AsyncSession): Database session dependency.

    Returns:
        MovieCreateResponseSchema: The created movie object.
    """
    existing_stmt = (
        select(MovieModel)
        .where(
            MovieModel.name == data.name,
            MovieModel.year == data.year,
            MovieModel.time == data.time
        )
    )
    result = await db.execute(existing_stmt)
    existing_movie: MovieModel = result.scalars().first()

    if existing_movie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{existing_movie.name}', release year "
                   f"'{existing_movie}' and time duration '{existing_movie.time}' "
                   f"already exists."
        )

    try:
        certification_stmt = (
            select(CertificationModel)
            .where(CertificationModel.name == data.certification)
        )
        result = await db.execute(certification_stmt)
        certification = result.scalars().first()

        if not certification:
            certification = CertificationModel(name=data.certification)
            db.add(certification)
            await db.flush()

        genres = []
        for genre_name in data.genres:
            genre_stmt = select(GenreModel).where(GenreModel.name == genre_name)
            result = await db.execute(genre_stmt)
            genre = result.scalars().first()

            if not genre:
                genre = GenreModel(name=genre_name)
                db.add(genre)
                await db.flush()

            genres.append(genre)

        stars = []
        for star_name in data.stars:
            star_stmt = select(StarModel).where(StarModel.name == star_name)
            result = await db.execute(star_stmt)
            star = result.scalars().first()

            if not star:
                star = StarModel(name=star_name)
                db.add(star)
                await db.flush()

            stars.append(star)

        directors = []
        for director_name in data.directors:
            director_stmt = select(DirectorModel).where(
                DirectorModel.name == director_name
            )
            result = await db.execute(director_stmt)
            director = result.scalars().first()

            if not director:
                director = DirectorModel(name=director_name)
                db.add(director)
                await db.flush()

            directors.append(director)

        movie = MovieModel(
            name=data.name,
            year=data.year,
            time=data.time,
            imdb=data.imdb,
            votes=data.votes,
            meta_score=data.meta_score,
            gross=data.gross,
            description=data.description,
            price=data.price,
            certification=certification,
            genres=genres,
            stars=stars,
            directors=directors
        )
        db.add(movie)
        await db.commit()
        await db.refresh(
            movie,
            ["certification", "genres", "stars", "directors"]
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data."
        )

    return MovieCreateResponseSchema.model_validate(movie)


@router.patch(
    "/movies/{movie_id}/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["movies", "moderator"],
    summary="Update movie",
    description="Update an existing movie's information. Only moderators and admins can perform this action.",
    responses={
        200: {
            "description": "Movie updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Movie updated successfully."
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Moderator or admin privileges required."
                    }
                }
            }
        },
        404: {
            "description": "Movie not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found"
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "name"],
                                "msg": "ensure this value has at least 1 characters",
                                "type": "value_error.any_str.min_length"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def update_movie(
    movie_id: int,
    data: MovieUpdateSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    """Update an existing movie's information in the database.

    Args:
        movie_id (int): The ID of the movie to update.
        data (MovieUpdateSchema): Updated movie data.
        authorized: Dependency to check moderator/admin rights.
        db (AsyncSession): Database session dependency.

    Returns:
        MessageResponseSchema: Success message.
    """
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    movie_update_data = data.model_dump(exclude_unset=True)

    try:
        if "certification" in movie_update_data:
            certification_stmt = (
                select(CertificationModel)
                .where(
                    CertificationModel.name == movie_update_data[
                        "certification"]
                )
            )
            result = await db.execute(certification_stmt)
            certification = result.scalars().first()

            if not certification:
                certification = CertificationModel(
                    name=movie_update_data["certification"]
                )
                db.add(certification)
                await db.flush()

            movie_update_data["certification"] = certification

        if "genres" in movie_update_data:
            genres = []
            for genre_name in movie_update_data["genres"]:
                genre_stmt = (
                    select(GenreModel)
                    .where(GenreModel.name == genre_name)
                )
                result = await db.execute(genre_stmt)
                genre = result.scalars().first()

                if not genre:
                    genre = GenreModel(name=genre_name)
                    db.add(genre)
                    await db.flush()

                genres.append(genre)

            movie_update_data["genres"] = genres

        if "stars" in movie_update_data:
            stars = []
            for star_name in movie_update_data["stars"]:
                star_stmt = (
                    select(StarModel)
                    .where(StarModel.name == star_name)
                )
                result = await db.execute(star_stmt)
                star = result.scalars().first()

                if not star:
                    star = StarModel(name=star_name)
                    db.add(star)
                    await db.flush()

                stars.append(star)

            movie_update_data["stars"] = stars

        if "directors" in movie_update_data:
            directors = []
            for director_name in movie_update_data["directors"]:
                director_stmt = (
                    select(DirectorModel)
                    .where(DirectorModel.name == director_name)
                )
                result = await db.execute(director_stmt)
                director = result.scalars().first()

                if not director:
                    director = DirectorModel(name=director_name)
                    db.add(director)
                    await db.flush()

                directors.append(director)

            movie_update_data["directors"] = directors

        for field, value in movie_update_data.items():
            setattr(movie, field, value)

        await db.commit()
        await db.refresh(
            movie,
            ["certification", "genres", "stars", "directors"]
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data"
        )

    return MessageResponseSchema(message="Movie updated successfully.")


@router.delete(
    "/movies/{movie_id}/",
    tags=["movies", "moderator"],
    summary="Delete movie",
    description="Delete a movie from the database. Only moderators and admins can perform this action.",
    responses={
        200: {
            "description": "Movie deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Movie deleted successfully."
                    }
                }
            }
        },
        204: {
            "description": "Movie deleted successfully"
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access denied. Moderator or admin privileges required."
                    }
                }
            }
        },
        404: {
            "description": "Movie not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found"
                    }
                }
            }
        }
    }
)
async def delete_movie(
    movie_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema | None:
    """Delete a movie from the database.

    Args:
        movie_id (int): The ID of the movie to delete.
        authorized: Dependency to check moderator/admin rights.
        db (AsyncSession): Database session dependency.

    Returns:
        MessageResponseSchema | None: Success message or None.
    """
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    purchaser_count_stmt = (
        select(func.count())
        .select_from(purchased_movies_association)
        .where(purchased_movies_association.c.movie_id == movie_id))

    result = await db.execute(purchaser_count_stmt)
    purchaser_count = result.scalar_one()

    if purchaser_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete movie: It has been purchased by {purchaser_count} users"
        )

    cart_count_stmt = (
        select(func.count(UserModel.id))
        .join(CartModel, UserModel.cart)
        .join(CartItemModel, CartModel.items)
        .where(CartItemModel.movie_id == movie_id)
    )
    result = await db.execute(cart_count_stmt)
    cart_count = result.scalar_one()

    await db.delete(movie)
    await db.commit()

    if cart_count > 0:
        return MessageResponseSchema(
            message=f"Movie deleted successfully. Note: It was in {cart_count} users' carts and has been removed."
        )

    return None
