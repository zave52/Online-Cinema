from typing import Sequence, Optional

from fastapi import APIRouter, status, Depends, Query
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db

from database.models.movies import (
    MovieModel,
    StarModel,
    DirectorModel,
    GenreModel
)
from schemas.movies import MovieListResponseSchema, MovieListItemSchema

router = APIRouter()


@router.get(
    "/movies/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK
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

    if year_from:
        stmt = stmt.where(MovieModel.year >= year_from)
    if year_to:
        stmt = stmt.where(MovieModel.year <= year_to)
    if imdb_min:
        stmt = stmt.where(MovieModel.imdb >= imdb_min)
    if genre:
        stmt = stmt.where(
            MovieModel.genres.any(GenreModel.name.ilike(f"%{genre}%"))
        )

    count_stmt = select(func.count(MovieModel.id)).select_from(stmt.subquery())
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return MovieListResponseSchema(movies=[], total_pages=0, total_items=0)

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
        prev_page=f"/cinema/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/cinema/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )
