"""Allow running as ``python -m agent``."""

from agent.cli import dispatch

if not dispatch():
    from agent.main import main
    main()
