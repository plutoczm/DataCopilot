from fastapi import APIRouter, Depends

from backend.app.presentation.api.dependencies.security import get_current_principal
from backend.app.presentation.api.routes import (
    agent,
    auth,
    chat,
    config,
    health,
    knowledge,
    query_execution,
    sql_review,
    text2sql,
    warehouse_design,
)


api_router = APIRouter()
api_router.include_router(health.router)

protected_router = APIRouter(dependencies=[Depends(get_current_principal)])
protected_router.include_router(auth.router)
protected_router.include_router(config.router)
protected_router.include_router(knowledge.router)
protected_router.include_router(chat.router)
protected_router.include_router(text2sql.router)
protected_router.include_router(sql_review.router)
protected_router.include_router(query_execution.router)
protected_router.include_router(warehouse_design.router)
protected_router.include_router(agent.router)
api_router.include_router(protected_router)
