from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import GOOGLE_CLIENT_ID, JWT_EXPIRE_HOURS, JWT_SECRET
from app.db.database import get_db
from app.models import Profile, User


router = APIRouter()


class GoogleCredentialRequest(BaseModel):
    credential: str = Field(min_length=1)


@router.post("/auth/google")
def sign_in_with_google(
    request: GoogleCredentialRequest,
    db: Session = Depends(get_db),
):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")

    try:
        claims = id_token.verify_oauth2_token(
            request.credential,
            Request(),
            GOOGLE_CLIENT_ID,
        )
    except (ValueError, GoogleAuthError) as exc:
        raise HTTPException(status_code=401, detail="Invalid Google credential.") from exc

    if not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google email is not verified.")

    google_sub = claims.get("sub")
    email = claims.get("email")
    if not isinstance(google_sub, str) or not isinstance(email, str):
        raise HTTPException(status_code=401, detail="Google credential is missing account details.")

    user = db.scalar(select(User).where(User.google_sub == google_sub))
    if user is None:
        user = db.scalar(select(User).where(User.email == email))

    if user is None:
        user = User(
            google_sub=google_sub,
            email=email,
            full_name=claims.get("name"),
            picture=claims.get("picture"),
        )
        db.add(user)
        db.flush()
    else:
        user.google_sub = google_sub
        user.email = email
        user.full_name = claims.get("name")
        user.picture = claims.get("picture")

    if user.profile is None:
        db.add(Profile(user_id=user.id, skills=[]))

    db.commit()
    db.refresh(user)

    expires_at = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    access_token = jwt.encode(
        {"sub": str(user.id), "exp": expires_at},
        JWT_SECRET,
        algorithm="HS256",
    )
    return {
        "access_token": access_token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "picture": user.picture,
            "has_resume": bool(user.profile and user.profile.resume_url),
        },
    }


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "picture": user.picture,
        "has_resume": bool(user.profile and user.profile.resume_url),
    }
