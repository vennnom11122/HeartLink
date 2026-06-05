from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEventType, AuditLog, Gender, LookingForGender, Photo, Profile, SearchSettings, User
from app.db.repositories.photos import PhotoRepository
from app.utils.constants import MAX_PROFILE_PHOTOS, MIN_PROFILE_PHOTOS
from app.utils.validators import validate_bio, validate_name


@dataclass(frozen=True)
class ProfileCreateDTO:
    display_name: str
    age: int
    gender: Gender
    looking_for_gender: LookingForGender
    city_id: int
    bio: str


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.photos = PhotoRepository(session)

    async def create_profile(self, user: User, data: ProfileCreateDTO) -> Profile:
        name_ok, name_error = validate_name(data.display_name)
        if not name_ok:
            raise ValueError(name_error or "Имя не подходит.")
        bio_ok, bio_error = validate_bio(data.bio)
        if not bio_ok:
            raise ValueError(bio_error or "Описание не подходит.")
        if data.age < 18:
            raise ValueError("Пользователь младше 18 не допускается.")
        existing = await self.session.scalar(select(Profile.id).where(Profile.user_id == user.id))
        if existing is not None:
            raise ValueError("У пользователя уже есть анкета.")

        profile = Profile(
            user_id=user.id,
            display_name=data.display_name.strip(),
            age=data.age,
            gender=data.gender,
            looking_for_gender=data.looking_for_gender,
            city_id=data.city_id,
            bio=data.bio.strip(),
            is_active=False,
            min_age_preference=18,
            max_age_preference=99,
        )
        self.session.add(profile)
        await self.session.flush()

        self.session.add(
            SearchSettings(
                profile_id=profile.id,
                city_ids=[data.city_id],
                min_age=18,
                max_age=99,
                gender_filter=data.looking_for_gender,
                show_other_cities=False,
            )
        )
        self.session.add(
            AuditLog(
                event_type=AuditEventType.PROFILE_CREATED,
                user_id=user.id,
                profile_id=profile.id,
                payload={"city_id": data.city_id},
            )
        )
        await self.session.flush()
        return profile

    async def add_photo(self, profile_id: int, telegram_file_id: str, file_unique_id: str) -> Photo:
        profile = await self.session.get(Profile, profile_id)
        if profile is None:
            raise ValueError("Анкета не найдена.")
        count = await self.photos.count_for_profile(profile_id)
        if count >= MAX_PROFILE_PHOTOS:
            raise ValueError(f"Можно загрузить максимум {MAX_PROFILE_PHOTOS} фото.")
        photo = await self.photos.add_photo(profile_id, telegram_file_id, file_unique_id)
        self.session.add(
            AuditLog(
                event_type=AuditEventType.PHOTO_UPLOADED,
                profile_id=profile_id,
                payload={"photo_id": photo.id},
            )
        )
        return photo

    async def set_main_photo(self, profile_id: int, photo_id: int) -> Photo:
        photo = await self.photos.set_main(profile_id, photo_id)
        self.session.add(
            AuditLog(
                event_type=AuditEventType.PROFILE_UPDATED,
                profile_id=profile_id,
                payload={"main_photo_id": photo_id},
            )
        )
        await self.session.flush()
        return photo

    async def delete_photo(self, profile_id: int, photo_id: int) -> None:
        await self.photos.delete_photo(profile_id, photo_id)
        if await self.photos.count_for_profile(profile_id) == 0:
            profile = await self.session.get(Profile, profile_id)
            if profile is not None:
                profile.is_active = False
        self.session.add(
            AuditLog(
                event_type=AuditEventType.PROFILE_UPDATED,
                profile_id=profile_id,
                payload={"deleted_photo_id": photo_id},
            )
        )
        await self.session.flush()

    async def activate_if_ready(self, profile_id: int) -> Profile:
        profile = await self.session.get(Profile, profile_id)
        if profile is None:
            raise ValueError("Анкета не найдена.")
        count = await self.photos.count_for_profile(profile_id)
        if count < MIN_PROFILE_PHOTOS:
            raise ValueError("Нужно загрузить хотя бы одно фото.")
        profile.is_active = True
        await self.session.flush()
        return profile

    async def hide(self, profile_id: int, *, hidden: bool = True) -> None:
        profile = await self.session.get(Profile, profile_id)
        if profile is None:
            raise ValueError("Анкета не найдена.")
        profile.is_hidden = hidden
        self.session.add(
            AuditLog(
                event_type=AuditEventType.PROFILE_UPDATED,
                profile_id=profile_id,
                payload={"is_hidden": hidden},
            )
        )
        await self.session.flush()

    async def delete(self, profile_id: int) -> None:
        profile = await self.session.get(Profile, profile_id)
        if profile is not None:
            await self.session.delete(profile)

    @staticmethod
    def format_profile(profile: Profile, *, include_rating: bool = True) -> str:
        city_name = profile.city.name if profile.city else "Город не указан"
        lines = [
            f"{profile.display_name}, {profile.age}",
            city_name,
            "",
            profile.bio,
        ]
        if include_rating:
            rating = float(profile.rating_avg or 0)
            if profile.rating_count:
                lines.extend(["", f"Рейтинг анкеты: {rating:.1f} ⭐"])
            else:
                lines.extend(["", "Рейтинг анкеты: пока мало оценок"])
        return "\n".join(lines)
