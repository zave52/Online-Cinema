import asyncio
from typing import Sequence, Optional

from fastapi import APIRouter, status, Depends, Query, HTTPException
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from config.dependencies import RoleChecker, get_current_user
from database import get_db
from database.models.accounts import UserGroupEnum, UserModel

from database.models.movies import (
    MovieModel,
    StarModel,
    DirectorModel,
    GenreModel,
    CertificationModel,
    CommentModel,
    LikeModel
)
from schemas.movies import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieCreateResponseSchema,
    MovieCreateRequestSchema,
    MovieDetailSchema,
    MovieUpdateSchema,
    MessageResponseSchema,
    NameSchema,
    GenreSchema,
    GenreListSchema,
    StarListSchema,
    StarSchema,
    DirectorListSchema,
    DirectorSchema
)

router = APIRouter()

moderator_and_admin = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)


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


@router.get(
    "/movies/{movie_id}/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK
)
async def get_movie_by_id(
    movie_id: int,
    db: AsyncSession = Depends(get_db)
) -> MovieDetailSchema:
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
        .order_by(desc("created_at"))
        .limit(10)
    )
    likes_stmt = (
        select(func.count())
        .select_from(
            select(MovieModel.likes).where(MovieModel.id == movie_id).subquery()
        )
    )
    favorites_stmt = (
        select(func.count())
        .select_from(
            select(MovieModel.favorites).where(
                MovieModel.id == movie_id
            ).subquery()
        )
    )
    avg_rating_stmt = (
        select(func.avg(MovieModel.rates)).where(MovieModel.id == movie_id)
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
    tags=["admin", "moderator"]
)
async def create_movie(
    data: MovieCreateRequestSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> MovieCreateResponseSchema:
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
    tags=["admin", "moderator"]
)
async def update_movie(
    movie_id: int,
    data: MovieUpdateSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
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
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["admin", "moderator"]
)
async def delete_movie(
    movie_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    # TODO: Prevent the deletion of a movie if at least one user has purchased it.

    await db.delete(movie)
    await db.commit()

    return


@router.get(
    "/movies/likes/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["likes", "movies"]
)
async def get_liked_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MovieListResponseSchema:
    count_stmt = (
        select(func.count(MovieModel.id))
        .where(
            MovieModel.likes.any(LikeModel.user_id == user.id)
        )
    )
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return MovieListResponseSchema(movies=[], total_pages=0, total_items=0)

    stmt = (
        select(MovieModel)
        .options(
            selectinload(MovieModel.genres)
        )
        .where(
            MovieModel.likes.any(LikeModel.user_id == user.id)
        )
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
        prev_page=f"/cinema/movies/likes/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/cinema/movies/likes/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.post(
    "/movies/{movie_id}/likes/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["likes", "movies"]
)
async def like_movie(
    movie_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema:
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    like_stmt = (
        select(LikeModel)
        .where(
            LikeModel.movie_id == movie_id,
            LikeModel.user_id == user.id
        )
    )
    result = await db.execute(like_stmt)
    like = result.scalars().first()

    if like:
        return MessageResponseSchema(message="You already like this movie.")

    new_like = LikeModel(user_id=user.id, movie_id=movie_id)
    db.add(new_like)
    await db.commit()

    return MessageResponseSchema(message="You successfully liked this movie.")


@router.delete(
    "/movies/{movie_id}/likes/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["likes", "movies"]
)
async def unlike_movie(
    movie_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    like_stmt = (
        select(LikeModel)
        .where(
            LikeModel.user_id == user.id,
            LikeModel.movie_id == movie_id
        )
    )
    result = await db.execute(like_stmt)
    like = result.scalars().first()

    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You haven't liked this movie yet."
        )

    await db.delete(like)
    await db.commit()

    return


@router.get(
    "/genres/",
    response_model=GenreListSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "moderator", "genres"]
)
async def get_genres(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> GenreListSchema:
    stmt = select(GenreModel)

    count_stmt = select(func.count(GenreModel.id)).select_from(stmt.subquery())
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return GenreListSchema(genres=[], total_pages=0, total_items=0)

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    genres: Sequence[GenreModel] = result.scalars().all()

    genre_list = [GenreSchema.model_validate(genre) for genre in genres]

    total_pages = (total_items + per_page - 1) // per_page

    return GenreListSchema(
        genres=genre_list,
        prev_page=f"/cinema/genres/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/cinema/genres/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/genres/{genre_id}/",
    response_model=GenreSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "moderator", "genres"]
)
async def get_genre_by_id(
    genre_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> GenreSchema:
    stmt = select(GenreModel).where(GenreModel.id == genre_id)
    result = await db.execute(stmt)
    genre = result.scalars().first()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre with the given id was not found."
        )

    return GenreSchema.model_validate(genre)


@router.post(
    "/genres/",
    response_model=GenreSchema,
    status_code=status.HTTP_201_CREATED,
    tags=["admin", "moderator", "genres"]
)
async def create_genre(
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> GenreSchema:
    stmt = select(GenreModel).where(GenreModel.name == data.name)
    result = await db.execute(stmt)
    existing_genre = result.scalars().first()

    if existing_genre:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A genre with the name '{data.name}' already exists."
        )

    genre = GenreModel(name=data.name)
    db.add(genre)
    await db.commit()
    await db.refresh(genre)

    return GenreSchema.model_validate(genre)


@router.patch(
    "/genres/{genre_id}/",
    response_model=GenreSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "moderator", "genres"]
)
async def update_genre(
    genre_id: int,
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> GenreSchema:
    stmt = select(GenreModel).where(GenreModel.id == genre_id)
    result = await db.execute(stmt)
    genre: GenreModel = result.scalars().first()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre with the given id was not found."
        )

    try:
        genre.name = data.name

        await db.commit()
        await db.refresh(genre)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data."
        )

    return GenreSchema.model_validate(genre)


