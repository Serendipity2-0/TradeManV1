from fastapi import APIRouter

from . import app
from . import schemas

user_router = APIRouter()

@user_router.post("/login", status_code=201)
async def loginc(login_credentials: schemas.LoginCredentials):
    return app.login_user(login_credentials)