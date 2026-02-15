from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import User


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_demo_user(
    x_demo_userid: str | None = Header(default=None, alias="X-Demo-UserId"),
    db: Session = Depends(get_db),
) -> User:
    if not x_demo_userid:
        raise HTTPException(status_code=401, detail="Missing X-Demo-UserId header")

    user = db.get(User, x_demo_userid)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid demo user")
    return user