@router.delete(
    "/genres/{genre_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["admin", "moderator", "genres"]
)
async def delete_genre(
    genre_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(GenreModel).where(GenreModel.id == genre_id)
    result = await db.execute(stmt)
    genre = result.scalars().first()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre with the given id was not found."
        )

    movies_check_stmt = select(func.count(MovieModel.id)).where(
        MovieModel.genres.any(GenreModel.id == genre_id)
    )
    result = await db.execute(movies_check_stmt)
    movies_count = result.scalar_one()

    if movies_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete genre: {movies_count} movies are associated with it"
        )

    await db.delete(genre)
    await db.commit()

    return


@router.get(
    "/stars/",
    response_model=StarListSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "moderator", "stars"]
)
async def get_stars(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, le=1, ge=100),
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> StarListSchema:
    stmt = select(StarModel)

    count_stmt = select(func.count(StarModel.id)).select_from(stmt.subquery())
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return StarListSchema(stars=[], total_pages=0, total_items=0)

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    stars: Sequence[StarModel] = result.scalars().all()

    star_list = [StarSchema.model_validate(star) for star in stars]

    total_pages = (total_items + per_page - 1) // per_page

    return StarListSchema(
        stars=star_list,
        prev_page=f"/cinema/stars/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/cinema/stars/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/stars/{star_id}/",
    response_model=StarSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "moderator", "stars"]
)
async def get_star_by_id(
    star_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> StarSchema:
    stmt = select(StarModel).where(StarModel.id == star_id)
    result = await db.execute(stmt)
    star = result.scalars().first()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star with the given id was not found."
        )

    return StarSchema.model_validate(star)


@router.post(
    "/stars/",
    response_model=StarSchema,
    status_code=status.HTTP_201_CREATED,
    tags=["admin", "moderator", "stars"]
)
async def create_star(
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> StarSchema:
    stmt = select(StarModel).where(StarModel.name == data.name)
    result = await db.execute(stmt)
    star = result.scalars().first()

    if star:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A star with the name '{data.name}' already exists."
        )

    star = StarModel(name=data.name)
    db.add(star)
    await db.commit()
    await db.refresh(star)

    return StarSchema.model_validate(star)


