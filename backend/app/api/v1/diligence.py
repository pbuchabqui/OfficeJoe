"""Endpoints for diligences (requests for additional information/documents)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.diligence import (
    DiligenceCreateRequest,
    DiligenceDetailedResponse,
    DiligenceItemCreateRequest,
    DiligenceItemResponse,
    DiligenceItemUpdateRequest,
    DiligencePaginatedResponse,
    DiligenceResponse,
    DiligenceUpdateRequest,
)
from app.services.diligence_service import (
    create_diligence,
    read_diligence,
    update_diligence,
    delete_diligence,
    list_diligences_by_case,
    add_item,
    update_item,
    delete_item,
    list_items_by_diligence,
)
from app.services.diligence_document_service import generate_termo_diligencia_docx

router = APIRouter(prefix="/diligences", tags=["Diligências"])


@router.post(
    "",
    response_model=DiligenceDetailedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar diligência",
)
async def create_diligence_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    payload: DiligenceCreateRequest = ...,
    current_user=Depends(require_permission("diligence:write")),
    db: AsyncSession = Depends(get_db),
) -> DiligenceDetailedResponse:
    """
    Cria uma nova diligência com itens.

    Valida:
    - Processo existe
    - Mínimo um item é fornecido
    """
    try:
        diligence = await create_diligence(db, case_id, payload)
        await db.commit()
        await db.refresh(diligence)
        return diligence
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{diligence_id}",
    response_model=DiligenceDetailedResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter diligência com detalhes",
)
async def read_diligence_endpoint(
    diligence_id: str = Path(..., description="ID da diligência"),
    current_user=Depends(require_permission("diligence:read")),
    db: AsyncSession = Depends(get_db),
) -> DiligenceDetailedResponse:
    """
    Obtém uma diligência específica com todos seus itens.
    """
    try:
        diligence = await read_diligence(db, diligence_id)
        return diligence
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{diligence_id}",
    response_model=DiligenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar diligência",
)
async def update_diligence_endpoint(
    diligence_id: str = Path(..., description="ID da diligência"),
    case_id: str = Query(..., description="ID do processo"),
    payload: DiligenceUpdateRequest = ...,
    current_user=Depends(require_permission("diligence:write")),
    db: AsyncSession = Depends(get_db),
) -> DiligenceResponse:
    """
    Atualiza uma diligência.
    """
    try:
        diligence = await update_diligence(db, diligence_id, case_id, payload)
        await db.commit()
        await db.refresh(diligence)
        return diligence
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{diligence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar diligência",
)
async def delete_diligence_endpoint(
    diligence_id: str = Path(..., description="ID da diligência"),
    current_user=Depends(require_permission("diligence:write")),
    db: AsyncSession = Depends(get_db),
):
    """
    Deleta uma diligência (cascata para itens).
    """
    try:
        await delete_diligence(db, diligence_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "",
    response_model=DiligencePaginatedResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar diligências por processo",
)
async def list_diligences_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(require_permission("diligence:read")),
    db: AsyncSession = Depends(get_db),
) -> DiligencePaginatedResponse:
    """
    Lista todas as diligências de um processo (paginado).
    """
    diligences, total = await list_diligences_by_case(db, case_id, limit=limit, offset=offset)
    return DiligencePaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=diligences,
    )


@router.post(
    "/{diligence_id}/items",
    response_model=DiligenceItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar item à diligência",
)
async def add_item_endpoint(
    diligence_id: str = Path(..., description="ID da diligência"),
    payload: DiligenceItemCreateRequest = ...,
    current_user=Depends(require_permission("diligence:write")),
    db: AsyncSession = Depends(get_db),
) -> DiligenceItemResponse:
    """
    Adiciona um novo item a uma diligência.
    """
    try:
        item = await add_item(db, diligence_id, payload)
        await db.commit()
        await db.refresh(item)
        return item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{diligence_id}/items/{item_id}",
    response_model=DiligenceItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar item de diligência",
)
async def update_item_endpoint(
    diligence_id: str = Path(..., description="ID da diligência"),
    item_id: str = Path(..., description="ID do item"),
    payload: DiligenceItemUpdateRequest = ...,
    current_user=Depends(require_permission("diligence:write")),
    db: AsyncSession = Depends(get_db),
) -> DiligenceItemResponse:
    """
    Atualiza um item de diligência.
    """
    try:
        item = await update_item(db, item_id, diligence_id, payload)
        await db.commit()
        await db.refresh(item)
        return item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{diligence_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar item de diligência",
)
async def delete_item_endpoint(
    diligence_id: str = Path(..., description="ID da diligência"),
    item_id: str = Path(..., description="ID do item"),
    current_user=Depends(require_permission("diligence:write")),
    db: AsyncSession = Depends(get_db),
):
    """
    Deleta um item de diligência.
    """
    try:
        await delete_item(db, item_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{diligence_id}/items",
    response_model=list[DiligenceItemResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar itens de diligência",
)
async def list_items_endpoint(
    diligence_id: str = Path(..., description="ID da diligência"),
    current_user=Depends(require_permission("diligence:read")),
    db: AsyncSession = Depends(get_db),
) -> list[DiligenceItemResponse]:
    """
    Lista todos os itens de uma diligência.
    """
    try:
        items = await list_items_by_diligence(db, diligence_id)
        return items
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{diligence_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Baixar Termo de Diligência em DOCX",
)
async def download_termo_diligencia_endpoint(
    diligence_id: str = Path(..., description="ID da diligência"),
    current_user=Depends(require_permission("diligence:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Gera e retorna um arquivo DOCX do Termo de Diligência.
    """
    try:
        docx_stream = await generate_termo_diligencia_docx(db, diligence_id)
        return StreamingResponse(
            iter([docx_stream.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=termo_diligencia_{diligence_id}.docx"},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
