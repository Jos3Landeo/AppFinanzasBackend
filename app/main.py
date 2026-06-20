from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.runtime_schema import ensure_runtime_schema
from app.routers import catalogs, debts, health, movements, reports
from app.settings import API_PREFIX, API_TITLE, API_VERSION


app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description='API inicial para la futura app movil, reutilizando la logica Python del bot actual.',
)


@app.on_event('startup')
def startup_event() -> None:
    ensure_runtime_schema()


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(catalogs.router, prefix=API_PREFIX)
app.include_router(movements.router, prefix=API_PREFIX)
app.include_router(debts.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
