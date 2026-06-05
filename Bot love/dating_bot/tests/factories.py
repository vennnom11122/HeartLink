from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import City, Gender, LookingForGender, Photo, PhotoModerationStatus, Profile, User


async def create_city(session: AsyncSession, name: str = "Москва") -> City:
    city = City(name=name, region=name, population=1_000_000)
    session.add(city)
    await session.flush()
    return city


async def create_profile(
    session: AsyncSession,
    *,
    telegram_id: int,
    city: City,
    gender: Gender = Gender.FEMALE,
    looking_for_gender: LookingForGender = LookingForGender.ANY,
    age: int = 25,
    rating_avg: float = 0,
    rating_count: int = 0,
    active: bool = True,
    approved_photo: bool = True,
    min_age_preference: int = 18,
    max_age_preference: int = 99,
) -> Profile:
    user = User(telegram_id=telegram_id, first_name=f"User{telegram_id}")
    session.add(user)
    await session.flush()
    profile = Profile(
        user_id=user.id,
        display_name=f"User{telegram_id}",
        age=age,
        gender=gender,
        looking_for_gender=looking_for_gender,
        city_id=city.id,
        bio="Люблю прогулки и хороший кофе",
        is_active=active,
        rating_avg=rating_avg,
        rating_count=rating_count,
        min_age_preference=min_age_preference,
        max_age_preference=max_age_preference,
    )
    session.add(profile)
    await session.flush()
    if approved_photo:
        session.add(
            Photo(
                profile_id=profile.id,
                telegram_file_id=f"file-{telegram_id}",
                file_unique_id=f"unique-{telegram_id}",
                position=1,
                is_main=True,
                is_approved=True,
                moderation_status=PhotoModerationStatus.APPROVED,
            )
        )
    await session.flush()
    return profile
