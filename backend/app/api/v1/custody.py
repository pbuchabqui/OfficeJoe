"""
Endpoints de cadeia de custódia documental.

GET  /api/v1/files/{file_id}/custody  – lista todos os eventos de custódia de um arquivo
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.custody import CustodyChain, CustodyEventResponse
from app.services.custody_service import get_file_for_custody, list_events_for_file

router = APIRouter(prefix="/files", tags=["Cadeia de Custódia"])


@router.get("/{file_id}/custody", response_model=CustodyChain)
async def get_custody_chain(
    file_id: str,
    current_user: User = Depends(require_permission("case:read")),
    db: AsyncSession = Depends(get_db),
) -> CustodyChain:
    """
    Retorna o histórico completo de custódia de um arquivo em ordem cronológica.

    Cada evento representa uma operação auditável realizada sobre o arquivo original
    (upload, visualização, download, verificação de integridade, etc.).
    """
    file = await get_file_for_custody(db, file_id)
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado.",
        )

    events = await list_events_for_file(db, file_id)

    return CustodyChain(
        file_id=file_id,
        total_events=len(events),
        events=[CustodyEventResponse.model_validate(e) for e in events],
    )
