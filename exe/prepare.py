"""Before building ModHub.exe: make the icon and the release notes from modhub.py."""
import ast
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / "build"
out.mkdir(exist_ok=True)
src = (root / "modhub.py").read_text("utf-8")

# release notes: this version's entry in APP_CHANGES
version, notes = "", []
for node in ast.parse(src).body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "APP_VERSION" for t in node.targets):
        version = ast.literal_eval(node.value)
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "APP_CHANGES" for t in node.targets):
        entries = ast.literal_eval(node.value)
        notes = next((e["notes"] for e in entries if e["version"] == version), [])
body = "\n".join(f"- {n}" for n in notes) or "- Improvements and fixes."
(out / "notes.md").write_text(
    f"## What's new in ModHub {version}\n\n{body}\n\n"
    "**Windows:** download **ModHub.exe** below and double-click it. If Windows says \"Windows protected your PC\", "
    "click **More info**, then **Run anyway**.\n\n"
    "**Mac:** download **ModHub-mac.zip** (Macs with Apple chips) or **ModHub-mac-intel.zip** (older Intel Macs), "
    "open it, and drag ModHub into Applications. The first time, macOS may say it can't check ModHub: open "
    "**System Settings > Privacy & Security**, scroll down and click **Open Anyway**.\n\n"
    "You only need to do that once. ModHub keeps itself up to date after that.\n",
    "utf-8")

# icon: ModHub draws its own
sys.path.insert(0, str(root))
import modhub  # noqa: E402
icons = modhub.write_icons()
shutil.copy2(icons / "modhub.ico", out / "modhub.ico")
shutil.copy2(icons / "modhub.icns", out / "modhub.icns")
print(f"ModHub {version}: icon and notes ready")
