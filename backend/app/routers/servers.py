from ..dependencies import get_db
from ..repositories import servers as servers_repository
from ..schemas import server as server_schemas
from ..schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, status, Security
from sqlalchemy.orm import Session
from ..auth.auth import get_current_active_user

router = APIRouter()


@router.get("/servers/", response_model=list[server_schemas.Server])
def get_servers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), user: user_schemas.User = Security(get_current_active_user, scopes=["servers:read"])):
    servers = servers_repository.get_servers(db, skip=skip, limit=limit)
    return servers


@router.get("/servers/{server_id}", response_model=server_schemas.Server)
def get_server_by_id(server_id: int, db: Session = Depends(get_db), user: user_schemas.User = Security(get_current_active_user, scopes=["servers:read"])):
    db_server = servers_repository.get_server_by_id(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return db_server


@router.post("/servers/{server_id}/pull")
def pull_server(server_id: int, db: Session = Depends(get_db), user: user_schemas.User = Security(get_current_active_user, scopes=["servers:pull"])):
    return servers_repository.pull_server_by_id(db, server_id=server_id)


@router.post("/servers/", response_model=server_schemas.Server)
def create_server(server: server_schemas.ServerCreate, db: Session = Depends(get_db), user: user_schemas.User = Security(get_current_active_user, scopes=["servers:create"])):
    return servers_repository.create_server(db=db, server=server)
