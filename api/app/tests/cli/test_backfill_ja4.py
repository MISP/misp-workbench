"""The backfill-ja4 command, with the repository mocked out.

What the repository calls actually do is covered against OpenSearch in
tests/repositories/test_ja4_correlations.py.
"""

from unittest.mock import MagicMock, patch

import pytest
from app.cli.__main__ import app
from typer.testing import CliRunner

CLI = "app.cli.__main__"


@pytest.fixture
def repo():
    with patch(f"{CLI}.correlations_repository") as repo, patch(
        f"{CLI}.SessionLocal"
    ), patch(f"{CLI}.get_runtime_settings", return_value=MagicMock()):
        repo.count_ja4_candidates.return_value = 5
        repo.start_ja4_reindex.return_value = "task-1"
        repo.ja4_reindex_status.side_effect = [
            {"completed": False, "total": 5, "updated": 2, "failures": []},
            {"completed": True, "total": 5, "updated": 5, "failures": []},
        ]
        repo.ja4_matching_enabled.return_value = True
        repo.recorrelate_ja4_attributes.return_value = {"attributes": 4, "stored": 8}
        with patch("time.sleep"):
            yield repo


def test_dry_run_only_counts(repo):
    result = CliRunner().invoke(app, ["backfill-ja4", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "5 attribute(s) would be reprocessed" in result.output
    repo.start_ja4_reindex.assert_not_called()
    repo.recorrelate_ja4_attributes.assert_not_called()


def test_reindexes_then_recorrelates(repo):
    result = CliRunner().invoke(app, ["backfill-ja4"])

    assert result.exit_code == 0, result.output
    assert "5 attribute(s) reprocessed, 0 failure(s)" in result.output
    assert "4 fingerprint(s) re-correlated, 8 correlation(s) stored" in result.output
    repo.ja4_reindex_status.assert_called_with("task-1")


def test_skip_correlations(repo):
    result = CliRunner().invoke(app, ["backfill-ja4", "--skip-correlations"])

    assert result.exit_code == 0, result.output
    repo.start_ja4_reindex.assert_called_once()
    repo.recorrelate_ja4_attributes.assert_not_called()


def test_leaves_correlations_alone_when_ja4_is_off(repo):
    repo.ja4_matching_enabled.return_value = False

    result = CliRunner().invoke(app, ["backfill-ja4"])

    assert result.exit_code == 0, result.output
    assert "ja4 correlation match type is off" in result.output
    repo.recorrelate_ja4_attributes.assert_not_called()
