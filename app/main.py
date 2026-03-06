from pathlib import Path

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

auth_demo_file = Path(__file__).resolve().parent / "ui" / "auth_demo.html"


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
@app.get("/auth-demo", include_in_schema=False, response_class=HTMLResponse)
async def auth_demo_page() -> HTMLResponse:
    if not auth_demo_file.exists():
        return HTMLResponse(content="auth demo file not found", status_code=404)
    return HTMLResponse(content=auth_demo_file.read_text(encoding="utf-8"))


@app.on_event("startup")
async def startup_db_bootstrap() -> None:
    await bootstrap_database()
