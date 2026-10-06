from pathlib import Path

import pytest

CUSTOM_COMPONENTS = str(Path(__file__).parent.parent / "custom_components")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    import custom_components

    if CUSTOM_COMPONENTS not in custom_components.__path__:
        custom_components.__path__.insert(0, CUSTOM_COMPONENTS)
    yield
