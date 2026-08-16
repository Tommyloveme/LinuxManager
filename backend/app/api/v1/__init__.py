from fastapi import APIRouter

from app.api.v1 import audit, auth, execute, files, jobs, playbooks, process, scripts, services, system, users
from app.api.v1 import terminal

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(scripts.router)
api_router.include_router(playbooks.router)
api_router.include_router(files.router)
api_router.include_router(process.router)
api_router.include_router(system.router)
api_router.include_router(services.router)
api_router.include_router(execute.router)
api_router.include_router(jobs.router)
api_router.include_router(audit.router)
api_router.include_router(terminal.router)
