from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import CreateUserRequest, CreateUserResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.admin)),
):
    result = await db.execute(select(User).order_by(User.created_at))
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.post("/", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    user, temp_pw = await AuthService(db).create_user(body.email, body.username, body.role, admin)
    return CreateUserResponse(user=UserResponse.model_validate(user), temp_password=temp_pw)


@router.patch("/{user_id}/status", response_model=UserResponse)
async def toggle_user_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot modify your own account")
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete your own account")
    await db.delete(user)
    await db.commit()
