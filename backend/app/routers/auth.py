from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.user import RegisterResponse
from app.services.firebase_auth import verify_firebase_token, FirebaseUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse)
async def register(
    firebase_user: FirebaseUser = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user or retrieve existing user.

    Validates Firebase ID token and creates/retrieves user record.
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.firebase_uid == firebase_user.uid)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return RegisterResponse(
            user_id=existing_user.id,
            email=existing_user.email,
            name=existing_user.name,
            is_enrolled=existing_user.voiceprint_embedding is not None,
            created=False,
        )

    # Create new user
    if not firebase_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for registration",
        )

    new_user = User(
        firebase_uid=firebase_user.uid,
        email=firebase_user.email,
        name=firebase_user.name or firebase_user.email.split("@")[0],
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return RegisterResponse(
        user_id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        is_enrolled=False,
        created=True,
    )
