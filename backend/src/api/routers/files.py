"""HTTP surface for files. Transport only: no rules, no queries."""

from collections.abc import AsyncIterator, Sequence

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import FileResponse

from src.api.deps import FileServiceDep, LimitDep, SettingsDep
from src.api.schemas import FileItem, FileUpdate
from src.domain.models import StoredFile

router = APIRouter(tags=["files"])


@router.get("/files", response_model=list[FileItem])
async def list_files(service: FileServiceDep, limit: LimitDep) -> Sequence[StoredFile]:
    return await service.list_files(limit=limit)


@router.post("/files", response_model=FileItem, status_code=status.HTTP_201_CREATED)
async def create_file(
    service: FileServiceDep,
    settings: SettingsDep,
    title: str = Form(...),
    file: UploadFile = File(...),
) -> StoredFile:
    async def chunks() -> AsyncIterator[bytes]:
        while chunk := await file.read(settings.upload_chunk_bytes):
            yield chunk

    return await service.create_file(
        title=title,
        filename=file.filename,
        content_type=file.content_type,
        chunks=chunks(),
    )


@router.get("/files/{file_id}", response_model=FileItem)
async def get_file(file_id: str, service: FileServiceDep) -> StoredFile:
    return await service.get_file(file_id)


@router.patch("/files/{file_id}", response_model=FileItem)
async def update_file(file_id: str, payload: FileUpdate, service: FileServiceDep) -> StoredFile:
    return await service.update_file(file_id, title=payload.title)


@router.get("/files/{file_id}/download")
async def download_file(file_id: str, service: FileServiceDep) -> FileResponse:
    file_item, path = await service.open_for_download(file_id)
    return FileResponse(
        path=path,
        media_type=file_item.mime_type,
        filename=file_item.original_name,
    )


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: str, service: FileServiceDep) -> None:
    await service.delete_file(file_id)
