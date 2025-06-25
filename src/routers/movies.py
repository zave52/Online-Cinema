from typing import Sequence, Optional

from fastapi import APIRouter, status, Depends, Query, HTTPException
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.dependencies import get_token, get_jwt_manager
from database import get_db
from database.models.accounts import UserModel, UserGroupModel, UserGroupEnum

from database.models.movies import (
    MovieModel,
    StarModel,
    DirectorModel,
    GenreModel, CertificationModel
)
from exceptions.security import BaseSecurityError
from schemas.movies import (
    MovieListResponseSchema,
    MovieListItemSchema, MovieCreateResponseSchema, MovieCreateRequestSchema
)
from security.interfaces import JWTManagerInterface

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


@router.post(
    "/movies/",
    response_model=MovieCreateResponseSchema,
    status_code=status.HTTP_201_CREATED,
    tags=["admin", "moderator"]
)
async def create_movie(
    data: MovieCreateRequestSchema,
    token: str = Depends(get_token),
    jwt_manager: JWTManagerInterface = Depends(get_jwt_manager),
    db: AsyncSession = Depends(get_db)
) -> MovieCreateResponseSchema:
    try:
        decoded_token = jwt_manager.decode_access_token(token)
        user_id = decoded_token.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

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

    group_stmt = (
        select(UserGroupModel)
        .join(UserModel)
        .where(UserModel.id == user_id)
    )
    result = await db.execute(group_stmt)
    user_group = result.scalars().first()

    if not user_group or user_group not in (
            UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and moderators can create movie."
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
