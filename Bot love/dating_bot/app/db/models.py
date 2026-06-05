from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class LookingForGender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    ANY = "any"


class PhotoModerationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LikeSource(str, enum.Enum):
    RATING = "rating"
    VALENTINE = "valentine"
    DIRECT_LIKE = "direct_like"


class ValentineStatus(str, enum.Enum):
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ComplaintReason(str, enum.Enum):
    FAKE = "fake_profile"
    INSULTS = "insults"
    SPAM = "spam"
    UNDERAGE = "underage"
    BAD_PHOTO = "inappropriate_photo"
    FRAUD = "fraud"
    OTHER = "other"


class ComplaintStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class AuditEventType(str, enum.Enum):
    USER_REGISTERED = "user_registered"
    PROFILE_CREATED = "profile_created"
    PROFILE_UPDATED = "profile_updated"
    PHOTO_UPLOADED = "photo_uploaded"
    RATING_CREATED = "rating_created"
    VALENTINE_SENT = "valentine_sent"
    MATCH_CREATED = "match_created"
    COMPLAINT_CREATED = "complaint_created"
    PROFILE_BLOCKED = "profile_blocked"
    USER_BANNED = "user_banned"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ERROR = "error"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    language_code: Mapped[str | None] = mapped_column(String(16))
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_moderator: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    ban_reason: Mapped[str | None] = mapped_column(Text)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped["Profile | None"] = relationship(back_populates="user", cascade="all, delete-orphan")


