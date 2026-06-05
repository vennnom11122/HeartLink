from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.db.models import (
    Block,
    Complaint,
    ComplaintStatus,
    Gender,
    LookingForGender,
    Photo,
    PhotoModerationStatus,
    Profile,
    ProfileView,
    Rating,
    User,
)
from app.db.repositories.profiles import ProfileRepository
from app.services.limit_service import DailyAction, LimitService


class SearchService:
    def __init__(self, session: AsyncSession, settings: Settings, limit_service: LimitService) -> None:
        self.session = session
        self.settings = settings
        self.limit_service = limit_service
        self.profile_repo = ProfileRepository(session)

    async def get_next_profile_for_viewer(self, viewer_profile_id: int) -> Profile | None:
        viewer = await self.profile_repo.get(viewer_profile_id)
        if viewer is None:
            raise ValueError("Анкета зрителя не найдена.")

        search_settings = await self.profile_repo.ensure_search_settings(viewer)

        approved_photo_exists = exists(
            select(Photo.id).where(
                Photo.profile_id == Profile.id,
                Photo.is_approved.is_(True),
                Photo.moderation_status == PhotoModerationStatus.APPROVED,
            )
        )

        block_exists = exists(
            select(Block.id).where(
                or_(
                    and_(Block.blocker_profile_id == viewer_profile_id, Block.blocked_profile_id == Profile.id),
                    and_(Block.blocker_profile_id == Profile.id, Block.blocked_profile_id == viewer_profile_id),
                )
            )
        )

        view_cutoff = datetime.now(timezone.utc) - timedelta(days=self.settings.profile_recent_view_days)
        recent_view_exists = exists(
            select(ProfileView.id).where(
                ProfileView.viewer_profile_id == viewer_profile_id,
                ProfileView.viewed_profile_id == Profile.id,
                ProfileView.created_at >= view_cutoff,
            )
        )

        rating_cutoff = datetime.now(timezone.utc) - timedelta(days=self.settings.rating_repeat_cooldown_days)
        recent_rating_exists = exists(
            select(Rating.id).where(
                Rating.from_profile_id == viewer_profile_id,
                Rating.to_profile_id == Profile.id,
                Rating.updated_at >= rating_cutoff,
            )
        )

        open_complaint_exists = exists(
            select(Complaint.id).where(
                Complaint.from_profile_id == viewer_profile_id,
                Complaint.to_profile_id == Profile.id,
                Complaint.status.in_([ComplaintStatus.NEW, ComplaintStatus.IN_PROGRESS]),
            )
        )

        stmt = (
            select(Profile)
            .join(User, User.id == Profile.user_id)
            .where(
                Profile.id != viewer_profile_id,
                Profile.is_active.is_(True),
                Profile.is_hidden.is_(False),
                User.is_banned.is_(False),
                User.is_blocked.is_(False),
                approved_photo_exists,
                ~block_exists,
                ~open_complaint_exists,
                ~recent_view_exists,
                ~recent_rating_exists,
                Profile.age >= search_settings.min_age,
                Profile.age <= search_settings.max_age,
                Profile.min_age_preference <= viewer.age,
                Profile.max_age_preference >= viewer.age,
                or_(
                    Profile.rating_count < self.settings.min_public_rating_count,
                    Profile.rating_avg >= self.settings.min_public_rating,
                ),
            )
            .options(selectinload(Profile.city), selectinload(Profile.photos), selectinload(Profile.user))
        )

        if search_settings.gender_filter != LookingForGender.ANY:
            stmt = stmt.where(Profile.gender == Gender(search_settings.gender_filter.value))

        accepted_by_candidate = [LookingForGender.ANY]
        if viewer.gender in (Gender.MALE, Gender.FEMALE):
            accepted_by_candidate.append(LookingForGender(viewer.gender.value))
        stmt = stmt.where(Profile.looking_for_gender.in_(accepted_by_candidate))

        city_ids = [int(city_id) for city_id in (search_settings.city_ids or [])]
        if not search_settings.show_other_cities:
            stmt = stmt.where(Profile.city_id.in_(city_ids or [viewer.city_id]))

        city_priority = case((Profile.city_id == viewer.city_id, 0), else_=1)
        new_profile_priority = case((Profile.rating_count < self.settings.min_public_rating_count, 0), else_=1)
        stmt = stmt.order_by(city_priority, new_profile_priority, User.last_active_at.desc(), Profile.created_at.desc())

        return await self.session.scalar(stmt.limit(1))

    async def record_view(self, viewer_profile_id: int, viewed_profile_id: int) -> ProfileView:
        await self.limit_service.increment(viewer_profile_id, DailyAction.VIEW)
        view = ProfileView(viewer_profile_id=viewer_profile_id, viewed_profile_id=viewed_profile_id)
        self.session.add(view)
        await self.session.flush()
        return view
