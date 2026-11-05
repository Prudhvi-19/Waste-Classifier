"""Replace the two legacy version checks used by fast.ai v1, not setuptools."""
import importlib
import sys
from importlib.metadata import distribution
from threading import Lock
from types import ModuleType

from packaging.requirements import Requirement

_IMPORT_LOCK = Lock()


def require_installed(specification):
    """The narrow pkg_resources.require API used in fastai/imports/core.py."""
    requirement = Requirement(specification)
    if requirement.extras:
        raise ValueError("Extras are not supported by the fast.ai compatibility check")
    if requirement.marker and not requirement.marker.evaluate():
        return []
    installed = distribution(requirement.name)
    if not requirement.specifier.contains(installed.version, prereleases=True):
        raise ImportError(f"{specification} is required; found {installed.version}")
    return [installed]


def import_fastai_vision():
    # fastai v1 only uses pkg_resources.require for version checks. Keeping old
    # setuptools solely for this API reintroduces security advisories. Supply
    # that narrow API during import, then remove it from the module registry.
    # fastai retains its reference; unrelated imports do not see a fake package.
    with _IMPORT_LOCK:
        if "fastai.vision" in sys.modules:
            return sys.modules["fastai.vision"]
        compatibility = ModuleType("pkg_resources")
        compatibility.require = require_installed
        previous = sys.modules.get("pkg_resources")
        sys.modules["pkg_resources"] = compatibility
        try:
            return importlib.import_module("fastai.vision")
        finally:
            if previous is None:
                sys.modules.pop("pkg_resources", None)
            else:
                sys.modules["pkg_resources"] = previous
