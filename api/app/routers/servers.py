from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import servers as servers_repository
from app.schemas import server as server_schemas
from app.schemas import task as task_schemas
from app.schemas import user as user_schemas
from app.worker import tasks
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/servers/", response_model=list[server_schemas.Server])
def get_servers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["servers:read"]
    ),
):
    return servers_repository.get_servers(db, skip=skip, limit=limit)


@router.get("/servers/{server_id}", response_model=server_schemas.Server)
def get_server_by_id(
    server_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["servers:read"]
    ),
):
    db_server = servers_repository.get_server_by_id(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )
    return db_server


@router.post(
    "/servers/{server_id}/pull",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=task_schemas.Task,
)
def pull_server(
    server_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["servers:pull"]
    ),
):
    task = tasks.server_pull_by_id.delay(server_id, user.id)

    return task_schemas.Task(
        task_id=task.id,
        status=task.status,
        message="pull server_id=%s enqueued" % server_id,
    )


@router.post(
    "/servers/",
    response_model=server_schemas.Server,
    status_code=status.HTTP_201_CREATED,
)
def create_server(
    server: server_schemas.ServerCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["servers:create"]
    ),
):
    return servers_repository.create_server(db=db, server=server)


@router.patch("/servers/{server_id}", response_model=server_schemas.Server)
def update_server(
    server_id: int,
    server: server_schemas.ServerUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["servers:update"]
    ),
):
    return servers_repository.update_server(db=db, server_id=server_id, server=server)


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["servers:delete"]
    ),
):
    return servers_repository.delete_server(db=db, server_id=server_id)
