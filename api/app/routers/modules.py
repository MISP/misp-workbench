from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import modules as modules_repository
from app.schemas import module as module_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/modules/", response_model=list[module_schemas.Module])
async def get_modules(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["modules:read"]
    ),
) -> list[module_schemas.Module]:

    return modules_repository.get_modules(db)


@router.post("/modules/{module_name}/query")
def update_module(
    module_name: str,
    query: module_schemas.ModuleQuery,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["modules:query"]
    ),
):
    return modules_repository.query_module(module_name=module_name, query=query)
