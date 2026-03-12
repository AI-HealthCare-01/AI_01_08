from pathlib import Path

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.apis.v1 import v1_routers
from app.core import config
from app.db.bootstrap import bootstrap_database
from app.db.databases import initialize_tortoise

app = FastAPI(
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)
initialize_tortoise(app)
allowed_origins = [origin.strip() for origin in config.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# `/api/docs`는 Swagger로 유지하고, 프로젝트 문서는 별도 경로로 제공합니다.
site_dir = Path(__file__).resolve().parent.parent / "site"
if site_dir.exists():
    app.mount("/api/project-docs", StaticFiles(directory=site_dir, html=True), name="project-docs")

app.include_router(v1_routers)

auth_login_file = Path(__file__).resolve().parent / "ui" / "auth_login.html"
auth_app_file = Path(__file__).resolve().parent / "ui" / "auth_app.html"
auth_app_dir = Path(__file__).resolve().parent / "ui" / "auth-demo"
auth_app_index = auth_app_dir / "index.html"
auth_app_assets = auth_app_dir / "assets"

if auth_app_assets.exists():
    app.mount("/auth-demo/app/assets", StaticFiles(directory=auth_app_assets), name="auth-demo-assets")


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
@app.get("/auth-demo", include_in_schema=False, response_class=HTMLResponse)
@app.get("/auth-demo/login", include_in_schema=False, response_class=HTMLResponse)
@app.get("/auth-demo/signup", include_in_schema=False, response_class=HTMLResponse)
async def auth_login_page() -> HTMLResponse:
    if auth_app_index.exists():
        return HTMLResponse(content=auth_app_index.read_text(encoding="utf-8"))
    if not auth_login_file.exists():
        return HTMLResponse(content="auth login file not found", status_code=404)
    return HTMLResponse(content=auth_login_file.read_text(encoding="utf-8"))


@app.get("/auth-demo/app", include_in_schema=False, response_class=HTMLResponse)
@app.get("/auth-demo/app/", include_in_schema=False, response_class=HTMLResponse)
async def auth_app_page() -> HTMLResponse:
    if auth_app_index.exists():
        return HTMLResponse(content=auth_app_index.read_text(encoding="utf-8"))
    if auth_app_file.exists():
        return HTMLResponse(content=auth_app_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="auth app file not found", status_code=404)


@app.get("/api/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.on_event("startup")
async def startup_db_bootstrap() -> None:
    await bootstrap_database()
