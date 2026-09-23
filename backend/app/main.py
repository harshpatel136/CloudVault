
from fastapi import FastAPI

from app.routes.auth import router as auth_router
from app.routes.files import router as files_router
from app.routes.users import router as users_router


app = FastAPI(title="Cloud File Vault")


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(files_router)
