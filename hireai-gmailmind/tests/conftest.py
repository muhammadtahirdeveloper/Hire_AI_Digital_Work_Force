"""Shared test fixtures and module mocks for the GmailMind test suite.

Mocks heavy dependencies (pgvector, database engine, etc.) so tests
can run without PostgreSQL or optional C-extension packages installed.

This conftest is loaded by pytest before any test module, ensuring
all problematic imports are intercepted early.
"""

import sys
import types
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mock pgvector before any model import touches it
# ---------------------------------------------------------------------------
_mock_pgvector = types.ModuleType("pgvector")
_mock_pgvector_sa = types.ModuleType("pgvector.sqlalchemy")
_mock_pgvector_sa.Vector = MagicMock  # type: ignore
sys.modules.setdefault("pgvector", _mock_pgvector)
sys.modules.setdefault("pgvector.sqlalchemy", _mock_pgvector_sa)

# ---------------------------------------------------------------------------
# Mock config.database (SessionLocal, engine, Base) before any import
# ---------------------------------------------------------------------------
if "config.database" not in sys.modules:
    _mock_db_module = types.ModuleType("config.database")
    _mock_db_module.SessionLocal = MagicMock  # type: ignore
    _mock_db_module.engine = MagicMock()  # type: ignore
    _mock_db_module.Base = MagicMock()  # type: ignore
    sys.modules["config.database"] = _mock_db_module

# ---------------------------------------------------------------------------
# Mock models.schemas — ORM models that need pgvector + real Base.
# We replace the entire module with mock classes so imports work.
# ---------------------------------------------------------------------------
if "models.schemas" not in sys.modules:
    _mock_schemas = types.ModuleType("models.schemas")
    for _cls_name in [
        "SenderProfile", "ActionLog", "FollowUp", "EmailEmbedding",
    ]:
        setattr(_mock_schemas, _cls_name, type(_cls_name, (), {}))
    sys.modules["models.schemas"] = _mock_schemas

# ---------------------------------------------------------------------------
# Mock celery app used by scheduler.tasks
# ---------------------------------------------------------------------------
if "celery" not in sys.modules:
    _mock_celery = types.ModuleType("celery")
    _mock_celery.Celery = MagicMock  # type: ignore
    sys.modules["celery"] = _mock_celery

# ---------------------------------------------------------------------------
# Ensure the local agents package has SDK symbols (function_tool, Agent, etc.)
# even when the openai-agents SDK is not installed.
# ---------------------------------------------------------------------------
import agents as _agents_pkg  # noqa: E402

if not hasattr(_agents_pkg, "function_tool"):
    _agents_pkg.function_tool = lambda fn: fn  # type: ignore

if not hasattr(_agents_pkg, "Agent"):
    _agents_pkg.Agent = type("Agent", (), {})  # type: ignore

if not hasattr(_agents_pkg, "Runner"):
    _agents_pkg.Runner = MagicMock  # type: ignore
