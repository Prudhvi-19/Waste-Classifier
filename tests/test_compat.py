import subprocess
import sys

import pytest

from app.fastai_compat import require_installed


def test_dependency_check_accepts_installed_version():
    assert require_installed("fastprogress>=0.2.1")[0].version == "1.0.3"


def test_dependency_check_does_not_suppress_version_conflicts():
    with pytest.raises(ImportError):
        require_installed("fastprogress>=999")


def test_compat_import_does_not_leave_a_global_pkg_resources_override():
    subprocess.run([sys.executable, "-c", "from app.fastai_compat import import_fastai_vision; import sys; import_fastai_vision(); assert 'pkg_resources' not in sys.modules"], check=True)
