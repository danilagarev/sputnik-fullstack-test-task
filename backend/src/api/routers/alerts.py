"""HTTP surface for alerts."""

from collections.abc import Sequence

from fastapi import APIRouter

from src.api.deps import FileServiceDep, LimitDep
from src.api.schemas import AlertItem
from src.domain.models import Alert

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertItem])
async def list_alerts(service: FileServiceDep, limit: LimitDep) -> Sequence[Alert]:
    return await service.list_alerts(limit=limit)
