from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.auth.oauth import exchange_code_for_token, generate_state, get_authorization_url
from app.auth.token_store import token_store
from app.linkedin.client import LinkedInClient

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    state = generate_state()
    request.session["oauth_state"] = state
    url = get_authorization_url(state)
    return RedirectResponse(url)


@router.get("/callback")
async def callback(request: Request, code: str, state: str):
    saved_state = request.session.get("oauth_state")
    if state != saved_state:
        return {"error": "Invalid state parameter"}

    token_data = await exchange_code_for_token(code)
    # Fetch member URN and store it alongside the token
    li = LinkedInClient(token_data["access_token"])
    member_urn = await li.get_member_urn()
    token_data["member_urn"] = member_urn
    token_store.save_token(token_data)

    return RedirectResponse("/")


@router.get("/status")
async def status():
    token = token_store.get_valid_token()
    return {"authenticated": token is not None}


@router.post("/logout")
async def logout():
    token_store.clear()
    return {"ok": True}
