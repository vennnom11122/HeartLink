from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import City
from app.utils.constants import POPULAR_CITY_NAMES


class CityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, city_id: int) -> City | None:
        return await self.session.get(City, city_id)

    async def get_by_name(self, name: str) -> City | None:
        return await self.session.scalar(
            select(City).where(func.lower(City.name) == name.strip().lower(), City.is_active.is_(True))
        )

    async def popular(self) -> list[City]:
        cities = (
            await self.session.scalars(
                select(City).where(City.name.in_(POPULAR_CITY_NAMES), City.is_active.is_(True))
            )
        ).all()
        by_name = {city.name: city for city in cities}
        return [by_name[name] for name in POPULAR_CITY_NAMES if name in by_name]

    async def search(self, query: str, *, limit: int = 10) -> list[City]:
        pattern = f"%{query.strip()}%"
        stmt: Select[tuple[City]] = (
            select(City)
            .where(City.is_active.is_(True), City.name.ilike(pattern))
            .order_by(City.population.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())

    async def page(self, *, page: int = 1, per_page: int = 10) -> list[City]:
        page = max(page, 1)
        return list(
            (
                await self.session.scalars(
                    select(City)
                    .where(City.is_active.is_(True))
                    .order_by(City.population.desc())
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                )
            ).all()
        )

