"""API tests for the Tech Lab — Notebooks router (CRUD + visibility + fork + execute)."""

from unittest.mock import patch

import pytest
from app.auth import auth
from app.models import lab as lab_models  # noqa: F401  (used by other test modules via fixtures)
from app.models import user as user_models
from app.repositories import lab as lab_repository
from app.schemas import lab as lab_schemas
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


SAMPLE_SOURCE = (
    "# %% [id=cell-1] code\n"
    "print('hello')\n"
    "# %% [id=cell-2] markdown\n"
    "## Notes\n"
)


class TestLabRouter(ApiTester):
    # ── Folders: CRUD ────────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["lab:create"]])
    def test_create_personal_folder(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/tech-lab/folders",
            json={"name": "research", "visibility": "personal"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        data = response.json()
        assert data["name"] == "research"
        assert data["visibility"] == "personal"
        assert data["parent_id"] is None

    @pytest.mark.parametrize("scopes", [["lab:create"]])
    def test_create_nested_folder_visibility_mismatch_400(
        self, client: TestClient, auth_token: auth.Token
    ):
        parent = client.post(
            "/tech-lab/folders",
            json={"name": "g-parent", "visibility": "global"},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        response = client.post(
            "/tech-lab/folders",
            json={
                "name": "p-child",
                "visibility": "personal",
                "parent_id": parent["id"],
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [[]])
    def test_create_folder_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/tech-lab/folders",
            json={"name": "x", "visibility": "personal"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["lab:create", "lab:update"]])
    def test_update_folder_rename(
        self, client: TestClient, auth_token: auth.Token
    ):
        created = client.post(
            "/tech-lab/folders",
            json={"name": "old", "visibility": "personal"},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        response = client.patch(
            f"/tech-lab/folders/{created['id']}",
            json={"name": "new"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "new"

    @pytest.mark.parametrize("scopes", [["lab:create", "lab:delete"]])
    def test_delete_folder(self, client: TestClient, auth_token: auth.Token):
        created = client.post(
            "/tech-lab/folders",
            json={"name": "trash", "visibility": "personal"},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        response = client.delete(
            f"/tech-lab/folders/{created['id']}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # ── Notebooks: CRUD ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["lab:create"]])
    def test_create_personal_notebook(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/tech-lab/notebooks",
            json={
                "name": "my-notebook",
                "visibility": "personal",
                "source": SAMPLE_SOURCE,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        data = response.json()
        assert data["name"] == "my-notebook"
        assert data["visibility"] == "personal"
        assert data["source"] == SAMPLE_SOURCE
        assert data["cell_outputs"] == {}

    @pytest.mark.parametrize("scopes", [["lab:create"]])
    def test_create_notebook_in_folder_visibility_mismatch_400(
        self, client: TestClient, auth_token: auth.Token
    ):
        folder = client.post(
            "/tech-lab/folders",
            json={"name": "g-folder", "visibility": "global"},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        response = client.post(
            "/tech-lab/notebooks",
            json={
                "name": "mismatch",
                "visibility": "personal",
                "folder_id": folder["id"],
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [["lab:create", "lab:read"]])
    def test_get_notebook_returns_full_payload(
        self, client: TestClient, auth_token: auth.Token
    ):
        created = client.post(
            "/tech-lab/notebooks",
            json={
                "name": "g-test",
                "visibility": "personal",
                "source": SAMPLE_SOURCE,
            },
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        response = client.get(
            f"/tech-lab/notebooks/{created['id']}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["source"] == SAMPLE_SOURCE

    @pytest.mark.parametrize(
        "scopes", [["lab:create", "lab:update", "lab:read"]]
    )
    def test_update_notebook_source_autosave(
        self, client: TestClient, auth_token: auth.Token
    ):
        created = client.post(
            "/tech-lab/notebooks",
            json={"name": "u", "visibility": "personal"},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        new_source = "# %% [id=z] code\nprint(1)\n"
        response = client.patch(
            f"/tech-lab/notebooks/{created['id']}",
            json={"source": new_source},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["source"] == new_source

    @pytest.mark.parametrize("scopes", [["lab:create", "lab:delete"]])
    def test_delete_notebook(
        self, client: TestClient, auth_token: auth.Token
    ):
        created = client.post(
            "/tech-lab/notebooks",
            json={"name": "del", "visibility": "personal"},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        response = client.delete(
            f"/tech-lab/notebooks/{created['id']}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # ── Tree ─────────────────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["lab:read", "lab:create"]])
    def test_tree_returns_personal_and_global(
        self, client: TestClient, auth_token: auth.Token
    ):
        client.post(
            "/tech-lab/folders",
            json={"name": "p-only", "visibility": "personal"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        client.post(
            "/tech-lab/notebooks",
            json={"name": "g-nb", "visibility": "global"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        response = client.get(
            "/tech-lab/tree",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        names = [f["name"] for f in data["folders"]] + [
            n["name"] for n in data["notebooks"]
        ]
        assert "p-only" in names
        assert "g-nb" in names

    # ── Visibility: cross-user ───────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["lab:read"]])
    def test_personal_notebook_invisible_to_other_user(
        self,
        client: TestClient,
        db: Session,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        # Notebook owned by user_1 (not the api_tester_user holding the token).
        nb = lab_repository.create_notebook(
            db,
            lab_schemas.LabNotebookCreate(
                name="user_1-private",
                visibility="personal",
                source="",
            ),
            current_user_id=user_1.id,
        )
        response = client.get(
            f"/tech-lab/notebooks/{nb.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [["lab:read"]])
    def test_global_notebook_visible_to_other_user(
        self,
        client: TestClient,
        db: Session,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        nb = lab_repository.create_notebook(
            db,
            lab_schemas.LabNotebookCreate(
                name="user_1-shared",
                visibility="global",
                source=SAMPLE_SOURCE,
            ),
            current_user_id=user_1.id,
        )
        response = client.get(
            f"/tech-lab/notebooks/{nb.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["source"] == SAMPLE_SOURCE

    @pytest.mark.parametrize("scopes", [["lab:update"]])
    def test_global_notebook_not_editable_by_non_owner(
        self,
        client: TestClient,
        db: Session,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        nb = lab_repository.create_notebook(
            db,
            lab_schemas.LabNotebookCreate(
                name="user_1-shared-2",
                visibility="global",
                source="",
            ),
            current_user_id=user_1.id,
        )
        response = client.patch(
            f"/tech-lab/notebooks/{nb.id}",
            json={"source": "tampered"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("scopes", [["lab:delete"]])
    def test_global_notebook_not_deletable_by_non_owner(
        self,
        client: TestClient,
        db: Session,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        nb = lab_repository.create_notebook(
            db,
            lab_schemas.LabNotebookCreate(
                name="user_1-shared-3",
                visibility="global",
                source="",
            ),
            current_user_id=user_1.id,
        )
        response = client.delete(
            f"/tech-lab/notebooks/{nb.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # ── Fork ────────────────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["lab:create", "lab:read"]])
    def test_fork_global_notebook_creates_personal_copy(
        self,
        client: TestClient,
        db: Session,
        user_1: user_models.User,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        original_source = (
            "# %% [id=aaaa1111-aaaa-aaaa-aaaa-aaaaaaaaaaaa] code\n"
            "x = 1\n"
        )
        nb = lab_repository.create_notebook(
            db,
            lab_schemas.LabNotebookCreate(
                name="forkable",
                visibility="global",
                source=original_source,
            ),
            current_user_id=user_1.id,
        )
        response = client.post(
            f"/tech-lab/notebooks/{nb.id}/fork",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        data = response.json()
        assert data["user_id"] == api_tester_user.id
        assert data["visibility"] == "personal"
        assert data["folder_id"] is None
        assert data["name"] == "forkable (fork)"
        # Cell ids must be regenerated.
        assert "aaaa1111-aaaa-aaaa-aaaa-aaaaaaaaaaaa" not in data["source"]
        assert "[id=" in data["source"]


class TestLabExecution(ApiTester):
    """Execute-flow tests with the celery task stubbed to a synchronous runner."""

    @pytest.mark.parametrize(
        "scopes", [["lab:create", "lab:run", "lab:read"]]
    )
    def test_execute_cell_owner_writes_outputs_to_notebook(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        # Create a notebook with a single code cell.
        cell_id = "cccc1111-cccc-cccc-cccc-cccccccccccc"
        source = f"# %% [id={cell_id}] code\nprint(40 + 2)\n"
        nb = client.post(
            "/tech-lab/notebooks",
            json={"name": "exec-test", "visibility": "personal", "source": source},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()

        # Stub the Celery task: write a synthetic mimebundle synchronously.
        def _fake_apply_async(args=None, queue=None, **_kwargs):
            execution_id = args[0]
            row = (
                db.query(lab_models.LabExecution)
                .filter(lab_models.LabExecution.id == execution_id)
                .first()
            )
            from datetime import datetime, timezone

            row.status = "success"
            row.outputs = [
                {"output_type": "stream", "name": "stdout", "text": "42\n"}
            ]
            row.execution_count = 1
            row.started_at = datetime.now(timezone.utc)
            row.finished_at = datetime.now(timezone.utc)
            # Owner-side persist into notebook.cell_outputs.
            notebook = (
                db.query(lab_models.LabNotebook)
                .filter(lab_models.LabNotebook.id == row.notebook_id)
                .first()
            )
            outputs_map = dict(notebook.cell_outputs or {})
            outputs_map[row.cell_id] = row.outputs
            notebook.cell_outputs = outputs_map
            db.commit()

            class _R:
                id = "fake-task-id"

            return _R()

        with patch(
            "app.worker.tasks.lab_execute_cell.apply_async",
            side_effect=_fake_apply_async,
        ):
            response = client.post(
                f"/tech-lab/notebooks/{nb['id']}/cells/execute",
                json={"cell_id": cell_id, "source": "print(40 + 2)"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        ex = response.json()
        assert ex["status"] == "success"
        assert ex["outputs"][0]["text"] == "42\n"

        # Owner-side outputs should be persisted onto the notebook.
        nb_full = client.get(
            f"/tech-lab/notebooks/{nb['id']}",
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        assert nb_full["cell_outputs"][cell_id][0]["text"] == "42\n"

    @pytest.mark.parametrize("scopes", [["lab:run"]])
    def test_execute_cell_non_owner_does_not_pollute_notebook_outputs(
        self,
        client: TestClient,
        db: Session,
        user_1: user_models.User,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        # user_1 owns a global notebook; api_tester_user runs a cell.
        cell_id = "dddd2222-dddd-dddd-dddd-dddddddddddd"
        source = f"# %% [id={cell_id}] code\nprint(1)\n"
        nb = lab_repository.create_notebook(
            db,
            lab_schemas.LabNotebookCreate(
                name="shared", visibility="global", source=source
            ),
            current_user_id=user_1.id,
        )

        def _fake_apply_async(args=None, queue=None, **_kwargs):
            execution_id = args[0]
            row = (
                db.query(lab_models.LabExecution)
                .filter(lab_models.LabExecution.id == execution_id)
                .first()
            )
            from datetime import datetime, timezone

            row.status = "success"
            row.outputs = [
                {"output_type": "stream", "name": "stdout", "text": "non-owner\n"}
            ]
            row.started_at = datetime.now(timezone.utc)
            row.finished_at = datetime.now(timezone.utc)
            # NOTE: deliberately do NOT update notebook.cell_outputs — that's
            # the contract for non-owner runs.
            db.commit()

            class _R:
                id = "fake-task-id"

            return _R()

        with patch(
            "app.worker.tasks.lab_execute_cell.apply_async",
            side_effect=_fake_apply_async,
        ):
            response = client.post(
                f"/tech-lab/notebooks/{nb.id}/cells/execute",
                json={"cell_id": cell_id, "source": "print(1)"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_201_CREATED, response.text

        # Notebook owner's snapshot should be untouched.
        db.refresh(nb)
        assert cell_id not in (nb.cell_outputs or {})

    @pytest.mark.parametrize(
        "scopes", [["lab:create", "lab:run", "lab:read"]]
    )
    def test_execute_all_creates_one_execution_per_code_cell(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        source = (
            "# %% [id=eeee1111-eeee-eeee-eeee-eeeeeeeeeeee] code\n"
            "print('a')\n"
            "# %% [id=eeee2222-eeee-eeee-eeee-eeeeeeeeeeee] markdown\n"
            "## skip me\n"
            "# %% [id=eeee3333-eeee-eeee-eeee-eeeeeeeeeeee] code\n"
            "print('b')\n"
        )
        nb = client.post(
            "/tech-lab/notebooks",
            json={"name": "exec-all", "visibility": "personal", "source": source},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()

        with patch(
            "app.worker.tasks.lab_execute_cell.apply_async"
        ) as mock_apply:
            mock_apply.return_value.id = "fake-task-id"
            response = client.post(
                f"/tech-lab/notebooks/{nb['id']}/cells/execute_all",
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        rows = response.json()
        assert len(rows) == 2  # markdown cell skipped
        cell_ids = {r["cell_id"] for r in rows}
        assert "eeee1111-eeee-eeee-eeee-eeeeeeeeeeee" in cell_ids
        assert "eeee3333-eeee-eeee-eeee-eeeeeeeeeeee" in cell_ids

    def test_executor_timeout_interrupts_kernel(
        self, db: Session, api_tester_user: user_models.User
    ):
        """When ``_drain_iopub`` reports ``timed_out=True`` the executor must
        interrupt the kernel and drain leftover IOPub before returning, so
        the next cell on the same kernel doesn't pick up stale messages."""
        import threading
        import time

        from app.services.tech_lab.lab import executor as lab_executor
        from app.services.tech_lab.lab.kernel_manager import (
            LabKernelRegistry,
            _Entry,
        )

        cell_id = "eeee4444-eeee-eeee-eeee-eeeeeeeeeeee"
        source = f"# %% [id={cell_id}] code\nwhile True: pass\n"
        nb = lab_repository.create_notebook(
            db,
            lab_schemas.LabNotebookCreate(
                name="timeout-test", visibility="personal", source=source
            ),
            current_user_id=api_tester_user.id,
        )
        row = lab_repository.create_execution(
            db, nb.id, cell_id, current_user_id=api_tester_user.id
        )

        class _Manager:
            def __init__(self):
                self.interrupt_called = False
                self.shutdown_called = False

            def shutdown_kernel(self, now=False):
                self.shutdown_called = True

            def interrupt_kernel(self):
                self.interrupt_called = True
                client.interrupted = True

        class _Client:
            def __init__(self):
                self.interrupted = False

            def execute(self, src, silent=False, store_history=True):
                return "msg-1"

            def stop_channels(self):
                pass

            def get_iopub_msg(self, timeout=None):
                # Pre-interrupt: simulate the cell never replying, so the
                # drain deadline elapses and timed_out=True flows back.
                if not self.interrupted:
                    raise TimeoutError("no message")
                # Post-interrupt: emit one stream output, then idle, so the
                # grace drain terminates promptly.
                if not getattr(self, "_drained_grace", False):
                    self._drained_grace = True
                    return {
                        "parent_header": {"msg_id": "msg-1"},
                        "msg_type": "stream",
                        "content": {"name": "stdout", "text": "post-interrupt\n"},
                    }
                return {
                    "parent_header": {"msg_id": "msg-1"},
                    "msg_type": "status",
                    "content": {"execution_state": "idle"},
                }

        manager = _Manager()
        client = _Client()

        reg = LabKernelRegistry(idle_seconds=10_000)
        reg._kernels[(api_tester_user.id, nb.id)] = _Entry(
            manager=manager,
            client=client,
            cwd="",
            last_active=time.monotonic(),
            lock=threading.Lock(),
            started=True,
        )

        lab_executor.execute_cell(
            db, row.id, timeout_seconds=1, registry=reg
        )

        db.refresh(row)
        assert row.status == "interrupted"
        assert manager.interrupt_called
        assert any(
            o.get("output_type") == "stream" and "post-interrupt" in o.get("text", "")
            for o in (row.outputs or [])
        )


class TestLabRepositoryUnit:
    """Pure-Python unit tests for helpers that don't need the API."""

    def test_regenerate_cell_ids_replaces_uuids(self):
        from app.repositories.lab import _regenerate_cell_ids

        src = (
            "# %% [id=11111111-1111-1111-1111-111111111111] code\n"
            "print(1)\n"
            "# %% [id=22222222-2222-2222-2222-222222222222] markdown\n"
            "## hi\n"
        )
        new_src, id_map = _regenerate_cell_ids(src)
        assert "11111111-1111-1111-1111-111111111111" not in new_src
        assert "22222222-2222-2222-2222-222222222222" not in new_src
        assert len(id_map) == 2
        for old_id, new_id in id_map.items():
            assert old_id != new_id
            assert new_id in new_src

    def test_regenerate_cell_ids_assigns_id_when_missing(self):
        from app.repositories.lab import _regenerate_cell_ids

        src = "# %% code\nprint(1)\n"
        new_src, _id_map = _regenerate_cell_ids(src)
        assert "[id=" in new_src


class TestCellParser:
    def test_parse_round_trip(self):
        from app.services.tech_lab.lab.cell_parser import (
            parse_cells,
            serialize_cells,
        )

        src = (
            "# %% [id=11111111-1111-1111-1111-111111111111] code\n"
            "x = 1\n"
            "y = 2\n"
            "# %% [id=22222222-2222-2222-2222-222222222222] markdown\n"
            "## Notes\n"
            "Some text.\n"
        )
        cells = parse_cells(src)
        assert len(cells) == 2
        assert cells[0].cell_id == "11111111-1111-1111-1111-111111111111"
        assert cells[0].type == "code"
        assert "x = 1" in cells[0].source
        assert cells[1].type == "markdown"
        assert "Notes" in cells[1].source
        assert serialize_cells(cells) == src

    def test_parse_assigns_id_when_missing(self):
        from app.services.tech_lab.lab.cell_parser import parse_cells

        cells = parse_cells("# %% code\nprint(1)\n")
        assert len(cells) == 1
        assert cells[0].cell_id  # uuid generated
        assert cells[0].type == "code"

    def test_parse_implicit_first_cell_before_delimiter(self):
        from app.services.tech_lab.lab.cell_parser import parse_cells

        cells = parse_cells(
            "x = 1\n# %% [id=aaa] code\nprint(x)\n"
        )
        assert len(cells) == 2
        assert "x = 1" in cells[0].source
        assert cells[1].cell_id == "aaa"


class TestNbformatIO:
    """Round-trip tests for export/import."""

    def test_to_nbformat_basic_shape(self):
        from app.services.tech_lab.lab.nbformat_io import to_nbformat

        class FakeNb:
            id = 7
            name = "x"
            visibility = "personal"
            source = (
                "# %% [id=aaaa] code\n"
                "print(1)\n"
                "# %% [id=bbbb] markdown\n"
                "## Notes\n"
            )
            cell_outputs = {
                "aaaa": [
                    {"output_type": "stream", "name": "stdout", "text": "1\n"}
                ]
            }

        blob = to_nbformat(FakeNb())
        assert blob["nbformat"] == 4
        assert len(blob["cells"]) == 2
        assert blob["cells"][0]["cell_type"] == "code"
        assert blob["cells"][0]["id"] == "aaaa"
        assert blob["cells"][0]["outputs"][0]["text"] == "1\n"
        assert blob["cells"][1]["cell_type"] == "markdown"
        assert blob["cells"][1]["id"] == "bbbb"

    def test_from_nbformat_drops_outputs_and_preserves_ids(self):
        from app.services.tech_lab.lab.nbformat_io import from_nbformat

        blob = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {"misp_workbench": {"name": "exported nb"}},
            "cells": [
                {
                    "cell_type": "code",
                    "id": "id-a",
                    "source": "print(1)\n",
                    "outputs": [
                        {"output_type": "stream", "name": "stdout", "text": "1\n"}
                    ],
                    "execution_count": 5,
                },
                {
                    "cell_type": "markdown",
                    "id": "id-b",
                    "source": ["## Hi\n"],
                },
            ],
        }
        source, name = from_nbformat(blob)
        assert "[id=id-a] code" in source
        assert "print(1)" in source
        assert "[id=id-b] markdown" in source
        assert "## Hi" in source
        # Outputs are dropped.
        assert "stdout" not in source
        assert name == "exported nb"


class TestExportImport(ApiTester):
    @pytest.mark.parametrize("scopes", [["lab:create", "lab:read"]])
    def test_export_returns_nbformat(
        self, client: TestClient, auth_token: auth.Token
    ):
        cell_id = "abcd1234-abcd-abcd-abcd-abcdabcdabcd"
        nb = client.post(
            "/tech-lab/notebooks",
            json={
                "name": "export-me",
                "visibility": "personal",
                "source": f"# %% [id={cell_id}] code\nprint(2 + 2)\n",
            },
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        response = client.get(
            f"/tech-lab/notebooks/{nb['id']}/export",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["nbformat"] == 4
        assert body["cells"][0]["id"] == cell_id
        assert body["metadata"]["misp_workbench"]["name"] == "export-me"

    @pytest.mark.parametrize("scopes", [["lab:create", "lab:read"]])
    def test_import_creates_personal_notebook(
        self,
        client: TestClient,
        auth_token: auth.Token,
        api_tester_user: user_models.User,
    ):
        import io
        import json as _json

        blob = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {"misp_workbench": {"name": "imported"}},
            "cells": [
                {
                    "cell_type": "code",
                    "id": "id-x",
                    "source": "print('hi')\n",
                    "outputs": [],
                    "execution_count": None,
                }
            ],
        }
        files = {
            "file": (
                "imported.ipynb",
                io.BytesIO(_json.dumps(blob).encode("utf-8")),
                "application/json",
            )
        }
        response = client.post(
            "/tech-lab/notebooks/import",
            files=files,
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        data = response.json()
        assert data["user_id"] == api_tester_user.id
        assert data["visibility"] == "personal"
        assert "[id=id-x] code" in data["source"]


class _FakeManager:
    def __init__(self):
        self.shutdown_called = False
        self.interrupt_called = False

    def shutdown_kernel(self, now=False):
        self.shutdown_called = True

    def interrupt_kernel(self):
        self.interrupt_called = True


class _FakeClient:
    def __init__(self):
        self.channels_stopped = False

    def stop_channels(self):
        self.channels_stopped = True


class TestKernelManagerUnit:
    def test_idle_eviction_pops_and_tears_down(self):
        """Eviction must shut down the kernel manager and remove the per-kernel
        tempdir — earlier versions only popped the dict entry, leaking the
        subprocess and its working directory."""
        import os
        import tempfile
        import time

        from app.services.tech_lab.lab.kernel_manager import (
            LabKernelRegistry,
            _Entry,
        )

        reg = LabKernelRegistry(idle_seconds=0)  # immediate eviction
        manager = _FakeManager()
        client = _FakeClient()
        cwd = tempfile.mkdtemp(prefix="lab-test-")
        reg._kernels[(1, 1)] = _Entry(
            manager=manager,
            client=client,
            cwd=cwd,
            last_active=time.monotonic() - 10,
        )
        reg._evict_idle()
        assert (1, 1) not in reg._kernels
        assert manager.shutdown_called
        assert client.channels_stopped
        assert not os.path.exists(cwd)
