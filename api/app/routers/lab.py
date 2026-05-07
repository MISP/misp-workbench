"""Tech Lab — Notebooks router.

Mounted under ``/tech-lab`` so notebooks (this file) sit alongside reactor
scripts under the same Tech Lab umbrella. Visibility (personal/global) and
ownership are enforced inside the repository; this layer only translates
exceptions into HTTP responses.
"""

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import lab as lab_repository
from app.schemas import lab as lab_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────
# Tree
# ──────────────────────────────────────────────────────────────────────────


@router.get("/tech-lab/tree", response_model=lab_schemas.LabTree)
async def get_tree(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:read"]
    ),
):
    return lab_repository.get_tree(db, current_user_id=user.id)


# ──────────────────────────────────────────────────────────────────────────
# Folders
# ──────────────────────────────────────────────────────────────────────────


@router.post(
    "/tech-lab/folders",
    response_model=lab_schemas.LabFolder,
    status_code=status.HTTP_201_CREATED,
)
async def create_folder(
    payload: lab_schemas.LabFolderCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:create"]
    ),
):
    try:
        return lab_repository.create_folder(db, payload, current_user_id=user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.patch(
    "/tech-lab/folders/{folder_id}",
    response_model=lab_schemas.LabFolder,
)
async def update_folder(
    folder_id: int,
    payload: lab_schemas.LabFolderUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:update"]
    ),
):
    try:
        folder = lab_repository.update_folder(
            db, folder_id, payload, current_user_id=user.id
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    if folder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )
    return folder


@router.delete(
    "/tech-lab/folders/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:delete"]
    ),
):
    try:
        result = lab_repository.delete_folder(
            db, folder_id, current_user_id=user.id
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )


# ──────────────────────────────────────────────────────────────────────────
# Notebooks
# ──────────────────────────────────────────────────────────────────────────


@router.post(
    "/tech-lab/notebooks",
    response_model=lab_schemas.LabNotebook,
    status_code=status.HTTP_201_CREATED,
)
async def create_notebook(
    payload: lab_schemas.LabNotebookCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:create"]
    ),
):
    try:
        return lab_repository.create_notebook(
            db, payload, current_user_id=user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.get(
    "/tech-lab/notebooks/{notebook_id}",
    response_model=lab_schemas.LabNotebook,
)
async def get_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:read"]
    ),
):
    nb = lab_repository.get_notebook_by_id(
        db, notebook_id, current_user_id=user.id
    )
    if nb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found"
        )
    return nb


@router.patch(
    "/tech-lab/notebooks/{notebook_id}",
    response_model=lab_schemas.LabNotebook,
)
async def update_notebook(
    notebook_id: int,
    payload: lab_schemas.LabNotebookUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:update"]
    ),
):
    try:
        nb = lab_repository.update_notebook(
            db, notebook_id, payload, current_user_id=user.id
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    if nb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found"
        )
    return nb


@router.delete(
    "/tech-lab/notebooks/{notebook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:delete"]
    ),
):
    try:
        result = lab_repository.delete_notebook(
            db, notebook_id, current_user_id=user.id
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found"
        )


@router.post(
    "/tech-lab/notebooks/{notebook_id}/fork",
    response_model=lab_schemas.LabNotebook,
    status_code=status.HTTP_201_CREATED,
)
async def fork_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:create"]
    ),
):
    nb = lab_repository.fork_notebook(
        db, notebook_id, current_user_id=user.id
    )
    if nb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found"
        )
    return nb


# ──────────────────────────────────────────────────────────────────────────
# Execution
# ──────────────────────────────────────────────────────────────────────────


@router.post(
    "/tech-lab/notebooks/{notebook_id}/cells/execute",
    response_model=lab_schemas.LabExecution,
    status_code=status.HTTP_201_CREATED,
)
async def execute_cell(
    notebook_id: int,
    payload: lab_schemas.LabExecuteRequest,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:run"]
    ),
):
    nb = lab_repository.get_notebook_by_id(
        db, notebook_id, current_user_id=user.id
    )
    if nb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found"
        )
    # Owner-only: capture the editor-current source onto the blob so the
    # executor finds the same slice. Non-owners run against the stored
    # source as-is (see write_cell_source contract).
    lab_repository.write_cell_source(
        db, notebook_id, payload.cell_id, payload.source, current_user_id=user.id
    )
    row = lab_repository.create_execution(
        db, notebook_id, payload.cell_id, current_user_id=user.id
    )

    from app.worker.tasks import lab_execute_cell as _task

    async_result = _task.apply_async(args=[row.id], queue="lab_kernel")
    row.celery_task_id = getattr(async_result, "id", None)
    db.commit()
    db.refresh(row)
    return row


@router.post(
    "/tech-lab/notebooks/{notebook_id}/cells/execute_all",
    response_model=list[lab_schemas.LabExecution],
    status_code=status.HTTP_201_CREATED,
)
async def execute_all_cells(
    notebook_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:run"]
    ),
):
    nb = lab_repository.get_notebook_by_id(
        db, notebook_id, current_user_id=user.id
    )
    if nb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found"
        )

    from app.services.tech_lab.lab.cell_parser import parse_cells
    from app.worker.tasks import lab_execute_cell as _task

    rows: list = []
    for cell in parse_cells(nb.source or ""):
        if cell.type != "code":
            continue
        row = lab_repository.create_execution(
            db, notebook_id, cell.cell_id, current_user_id=user.id
        )
        async_result = _task.apply_async(args=[row.id], queue="lab_kernel")
        row.celery_task_id = getattr(async_result, "id", None)
        db.commit()
        db.refresh(row)
        rows.append(row)
    return rows


@router.get(
    "/tech-lab/notebooks/{notebook_id}/executions/{execution_id}",
    response_model=lab_schemas.LabExecution,
)
async def get_execution(
    notebook_id: int,
    execution_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:read"]
    ),
):
    row = lab_repository.get_execution(db, execution_id, current_user_id=user.id)
    if row is None or row.notebook_id != notebook_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found"
        )
    return row


@router.post(
    "/tech-lab/notebooks/{notebook_id}/kernel/interrupt",
    status_code=status.HTTP_202_ACCEPTED,
)
async def interrupt_kernel(
    notebook_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:run"]
    ),
):
    nb = lab_repository.get_notebook_by_id(
        db, notebook_id, current_user_id=user.id
    )
    if nb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found"
        )
    from app.worker.tasks import lab_kernel_interrupt as _task

    _task.apply_async(args=[user.id, notebook_id], queue="lab_kernel")
    return {"status": "queued"}


@router.post(
    "/tech-lab/notebooks/{notebook_id}/kernel/shutdown",
    status_code=status.HTTP_202_ACCEPTED,
)
async def shutdown_kernel(
    notebook_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["lab:run"]
    ),
):
    nb = lab_repository.get_notebook_by_id(
        db, notebook_id, current_user_id=user.id
    )
    if nb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found"
        )
    from app.worker.tasks import lab_kernel_shutdown as _task

    _task.apply_async(args=[user.id, notebook_id], queue="lab_kernel")
    return {"status": "queued"}
