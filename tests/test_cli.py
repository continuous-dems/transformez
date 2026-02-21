import subprocess
import sys

# CMD will run Transformez
CMD = [sys.executable, "-m", "transformez.cli"]


def run_transformez(args):
    """Run transformez and return result."""

    return subprocess.run(CMD + args, capture_output=True, text=True)


def test_help():
    """Does the help menu work?"""

    result = run_transformez(["--help"])
    assert result.returncode == 0


def test_version():
    """Does version print?"""

    result = run_transformez(["--version"])
    assert result.returncode == 0


def test_list_modules():
    """Can we list datums without crashing?"""

    result = run_transformez(["--list-datums"])
    assert result.returncode == 0
    assert "lat" in result.stdout
    assert "mllw" in result.stdout
    assert "NAVD88" in result.stdout
    assert "g2018" in result.stdout
