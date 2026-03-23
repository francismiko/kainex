"""CLI entry-point for the Kainex AI Trading Agent.

Usage:
    python -m agent              Run the agent loop (default)
    python -m agent versions     List all strategy versions
    python -m agent stats        Show current version stats
    python -m agent compare      Compare all versions side-by-side
    python -m agent best         Show the best-performing version
"""

from __future__ import annotations

import json
import sys

from agent.strategy_journal import StrategyJournal


def _journal() -> StrategyJournal:
    return StrategyJournal()


# ── Formatters ────────────────────────────────────────────────────


def _print_version(v: dict, *, verbose: bool = False) -> None:
    active = " (active)" if v.get("is_active") else ""
    print(f"\n{'=' * 60}")
    print(f"  Version:  {v['version_id']}{active}")
    print(f"  Persona:  {v['persona']}")
    print(f"  Model:    {v['model']}")
    print(f"  Created:  {v['created_at']}")

    stats = v.get("stats")
    if stats:
        print(f"  Trades:   {stats['trade_count']}")
        print(f"  Win rate: {stats['win_rate']:.1f}%")
        print(f"  PnL:      {stats['total_pnl']:.2f}")
        print(f"  Max DD:   {stats['max_drawdown']:.2f}")
        print(f"  Sharpe:   {stats['sharpe_ratio']:.4f}")

    if verbose:
        print(f"  Params:   {json.dumps(v['parameters'], ensure_ascii=False)}")
        print(f"  Reasoning: {v['reasoning'][:300]}")


def _print_stats(stats: dict) -> None:
    print(f"  Trades:       {stats['trade_count']}")
    print(f"  Decisions:    {stats['decision_count']}")
    print(f"  Wins/Losses:  {stats['win_count']} / {stats['loss_count']}")
    print(f"  Win rate:     {stats['win_rate']:.1f}%")
    print(f"  Total PnL:    {stats['total_pnl']:.2f}")
    print(f"  Max drawdown: {stats['max_drawdown']:.2f}")
    print(f"  Sharpe ratio: {stats['sharpe_ratio']:.4f}")
    print(f"  Avg confid.:  {stats['avg_confidence']:.4f}")


# ── Commands ──────────────────────────────────────────────────────


def cmd_versions() -> None:
    """List all strategy versions."""
    journal = _journal()
    versions = journal.list_versions()
    journal.close()

    if not versions:
        print("No strategy versions found.")
        return

    print(f"Found {len(versions)} strategy version(s):")
    for v in versions:
        _print_version(v, verbose=True)
    print()


def cmd_stats() -> None:
    """Show stats for the active strategy version."""
    journal = _journal()
    active = journal.get_active_version()
    if active is None:
        print("No active strategy version.")
        journal.close()
        return

    stats = journal.get_version_stats(active["version_id"])
    journal.close()

    print(f"\nActive strategy: {active['version_id']}")
    print(f"  Persona: {active['persona']}")
    print(f"  Model:   {active['model']}")
    print(f"  Created: {active['created_at']}")
    print()
    _print_stats(stats)
    print()


def cmd_compare() -> None:
    """Compare all versions side-by-side."""
    journal = _journal()
    versions = journal.list_versions()
    journal.close()

    if not versions:
        print("No strategy versions to compare.")
        return

    # Header.
    header = f"{'Version':<10} {'Persona':<14} {'Trades':>7} {'Win%':>7} {'PnL':>12} {'MaxDD':>10} {'Sharpe':>8}"
    print(f"\n{header}")
    print("-" * len(header))

    for v in versions:
        s = v.get("stats", {})
        active = "*" if v.get("is_active") else " "
        print(
            f"{active}{v['version_id']:<9} {v['persona']:<14} {s.get('trade_count', 0):>7} "
            f"{s.get('win_rate', 0):>6.1f}% {s.get('total_pnl', 0):>11.2f} "
            f"{s.get('max_drawdown', 0):>10.2f} {s.get('sharpe_ratio', 0):>8.4f}"
        )

    print()


def cmd_best() -> None:
    """Show the best strategy version by PnL."""
    journal = _journal()
    best = journal.get_best_version(metric="pnl")
    journal.close()

    if best is None:
        print("No strategy versions found.")
        return

    print("\nBest strategy version (by PnL):")
    _print_version(best, verbose=True)
    print()


# ── Dispatch ──────────────────────────────────────────────────────


COMMANDS: dict[str, tuple[callable, str]] = {
    "versions": (cmd_versions, "List all strategy versions"),
    "stats": (cmd_stats, "Show current version statistics"),
    "compare": (cmd_compare, "Compare all versions"),
    "best": (cmd_best, "Show best-performing version"),
}


def dispatch(args: list[str] | None = None) -> bool:
    """Handle CLI sub-commands.

    Returns ``True`` if a sub-command was handled, ``False`` if the
    default agent run-loop should start.
    """
    argv = args if args is not None else sys.argv[1:]

    if not argv:
        return False  # No sub-command: run the agent.

    cmd = argv[0].lower()

    if cmd in ("--help", "-h", "help"):
        print("Kainex AI Trading Agent\n")
        print("Usage: python -m agent [command]\n")
        print("Commands:")
        for name, (_, desc) in COMMANDS.items():
            print(f"  {name:<12} {desc}")
        print(f"  {'(default)':<12} Run the agent trading loop")
        return True

    if cmd in COMMANDS:
        fn, _ = COMMANDS[cmd]
        fn()
        return True

    # Unknown command: let the caller decide.
    return False
