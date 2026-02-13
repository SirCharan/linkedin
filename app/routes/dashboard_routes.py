from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.token_store import token_store

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    token = token_store.get_valid_token()
    if not token:
        return templates.TemplateResponse("login.html", {"request": request})
    return templates.TemplateResponse("dashboard.html", {"request": request})
