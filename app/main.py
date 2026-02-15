from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routes.auth_routes import router as auth_router
from app.routes.auto_routes import router as auto_router
from app.routes.comment_routes import router as comment_router
from app.routes.dashboard_routes import router as dashboard_router

app = FastAPI(title="LinkedIn Smart Replies")
app.add_middleware(SessionMiddleware, secret_key=settings.app_secret_key)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_router)
app.include_router(comment_router)
app.include_router(auto_router)
app.include_router(dashboard_router)
