# This file intentionally left minimal to avoid
# conflicting with the openai-agents SDK package.
#
# The local agents/ directory (industry-specific agents) shadows the
# installed openai-agents SDK.  We re-export the SDK's public symbols
# so that `from agents import Agent` etc. continue to work.

import importlib as _importlib
import sys as _sys
import os as _os


def _load_sdk():
    """Import the real openai-agents SDK, bypassing this local package."""
    this_dir = _os.path.dirname(_os.path.abspath(__file__))
    parent_dir = _os.path.dirname(this_dir)

    # 1. Remove this partially-loaded local package from sys.modules
    saved_self = _sys.modules.pop(__name__, None)

    # 2. Remove the project root from sys.path so Python skips us
    original_path = _sys.path[:]
    _sys.path = [
        p for p in _sys.path
        if _os.path.realpath(p) != _os.path.realpath(parent_dir)
    ]

    sdk = None
    try:
        # 3. Import the SDK — it loads as "agents" so relative imports work
        sdk = _importlib.import_module("agents")
    except ImportError:
        pass
    finally:
        # 4. Restore sys.path
        _sys.path = original_path
        # 5. Restore our module in sys.modules (SDK sub-modules stay)
        if saved_self is not None:
            _sys.modules[__name__] = saved_self

    return sdk


_sdk = _load_sdk()

if _sdk is not None:
    # Re-export every public symbol from the SDK
    _exports = {k: getattr(_sdk, k) for k in dir(_sdk) if not k.startswith("_")}
    globals().update(_exports)
