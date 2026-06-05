from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEventType, AuditLog, Block, Conversation, Like, LikeSource, Match


@dataclass(frozen=True)
class MatchResult:
    match: Match | None
    created: bool
    is_mutual: bool


class MatchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_like(self, from_profile_id: int, to_profile_id: int, source: LikeSource) -> MatchResult:
        if from_profile_id == to_profile_id:
            raise ValueError("Нельзя поставить симпатию самому себе.")
        if await self._has_block_between(from_profile_id, to_profile_id):
            raise ValueError("Нельзя поставить симпатию заблокированному пользователю.")

        like = await self.session.scalar(
            select(Like).where(
                Like.from_profile_id == from_profile_id,
                Like.to_profile_id == to_profile_id,
                Like.source == source,
            )
        )
        if like is None:
            self.session.add(Like(from_profile_id=from_profile_id, to_profile_id=to_profile_id, source=source))

        reciprocal_like = await self.session.scalar(
            select(Like).where(
                Like.from_profile_id == to_profile_id,
                Like.to_profile_id == from_profile_id,
            )
        )
        if reciprocal_like is None:
            await self.session.flush()
            return MatchResult(match=None, created=False, is_mutual=False)

        match, created = await self.ensure_match(from_profile_id, to_profile_id)
        return MatchResult(match=match, created=created, is_mutual=True)

    async def remove_like(self, from_profile_id: int, to_profile_id: int, source: LikeSource) -> Match | None:
        await self.session.execute(
            delete(Like).where(
                Like.from_profile_id == from_profile_id,
                Like.to_profile_id == to_profile_id,
                Like.source == source,
            )
        )
        await self.session.flush()

        match = await self._get_match(from_profile_id, to_profile_id)
        if match is not None and not await self._has_mutual_interest(from_profile_id, to_profile_id):
            match.is_active = False
            await self.session.flush()
        return match

    async def ensure_match(self, profile_a_id: int, profile_b_id: int) -> tuple[Match, bool]:
        profile1_id, profile2_id = sorted((profile_a_id, profile_b_id))
        match = await self._get_match(profile_a_id, profile_b_id)
        if match is not None:
            if not match.is_active:
                match.is_active = True
                await self.session.flush()
            return match, False

        match = Match(profile1_id=profile1_id, profile2_id=profile2_id)
        self.session.add(match)
        await self.session.flush()

        conversation = Conversation(
            match_id=match.id,
            profile1_id=profile1_id,
            profile2_id=profile2_id,
        )
        self.session.add(conversation)
        self.session.add(
            AuditLog(
                event_type=AuditEventType.MATCH_CREATED,
                profile_id=profile1_id,
                payload={"profile1_id": profile1_id, "profile2_id": profile2_id},
            )
        )
        await self.session.flush()
        return match, True

    async def _get_match(self, profile_a_id: int, profile_b_id: int) -> Match | None:
        profile1_id, profile2_id = sorted((profile_a_id, profile_b_id))
        return await self.session.scalar(
            select(Match).where(Match.profile1_id == profile1_id, Match.profile2_id == profile2_id)
        )

    async def _has_mutual_interest(self, profile_a_id: int, profile_b_id: int) -> bool:
        a_likes_b = await self.session.scalar(
            select(Like.id).where(
                Like.from_profile_id == profile_a_id,
                Like.to_profile_id == profile_b_id,
            )
        )
        b_likes_a = await self.session.scalar(
            select(Like.id).where(
                Like.from_profile_id == profile_b_id,
                Like.to_profile_id == profile_a_id,
            )
        )
        return a_likes_b is not None and b_likes_a is not None

    async def _has_block_between(self, profile_a_id: int, profile_b_id: int) -> bool:
        block_id = await self.session.scalar(
            select(Block.id).where(
                or_(
                    (Block.blocker_profile_id == profile_a_id) & (Block.blocked_profile_id == profile_b_id),
                    (Block.blocker_profile_id == profile_b_id) & (Block.blocked_profile_id == profile_a_id),
                )
            )
        )
        return block_id is not None