class City(Base):
    __tablename__ = "cities"
    __table_args__ = (
        UniqueConstraint("name", "region", name="uq_cities_name_region"),
        Index("ix_cities_name", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False)
    population: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    profiles: Mapped[list["Profile"]] = relationship(back_populates="city")


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("age >= 18 AND age <= 99", name="ck_profiles_age_18_99"),
        CheckConstraint("length(display_name) > 0", name="ck_profiles_display_name_not_empty"),
        CheckConstraint("length(bio) <= 500", name="ck_profiles_bio_max_500"),
        CheckConstraint("min_age_preference >= 18", name="ck_profiles_min_age_pref_18"),
        CheckConstraint("max_age_preference <= 99", name="ck_profiles_max_age_pref_99"),
        CheckConstraint("min_age_preference <= max_age_preference", name="ck_profiles_age_pref_order"),
        CheckConstraint("rating_avg >= 0 AND rating_avg <= 10", name="ck_profiles_rating_avg_range"),
        CheckConstraint("rating_count >= 0", name="ck_profiles_rating_count_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[Gender] = mapped_column(SAEnum(Gender, name="gender", native_enum=False), nullable=False)
    looking_for_gender: Mapped[LookingForGender] = mapped_column(
        SAEnum(LookingForGender, name="looking_for_gender", native_enum=False),
        nullable=False,
    )
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), index=True)
    bio: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    rating_avg: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.00"), server_default="0")
    rating_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    min_age_preference: Mapped[int] = mapped_column(Integer, default=18, server_default="18")
    max_age_preference: Mapped[int] = mapped_column(Integer, default=99, server_default="99")

    user: Mapped[User] = relationship(back_populates="profile")
    city: Mapped[City] = relationship(back_populates="profiles")
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="Photo.position",
    )
    search_settings: Mapped["SearchSettings | None"] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class Photo(Base):
    __tablename__ = "photos"
    __table_args__ = (
        CheckConstraint("position >= 1 AND position <= 6", name="ck_photos_position_1_6"),
        Index("ix_photos_profile_main", "profile_id", "is_main"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    telegram_file_id: Mapped[str] = mapped_column(String(512), nullable=False)
    file_unique_id: Mapped[str] = mapped_column(String(256), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    moderation_status: Mapped[PhotoModerationStatus] = mapped_column(
        SAEnum(PhotoModerationStatus, name="photo_moderation_status", native_enum=False),
        default=PhotoModerationStatus.PENDING,
        server_default=PhotoModerationStatus.PENDING.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped[Profile] = relationship(back_populates="photos")


class ProfileView(Base):
    __tablename__ = "profile_views"
    __table_args__ = (
        Index("ix_profile_views_viewer_created", "viewer_profile_id", "created_at"),
        UniqueConstraint("viewer_profile_id", "viewed_profile_id", "created_at", name="uq_profile_views_once_at_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    viewer_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    viewed_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        CheckConstraint("score >= 1 AND score <= 10", name="ck_ratings_score_1_10"),
        UniqueConstraint("from_profile_id", "to_profile_id", name="uq_ratings_from_to"),
        Index("ix_ratings_to_profile", "to_profile_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    from_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    to_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("from_profile_id", "to_profile_id", "source", name="uq_likes_from_to_source"),
        Index("ix_likes_to_profile", "to_profile_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    from_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    to_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    source: Mapped[LikeSource] = mapped_column(
        SAEnum(LikeSource, name="like_source", native_enum=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("profile1_id < profile2_id", name="ck_matches_profile_order"),
        UniqueConstraint("profile1_id", "profile2_id", name="uq_matches_profiles"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile1_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    profile2_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    conversation: Mapped["Conversation | None"] = relationship(back_populates="match", cascade="all, delete-orphan")


class Valentine(Base):
    __tablename__ = "valentines"
    __table_args__ = (
        CheckConstraint("message IS NULL OR length(message) <= 300", name="ck_valentines_message_max_300"),
        Index("ix_valentines_to_status", "to_profile_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    from_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    to_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    message: Mapped[str | None] = mapped_column(String(300))
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    status: Mapped[ValentineStatus] = mapped_column(
        SAEnum(ValentineStatus, name="valentine_status", native_enum=False),
        default=ValentineStatus.SENT,
        server_default=ValentineStatus.SENT.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint("comment IS NULL OR length(comment) <= 500", name="ck_complaints_comment_max_500"),
        Index("ix_complaints_to_status", "to_profile_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    from_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    to_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    reason: Mapped[ComplaintReason] = mapped_column(
        SAEnum(ComplaintReason, name="complaint_reason", native_enum=False),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[ComplaintStatus] = mapped_column(
        SAEnum(ComplaintStatus, name="complaint_status", native_enum=False),
        default=ComplaintStatus.NEW,
        server_default=ComplaintStatus.NEW.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    moderator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (
        UniqueConstraint("blocker_profile_id", "blocked_profile_id", name="uq_blocks_blocker_blocked"),
        Index("ix_blocks_blocked", "blocked_profile_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    blocker_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    blocked_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyLimit(Base):
    __tablename__ = "daily_limits"
    __table_args__ = (
        UniqueConstraint("profile_id", "date", name="uq_daily_limits_profile_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    ratings_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    valentines_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    likes_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    views_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    complaints_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class SearchSettings(Base, TimestampMixin):
    __tablename__ = "search_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, index=True)
    city_ids: Mapped[list[int]] = mapped_column(JSON, default=list, server_default="[]")
    min_age: Mapped[int] = mapped_column(Integer, default=18, server_default="18")
    max_age: Mapped[int] = mapped_column(Integer, default=99, server_default="99")
    gender_filter: Mapped[LookingForGender] = mapped_column(
        SAEnum(LookingForGender, name="search_gender_filter", native_enum=False),
        default=LookingForGender.ANY,
        server_default=LookingForGender.ANY.value,
        nullable=False,
    )
    show_other_cities: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    profile: Mapped[Profile] = relationship(back_populates="search_settings")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_conversations_match"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    profile1_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    profile2_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    match: Mapped[Match] = relationship(back_populates="conversation")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("length(text) > 0 AND length(text) <= 1000", name="ck_messages_text_len"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    from_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    to_profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_event_created", "event_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[AuditEventType] = mapped_column(
        SAEnum(AuditEventType, name="audit_event_type", native_enum=False),
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

