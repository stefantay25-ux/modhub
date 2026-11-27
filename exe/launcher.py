"""ModHub.exe: a small starter that runs ModHub with the Python inside the .exe.

ModHub itself lives in your data folder (~/.modhub/app/modhub.py), so it can keep updating
itself from GitHub exactly like the Python version does. This .exe only needs replacing if
you want a newer Python or window engine.
"""
import os
import re
import runpy
import shutil
import sys
from pathlib import Path

# Every copy of ModHub.exe that ModHub starts (its window, a restart) unpacks fresh,
# so it never depends on the folder of the copy that started it.
os.environ["PYINSTALLER_RESET_ENVIRONMENT"] = "1"


def version_of(path):
    try:
        m = re.search(r'^APP_VERSION = "([^"]+)"', path.read_text("utf-8"), re.M)
        return tuple(int(x) for x in re.findall(r"\d+", m.group(1))) if m else ()
    except (OSError, UnicodeDecodeError):
        return ()


def works(path):
    try:
        compile(path.read_text("utf-8"), str(path), "exec")
        return True
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
        return False


def main():
    bundled = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "modhub.py"
    app = Path.home() / ".modhub" / "app" / "modhub.py"
    args = sys.argv[1:]
    if args and args[0].lower().endswith(".py") and Path(args[0]).is_file():
        script, args = Path(args[0]), args[1:]  # ModHub starting another copy of itself
    else:
        if not app.exists() or not works(app) or version_of(bundled) > version_of(app):
            app.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled, app)
        script = app
    sys.argv = [str(script), *args]
    sys.path.insert(0, str(script.parent))
    runpy.run_path(str(script), run_name="__main__")


if False:  # never runs: tells the .exe builder to pack everything ModHub uses
    import modhub  # noqa: F401
    import webview  # noqa: F401

main()
