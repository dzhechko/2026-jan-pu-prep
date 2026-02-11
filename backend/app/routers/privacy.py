"""Privacy router -- data export and account deletion (US-7.1 / US-7.2)."""

from fastapi import APIRouter, HTTPException

from app.dependencies import CurrentUser, DbSession
from app.schemas.privacy import (
    DeleteAccountRequest,
    DeleteAccountResponse,
    ExportResponse,
)
from app.services import privacy_service

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.post("/export", response_model=ExportResponse)
async def export_data(
    db: DbSession,
    current_user: CurrentUser,
) -> ExportResponse:
    """Export all user data as JSON (US-7.1)."""
    data = await privacy_service.export_user_data(db, current_user["user_id"])
    return ExportResponse(**data)


@router.post("/delete", response_model=DeleteAccountResponse)
async def delete_account(
    body: DeleteAccountRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> DeleteAccountResponse:
    """Delete user account and all associated data (US-7.2).

    The user must send confirmation="УДАЛИТЬ" in the request body.
    """
    if body.confirmation != "УДАЛИТЬ":
        raise HTTPException(
            status_code=400,
            detail="Для подтверждения введите УДАЛИТЬ",
        )

    deleted = await privacy_service.delete_user_account(
        db, current_user["user_id"]
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")

    return DeleteAccountResponse(
        status="ok",
        message="Аккаунт и все данные удалены",
    )