@router.patch(
    "/stars/{star_id}/",
    response_model=StarSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "moderator", "stars"]
)
async def update_star(
    star_id: int,
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> StarSchema:
    stmt = select(StarModel).where(StarModel.id == star_id)
    result = await db.execute(stmt)
    star = result.scalars().first()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star with the given id was not found."
        )

    try:
        star.name = data.name

        await db.commit()
        await db.refresh(star)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data."
        )

    return StarSchema.model_validate(star)


@router.delete(
    "/stars/{star_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["admin", "moderator", "stars"]
)
async def delete_star(
    star_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(StarModel).where(StarModel.id == star_id)
    result = await db.execute(stmt)
    star = result.scalars().first()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star with the given id was not found."
        )

    movies_check_stmt = select(func.count(MovieModel.id)).where(
        MovieModel.stars.any(StarModel.id == star_id)
    )
    result = await db.execute(movies_check_stmt)
    movies_count = result.scalar_one()

    if movies_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete star: {movies_count} movies are associated with it"
        )

    await db.delete(star)
    await db.commit()

    return


@router.get(
    "/director/",
    response_model=DirectorListSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "moderator", "stars"]
)
async def get_directors(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, le=1, ge=100),
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> DirectorListSchema:
    stmt = select(DirectorModel)

    count_stmt = (
        select(func.count(DirectorModel.id))
        .select_from(stmt.subquery())
    )
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return DirectorListSchema(directors=[], total_pages=0, total_items=0)

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    directors: Sequence[DirectorModel] = result.scalars().all()

    director_list = [
        DirectorSchema.model_validate(director) for director in directors
    ]

    total_pages = (total_items + per_page - 1) // per_page

    return DirectorListSchema(
        directors=director_list,
        prev_page=f"/cinema/directors/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/cinema/directors/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/directors/{director_id}/",
    response_model=DirectorSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "moderator", "directors"]
)
async def get_director_by_id(
    director_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> DirectorSchema:
    stmt = select(DirectorModel).where(DirectorModel.id == director_id)
    result = await db.execute(stmt)
    director = result.scalars().first()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director with the given id was not found."
        )

    return DirectorSchema.model_validate(director)


@router.post(
    "/directors/",
    response_model=DirectorSchema,
    status_code=status.HTTP_201_CREATED,
    tags=["admin", "moderator", "directors"]
)
async def create_director(
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> DirectorSchema:
    stmt = select(DirectorModel).where(DirectorModel.name == data.name)
    result = await db.execute(stmt)
    director = result.scalars().first()

    if director:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A director with the name '{data.name}' already exists."
        )

    director = DirectorModel(name=data.name)
    db.add(director)
    await db.commit()
    await db.refresh(director)

    return DirectorSchema.model_validate(director)


@router.patch(
    "/directors/{director_id}/",
    response_model=DirectorSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "moderator", "directors"]
)
async def update_director(
    director_id: int,
    data: NameSchema,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> DirectorSchema:
    stmt = select(DirectorModel).where(DirectorModel.id == director_id)
    result = await db.execute(stmt)
    director = result.scalars().first()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director with the given id was not found."
        )

    try:
        director.name = data.name

        await db.commit()
        await db.refresh(director)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data."
        )

    return DirectorSchema.model_validate(director)


@router.delete(
    "/directors/{director_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["admin", "moderator", "directors"]
)
async def delete_director(
    director_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(DirectorModel).where(DirectorModel.id == director_id)
    result = await db.execute(stmt)
    director = result.scalars().first()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director with the given id was not found"
        )

    movies_check_stmt = select(func.count(MovieModel.id)).where(
        MovieModel.genres.any(DirectorModel.id == director_id)
    )
    result = await db.execute(movies_check_stmt)
    movies_count = result.scalar_one()

    if movies_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete director: {movies_count} movies are associated with it"
        )

    await db.delete(director)
    await db.commit()

    return
