"""All queries against the alerts table."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AlertLevel
from src.domain.models import Alert


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, limit: int) -> Sequence[Alert]:
        statement = select(Alert).order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit)
        result = await self._session.execute(statement)
        return result.scalars().all()

    def add(self, *, file_id: str, level: AlertLevel, message: str) -> Alert:
        alert = Alert(file_id=file_id, level=level.value, message=message)
        self._session.add(alert)
        return alert
