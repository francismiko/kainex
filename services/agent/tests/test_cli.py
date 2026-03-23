from pathlib import Path
from unittest.mock import patch

import pytest

from agent.cli import dispatch, cmd_versions, cmd_stats, cmd_compare, cmd_best
from agent.strategy_journal import StrategyJournal


@pytest.fixture()
def journal(tmp_path: Path) -> StrategyJournal:
    db = tmp_path / "cli_test.db"
    return StrategyJournal(db_path=str(db))


class TestDispatch:
    def test_no_args_returns_false(self):
        assert dispatch([]) is False

    def test_help_returns_true(self, capsys):
        assert dispatch(["--help"]) is True
        out = capsys.readouterr().out
        assert "Usage" in out

    def test_known_commands_return_true(self, tmp_path: Path):
        """All known sub-commands return True (handled)."""
        db_path = str(tmp_path / "dispatch.db")
        # Each call to _journal() must return a fresh instance since
        # commands close the journal when they're done.
        with patch("agent.cli._journal", side_effect=lambda: StrategyJournal(db_path)):
            for cmd in ("versions", "stats", "compare", "best"):
                assert dispatch([cmd]) is True

    def test_unknown_command_returns_false(self):
        assert dispatch(["nonexistent"]) is False


class TestCLICommands:
    """Smoke-test each command against a real (temporary) journal."""

    def test_versions_empty(self, capsys, tmp_path: Path):
        with patch("agent.cli._journal", return_value=StrategyJournal(str(tmp_path / "a.db"))):
            cmd_versions()
        out = capsys.readouterr().out
        assert "No strategy versions" in out

    def test_versions_with_data(self, capsys, tmp_path: Path):
        j = StrategyJournal(str(tmp_path / "b.db"))
        j.create_version("balanced", "m", {"x": 1}, "test")
        with patch("agent.cli._journal", return_value=j):
            cmd_versions()
        out = capsys.readouterr().out
        assert "v1" in out
        assert "balanced" in out

    def test_stats_no_active(self, capsys, tmp_path: Path):
        with patch("agent.cli._journal", return_value=StrategyJournal(str(tmp_path / "c.db"))):
            cmd_stats()
        out = capsys.readouterr().out
        assert "No active" in out

    def test_stats_with_active(self, capsys, tmp_path: Path):
        j = StrategyJournal(str(tmp_path / "d.db"))
        j.create_version("aggressive", "m", {}, "r")
        with patch("agent.cli._journal", return_value=j):
            cmd_stats()
        out = capsys.readouterr().out
        assert "aggressive" in out
        assert "Trades:" in out

    def test_compare_empty(self, capsys, tmp_path: Path):
        with patch("agent.cli._journal", return_value=StrategyJournal(str(tmp_path / "e.db"))):
            cmd_compare()
        out = capsys.readouterr().out
        assert "No strategy versions" in out

    def test_compare_with_data(self, capsys, tmp_path: Path):
        j = StrategyJournal(str(tmp_path / "f.db"))
        j.create_version("balanced", "m", {}, "a")
        j.create_version("aggressive", "m", {}, "b")
        with patch("agent.cli._journal", return_value=j):
            cmd_compare()
        out = capsys.readouterr().out
        assert "v1" in out
        assert "v2" in out

    def test_best_empty(self, capsys, tmp_path: Path):
        with patch("agent.cli._journal", return_value=StrategyJournal(str(tmp_path / "g.db"))):
            cmd_best()
        out = capsys.readouterr().out
        assert "No strategy versions" in out

    def test_best_with_data(self, capsys, tmp_path: Path):
        j = StrategyJournal(str(tmp_path / "h.db"))
        v1 = j.create_version("balanced", "m", {}, "a")
        j.record_trade(v1, {"symbol": "BTC", "action": "buy", "price": 1, "quantity": 1, "pnl": 500.0})
        with patch("agent.cli._journal", return_value=j):
            cmd_best()
        out = capsys.readouterr().out
        assert "v1" in out
        assert "Best" in out
