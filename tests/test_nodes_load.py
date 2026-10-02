import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_loads_without_google_sdk():
    spec = importlib.util.spec_from_file_location(
        "gemini_v2_testpkg",
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert len(module.NODE_CLASS_MAPPINGS) >= 7
