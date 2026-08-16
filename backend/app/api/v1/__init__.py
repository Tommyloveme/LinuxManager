from fastapi import APIRouter

from app.api.v1 import auth, execute, files, process, scripts, services, system, terminal, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(scripts.router)
api_router.include_router(files.router)
api_router.include_router(process.router)
api_router.include_router(system.router)
api_router.include_router(services.router)
api_router.include_router(execute.router)
api_router.include_router(terminal.router)
