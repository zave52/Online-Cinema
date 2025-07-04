import asyncio
from typing import Sequence, Optional

from fastapi import (
    APIRouter,
    status,
    Depends,
    Query,
    HTTPException,
    BackgroundTasks
)
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from config.dependencies import RoleChecker, get_current_user, get_email_sender
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
from notifications.interfaces import EmailSenderInterface
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
    DirectorSchema,
    GenreWithMovieCountSchema,
    RateMovieSchema,
    CommentSchema,
    CommentMovieRequestSchema
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
    tags=["movies"]
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
        prev_page=f"/cinema/movies/likes/?page={page - 1}&per_page={per_page}{f'&sort_by={sort_by}' if sort_by else ''}" if page > 1 else None,
        next_page=f"/cinema/movies/likes/?page={page + 1}&per_page={per_page}{f'&sort_by={sort_by}' if sort_by else ''}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get(
    "/movies/favorites/",
    response_model=MovieListResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["favorites", "movies"]
)
async def get_favorite_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MovieListResponseSchema:
    count_stmt = (
        select(func.count(MovieModel.id))
        .where(
            MovieModel.favorites.any(FavoriteMovieModel.user_id == user.id)
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
            MovieModel.favorites.any(FavoriteMovieModel.user_id == user.id)
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
        prev_page=f"/cinema/movies/favorites/?page={page - 1}&per_page={per_page}{f'&sort_by={sort_by}' if sort_by else ''}" if page > 1 else None,
        next_page=f"/cinema/movies/favorites/?page={page + 1}&per_page={per_page}{f'&sort_by={sort_by}' if sort_by else ''}" if page < total_pages else None,
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
    responses={
        status.HTTP_204_NO_CONTENT: {},
        status.HTTP_200_OK: {"model": MessageResponseSchema}
    },
    tags=["admin", "moderator"]
)
async def delete_movie(
    movie_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> MessageResponseSchema | None:
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
        .where(UserModel.cart.any(MovieModel.id == movie_id))
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


@router.post(
    "/movies/{movie_id}/comments/",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED,
    tags=["comments", "movies"]
)
async def comment_movie(
    movie_id: int,
    data: CommentMovieRequestSchema,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CommentSchema:
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    comment = CommentModel(
        content=data.content,
        movie_id=movie_id,
        user_id=user.id
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return CommentSchema.model_validate(comment)


@router.post(
    "/movies/{movie_id}/comments/{comment_id}/replies/",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED,
    tags=["comments", "movies"]
)
async def reply_to_comment(
    movie_id: int,
    comment_id: int,
    background_tasks: BackgroundTasks,
    data: CommentMovieRequestSchema,
    user: UserModel = Depends(get_current_user),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
    db: AsyncSession = Depends(get_db)
) -> CommentSchema:
    movie_stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(movie_stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given id was not found."
        )

    parent_comment_stmt = (
        select(CommentModel)
        .options(joinedload(CommentModel.user))
        .where(
            CommentModel.id == comment_id,
            CommentModel.movie_id == movie_id
        )
    )
    result = await db.execute(parent_comment_stmt)
    parent_comment = result.scalars().first()

    if not parent_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment with the given id was not found for this movie."
        )

    reply = CommentModel(
        content=data.content,
        movie_id=movie_id,
        user_id=user.id,
        parent_id=comment_id
    )

    db.add(reply)
    await db.commit()
    await db.refresh(reply)

    background_tasks.add_task(
        email_sender.send_comment_reply_notification_email,
        parent_comment.user.email,
        parent_comment.id,
        reply.content,
        user.email
    )

    return CommentSchema.model_validate(reply)


@router.delete(
    "/movies/{movie_id}/comments/{comment_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["comments", "movies"]
)
async def delete_comment(
    movie_id: int,
    comment_id: int,
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

    comment_stmt = (
        select(CommentModel)
        .where(
            CommentModel.id == comment_id,
            CommentModel.movie_id == movie_id
        )
    )
    result = await db.execute(comment_stmt)
    comment: CommentModel = result.scalars().first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment with the given id was not found for this movie."
        )

    if comment.user_id != user.id and user.group.name not in (
            UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this comment."
        )

    await db.delete(comment)
    await db.commit()

    return


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


@router.post(
    "/movies/{movie_id}/favorites/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["favorites", "movies"]
)
async def add_movie_to_favorites(
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

    favorite_stmt = (
        select(FavoriteMovieModel)
        .where(
            FavoriteMovieModel.movie_id == movie_id,
            FavoriteMovieModel.user_id == user.id
        )
    )
    result = await db.execute(favorite_stmt)
    existing_favorite = result.scalars().first()

    if existing_favorite:
        return MessageResponseSchema(
            message="You have already added this movie to favorites."
        )

    new_favorite = FavoriteMovieModel(movie_id=movie_id, user_id=user.id)
    db.add(new_favorite)
    await db.commit()

    return MessageResponseSchema(
        message="You successfully added this movie to favorites."
    )


@router.delete(
    "/movies/{movie_id}/favorites/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["favorites", "movies"]
)
async def remove_movie_from_favorites(
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

    favorite_stmt = (
        select(FavoriteMovieModel)
        .where(
            FavoriteMovieModel.movie_id == movie_id,
            FavoriteMovieModel.user_id == user.id
        )
    )
    result = await db.execute(favorite_stmt)
    favorite = result.scalars().first()

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This movie is not in your favorites."
        )

    await db.delete(favorite)
    await db.commit()

    return


@router.post(
    "/movies/{movie_id}/rates/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    tags=["rates", "movies"]
)
async def rate_movie(
    movie_id: int,
    data: RateMovieSchema,
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

    rate_stmt = (
        select(RateMovieModel)
        .where(
            RateMovieModel.movie_id == movie_id,
            RateMovieModel.user_id == user.id
        )
    )
    result = await db.execute(rate_stmt)
    existing_rate: RateMovieModel = result.scalars().first()

    if existing_rate:
        previous_rate = existing_rate.rate
        existing_rate.rate = data.rate
        await db.commit()

        return MessageResponseSchema(
            message=f"You changed your rating for the movie "
                    f"from {previous_rate} to {existing_rate.rate}."
        )

    new_rate = RateMovieModel(
        rate=data.rate,
        movie_id=movie_id,
        user_id=user.id
    )
    db.add(new_rate)
    await db.commit()

    return MessageResponseSchema(
        message=f"You gave the movie a rating of {new_rate.rate}."
    )


@router.delete(
    "/movies/{movie_id}/rates/",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["rates", "movies"]
)
async def delete_rate(
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

    rate_stmt = (
        select(RateMovieModel)
        .where(
            RateMovieModel.movie_id == movie_id,
            RateMovieModel.user_id == user.id
        )
    )
    result = await db.execute(rate_stmt)
    rate: RateMovieModel = result.scalars().first()

    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You haven't rated this movie yet."
        )

    await db.delete(rate)
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
    subquery = (
        select(
            GenreModel.id,
            func.count(MovieModel.id).label("movie_count")
        )
        .join(MovieModel.genres)
        .group_by(GenreModel.id)
        .subquery()
    )

    stmt = (
        select(GenreModel, subquery.c.movie_count)
        .outerjoin(subquery, GenreModel.id == subquery.c.id)
    )

    count_stmt = select(func.count(GenreModel.id))
    result = await db.execute(count_stmt)
    total_items = result.scalar_one()

    if not total_items:
        return GenreListSchema(genres=[], total_pages=0, total_items=0)

    offset = (page - 1) * per_page

    stmt = stmt.offset(offset).limit(per_page).order_by(GenreModel.name)
    result = await db.execute(stmt)
    genres_with_counts = result.all()

    genre_list = [
        GenreWithMovieCountSchema(
            id=genre.id,
            name=genre.name,
            movie_count=count or 0
        )
        for genre, count in genres_with_counts
    ]

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
    response_model=GenreWithMovieCountSchema,
    status_code=status.HTTP_200_OK,
    tags=["admin", "moderator", "genres"]
)
async def get_genre_by_id(
    genre_id: int,
    authorized: None = Depends(moderator_and_admin),
    db: AsyncSession = Depends(get_db)
) -> GenreWithMovieCountSchema:
    stmt = select(GenreModel).where(GenreModel.id == genre_id)
    result = await db.execute(stmt)
    genre: GenreModel = result.scalars().first()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre with the given id was not found."
        )

    movie_count_stmt = (
        select(func.count(MovieModel.id))
        .where(MovieModel.genres.any(GenreModel.id == genre_id))
    )
    result = await db.execute(movie_count_stmt)
    movie_count = result.scalar_one()

    return GenreWithMovieCountSchema(
        id=genre_id,
        name=genre.name,
        movie_count=movie_count
    )


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
    per_page: int = Query(10, ge=1, le=100),
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
    per_page: int = Query(10, ge=1, le=100),
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
