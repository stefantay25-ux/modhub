#!/usr/bin/env python3
"""
ModHub - your go-to Minecraft mods, installed into any version and launcher.

Double-click modhub.py (or run: python modhub.py). It opens in its own app window
using Edge or Chrome's app mode. If neither is installed, it opens in a browser tab.
Close the window to quit. In the app you can add a desktop / Start menu shortcut.

The first time, build your mod library by searching Modrinth + CurseForge, or by
importing an existing mods folder. After that, pick a Minecraft version and a
launcher and click Install.

Mods, resource packs and shaders come from Modrinth, or from files you add yourself (for example
ones you downloaded from CurseForge: drag them into ModHub).

Launchers:
  Minecraft Launcher  creates a new profile with its own mods folder
                      (Fabric/Quilt fully automatic, Forge/NeoForge need the loader installed once)
  Prism Launcher      creates a ready-to-play instance
  Modrinth App        builds a .mrpack modpack and opens it in the app to import
  CurseForge App      builds a profile .zip to import (Create Custom Profile -> Import)
  Lunar Client        copies Fabric mods into the Lunar mods folder you choose
  Any folder          copies mods into any mods folder (works with every launcher)

Mods that aren't out for your version can optionally be ported with Claude Code.

Options: --tab (open in a normal browser tab), --console (Windows: keep the console window)

Only needs Python 3.8+. No extra packages. Your library + settings live in ~/.modhub/
"""

import ast
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
import zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_VERSION = "4.0.6"
FROZEN = bool(getattr(sys, "frozen", False))  # running inside ModHub.exe
# What's new in each version of ModHub, newest first. Shown after an update, before one, and in Settings.
APP_CHANGES = [
    {"version": "4.0.2", "notes": [
        "ModHub is now available for Linux. Download it from the website, extract the archive and run ModHub.",
    ]},
    {"version": "4.0", "notes": [
        "Introducing the Home page: mod updates, your instances, recent fixes and suggested mods, all on one screen. Home is now the first page ModHub opens to.",
        "Mod updates in one place. ModHub checks every instance for newer versions of your mods, shows the changelog for each one, and updates them all with a single click.",
        "Modpack sharing. Share any loadout as a short code or a .modhub file, and anyone can add it to ModHub in one step.",
        "Modrinth modpack support. Export a loadout as a .mrpack for Prism, the Modrinth App and other launchers, or open any .mrpack to add it to ModHub.",
    ]},
    {"version": "3.8.1", "notes": [
        "Fluid animations are now the default, with smoother page transitions, collapsing page titles, cards that ease into view and refined pop-up windows.",
        "If you chose Fewer or Off, your setting is kept. The previous animations remain available as Classic under More options.",
    ]},
    {"version": "3.8", "notes": [
        "A refreshed interface with more spacing, shorter page introductions, softer cards and a cleaner sidebar.",
        "What's new has moved to the sidebar, below How to use.",
        "New Fluid animations, available as a preview under Settings, More options, Animations.",
        "Fixed an issue where the ModHub logo kept spinning after it was clicked.",
    ]},
    {"version": "3.7.3", "notes": [
        "Added a new hidden theme with its own pixel font.",
    ]},
    {"version": "3.7.2", "notes": [
        "ModHub now checks for updates every 30 minutes, and again when you return to it, so new versions arrive sooner.",
        "You're notified as soon as a new version is ready to install.",
        "Added more hidden themes. Settings now shows how many you've found.",
    ]},
    {"version": "3.7.1", "notes": [
        "Seven new themes: Sunset, Aurora, Nether, The End, Deep sea, Cherry and Mint.",
        "Aurora, Nether, The End and Deep sea have animated backgrounds. Set Animations to Off in More options to keep them still.",
        "Added a few hidden themes to discover.",
    ]},
    {"version": "3.7", "notes": [
        "ModHub now checks an instance whenever its mods change, including mods added by hand, and fixes problems before you launch the game.",
        "Duplicate copies of the same mod are detected, and the extra copy is turned off.",
        "Mods built for a different loader, such as a NeoForge mod in a Fabric instance, are replaced with the correct version or turned off if none exists.",
    ]},
    {"version": "3.6", "notes": [
        "ModHub now resolves \"Incompatible mods found!\" errors automatically. When Fabric, Quilt, NeoForge or Forge stops the game, ModHub adds missing mods, swaps in compatible versions and turns off conflicting ones.",
        "Progress appears at the top of ModHub, followed by a summary of every change. Then launch Minecraft again.",
        "Failed or corrupted downloads are now retried automatically.",
    ]},
    {"version": "3.5", "notes": [
        "On Windows, the Python version of ModHub now upgrades itself to the ModHub app, so it always opens in its own window.",
        "Desktop and Start menu shortcuts, and modhub.py itself, now open the app.",
    ]},
    {"version": "3.4", "notes": [
        "Added How to use: a short four-step guide at the bottom of the sidebar, with shortcuts to each page.",
    ]},
    {"version": "3.3", "notes": [
        "ModHub is now available for Mac, for both Apple silicon and Intel Macs.",
        "More options under Appearance is reorganised into two panels, Colours and Layout.",
    ]},
    {"version": "3.2", "notes": [
        "Appearance is simpler: choose from nine ready-made themes, or pick any colour with Your colour. Detailed options remain under More options.",
        "Discover now shows a sharp mod icon when a mod has no screenshots, instead of a blurred image.",
        "ModHub is now available as a standalone Windows app (ModHub.exe), with no Python required. It updates itself automatically.",
    ]},
    {"version": "3.1", "notes": [
        "Gradient backgrounds that fade your colour into black in dark mode or white in light mode, with Gradient, Vivid, Glow and Plain styles, direction and strength controls.",
        "Custom colours: choose any colour under Colour.",
        "More customisation: corner style, a translucent sidebar, four interface sizes and animation levels.",
        "Updates are now delivered directly from GitHub, with no setup required.",
        "Settings and the Install page are now organised into clear sections.",
        "Higher-resolution images: mod pages open with the featured image and full-size screenshots, and Discover shows a screenshot for each mod.",
    ]},
    {"version": "3.0", "notes": [
        "Introducing Discover: popular and recently updated mods for your Minecraft version, plus recommendations based on your library.",
        "Mod pages: view screenshots, descriptions, requirements and version availability for any mod.",
        "Light mode, dark mode or match your system, plus six colour themes, under Settings, Appearance.",
        "A cleaner layout with fewer buttons in Library, a tidier sidebar and Settings grouped into sections.",
        "Fixed the logo darkening on hover.",
    ]},
    {"version": "2.6", "notes": [
        "Added a What's new button showing recent updates or the full history.",
        "A red dot indicates an update you haven't read about yet.",
    ]},
    {"version": "2.5", "notes": [
        "After an update, ModHub shows what changed. You can also preview what's coming before you update.",
        "The full update history is available under Settings, Updates.",
    ]},
    {"version": "2.4", "notes": [
        "Quick search: press Ctrl+K, or click Search in the sidebar, to jump to any page, mod, loadout or action.",
        "Installs show a progress ring, with each mod listed as it completes.",
        "Refined switches, dropdowns and button feedback.",
        "The page title becomes a compact bar as you scroll.",
        "Tooltips on mod slots, illustrated empty states and an animated logo on start-up.",
    ]},
    {"version": "2.3", "notes": [
        "What changed: after updating an instance, view each mod's changelog.",
        "Library backups: save your entire library to one file and restore it on another computer.",
    ]},
    {"version": "2.2", "notes": [
        "Crash helper: when Minecraft crashes, ModHub identifies the responsible mod and offers a fix.",
        "Performance boost: add a trusted set of mods for higher FPS in one click.",
        "Bring your settings, keybinds and server list into a new instance.",
    ]},
    {"version": "2.1", "notes": [
        "ModHub now checks that your mods are compatible and fixes what it can, such as mismatched Sodium and Iris versions.",
        "Anything that can't be fixed automatically is listed, with an option to turn that mod off.",
    ]},
    {"version": "2.0", "notes": [
        "Loadouts: keep separate sets of mods, such as PvP or Building.",
        "Update my instances: bring everything you've installed up to date in one click.",
        "Notifications when a mod that wasn't ready for your version is released.",
    ]},
    {"version": "1.x", "notes": [
        "Resource packs and shaders, CurseForge file import, automatic detection of new Minecraft versions, a dedicated app window, automatic updates from GitHub, and Port with Claude.",
    ]},
]
USER_AGENT = f"modhub/{APP_VERSION} (personal mod manager script)"
MODRINTH = "https://api.modrinth.com/v2"
LOADERS = ("fabric", "quilt", "forge", "neoforge")
LOADER_NAMES_PY = {"fabric": "Fabric", "quilt": "Quilt", "forge": "Forge", "neoforge": "NeoForge"}
DATA_DIR = Path.home() / ".modhub"
CONFIG_PATH = DATA_DIR / "config.json"
EXPORT_DIR = DATA_DIR / "exports"
PORTS_DIR = DATA_DIR / "ports"
LOCAL_DIR = DATA_DIR / "files"
UPDATES_DIR = DATA_DIR / "updates"
PORT_TASK_FILE = "MODHUB_PORT_TASK.md"
PORT_OUTPUT = "modhub-output"
CLAUDE_PROMPT = "Read MODHUB_PORT_TASK.md in this folder and do the port it describes."
MANIFEST_NAME = ".modhub.json"
VERSIONS_NAME = ".modhub-versions.json"

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass


class UserError(Exception):
    """An error with a message meant for the user."""


# =========================================================================== #
# HTTP
# =========================================================================== #
def http_json(method, url, body=None, headers=None, retries=4):
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (401, 403) and "curseforge" in url:
                raise UserError("CurseForge rejected the API key. Check it in Settings.")
            if e.code == 429 or e.code >= 500:
                reset = e.headers.get("X-Ratelimit-Reset")
                time.sleep(min(max(int(reset) if reset and reset.isdigit() else 2 ** attempt, 1), 60))
                last = e
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2 ** attempt)
    raise UserError(f"Couldn't reach {urllib.parse.urlparse(url).netloc} - check your internet. ({last})")


def zread(z, name, limit=32_000_000):
    """Read a file inside a .jar/.zip, refusing absurd sizes (a crafted file could otherwise exhaust memory)."""
    info = z.getinfo(name) if isinstance(name, str) else name
    if info.file_size > limit:
        raise ValueError(f"{info.filename} is too big to read")
    return z.read(info)


def safe_filename(name):
    """A file name from the internet, safe to write into a mods folder: no folders, no tricks."""
    base = str(name or "").replace("\\", "/").split("/")[-1].strip()
    if not base or base in (".", "..") or base.startswith(".") or any(ord(c) < 32 for c in base) \
            or re.search(r'[<>:"|?*]', base) or len(base) > 200:
        raise UserError(f"Skipped a file with an unsafe name: {str(name)[:80]!r}")
    return base


def download(url, dest: Path, expected_sha1=None, attempts=3):
    """Download with a few automatic retries: a dropped connection or a damaged file is tried again."""
    for n in range(attempts):
        try:
            return _download_once(url, dest, expected_sha1)
        except UserError:
            raise
        except Exception:
            if n == attempts - 1:
                raise
            time.sleep(1.5 * (n + 1))


def _download_once(url, dest: Path, expected_sha1=None):
    if not str(url).startswith("https://"):
        raise UserError("Refused to download over an insecure connection.")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    fd, tmp = tempfile.mkstemp(dir=dest.parent, suffix=".part")
    h = hashlib.sha1()
    try:
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(req, timeout=120) as r:
            for chunk in iter(lambda: r.read(1 << 16), b""):
                h.update(chunk)
                out.write(chunk)
        if expected_sha1 and h.hexdigest().lower() != expected_sha1.lower():
            raise RuntimeError("file failed its hash check")
        os.replace(tmp, dest)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def chunks(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def q(params):
    return urllib.parse.urlencode(params)


# =========================================================================== #
# Local file helpers
# =========================================================================== #
def sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_mod_ids(jar):
    """The in-game mod id(s) a jar declares, used to catch the same mod coming from two sites."""
    ids = set()
    try:
        with zipfile.ZipFile(jar) as z:
            names = set(z.namelist())
            if "fabric.mod.json" in names:
                try:
                    ids.add(json.loads(zread(z, "fabric.mod.json").decode("utf-8", "replace"), strict=False)["id"])
                except Exception:
                    pass
            if "quilt.mod.json" in names:
                try:
                    ids.add(json.loads(zread(z, "quilt.mod.json").decode("utf-8", "replace"))["quilt_loader"]["id"])
                except Exception:
                    pass
            for toml in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
                if toml in names:
                    text = zread(z, toml).decode("utf-8", "replace")
                    ids.update(re.findall(r'^\s*modId\s*=\s*"([^"]+)"', text, re.M))
                    break
    except Exception:
        pass
    return ids


def safe_name(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip().rstrip(".") or "ModHub"


def open_path(path):
    path = str(path)
    if platform.system() == "Windows":
        os.startfile(path)  # noqa
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# =========================================================================== #
# Config
# =========================================================================== #
def default_paths():
    home = Path.home()
    system = platform.system()
    if system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return {"official": appdata / ".minecraft", "prism": appdata / "PrismLauncher",
                "modrinth_app": appdata / "ModrinthApp", "curseforge_app": home / "curseforge" / "minecraft"}
    if system == "Darwin":
        base = home / "Library" / "Application Support"
        return {"official": base / "minecraft", "prism": base / "PrismLauncher",
                "modrinth_app": base / "ModrinthApp", "curseforge_app": home / "Documents" / "curseforge" / "minecraft"}
    prism = home / ".local/share/PrismLauncher"
    flatpak = home / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher"
    return {"official": home / ".minecraft", "prism": prism if prism.exists() or not flatpak.exists() else flatpak,
            "modrinth_app": home / ".local/share/ModrinthApp", "curseforge_app": home / "curseforge" / "minecraft"}


def load_config():
    cfg = {}
    try:
        cfg = json.loads(CONFIG_PATH.read_text("utf-8"))
    except Exception:
        pass
    # loadouts: several named libraries. CFG["favorites"] is always the active loadout's list.
    if not isinstance(cfg.get("loadouts"), dict) or not cfg["loadouts"]:
        cfg["loadouts"] = {"main": {"name": "My mods", "favorites": cfg.get("favorites") or []}}
        cfg["active_loadout"] = "main"
    if cfg.get("active_loadout") not in cfg["loadouts"]:
        cfg["active_loadout"] = next(iter(cfg["loadouts"]))
    for lo in cfg["loadouts"].values():
        lo.setdefault("favorites", [])
    cfg["favorites"] = cfg["loadouts"][cfg["active_loadout"]]["favorites"]
    all_favs = [f for lo in cfg["loadouts"].values() for f in lo["favorites"]]
    had_cf = "cf_key" in cfg or any(f.get("source") == "curseforge" for f in all_favs)
    cfg.pop("cf_key", None)
    for f in all_favs:
        f.setdefault("kind", "mod")
        if f.get("source") == "curseforge":  # CurseForge search was removed: keep the mod, ask for its file
            f.update(source="local", id=f"cf{f['id']}", files=[], from_curseforge=True)
    cfg.setdefault("loader", "fabric")
    cfg.setdefault("paths", {})
    cfg.setdefault("last", {})
    cfg.setdefault("ports", {})
    cfg.setdefault("installs", [])
    cfg.setdefault("watch", {})
    cfg.setdefault("caught_up", [])
    cfg.setdefault("crashes", [])
    migrated = False
    if not cfg.get("fluid_default"):  # 3.8.1: Fluid animations became the default, so move everyone still on the old default
        cfg["fluid_default"] = True
        if isinstance(cfg.get("theme"), dict) and cfg["theme"].get("motion", "full") == "full":
            cfg["theme"]["motion"] = "fluid"
        migrated = CONFIG_PATH.exists()
    if had_cf or migrated:
        try:
            save_config(cfg)  # wipe the old CurseForge key from disk
        except OSError:
            pass
    return cfg


def save_config(cfg):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps({k: v for k, v in cfg.items() if k != "favorites"}, indent=2), "utf-8")
    private(tmp)
    os.replace(tmp, CONFIG_PATH)


def private(path):
    """Only you can read it (on Mac and Linux; Windows keeps your user folder private already)."""
    try:
        if os.name != "nt":
            os.chmod(path, 0o600)
    except OSError:
        pass


def launcher_path(cfg, key):
    custom = (cfg.get("paths") or {}).get(key)
    return Path(os.path.expandvars(os.path.expanduser(custom))) if custom else default_paths()[key]


CFG_LOCK = threading.Lock()
CFG = load_config()


# =========================================================================== #
# Modrinth
# =========================================================================== #
def search_loaders(loader):
    return ["quilt", "fabric"] if loader == "quilt" else [loader]


def mr_search(query, loader=None, limit=20, kind="mod", version=None, index=None):
    facets = [[f"project_type:{kind}"]]
    if loader and kind == "mod":
        facets.append([f"categories:{l}" for l in search_loaders(loader)])
    if version:
        facets.append([f"versions:{version}"])
    params = {"limit": limit, "facets": json.dumps(facets)}
    if query:
        params["query"] = query
    if index in ("relevance", "downloads", "follows", "newest", "updated"):
        params["index"] = index
    r = http_json("GET", f"{MODRINTH}/search?" + q(params)) or {}
    return [{"source": "modrinth", "id": h["project_id"], "slug": h.get("slug"), "name": h.get("title"),
             "desc": h.get("description", ""), "icon": h.get("icon_url") or "", "downloads": h.get("downloads", 0),
             "author": h.get("author", ""), "kind": kind,
             "shot": _https(h.get("featured_gallery") or next(iter(h.get("gallery") or []), "")),
             "url": f"https://modrinth.com/{kind}/{h.get('slug') or h['project_id']}"}
            for h in r.get("hits") or []]


# ---- Discover: what's out for your version, and what goes with your library ----
GOES_WITH = {  # slug in your library -> (slug to suggest, why)
    "sodium": [("lithium", "faster game logic"), ("ferrite-core", "uses less memory"),
               ("entityculling", "skips drawing what you can't see"), ("immediatelyfast", "faster text and HUD")],
    "embeddium": [("ferrite-core", "uses less memory"), ("modernfix", "faster loading")],
    "iris": [("complementary-reimagined", "a favourite shader for Iris"), ("bsl-shaders", "a classic shader for Iris")],
    "fabric-api": [("modmenu", "see and set up your mods in game")],
    "create": [("jei", "look up Create's recipes")],
    "xaeros-minimap": [("xaeros-world-map", "a full map to go with it")],
    "journeymap": [("waystones", "travel between the places you mark")],
}
DISCOVER_CACHE = {}


def discover_feed(kind, version, loader):
    key = (kind, version, loader)
    hit_ = DISCOVER_CACHE.get(key)
    if hit_ and time.time() - hit_[0] < 600:
        feed = hit_[1]
    else:
        feed = {"popular": mr_search("", loader, 18, kind, version, "follows"),
                "updated": mr_search("", loader, 12, kind, version, "updated")}
        DISCOVER_CACHE[key] = (time.time(), feed)
    with CFG_LOCK:
        mine = {(f.get("slug") or "").lower(): f.get("name") for f in CFG.get("favorites", []) if f.get("source") == "modrinth"}
    wanted = {}
    for slug, name in mine.items():
        for sug, why in GOES_WITH.get(slug, []):
            if sug not in mine and sug not in wanted:
                wanted[sug] = f"Goes with {name}: {why}"
    picks = []
    if wanted:
        try:
            got = http_json("GET", f"{MODRINTH}/projects?" + q({"ids": json.dumps(list(wanted))})) or []
        except Exception:
            got = []
        lds = set(watch_loaders(kind, loader))
        for pr in got:
            ptype = pr.get("project_type") if pr.get("project_type") in ("resourcepack", "shader") else "mod"
            if ptype != kind:
                continue
            if version and pr.get("game_versions") and version not in pr["game_versions"]:
                continue
            if pr.get("loaders") and not lds & set(pr["loaders"]):
                continue
            item = mr_fav(pr)
            item.update(why=wanted.get((pr.get("slug") or "").lower(), ""), downloads=pr.get("downloads", 0))
            picks.append(item)
    return {"picks": picks, **feed}


def _release_like(v):
    return bool(re.fullmatch(r"\d+(\.\d+)+", v or ""))


def project_page(pid, version, loader):
    """Everything the mod page shows: details, pictures, and whether it's out for your version."""
    p = http_json("GET", f"{MODRINTH}/project/{urllib.parse.quote(pid)}")
    if not p:
        raise UserError("Modrinth doesn't have that project any more.")
    kind = p.get("project_type") if p.get("project_type") in ("resourcepack", "shader") else "mod"
    out = mr_fav(p)
    out.update(body=(p.get("body") or "")[:20000], downloads=p.get("downloads", 0), followers=p.get("followers", 0),
               categories=[c for c in p.get("categories") or [] if c not in LOADERS][:8], loaders=p.get("loaders") or [],
               gallery=[{"url": _https(g.get("url")), "full": _https(g.get("raw_url")) or _https(g.get("url")),
                         "title": g.get("title") or "", "featured": bool(g.get("featured"))}
                        for g in sorted(p.get("gallery") or [], key=lambda g: (not g.get("featured"), g.get("ordering", 0)))
                        if isinstance(g, dict) and _https(g.get("url"))][:10],
               license=(p.get("license") or {}).get("name") or (p.get("license") or {}).get("id") or "",
               updated=p.get("updated") or "", links={k: p.get(k) for k in ("source_url", "issues_url", "wiki_url", "discord_url")
                                                       if str(p.get(k) or "").startswith("https://")})
    rel = [v for v in p.get("game_versions") or [] if _release_like(v)]
    out["newest_mc"] = max(rel, key=version_tuple) if rel else ""
    out["ready"] = None
    out["needs"] = []
    if version:
        try:
            v = mr_latest_for(p["id"], watch_loaders(kind, loader), version)
        except Exception:
            v = None
        if v:
            out["ready"] = {"version": v.get("version_number") or "", "type": v.get("version_type") or "release"}
            need = [d["project_id"] for d in v.get("dependencies") or [] if d.get("dependency_type") == "required" and d.get("project_id")]
            if need:
                projs = mr_projects(need)
                out["needs"] = [mr_fav(projs[i]) for i in need if i in projs]
    try:
        team = http_json("GET", f"{MODRINTH}/project/{p['id']}/members") or []
        owner = next((m for m in team if m.get("role") == "Owner"), team[0] if team else None)
        out["author"] = ((owner or {}).get("user") or {}).get("username", "")
    except Exception:
        out["author"] = ""
    return out


def _https(u):
    return u if isinstance(u, str) and u.startswith("https://") else ""


def mr_projects(ids):
    out = {}
    for c in chunks(ids, 100):
        for p in http_json("GET", f"{MODRINTH}/projects?" + q({"ids": json.dumps(c)})) or []:
            out[p["id"]] = p
    return out


def mr_fav(p):
    return {"source": "modrinth", "id": p["id"], "slug": p.get("slug"), "name": p.get("title"),
            "icon": p.get("icon_url") or "", "desc": p.get("description", ""),
            "kind": p.get("project_type") if p.get("project_type") in ("resourcepack", "shader") else "mod",
            "url": f"https://modrinth.com/{p.get('project_type', 'mod')}/{p.get('slug') or p['id']}"}


def mr_latest_for(project_id, loaders, gv, since=None):
    """Newest stable build for this version. `since` (a date) keeps a version ModHub chose to fix a clash."""
    versions = http_json("GET", f"{MODRINTH}/project/{project_id}/version?" +
                         q({"loaders": json.dumps(loaders), "game_versions": json.dumps([gv])})) or []
    if since:
        versions = [v for v in versions if v.get("date_published", "") >= since] or versions
    if not versions:
        return None
    versions.sort(key=lambda v: v.get("date_published", ""), reverse=True)
    releases = [v for v in versions if v.get("version_type") == "release"]
    return (releases or versions)[0]


def mr_latest_any(project_id):
    versions = http_json("GET", f"{MODRINTH}/project/{project_id}/version") or []
    versions.sort(key=lambda v: v.get("date_published", ""), reverse=True)
    return versions[0] if versions else None


def mr_primary_file(version):
    files = version.get("files") or []
    f = next((f for f in files if f.get("primary")), files[0]) if files else None
    if not f:
        return None
    try:  # a file name with folders or tricks in it is never written anywhere
        return {**f, "filename": safe_filename(f.get("filename"))}
    except UserError:
        return None


def mr_game_versions():
    tags = http_json("GET", f"{MODRINTH}/tag/game_version") or []
    return [{"v": t["version"], "type": t.get("version_type", "release")} for t in tags]


# =========================================================================== #
# Loader versions
# =========================================================================== #
def loader_version(loader, gv):
    if loader == "fabric":
        lst = http_json("GET", f"https://meta.fabricmc.net/v2/versions/loader/{urllib.parse.quote(gv)}") or []
        if not lst:
            raise UserError(f"Fabric doesn't support Minecraft {gv} yet.")
        stable = [x for x in lst if (x.get("loader") or {}).get("stable")]
        return (stable or lst)[0]["loader"]["version"]
    if loader == "quilt":
        lst = http_json("GET", f"https://meta.quiltmc.org/v3/versions/loader/{urllib.parse.quote(gv)}") or []
        if not lst:
            raise UserError(f"Quilt doesn't support Minecraft {gv} yet.")
        stable = [x for x in lst if "beta" not in x["loader"]["version"] and "pre" not in x["loader"]["version"]]
        return (stable or lst)[0]["loader"]["version"]
    if loader == "forge":
        promos = (http_json("GET", "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json") or {}).get("promos", {})
        v = promos.get(f"{gv}-recommended") or promos.get(f"{gv}-latest")
        if not v:
            raise UserError(f"Forge doesn't support Minecraft {gv} yet.")
        return v
    if loader == "neoforge":
        r = http_json("GET", "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge") or {}
        versions = r.get("versions") or []
        parts = gv.split(".")
        prefixes = [gv + "."]
        if parts[0] == "1" and len(parts) >= 2:
            prefixes.append(f"{parts[1]}.{parts[2] if len(parts) > 2 else 0}.")
        match = [v for v in versions if any(v.startswith(p) for p in prefixes)]
        stable = [v for v in match if "beta" not in v and "alpha" not in v]
        if not match:
            raise UserError(f"NeoForge doesn't support Minecraft {gv} yet.")
        return (stable or match)[-1]
    raise UserError(f"Unknown loader {loader}")


# =========================================================================== #
# Jobs (long-running work reported to the UI)
# =========================================================================== #
JOBS = {}
OPENABLE = set()  # paths the UI is allowed to ask us to open


class Job:
    def __init__(self):
        self.id = secrets.token_hex(6)
        self.lines = []
        self.progress = 0.0
        self.done = False
        self.error = None
        self.result = None
        self.changes = []
        self.updates = []

    def log(self, msg):
        self.lines.append(msg)
        print(msg)

    def view(self, since=0):
        return {"lines": self.lines[since:], "next": len(self.lines), "progress": round(self.progress, 3),
                "done": self.done, "error": self.error, "result": self.result if self.done else None}


def start_job(fn, *args):
    job = Job()
    JOBS[job.id] = job

    def runner():
        try:
            job.result = fn(job, *args)
        except UserError as e:
            job.error = str(e)
        except Exception as e:
            traceback.print_exc()
            job.error = f"Something went wrong: {e}"
        finally:
            job.progress = 1.0
            job.done = True
    threading.Thread(target=runner, daemon=True).start()
    return job.id


# =========================================================================== #
# Resolving your library for a version
# =========================================================================== #
def resolve(job, favorites, gv, loader, ports=None):
    """Work out what to install for this version: mods, resource packs and your own files."""
    loaders = search_loaders(loader)
    with CFG_LOCK:
        pins = dict(CFG.get("pins") or {})
    items, order = {}, []

    def add(fav, dep_of=None):
        k = f"{fav['source']}:{fav['id']}"
        if k in items:
            if dep_of and dep_of not in items[k]["dep_of"]:
                items[k]["dep_of"].append(dep_of)
            return
        it = {"key": k, "source": fav["source"], "id": fav["id"], "name": fav.get("name") or fav["id"],
              "url": fav.get("url", ""), "icon": fav.get("icon", ""), "kind": fav.get("kind") or "mod",
              "dep_of": [dep_of] if dep_of else [], "favorite": dep_of is None,
              "status": "pending", "version": "", "notes": [], "fav": fav}
        items[k] = it
        order.append(it)

    for f in favorites:
        add(f)

    i = 0
    while i < len(order):
        it = order[i]
        i += 1
        job.progress = 0.05 + 0.4 * i / len(order)
        job.log(f"Checking {it['name']}...")
        if it["source"] == "local":
            pick = local_file_for(it["fav"], gv)
            if not pick:
                it["status"] = "needs_file"
                continue
            path = LOCAL_DIR / it["id"] / pick["file"]
            if not path.exists():
                it["status"] = "needs_file"
                it["notes"].append("the saved file is missing, add it again")
                continue
            it.update(status="ready", version="your file" if pick["version"] != "any" else "your file (any version)",
                      file={"local": str(path), "filename": pick["file"], "sha1": None})
            continue
        if it["kind"] == "shader":
            sl = shader_loader(loader)
            if sl:
                add(sl, dep_of=it["name"])
            else:
                it["notes"].append("needs a shader mod for this loader. Add Iris or Oculus yourself")
            v = mr_latest_for(it["id"], ["iris", "optifine", "canvas"], gv)
            if not v:
                v = mr_latest_any(it["id"])
                if v:
                    made = ", ".join((v.get("game_versions") or [])[-1:]) or "an older version"
                    it["notes"].append(f"made for {made}, usually still works")
            if not v:
                it["status"] = "not_ready"
                continue
        elif it["kind"] == "resourcepack":
            v = mr_latest_for(it["id"], ["minecraft"], gv)
            if not v:
                v = mr_latest_any(it["id"])
                if v:
                    made = ", ".join((v.get("game_versions") or [])[-1:]) or "an older version"
                    it["notes"].append(f"made for {made}, usually still works")
            if not v:
                it["status"] = "not_ready"
                continue
        else:
            v = mr_latest_for(it["id"], loaders, gv, since=(pins or {}).get(f"{it['id']}|{gv}|{loader}"))
            if not v:
                it["status"] = "not_ready"
                continue
        f = mr_primary_file(v)
        if not f:
            it["status"] = "not_ready"
            continue
        it.update(status="ready", version=v.get("version_number", ""), changelog=(v.get("changelog") or "")[:4000],
                  file={"url": f["url"], "filename": safe_filename(f["filename"]), "sha1": (f.get("hashes") or {}).get("sha1"),
                        "sha512": (f.get("hashes") or {}).get("sha512"), "size": f.get("size")})
        if it["kind"] == "mod":
            for d in v.get("dependencies") or []:
                if d.get("dependency_type") != "required":
                    continue
                pid = d.get("project_id")
                if not pid and d.get("version_id"):
                    dv = http_json("GET", f"{MODRINTH}/version/{d['version_id']}")
                    pid = dv and dv.get("project_id")
                if pid:
                    add({"source": "modrinth", "id": pid, "name": pid, "kind": "mod"}, dep_of=it["name"])

    # names/links for dependencies we only know by id
    mr_missing = [it["id"] for it in order if it["source"] == "modrinth" and not it["url"]]
    if mr_missing:
        for pid, pr in mr_projects(mr_missing).items():
            fav = mr_fav(pr)
            for it in order:
                if it["key"] == f"modrinth:{pid}":
                    it.update(name=fav["name"], url=fav["url"], icon=fav["icon"])

    # mods you ported with Claude fill the gaps
    for it in order:
        if it["status"] == "not_ready" and it["kind"] == "mod":
            pt = find_port(ports or {}, it["key"], gv, loader)
            if pt:
                jar = Path(pt["jar"])
                it.update(status="ready", ported=True, version="your port",
                          file={"local": str(jar), "filename": jar.name, "sha1": None})
                it["notes"].append("built by Claude for you. Personal use only")

    by_name = {it["name"]: it for it in order}
    for it in order:
        if it["dep_of"] and it["status"] != "ready":
            for parent in it["dep_of"]:
                if parent in by_name:
                    by_name[parent]["notes"].append(f"needs {it['name']}, which isn't available for {gv}")
    for it in order:
        it.pop("fav", None)
    return order


SHADER_LOADERS = {"fabric": "iris", "quilt": "iris", "neoforge": "iris", "forge": "oculus"}
_SHADER_LOADER_CACHE = {}


def shader_loader(loader):
    """The mod that runs shaders: Iris (Fabric, Quilt, NeoForge) or Oculus (Forge)."""
    slug = SHADER_LOADERS.get(loader)
    if not slug:
        return None
    if slug not in _SHADER_LOADER_CACHE:
        try:
            pr = http_json("GET", f"{MODRINTH}/project/{slug}")
        except Exception:
            return None
        _SHADER_LOADER_CACHE[slug] = ({"source": "modrinth", "id": pr["id"], "name": pr.get("title") or slug,
                                       "url": f"https://modrinth.com/mod/{pr.get('slug') or slug}",
                                       "icon": pr.get("icon_url") or "", "kind": "mod"} if pr else None)
    return _SHADER_LOADER_CACHE[slug]


def check_job(job, gv, loader):
    with CFG_LOCK:
        favs, ports = list(CFG["favorites"]), dict(CFG.get("ports") or {})
    if not favs:
        raise UserError("Your library is empty. Add some mods in Library first.")
    items = resolve(job, favs, gv, loader, ports)
    ready = sum(1 for i in items if i["status"] == "ready")
    job.log(f"Done: {ready} of {len(items)} available for {gv}.")
    return {"items": items}


# =========================================================================== #
# Writing mods into a folder
# =========================================================================== #
def _place(job, folder: Path, items, managed, progress):
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {}
    mpath = folder / MANIFEST_NAME
    if managed:
        try:
            manifest = json.loads(mpath.read_text("utf-8"))
        except Exception:
            manifest = {}
    placed = []
    vpath = folder / VERSIONS_NAME
    versions = {}
    if managed:
        try:
            versions = json.loads(vpath.read_text("utf-8"))
        except Exception:
            versions = {}
    for n, it in enumerate(items, 1):
        job.progress = progress[0] + (progress[1] - progress[0]) * n / max(len(items), 1)
        f = it["file"]
        target = folder / f["filename"]
        old = manifest.get(it["key"])
        prev = versions.get(it["key"])
        if f.get("local"):
            src = Path(f["local"])
            label = "your port" if it.get("ported") else "your file"
            if target.exists() and sha1_of(target) == sha1_of(src):
                job.log(f"  = {it['name']} ({label}, already there)")
            else:
                job.log(f"  + {it['name']} ({label})")
                shutil.copy2(src, target)
                job.changes.append(it["name"])
        elif target.exists() and (sha1_of(target) == f["sha1"].lower() if f.get("sha1") else target.stat().st_size > 0):
            job.log(f"  = {it['name']} (already there)")
        else:
            ver = it["version"]
            job.log(f"  + {ver}" if ver.lower().startswith(it["name"].lower()) else f"  + {it['name']} {ver}")
            try:
                download(f["url"], target, f.get("sha1"))
                job.changes.append(it["name"])
                if (old and old != f["filename"]) or (prev and prev != it["version"]):
                    job.updates.append({"key": it["key"], "name": it["name"], "icon": it.get("icon", ""),
                                        "url": it.get("url", ""), "kind": it.get("kind", "mod"),
                                        "from": prev or re.sub(r"\.(jar|zip)$", "", old or ""), "to": it["version"],
                                        "changelog": it.get("changelog", "")})
            except Exception as e:
                it["status"] = "failed"
                it["notes"].append(f"download failed: {e}")
                job.log(f"    ! failed: {e}")
                continue
        if old and old != f["filename"] and Path(old).name == old and (folder / old).exists():
            (folder / old).unlink()
            job.log(f"    removed older copy {old}")
        manifest[it["key"]] = f["filename"]
        if it.get("version") and not f.get("local"):
            versions[it["key"]] = it["version"]
        placed.append((it, target))
    if managed:
        try:
            vpath.write_text(json.dumps(versions, indent=2), "utf-8")
        except OSError:
            pass
    return manifest, mpath, placed


KIND_FOLDERS = {"resourcepack": "resourcepacks", "shader": "shaderpacks"}
KIND_WORDS = {"resourcepack": ("resource pack", "resource packs"), "shader": ("shader", "shaders")}


def install_mods(job, mods_dir: Path, items, managed=True):
    """Mods go in mods_dir; resource packs and shaders go in the resourcepacks/shaderpacks folders next to it."""
    ready = [i for i in items if i["status"] == "ready"]
    mods = [i for i in ready if i.get("kind", "mod") == "mod"]
    manifest, mpath, placed = _place(job, mods_dir, mods, managed, (0.5, 0.8))

    # the same mod added twice (say from Modrinth and as your own file) -> keep one
    seen = {}
    for it, path in sorted(placed, key=lambda q: (not q[0]["favorite"], q[0]["source"] != "modrinth")):
        ids = read_mod_ids(path)
        clash = next((seen[i] for i in ids if i in seen), None)
        if clash and path.exists():
            path.unlink()
            it["status"] = "duplicate"
            it["notes"].append(f"same mod as {clash['name']}, kept that one")
            manifest.pop(it["key"], None)
            job.log(f"    skipped {it['name']} - same mod as {clash['name']}")
        else:
            for i in ids:
                seen[i] = it
    if managed:
        mpath.write_text(json.dumps(manifest, indent=2), "utf-8")
    for kind, folder in KIND_FOLDERS.items():
        these = [i for i in ready if i.get("kind") == kind]
        if not these:
            continue
        one, many = KIND_WORDS[kind]
        job.log(f"Adding {len(these)} {one if len(these) == 1 else many}...")
        pman, ppath, _ = _place(job, mods_dir.parent / folder, these, managed, (0.8, 0.92))
        if managed:
            ppath.write_text(json.dumps(pman, indent=2), "utf-8")


# =========================================================================== #
# Checking that mods work together (the same rules Fabric/Forge use when the game starts)
# =========================================================================== #
LOADER_IDS = {"minecraft", "java", "fabricloader", "fabric-loader", "quilt_loader", "quilted_fabric_api_base",
              "forge", "neoforge", "javafml", "lowcodefml", "mixinextras_compat"}


def _vkey(v):
    """A sortable key for versions like 1.12.0+mc26.3, 0.9.3-beta.2, 26.3."""
    v = str(v or "").strip().lstrip("vV")
    v = v.split("+", 1)[0]
    core, _, pre = v.partition("-")
    nums = []
    for part in re.split(r"[.]", core):
        m = re.match(r"(\d+)", part)
        nums.append(int(m.group(1)) if m else 0)
    while len(nums) > 1 and nums[-1] == 0:
        nums.pop()
    # a pre-release (1.2.0-beta) sorts before the release (1.2.0)
    return (tuple(nums), 0 if pre else 1, tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", pre)) if pre else ())


def _cmp(a, b):
    ka, kb = _vkey(a), _vkey(b)
    na, nb = list(ka[0]), list(kb[0])
    n = max(len(na), len(nb))
    na += [0] * (n - len(na)); nb += [0] * (n - len(nb))
    ka, kb = (tuple(na),) + ka[1:], (tuple(nb),) + kb[1:]
    return (ka > kb) - (ka < kb)


def _fabric_single(version, c):
    c = c.strip()
    if c in ("", "*"):
        return True
    for op in (">=", "<=", ">", "<", "="):
        if c.startswith(op):
            r = _cmp(version, c[len(op):])
            return {">=": r >= 0, "<=": r <= 0, ">": r > 0, "<": r < 0, "=": r == 0}[op]
    if c[0] in "~^":
        base = c[1:]
        parts = [int(x) if x.isdigit() else 0 for x in re.findall(r"\d+", base.split("+")[0])] or [0]
        if c[0] == "~":
            upper = parts[:2] if len(parts) > 1 else [parts[0] + 1]
            if len(upper) == 2:
                upper[1] += 1
        else:
            upper = [parts[0] + 1]
        return _cmp(version, base) >= 0 and _cmp(version, ".".join(map(str, upper))) < 0
    if re.search(r"(^|\.)[xX*]($|\.)", c):
        pre = [x for x in c.split(".") if x not in ("x", "X", "*")]
        got = re.findall(r"\d+", str(version).split("+")[0])
        return got[:len(pre)] == pre
    return _cmp(version, c) == 0


def fabric_satisfies(version, pred):
    """Fabric/Quilt version rules: a list means any of them; spaces inside one mean all of them."""
    if pred is None:
        return True
    preds = pred if isinstance(pred, list) else [pred]
    for p_ in preds:
        if isinstance(p_, dict):  # quilt {"versions": ...}
            p_ = p_.get("versions", "*")
        if isinstance(p_, list):
            if fabric_satisfies(version, p_):
                return True
            continue
        if all(_fabric_single(version, part) for part in str(p_).split()):
            return True
    return False


def maven_satisfies(version, rng):
    """Forge/NeoForge versionRange like [1.20,1.21) or [0.5.1,)."""
    rng = (rng or "").strip()
    if not rng or rng == "*":
        return True
    for m in re.finditer(r"([\[(])\s*([^,\])]*)\s*(?:,\s*([^\])]*))?\s*([\])])", rng):
        lo_inc, lo, hi, hi_inc = m.group(1) == "[", m.group(2).strip(), m.group(3), m.group(4) == "]"
        if hi is None:  # [1.2] means exactly 1.2
            if _cmp(version, lo) == 0:
                return True
            continue
        hi = hi.strip()
        ok = (not lo or (_cmp(version, lo) >= 0 if lo_inc else _cmp(version, lo) > 0)) and \
             (not hi or (_cmp(version, hi) <= 0 if hi_inc else _cmp(version, hi) < 0))
        if ok:
            return True
    if not re.search(r"[\[(]", rng):  # a bare version means "this or newer" for Forge
        return _cmp(version, rng) >= 0
    return False


def _read_meta_from_zip(z, out, nested=True, depth=0):
    names = set(z.namelist())
    if depth == 0:
        fm = out.setdefault("formats", [])
        for f, tag in (("fabric.mod.json", "fabric"), ("quilt.mod.json", "quilt"),
                       ("META-INF/neoforge.mods.toml", "neoforge"), ("META-INF/mods.toml", "forge")):
            if f in names:
                fm.append(tag)
    if "fabric.mod.json" in names:
        try:
            m = json.loads(zread(z, "fabric.mod.json").decode("utf-8", "replace"), strict=False)
            mid, ver = m.get("id"), str(m.get("version", ""))
            if mid:
                out["ids"].setdefault(mid, ver)
                for pv in m.get("provides") or []:
                    out["ids"].setdefault(pv, ver)
                if depth == 0:
                    out.update(main=mid, name=m.get("name") or mid, version=ver)
                    for dep, pred in (m.get("depends") or {}).items():
                        out["deps"].append({"on": dep, "pred": pred, "style": "fabric", "type": "requires"})
                    for dep, pred in (m.get("breaks") or {}).items():
                        out["deps"].append({"on": dep, "pred": pred, "style": "fabric", "type": "breaks"})
        except Exception:
            pass
    if "quilt.mod.json" in names:
        try:
            ql = json.loads(zread(z, "quilt.mod.json").decode("utf-8", "replace")).get("quilt_loader", {})
            mid, ver = ql.get("id"), str(ql.get("version", ""))
            if mid:
                out["ids"].setdefault(mid, ver)
                for pv in ql.get("provides") or []:
                    out["ids"].setdefault(pv if isinstance(pv, str) else pv.get("id"), ver)
                if depth == 0 and not out.get("main"):
                    out.update(main=mid, name=(ql.get("metadata") or {}).get("name") or mid, version=ver)
                    for d in ql.get("depends") or []:
                        if isinstance(d, str):
                            out["deps"].append({"on": d, "pred": "*", "style": "fabric", "type": "requires"})
                        elif isinstance(d, dict) and not d.get("optional"):
                            out["deps"].append({"on": d.get("id"), "pred": d.get("versions", "*"), "style": "fabric", "type": "requires"})
                    for d in ql.get("breaks") or []:
                        if isinstance(d, dict):
                            out["deps"].append({"on": d.get("id"), "pred": d.get("versions", "*"), "style": "fabric", "type": "breaks"})
        except Exception:
            pass
    for toml in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
        if toml not in names:
            continue
        text = zread(z, toml).decode("utf-8", "replace")
        jar_ver = ""
        if "META-INF/MANIFEST.MF" in names:
            mm = re.search(r"^Implementation-Version:\s*(\S+)", zread(z, "META-INF/MANIFEST.MF").decode("utf-8", "replace"), re.M)
            jar_ver = mm.group(1) if mm else ""
        mods = re.split(r"^\s*\[\[mods\]\]\s*$", text, flags=re.M)[1:]
        for i, block in enumerate(mods):
            mid = re.search(r'^\s*modId\s*=\s*"([^"]+)"', block, re.M)
            ver = re.search(r'^\s*version\s*=\s*"([^"]+)"', block, re.M)
            if not mid:
                continue
            v = ver.group(1) if ver else ""
            if "${" in v:
                v = jar_ver
            out["ids"].setdefault(mid.group(1), v)
            if depth == 0 and i == 0 and not out.get("main"):
                dn = re.search(r'^\s*displayName\s*=\s*"([^"]+)"', block, re.M)
                out.update(main=mid.group(1), name=dn.group(1) if dn else mid.group(1), version=v)
        if depth == 0:
            for blk in re.split(r"^\s*\[\[dependencies\.[^\]]+\]\]\s*$", text, flags=re.M)[1:]:
                dep = re.search(r'^\s*modId\s*=\s*"([^"]+)"', blk, re.M)
                rng = re.search(r'^\s*versionRange\s*=\s*"([^"]*)"', blk, re.M)
                typ = re.search(r'^\s*type\s*=\s*"([^"]+)"', blk, re.M)
                mand = re.search(r'^\s*mandatory\s*=\s*(true|false)', blk, re.M)
                if not dep:
                    continue
                t = (typ.group(1).lower() if typ else ("required" if not mand or mand.group(1) == "true" else "optional"))
                if t in ("required", "incompatible"):
                    out["deps"].append({"on": dep.group(1), "pred": rng.group(1) if rng else "", "style": "maven",
                                        "type": "requires" if t == "required" else "breaks"})
        break
    if nested and depth < 2:  # mods bundled inside mods (jar-in-jar)
        for n in names:
            if (n.startswith("META-INF/jars/") or n.startswith("META-INF/jarjar/")) and n.endswith(".jar"):
                try:
                    import io
                    with zipfile.ZipFile(io.BytesIO(zread(z, n, 128_000_000))) as inner:
                        _read_meta_from_zip(inner, out, nested=True, depth=depth + 1)
                except Exception:
                    pass


def jar_meta(path: Path):
    out = {"file": path.name, "ids": {}, "deps": [], "main": None, "name": path.stem, "version": ""}
    try:
        with zipfile.ZipFile(path) as z:
            _read_meta_from_zip(z, out)
    except Exception:
        pass
    return out


def _wanted_text(pred, style, breaks=False):
    """Turn a version rule into words: '1.12.0 or newer', 'newer than 1.12.0'..."""
    if style == "maven":
        m = re.fullmatch(r"\[\s*([^,\]]+)\s*,\s*\)", (pred or "").strip())
        if m:
            return f"{m.group(1)} or newer"
        return f"version {pred}" if pred else "any version"
    p_ = pred if isinstance(pred, str) else " or ".join(map(str, pred)) if isinstance(pred, list) else str(pred)
    p_ = p_.strip()
    if breaks:
        m = re.fullmatch(r"<=\s*(\S+)", p_)
        if m:
            return f"newer than {m.group(1)}"
        m = re.fullmatch(r"<\s*(\S+)", p_)
        if m:
            return f"{m.group(1)} or newer"
        return f"a version that isn't {p_}"
    for pat, fmt in ((r">=\s*(\S+)", "{} or newer"), (r">\s*(\S+)", "newer than {}"), (r"<=\s*(\S+)", "{} or older"),
                     (r"<\s*(\S+)", "older than {}"), (r"[~^]\s*(\S+)", "{} or a close newer version")):
        m = re.fullmatch(pat, p_)
        if m:
            return fmt.format(m.group(1))
    return "any version" if p_ in ("*", "") else f"version {p_}"


def _mc_from(pred):
    found = re.findall(r"\d+(?:\.\d+)+", json.dumps(pred))
    return found[0] if found else "another version"


def _show(v):
    return str(v or "").split("+", 1)[0] or "an unknown version"


def loads_on(formats, loader, gv=None):
    """Can a mod built for these loaders run on this one?"""
    ok = {"fabric": {"fabric"}, "quilt": {"quilt", "fabric"}, "forge": {"forge"},
          "neoforge": {"neoforge"} | ({"forge"} if gv and version_tuple(gv) < (1, 20, 5) and not gv.startswith("2") else set())}
    return bool(set(formats) & ok.get(loader, set()))


def check_mods(folder: Path, gv=None, loader=None):
    """Find mods that are missing something, too old/new for each other, made for another Minecraft
    or another loader, or installed twice."""
    jars = sorted(f for f in folder.glob("*.jar")) if folder.is_dir() else []
    metas = [jar_meta(j) for j in jars]
    problems = []
    if loader:
        for m in metas:
            if m.get("formats") and not loads_on(m["formats"], loader, gv):
                built = {"fabric": "Fabric", "quilt": "Quilt", "forge": "Forge", "neoforge": "NeoForge"}
                problems.append({"type": "wrong_loader", "file": m["file"], "mod": m["name"], "mod_id": m["main"],
                                 "style": "fabric", "message": f"{m['name']} is made for {built.get(m['formats'][0], m['formats'][0])}, "
                                 f"so it won't load with {built.get(loader, loader)}."})
        metas = [m for m in metas if not m.get("formats") or loads_on(m["formats"], loader, gv)]
    by_main = {}
    for m in metas:
        if m["main"]:
            by_main.setdefault(m["main"], []).append(m)
    for mid, copies in by_main.items():
        if len(copies) > 1:
            problems.append({"type": "duplicate", "file": copies[0]["file"], "mod": copies[0]["name"], "mod_id": mid,
                             "copies": [c["file"] for c in copies], "versions": [c["version"] for c in copies], "style": "fabric",
                             "message": f"{copies[0]['name']} is installed {len(copies)} times ({', '.join(c['file'] for c in copies)})."})
    have = {}
    for m in metas:
        for mid, ver in m["ids"].items():
            have.setdefault(mid, (ver, m))
    for m in metas:
        if not m["main"]:
            continue
        for d in m["deps"]:
            dep = d["on"]
            sat = fabric_satisfies if d["style"] == "fabric" else maven_satisfies
            if dep == "minecraft":
                if gv and d["type"] == "requires" and d["pred"] and not sat(gv, d["pred"]):
                    problems.append({"type": "minecraft", "file": m["file"], "mod": m["name"], "mod_id": m["main"],
                                     "want": d["pred"], "style": d["style"],
                                     "message": f"{m['name']} is made for Minecraft {_mc_from(d['pred'])}, not {gv}."})
                continue
            if dep in LOADER_IDS or dep == m["main"]:
                continue
            got = have.get(dep)
            if d["type"] == "requires":
                if not got:
                    problems.append({"type": "missing", "file": m["file"], "mod": m["name"], "mod_id": m["main"],
                                     "on": dep, "want": d["pred"], "style": d["style"],
                                     "message": f"{m['name']} needs {dep}, which isn't installed."})
                elif not sat(got[0], d["pred"]):
                    problems.append({"type": "needs_version", "file": m["file"], "mod": m["name"], "mod_id": m["main"],
                                     "on": dep, "on_name": got[1]["name"], "on_file": got[1]["file"], "have": got[0],
                                     "want": d["pred"], "style": d["style"],
                                     "message": f"{m['name']} needs {got[1]['name']} {_wanted_text(d['pred'], d['style'])}, but {_show(got[0])} is installed."})
            elif got and d["pred"] and (sat(got[0], d["pred"]) if d["style"] == "fabric" else maven_satisfies(got[0], d["pred"])):
                problems.append({"type": "conflict", "file": m["file"], "mod": m["name"], "mod_id": m["main"],
                                 "on": dep, "on_name": got[1]["name"], "on_file": got[1]["file"], "have": got[0],
                                 "want": d["pred"], "style": d["style"],
                                 "message": f"{m['name']} doesn't work with {got[1]['name']} {_show(got[0])}. It needs {got[1]['name']} {_wanted_text(d['pred'], d['style'], breaks=True)}."})
    return problems


def _ok_for(problem, version):
    """Would this version of the other mod solve the problem?"""
    sat = fabric_satisfies if problem["style"] == "fabric" else maven_satisfies
    if problem["type"] == "needs_version":
        return sat(version, problem["want"])
    if problem["type"] == "conflict":
        return not sat(version, problem["want"])
    return True


def fix_problems(job, folder: Path, problems, gv, loader, managed=True):
    """Fix what can be fixed safely: get a version of the other mod that fits, or add what's missing."""
    if not problems:
        return problems
    mpath = folder / MANIFEST_NAME
    try:
        manifest = json.loads(mpath.read_text("utf-8"))
    except Exception:
        manifest = {}
    by_file = {v: k for k, v in manifest.items()}
    loaders = search_loaders(loader)
    tmpdir = Path(tempfile.mkdtemp(prefix="modhub-fix-"))
    try:
        for pr in problems:
            pr.setdefault("status", "open")
            if pr["type"] in ("needs_version", "conflict"):
                key = by_file.get(pr["on_file"])
                pid = key.split(":", 1)[1] if key and key.startswith("modrinth:") else None
                if not pid:
                    try:  # not installed by ModHub: look it up by its mod id
                        proj = http_json("GET", f"{MODRINTH}/project/{urllib.parse.quote(pr['on'])}")
                        pid = proj and proj.get("id")
                    except Exception:
                        pid = None
                if not pid:
                    continue
                job.log(f"Looking for a {pr['on_name']} that works with {pr['mod']}...")
                try:
                    versions = http_json("GET", f"{MODRINTH}/project/{pid}/version?" +
                                         q({"loaders": json.dumps(loaders), "game_versions": json.dumps([gv])})) or []
                except Exception:
                    versions = []
                versions.sort(key=lambda v: v.get("date_published", ""), reverse=True)
                for v in versions[:6]:
                    f = mr_primary_file(v)
                    if not f:
                        continue
                    cand = tmpdir / f["filename"]
                    try:
                        download(f["url"], cand, (f.get("hashes") or {}).get("sha1"))
                    except Exception:
                        continue
                    cver = jar_meta(cand)["ids"].get(pr["on"], v.get("version_number", ""))
                    if _ok_for(pr, cver):
                        old = folder / pr["on_file"]
                        if old.exists():
                            old.unlink()
                        shutil.move(str(cand), str(folder / f["filename"]))
                        if managed and key:
                            manifest[key] = f["filename"]
                        beta = "" if v.get("version_type") == "release" else f" ({v.get('version_type')})"
                        with CFG_LOCK:  # remember it, so updates don't swap back to the clashing version
                            CFG.setdefault("pins", {})[f"{pid}|{gv}|{loader}"] = v.get("date_published", "")
                            save_config(CFG)
                        pr.update(status="fixed", fix=f"Switched {pr['on_name']} from {_show(pr['have'])} to {_show(cver)}{beta}.")
                        job.log(f"  fixed: {pr['fix']}")
                        job.changes.append(pr["on_name"])
                        break
            elif pr["type"] == "duplicate":
                keep = next((c for c in pr["copies"] if c in by_file), None)
                if not keep:  # the newest one wins
                    keep = max(zip(pr["copies"], pr["versions"]), key=lambda cv: (version_tuple(cv[1] or "0"),
                               (folder / cv[0]).stat().st_mtime if (folder / cv[0]).exists() else 0))[0]
                for c in pr["copies"]:
                    if c != keep and (folder / c).exists():
                        os.replace(folder / c, folder / (c + ".disabled"))
                pr.update(status="fixed", fix=f"Turned off the extra copy of {pr['mod']}, kept {keep}.")
                job.log(f"  fixed: {pr['fix']}")
                job.changes.append(pr["mod"])
            elif pr["type"] == "wrong_loader":
                old = folder / pr["file"]
                job.log(f"Looking for the {LOADER_NAMES_PY.get(loader, loader)} version of {pr['mod']}...")
                v = None
                try:
                    sha = hashlib.sha1(old.read_bytes()).hexdigest()
                    found = http_json("POST", f"{MODRINTH}/version_files", {"hashes": [sha], "algorithm": "sha1"}) or {}
                    pid = (found.get(sha) or {}).get("project_id")
                    v = pid and mr_latest_for(pid, loaders, gv)
                except Exception:
                    v = None
                f = v and mr_primary_file(v)
                try:
                    if f:
                        download(f["url"], folder / f["filename"], (f.get("hashes") or {}).get("sha1"))
                        key = by_file.get(pr["file"])
                        if managed and key:
                            manifest[key] = f["filename"]
                        if old.exists() and old.name != f["filename"]:
                            old.unlink()
                        pr.update(status="fixed", fix=f"Swapped {pr['mod']} for its {LOADER_NAMES_PY.get(loader, loader)} version.")
                    elif old.exists():
                        os.replace(old, old.with_name(old.name + ".disabled"))
                        pr.update(status="fixed", fix=f"Turned off {pr['mod']}: there's no {LOADER_NAMES_PY.get(loader, loader)} version of it yet.")
                    if pr["status"] == "fixed":
                        job.log(f"  fixed: {pr['fix']}")
                        job.changes.append(pr["mod"])
                except Exception:
                    traceback.print_exc()
            elif pr["type"] == "missing":
                job.log(f"Looking for {pr['on']}, which {pr['mod']} needs...")
                try:
                    proj = http_json("GET", f"{MODRINTH}/project/{urllib.parse.quote(pr['on'])}")
                    v = proj and mr_latest_for(proj["id"], loaders, gv)
                except Exception:
                    proj, v = None, None
                f = v and mr_primary_file(v)
                if f:
                    try:
                        download(f["url"], folder / f["filename"], (f.get("hashes") or {}).get("sha1"))
                        if managed:
                            manifest[f"modrinth:{proj['id']}"] = f["filename"]
                        pr.update(status="fixed", fix=f"Added {proj.get('title') or pr['on']}.", on_name=proj.get("title") or pr["on"])
                        job.log(f"  fixed: {pr['fix']}")
                        job.changes.append(proj.get("title") or pr["on"])
                    except Exception:
                        pass
        if managed:
            mpath.write_text(json.dumps(manifest, indent=2), "utf-8")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    # anything still open? check again, because one fix can solve (or reveal) another
    left = check_mods(folder, gv, loader)
    open_keys = {(x["type"], x["file"], x.get("on")) for x in left}
    for pr in problems:
        if pr["status"] == "open" and (pr["type"], pr["file"], pr.get("on")) not in open_keys:
            pr["status"] = "fixed"
            pr.setdefault("fix", "Sorted out by another fix.")
    known = {(x["type"], x["file"], x.get("on")) for x in problems}
    problems += [dict(x, status="open") for x in left if (x["type"], x["file"], x.get("on")) not in known]
    return problems


def check_and_fix(job, folder: Path, gv, loader, managed=True):
    job.log("Checking that your mods work together...")
    problems = check_mods(folder, gv, loader)
    if problems:
        problems = fix_problems(job, folder, problems, gv, loader, managed)
    still = [x for x in problems if x["status"] == "open"]
    job.log("All your mods work together." if not still else f"{len(still)} problem(s) need you.")
    return problems


# =========================================================================== #
# Crash helper: read crash reports and explain them
# =========================================================================== #
CRASH_MARKERS = ("---- Minecraft Crash Report ----", "Incompatible mods found", "Incompatible mod set",
                 "Mod resolution encountered", "Mod resolution failed", "#@!@# Game crashed!",
                 "Exception in thread \"main\"", "java.lang.OutOfMemoryError", "UnsupportedClassVersionError",
                 "Minecraft has crashed", "Failed to start the minecraft server", "Mixin apply failed",
                 "MixinApplyError", "Mixin transformation of")
CRASH_SCAN_SECONDS = 60
NOT_MODS = {"minecraft", "java", "fabricloader", "fabric-loader", "quilt_loader", "forge", "neoforge", "mixinextras",
            "fabric-api", "none", "unknown"}


def _mods_index(mods_dir: Path):
    idx = {}
    for j in sorted(mods_dir.glob("*.jar")) if mods_dir.is_dir() else []:
        m = jar_meta(j)
        if m["main"]:
            idx[m["main"].lower()] = {"id": m["main"], "name": m["name"], "file": j.name}
            idx.setdefault(m["name"].lower(), idx[m["main"].lower()])
    return idx


def diagnose_crash(text, mods_dir: Path):
    """Turn a crash report or log into a plain-English explanation."""
    idx = _mods_index(mods_dir)
    found_ids = []

    def culprit(x):
        x = (x or "").strip().strip("'\"").lower()
        if x and x not in NOT_MODS and x in idx and idx[x] not in found_ids:
            found_ids.append(idx[x])

    d = {"kind": "unknown", "title": "The game crashed", "explain": "", "fix_check": False}
    low = text.lower()
    if any(k in text for k in ("Incompatible mods found", "Incompatible mod set", "Mod resolution encountered",
                               "Mod resolution failed")) or re.search(r"which is missing|requires .* but only the wrong version", low):
        d.update(kind="clash", title="Some mods don't work together", fix_check=True,
                 explain="The game stopped before it started, because some mods need other mods, or different versions of them. Fix it lets ModHub sort this out for you.")
        for m in re.finditer(r"Mod '([^']+)' \(([^)]+)\)", text):
            culprit(m.group(2)); culprit(m.group(1))
        for m in re.finditer(r"(?:Remove|Replace) mod '([^']+)' \(([^)]+)\)", text):
            culprit(m.group(2))
    elif "outofmemoryerror" in low or "out of memory" in low:
        d.update(kind="memory", title="Minecraft ran out of memory",
                 explain="The game needed more memory (RAM) than it was given. In Prism Launcher: right-click the instance, Edit, Settings, Java, and raise Maximum memory to 4096 MB or more. "
                         "In the Minecraft Launcher: Installations, edit the profile, More options, and change -Xmx2G in JVM arguments to -Xmx4G or more.")
    elif "unsupportedclassversionerror" in low or "compiled by a more recent version of the java runtime" in low:
        d.update(kind="java", title="Minecraft needs a newer Java",
                 explain="A mod (or Minecraft itself) needs a newer version of Java than the one the launcher used. In your launcher's settings, let it pick Java automatically, or choose the newest Java it offers.")
    elif any(k in low for k in ("pixel format not accelerated", "glfw error 65542", "driver does not appear to support opengl",
                                "couldn't set pixel format")):
        d.update(kind="graphics", title="Your graphics driver needs an update",
                 explain="Minecraft couldn't talk to your graphics card. Update your graphics driver from NVIDIA, AMD or Intel's website (or Windows Update), then restart your computer.")
    # mods named in the report (works for most crashes)
    for m in re.finditer(r"Suspected Mods?:\s*(.+)", text):
        for part in re.split(r",\s*", m.group(1)):
            mm = re.match(r"\s*(.+?)\s*\(([^)]+)\)", part)
            if mm:
                culprit(mm.group(2)); culprit(mm.group(1))
    for m in re.finditer(r"(?:from mod|mod) ([a-z0-9_\-]+)[:\]\s]", text):
        if "mixin" in text[max(0, m.start() - 200):m.start()].lower():
            culprit(m.group(1))
    for m in re.finditer(r"Mixin (?:apply|transformation|prepare)[^\n]*?(?:for mod|from mod) ([a-z0-9_\-]+)", text):
        culprit(m.group(1))
    if d["kind"] == "unknown":
        desc = re.search(r"^Description:\s*(.+)$", text, re.M)
        exc = re.search(r"^((?:java|net|com|org)\.[\w.$]+(?:Exception|Error)[^\n]*)", text, re.M)
        if found_ids:
            names = " and ".join(c["name"] for c in found_ids[:2])
            d.update(kind="mod", title=f"{names} crashed the game",
                     explain=f"The crash report points at {names}. Usually this means it doesn't fully support this Minecraft version yet, or it clashes with another mod. Turning it off should get you playing again.")
        else:
            d.update(explain="ModHub couldn't tell exactly why. " + (f"The report says: {desc.group(1).strip()}. " if desc else "")
                     + "Copy the report and paste it to Claude to get help.")
        if exc:
            d["error"] = exc.group(1)[:200]
    d["culprits"] = found_ids[:4]
    d["fix_check"] = d["fix_check"] or d["kind"] in ("clash",)
    return d


# ---- auto-fix for "Incompatible mods found!" and missing-dependency errors ----
# Fabric and Quilt print the fix themselves ("Install X", "Replace Y with...", "Remove mod Z"), and
# NeoForge/Forge list missing or wrong dependencies. ModHub reads those and carries them out.
SKIP_DEPS = {"minecraft", "java", "fabricloader", "fabric-loader", "quilt_loader", "forge", "neoforge", "fml", "javafml"}


def _fabric_pred(spec):
    """Fabric's English ("version 1.2 or later", "any version between 1 and 2 (exclusive)") as a version rule."""
    sp = (spec or "").strip().rstrip(".!")
    v = r"([0-9][\w.+\-]*)"
    for pat, fmt in ((rf"between {v} and {v}", ">={0} <{1}"), (rf"{v} or later", ">={0}"), (rf"{v} or earlier", "<={0}"),
                     (rf"(?:later than|after) {v}", ">{0}"), (rf"(?:earlier than|before) {v}", "<{0}"),
                     (rf"version {v}\b", "{0}")):
        m = re.search(pat, sp)
        if m:
            return fmt.format(*m.groups())
    return "*"


def parse_mod_errors(text, mods_dir: Path):
    """The fixes a mod-loading error asks for, as problems ModHub's fixer understands, plus mods to turn off."""
    idx = _mods_index(mods_dir)
    find = lambda mid, name="": idx.get((mid or "").lower()) or idx.get((name or "").lower())
    out, seen = [], set()

    def add(item):
        key = (item["type"], (item.get("on") or item.get("file") or "").lower())
        if key not in seen:
            seen.add(key)
            out.append(item)

    def missing(dep, by="a mod"):
        if dep.lower() not in SKIP_DEPS and not find(dep):
            add({"type": "missing", "on": dep, "mod": by, "file": "", "want": None, "style": "fabric",
                 "message": f"{by} needs {dep}, which isn't installed."})

    def needs(dep, dep_name, have, pred, style, by="a mod"):
        m = find(dep, dep_name)
        if m:
            add({"type": "needs_version", "on": m["id"], "on_name": m["name"], "on_file": m["file"], "have": have or "",
                 "want": pred, "style": style, "mod": by, "file": m["file"],
                 "message": f"{by} needs a different version of {m['name']}."})

    # Fabric / Quilt: the suggested solution
    for m in re.finditer(r"^\s*-\s*Install ([\w.\-]+)(?:,\s*(.+?))?\.?\s*$", text, re.M):
        missing(m.group(1), "Fabric")
    for m in re.finditer(r"^\s*-\s*Replace (?:mod )?'([^']+)' \(([^)]+)\) (\S+) with (.+?)\.?\s*$", text, re.M):
        needs(m.group(2), m.group(1), m.group(3), _fabric_pred(m.group(4)), "fabric", "Fabric")
    for m in re.finditer(r"^\s*-\s*Remove mod '([^']+)' \(([^)]+)\)", text, re.M):
        mm = find(m.group(2), m.group(1))
        if mm:
            add({"type": "remove", "file": mm["file"], "on_name": m.group(1) or mm["name"], "on": mm["id"]})
    # Fabric / Quilt: the details (older loaders print only these)
    for m in re.finditer(r"Mod '([^']+)' \(([^)]+)\) \S+ requires (.+?) of (?:mod )?'?([^'(]+?)'? \(([^)]+)\), which is missing", text):
        missing(m.group(5), m.group(1))
    for m in re.finditer(r"Mod '([^']+)' \(([^)]+)\) (\S+) requires (.+?) of (?:mod )?'([^']+)' \(([^)]+)\), "
                         r"but only the wrong version is present: ([^!\n]+)", text):
        if m.group(6).lower() == "minecraft":  # the mod is made for another Minecraft: get the right build of it
            needs(m.group(2), m.group(1), m.group(3), "*", "fabric", m.group(1))
        elif m.group(6).lower() not in SKIP_DEPS:
            needs(m.group(6), m.group(5), m.group(7).strip(), _fabric_pred(m.group(4)), "fabric", m.group(1))
    # NeoForge / Forge
    for m in re.finditer(r"Mod ID: '([^']+)', Requested by: '([^']+)', Expected range: '([^']+)', Actual version: '([^']+)'", text):
        dep, by, rng, actual = m.groups()
        if dep.lower() in SKIP_DEPS:
            continue
        by_name = (find(by) or {}).get("name", by)
        if "MISSING" in actual.upper():
            missing(dep, by_name)
        else:
            needs(dep, "", actual, rng, "maven", by_name)
    return out


def autofix_mods_job(job, iid, text):
    """Carry out what the game's error asked for, then check the whole instance."""
    with CFG_LOCK:
        rec = next((dict(r) for r in CFG.get("installs", []) if r["id"] == iid), None)
    if not rec or not rec.get("path"):
        raise UserError("ModHub can't change that instance.")
    folder = Path(rec["path"])
    actions = parse_mod_errors(text, folder)
    done = []
    for a in [a for a in actions if a["type"] == "remove"]:
        try:
            turn_off_mod(iid, a["file"])
            done.append(f"Turned off {a['on_name']}, which doesn't work with your other mods.")
            job.log(f"  turned off {a['on_name']}")
        except UserError:
            pass
    problems = [a for a in actions if a["type"] != "remove"]
    if problems:
        job.log("Doing what the game asked for...")
        problems = fix_problems(job, folder, problems, rec["version"], rec["loader"], managed=True)
    more = check_and_fix(job, folder, rec["version"], rec["loader"], managed=True)
    for p in problems + more:
        if p.get("status") == "fixed" and p.get("fix") and p["fix"] not in done:
            done.append(p["fix"])
    still, seen = [], set()
    for p in more + problems:  # what's left: from the full check, and anything the game asked for that couldn't be done
        if p.get("status") == "open" and p.get("message") and p["message"] not in seen:
            seen.add(p["message"])
            still.append(p)
    return {"fixed": done, "still": still, "install_id": iid, "instance": rec["name"]}


def start_autofix(iid, text):
    """Fix a crashed instance in the background and record how it went on the crash."""
    def set_fix(info):
        with CFG_LOCK:
            for c in CFG.get("crashes", []):
                if c["install_id"] == iid:
                    c["autofix"] = info
            save_config(CFG)

    def runner(job):
        set_fix({"status": "fixing"})
        try:
            res = autofix_mods_job(job, iid, text)
        except Exception as e:
            traceback.print_exc()
            set_fix({"status": "failed", "error": str(e)[:300]})
            raise
        status = "fixed" if res["fixed"] and not res["still"] else "partly" if res["fixed"] else "failed"
        set_fix({"status": status, "fixed": res["fixed"],
                 "still": [{"message": p["message"], "file": p.get("file"), "mod": p.get("mod")} for p in res["still"]]})
        return res
    return start_job(runner)


def minecraft_running():
    """Is the game open? (Then ModHub leaves its files alone.)"""
    try:
        if platform.system() == "Windows":
            out = subprocess.run(["tasklist", "/V", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                                 creationflags=0x08000000, timeout=20).stdout.lower()
            return any(("javaw.exe" in l or "java.exe" in l) and "minecraft" in l for l in out.splitlines())
        out = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True, timeout=20).stdout
        return any("java" in l and ("minecraft" in l.lower() or "net.fabricmc" in l) for l in out.splitlines())
    except Exception:
        return False


def _folder_sig(folder: Path):
    try:
        return hashlib.sha1(json.dumps(sorted((f.name, f.stat().st_size, int(f.stat().st_mtime))
                                              for f in folder.iterdir() if f.suffix.lower() == ".jar")).encode()).hexdigest()
    except OSError:
        return None


PRECHECK_SECONDS = 90
PRECHECK_FIRST = 30


def precheck_watch():
    """When an instance's mods change (even outside ModHub), check and fix them before the game is started."""
    time.sleep(PRECHECK_FIRST)
    while True:
        try:
            with CFG_LOCK:
                recs = [dict(r) for r in CFG.get("installs", []) if not r.get("export") and r.get("path")]
                auto = CFG.get("autofix_mods", True)
            busy = any(not j.done for j in list(JOBS.values()))
            if auto and recs and not busy and not minecraft_running():
                for r in recs:
                    folder = Path(r["path"])
                    sig = _folder_sig(folder) if folder.is_dir() else None
                    if not sig or sig == r.get("checked_sig"):
                        continue
                    if r.get("checked_sig") is None:  # first time ModHub sees it: just remember, the install already checked it
                        _set_checked(r["id"], sig)
                        continue
                    job = start_job(lambda job, rid=r["id"]: precheck_instance(job, rid))
                    while not JOBS[job].done:
                        time.sleep(1)
        except Exception:
            traceback.print_exc()
        time.sleep(PRECHECK_SECONDS)


def _set_checked(iid, sig):
    with CFG_LOCK:
        for x in CFG.get("installs", []):
            if x["id"] == iid:
                x["checked_sig"] = sig
        save_config(CFG)


def precheck_instance(job, iid):
    with CFG_LOCK:
        rec = next((dict(r) for r in CFG.get("installs", []) if r["id"] == iid), None)
    if not rec:
        return {}
    folder = Path(rec["path"])
    job.log(f"{rec['name']}'s mods changed. Checking them before you play...")
    probs = check_and_fix(job, folder, rec["version"], rec["loader"], managed=True)
    _set_checked(iid, _folder_sig(folder))
    fixed = [p["fix"] for p in probs if p.get("status") == "fixed" and p.get("fix")]
    still = [{"message": p["message"], "file": p.get("file"), "mod": p.get("mod")} for p in probs if p.get("status") == "open"]
    if fixed or still:
        entry = {"install_id": iid, "instance": rec["name"], "version": rec["version"], "loader": rec["loader"], "file": "",
                 "at": now_iso(), "kind": "precheck", "title": "Some mods wouldn't have worked together", "fix_check": True,
                 "explain": "", "culprits": [],
                 "autofix": {"status": "fixed" if not still else "partly" if fixed else "failed", "fixed": fixed, "still": still}}
        with CFG_LOCK:
            CFG["crashes"] = [c for c in CFG.get("crashes", []) if c["install_id"] != iid] + [entry]
            save_config(CFG)
    return {"fixed": fixed, "still": still}


def _newest_crash_file(game_dir: Path, after: float):
    """The newest crash report, or the game log if the last run ended in an error."""
    cands = []
    cr = game_dir / "crash-reports"
    if cr.is_dir():
        cands += [f for f in cr.glob("crash-*.txt")]
    log = game_dir / "logs" / "latest.log"
    if log.exists():
        cands.append(log)
    for f in sorted(cands, key=lambda f: f.stat().st_mtime, reverse=True):
        if f.stat().st_mtime <= after:
            return None
        try:
            text = f.read_text("utf-8", "replace")
        except OSError:
            continue
        if f.name == "latest.log":
            tail = text[-60000:]
            if not any(m in tail for m in CRASH_MARKERS):
                continue
            text = tail
        return f, text[:200000]
    return None


def _iso_to_ts(iso):
    try:
        return datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return 0


def scan_crashes():
    with CFG_LOCK:
        recs = [dict(r) for r in CFG.get("installs", []) if not r.get("export") and r.get("path")]
    new = []
    for r in recs:
        mods_dir = Path(r["path"])
        game_dir = mods_dir.parent
        seen = max(r.get("crash_seen", 0), _iso_to_ts(r.get("updated") or r.get("installed") or ""))
        got = _newest_crash_file(game_dir, seen)
        if not got:
            continue
        f, text = got
        d = diagnose_crash(text, mods_dir)
        crash = {"install_id": r["id"], "instance": r["name"], "version": r["version"], "loader": r["loader"],
                 "file": str(f), "at": datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                 **d}
        OPENABLE.add(str(f))
        new.append(crash)
        with CFG_LOCK:
            for x in CFG.get("installs", []):
                if x["id"] == r["id"]:
                    x["crash_seen"] = f.stat().st_mtime
            CFG["crashes"] = [c for c in CFG.get("crashes", []) if c["install_id"] != r["id"]] + [crash]
            auto = CFG.get("autofix_mods", True)
            save_config(CFG)
        if auto and d["kind"] == "clash":  # "Incompatible mods found!": fix it without being asked
            crash["autofix"] = {"status": "fixing"}
            start_autofix(r["id"], text)
    return new


def crash_watch():
    time.sleep(20)
    while True:
        try:
            scan_crashes()
        except Exception:
            traceback.print_exc()
        time.sleep(CRASH_SCAN_SECONDS)


def crash_excerpt(path):
    """The part of a crash report worth sending to someone for help."""
    try:
        text = Path(path).read_text("utf-8", "replace")
    except OSError:
        raise UserError("The crash report is gone.")
    if Path(path).name == "latest.log":
        lines = text.splitlines()
        hit = next((i for i in range(len(lines) - 1, -1, -1) if any(m in lines[i] for m in CRASH_MARKERS)), max(0, len(lines) - 80))
        text = "\n".join(lines[max(0, hit - 30):hit + 90])
    else:
        text = text[:12000]
    return text


# =========================================================================== #
# Performance boost: a trusted set of performance mods
# =========================================================================== #
PERF_MODS = [
    ("sodium", "Much faster graphics. Often doubles your FPS."),
    ("embeddium", "Faster graphics for Forge, based on Sodium."),
    ("lithium", "Faster game logic, so less lag from mobs, redstone and farms."),
    ("ferrite-core", "Uses noticeably less memory (RAM)."),
    ("entityculling", "Skips drawing mobs and block entities you can't see."),
    ("immediatelyfast", "Draws text, maps and the HUD faster."),
    ("modernfix", "Faster loading and lower memory use."),
    ("dynamic-fps", "Lowers FPS when the game is in the background, to save power."),
]
_PERF_CACHE = {}


def perf_list(loader, gv=None):
    loader = loader if loader in LOADERS else "fabric"
    ok_loaders = {"quilt": {"quilt", "fabric"}}.get(loader, {loader})
    with CFG_LOCK:
        have = {str(f["id"]) for f in CFG["favorites"] if f.get("source") == "modrinth"}
    out = []
    for slug, why in PERF_MODS:
        if slug not in _PERF_CACHE:
            try:
                _PERF_CACHE[slug] = http_json("GET", f"{MODRINTH}/project/{slug}")
            except Exception:
                _PERF_CACHE[slug] = None
        pr = _PERF_CACHE[slug]
        if not pr:
            continue
        loaders = set(pr.get("loaders") or [])
        if slug == "embeddium" and loader != "forge":
            continue  # Sodium covers the other loaders
        reason = None
        if not loaders & ok_loaders:
            reason = f"not made for {LOADER_NAMES_PY[loader]}"
        elif gv and gv not in (pr.get("game_versions") or []):
            reason = f"not out for {gv} yet"
        fav = mr_fav(pr)
        out.append({**fav, "why": why, "available": reason is None, "reason": reason,
                    "in_library": pr["id"] in have})
    return out


def perf_add(ids):
    added = []
    with CFG_LOCK:
        have = {str(f["id"]) for f in CFG["favorites"] if f.get("source") == "modrinth"}
        for pr in _PERF_CACHE.values():
            if pr and pr["id"] in ids and pr["id"] not in have:
                fav = mr_fav(pr)
                CFG["favorites"].append({k: fav.get(k) for k in ("source", "id", "slug", "name", "icon", "desc", "url", "kind")})
                added.append(fav["name"])
        save_config(CFG)
    return added


# =========================================================================== #
# Bring my settings along: video settings, keybinds, servers and mod configs
# =========================================================================== #
SETTINGS_FILES = {"options.txt": "video settings and keybinds", "optionsof.txt": "OptiFine settings",
                  "optionsshaders.txt": "shader settings", "servers.dat": "server list"}
SETTINGS_DIRS = ("config",)


def settings_sources(cfg):
    """Instances you've played that have settings worth copying, most recently played first."""
    seen, out = set(), []

    def add(game_dir, name, launcher):
        g = Path(game_dir)
        try:
            key = str(g.resolve()).lower()
        except OSError:
            return
        if key in seen or not (g / "options.txt").exists():
            return
        seen.add(key)
        out.append({"path": str(g), "name": name, "launcher": launcher,
                    "played": (g / "options.txt").stat().st_mtime})
    for f in find_mod_folders(cfg):
        add(Path(f["path"]).parent, f["name"], f["launcher"])
    for r in cfg.get("installs", []):
        if r.get("path"):
            add(Path(r["path"]).parent, r["name"], r.get("launcher_name", ""))
    add(launcher_path(cfg, "official"), "Default (.minecraft)", "Minecraft Launcher")
    out.sort(key=lambda x: x["played"], reverse=True)
    return out[:20]


def copy_settings(src: Path, dst: Path, log=print):
    """Copy settings into a new instance. Never overwrites settings that are already there."""
    if not src.is_dir():
        raise UserError("The instance to copy settings from isn't there any more.")
    try:
        if src.resolve() == dst.resolve():
            return []
    except OSError:
        pass
    dst.mkdir(parents=True, exist_ok=True)
    brought = []
    for name, label in SETTINGS_FILES.items():
        f = src / name
        if f.is_file() and not (dst / name).exists():
            shutil.copy2(f, dst / name)
            brought.append(label)
    for d in SETTINGS_DIRS:
        sd = src / d
        if not sd.is_dir():
            continue
        n = 0
        for f in sd.rglob("*"):
            if not f.is_file() or f.stat().st_size > 20_000_000:
                continue
            target = dst / d / f.relative_to(sd)
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            n += 1
        if n:
            brought.append(f"{n} mod setting {'file' if n == 1 else 'files'}")
    if brought:
        log("Brought along: " + ", ".join(brought))
    return brought


# =========================================================================== #
# Back up and move your library
# =========================================================================== #
BACKUP_MARKER = "modhub-backup.json"


# =========================================================================== #
# 4.0: mod updates in one place
# =========================================================================== #
MOD_UPDATES_SECONDS = 6 * 60 * 60


def _instance_entries(rec):
    """Every Modrinth file ModHub put in this instance: (kind, key, file name, version it installed)."""
    mods_dir = Path(rec["path"])
    out = []
    for kind, folder in (("mod", mods_dir), ("resourcepack", mods_dir.parent / "resourcepacks"), ("shader", mods_dir.parent / "shaderpacks")):
        try:
            manifest = json.loads((folder / MANIFEST_NAME).read_text("utf-8"))
        except Exception:
            continue
        try:
            versions = json.loads((folder / VERSIONS_NAME).read_text("utf-8"))
        except Exception:
            versions = {}
        for key, fname in (manifest or {}).items():
            if isinstance(key, str) and key.startswith("modrinth:") and isinstance(fname, str) and (folder / fname).exists():
                out.append((kind, key, fname, versions.get(key, "")))
    return out


def check_mod_updates(job=None):
    """Look up the newest version of every mod in every instance ModHub installed, without changing anything."""
    from concurrent.futures import ThreadPoolExecutor
    with CFG_LOCK:
        recs = [dict(r) for r in CFG.get("installs", []) if not r.get("export") and r.get("path")]
        pins = dict(CFG.get("pins") or {})
        names = {f"{f['source']}:{f['id']}": f for lo in CFG["loadouts"].values() for f in lo["favorites"]}
    wanted, rows = {}, []
    for rec in recs:
        if not Path(rec["path"]).is_dir():
            continue
        off = set(rec.get("disabled") or [])
        for kind, key, fname, ver in _instance_entries(rec):
            if key in off:
                continue
            pid = key.split(":", 1)[1]
            loaders = watch_loaders(kind, rec["loader"])
            lk = (pid, tuple(loaders), rec["version"], pins.get(f"{pid}|{rec['version']}|{rec['loader']}") if kind == "mod" else None)
            wanted[lk] = None
            rows.append((rec, kind, key, fname, ver, lk))
    if job:
        job.log(f"Checking {len(wanted)} mods across {len(recs)} instances...")

    def look(lk):
        pid, loaders, gv, since = lk
        try:
            return lk, mr_latest_for(pid, list(loaders), gv, since=since)
        except Exception:
            return lk, None
    with ThreadPoolExecutor(max_workers=8) as pool:
        for n, (lk, v) in enumerate(pool.map(look, list(wanted)), 1):
            wanted[lk] = v
            if job:
                job.progress = .05 + .85 * n / max(len(wanted), 1)
    items, unknown = [], []
    for rec, kind, key, fname, ver, lk in rows:
        v = wanted.get(lk)
        f = v and mr_primary_file(v)
        if not f or f["filename"] == fname:
            continue
        fav = names.get(key) or {}
        items.append({"instance": rec["id"], "instance_name": rec["name"], "version": rec["version"], "loader": rec["loader"],
                      "key": key, "kind": kind, "name": fav.get("name") or "", "icon": fav.get("icon") or "", "url": fav.get("url") or "",
                      "from": ver or re.sub(r"\.(jar|zip)$", "", fname), "to": v.get("version_number", ""),
                      "date": (v.get("date_published") or "")[:10], "changelog": (v.get("changelog") or "")[:1500]})
        if not fav.get("name"):
            unknown.append(key.split(":", 1)[1])
    if unknown:  # dependencies we only know by id
        try:
            for pid, pr in mr_projects(sorted(set(unknown))).items():
                fav = mr_fav(pr)
                for it in items:
                    if it["key"] == f"modrinth:{pid}" and not it["name"]:
                        it.update(name=fav["name"], icon=fav["icon"], url=fav["url"])
        except Exception:
            pass
    for it in items:
        it["name"] = it["name"] or it["key"].split(":", 1)[1]
    result = {"at": now_iso(), "items": items, "instances": len(recs)}
    with CFG_LOCK:
        CFG["mod_updates"] = result
        save_config(CFG)
    return result


def mod_updates_job(job):
    return check_mod_updates(job)


def apply_mod_updates_job(job, iids=None):
    with CFG_LOCK:
        waiting = sorted({u["instance"] for u in (CFG.get("mod_updates") or {}).get("items", [])})
        recs = [r for r in CFG.get("installs", []) if r["id"] in (iids or waiting) and not r.get("export")]
    if not recs:
        raise UserError("Everything is already up to date.")
    summary = []
    for n, rec in enumerate(recs, 1):
        job.log(f"--- {rec['name']} ({n} of {len(recs)})")
        try:
            res = install_job(job, install_request(rec), remember=False)
            summary.append({"name": rec["name"], "install_id": rec["id"], "updates": res.get("updates") or [],
                            "problems": res.get("problems") or []})
        except UserError as e:
            summary.append({"name": rec["name"], "error": str(e)})
    return {"summary": summary, "mod_updates": CFG.get("mod_updates")}


def mod_updates_watch():
    time.sleep(120)
    while True:
        try:
            with CFG_LOCK:
                last = (CFG.get("mod_updates") or {}).get("at")
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() if last else 1e9
            if age >= MOD_UPDATES_SECONDS - 60 and not any(not j.done for j in JOBS.values()):
                check_mod_updates()
        except Exception:
            traceback.print_exc()
        time.sleep(30 * 60)


# =========================================================================== #
# 4.0: sharing modpacks (share codes, .modhub files and Modrinth .mrpack files)
# =========================================================================== #
SHARE_PREFIX = "MH1-"
SHARE_KINDS = {"mod": "m", "resourcepack": "r", "shader": "s"}
SHARE_KINDS_BACK = {v: k for k, v in SHARE_KINDS.items()}
SHARE_PENDING = {}
MRPACK_LOADERS = {"fabric": "fabric-loader", "quilt": "quilt-loader", "forge": "forge", "neoforge": "neoforge"}


def _loadout(lid):
    with CFG_LOCK:
        lid = lid if lid in CFG["loadouts"] else CFG["active_loadout"]
        lo = json.loads(json.dumps(CFG["loadouts"][lid]))
    return lid, lo


def share_code(lid=None):
    import base64, zlib
    _, lo = _loadout(lid)
    mr = [f for f in lo["favorites"] if f.get("source") == "modrinth"]
    if not mr:
        raise UserError(f"\"{lo['name']}\" has no Modrinth mods to share yet. Files you added yourself can't go in a share code.")
    data = json.dumps({"n": lo["name"], "m": [SHARE_KINDS.get(f.get("kind") or "mod", "m") + str(f["id"]) for f in mr]}, separators=(",", ":"))
    code = SHARE_PREFIX + base64.urlsafe_b64encode(zlib.compress(data.encode(), 9)).decode().rstrip("=")
    return {"code": code, "name": lo["name"], "count": len(mr), "own": len(lo["favorites"]) - len(mr)}


def decode_share(text):
    import base64, zlib
    m = re.search(re.escape(SHARE_PREFIX) + r"([A-Za-z0-9_-]{8,20000})", text or "")
    if not m:
        raise UserError("That doesn't look like a ModHub share code. They start with MH1-.")
    raw = m.group(1)
    try:
        packed = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        d = zlib.decompressobj()
        data = json.loads(d.decompress(packed, 200_000).decode())
    except Exception:
        raise UserError("That share code is damaged. Ask for it again, and copy all of it.")
    items = []
    for x in (data.get("m") or [])[:500] if isinstance(data, dict) else []:
        if isinstance(x, str) and len(x) > 1 and x[0] in SHARE_KINDS_BACK and re.fullmatch(r"[A-Za-z0-9]{2,32}", x[1:]):
            items.append({"id": x[1:], "kind": SHARE_KINDS_BACK[x[0]]})
    if not items:
        raise UserError("That share code has no mods in it.")
    return {"name": str(data.get("n") or "Shared modpack")[:40], "items": items, "own_files": []}


def _pack_preview(pack):
    found = mr_projects([i["id"] for i in pack["items"]])
    favs = []
    for it in pack["items"]:
        p = found.get(it["id"]) or next((x for x in found.values() if x.get("slug") == it["id"]), None)
        if p:
            favs.append(mr_fav(p))
    token = uuid.uuid4().hex
    SHARE_PENDING[token] = {"name": pack["name"], "favorites": favs, "own_files": pack.get("own_files", []), "at": time.time()}
    for k in [k for k, v in SHARE_PENDING.items() if time.time() - v["at"] > 3600]:
        SHARE_PENDING.pop(k, None)
    return {"token": token, "name": pack["name"], "items": favs, "missing": len(pack["items"]) - len(favs),
            "own": [Path(x).name for x in pack.get("own_files", [])]}


def share_preview_code(code):
    return _pack_preview(decode_share(code))


def read_mrpack(path):
    """A Modrinth modpack: find each file on Modrinth by its hash; keep any extra files it carries."""
    with zipfile.ZipFile(path) as z:
        info = z.getinfo("modrinth.index.json")
        if info.file_size > 5_000_000:
            raise UserError("That modpack's list is too big.")
        index = json.loads(z.read(info))
        hashes = []
        for f in (index.get("files") or [])[:1000]:
            h = (f.get("hashes") or {}).get("sha1")
            if isinstance(h, str) and re.fullmatch(r"[0-9a-fA-F]{40}", h) and str(f.get("path", "")).startswith(("mods/", "resourcepacks/", "shaderpacks/")):
                hashes.append(h.lower())
        found = http_json("POST", f"{MODRINTH}/version_files", {"hashes": hashes, "algorithm": "sha1"}) if hashes else {}
        items, seen = [], set()
        for h in hashes:
            pid = ((found or {}).get(h) or {}).get("project_id")
            if pid and pid not in seen:
                seen.add(pid)
                items.append({"id": pid, "kind": "mod"})
        own = []
        tmpdir = Path(tempfile.mkdtemp(prefix="share-", dir=DATA_DIR))
        total = 0
        for zi in z.infolist()[:2000]:
            parts = zi.filename.split("/")
            if len(parts) == 3 and parts[0] in ("overrides", "client-overrides") and parts[1] in ("mods", "resourcepacks", "shaderpacks") \
                    and parts[2].lower().endswith((".jar", ".zip")) and not zi.is_dir():
                total += zi.file_size
                if total > 300_000_000:
                    break
                try:
                    name = safe_filename(parts[2])
                except UserError:
                    continue
                out = tmpdir / name
                with z.open(zi) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                own.append(str(out))
    missing = len(hashes) - len(seen)
    name = str(index.get("name") or Path(path).stem)[:40]
    return {"name": name, "items": items, "own_files": own, "unmatched": max(0, missing)}


def share_preview_file(path, filename):
    low = filename.lower()
    if low.endswith(".mrpack"):
        try:
            pack = read_mrpack(path)
        except (zipfile.BadZipFile, KeyError):
            raise UserError(f"{filename} isn't a Modrinth modpack.")
        if not pack["items"] and not pack["own_files"]:
            raise UserError(f"ModHub couldn't find any of {filename}'s mods on Modrinth.")
        prev = _pack_preview(pack) if pack["items"] else {"token": uuid.uuid4().hex, "name": pack["name"], "items": [], "missing": 0,
                                                            "own": [Path(x).name for x in pack["own_files"]]}
        if not pack["items"]:
            SHARE_PENDING[prev["token"]] = {"name": pack["name"], "favorites": [], "own_files": pack["own_files"], "at": time.time()}
        prev["missing"] += pack.get("unmatched", 0)
        return prev
    text = Path(path).read_text("utf-8", errors="replace")[:500_000]
    return share_preview_code(text)


def share_import(token, mode="new", name=None):
    pend = SHARE_PENDING.pop(token, None)
    if not pend:
        raise UserError("That share has expired. Open the code or file again.")
    with CFG_LOCK:
        if mode == "new":
            base = (name or pend["name"] or "Shared modpack").strip()[:40] or "Shared modpack"
            taken = {v["name"].lower() for v in CFG["loadouts"].values()}
            nm, n = base, 2
            while nm.lower() in taken:
                nm, n = f"{base} {n}"[:40], n + 1
            lid = uuid.uuid4().hex[:8]
            CFG["loadouts"][lid] = {"name": nm, "favorites": []}
            CFG["active_loadout"] = lid
            CFG["favorites"] = CFG["loadouts"][lid]["favorites"]
        have = {f"{f['source']}:{f['id']}" for f in CFG["favorites"]}
        added = 0
        for f in pend["favorites"]:
            if f"modrinth:{f['id']}" not in have:
                CFG["favorites"].append(f)
                added += 1
        target = CFG["loadouts"][CFG["active_loadout"]]["name"]
        save_config(CFG)
    own = 0
    for fp in pend.get("own_files", []):
        p = Path(fp)
        if p.is_file():
            try:
                add_local_file(p, p.name)
                own += 1
            except UserError:
                pass
            finally:
                try:
                    p.unlink()
                except OSError:
                    pass
    return {"added": added, "own": own, "loadout": target, **state()}


def _downloads_dir():
    home = Path.home()
    out = next((d for d in (home / "Downloads", home / "Desktop") if d.is_dir()), EXPORT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    return out


def _unique(folder, stem, ext):
    stem = re.sub(r'[\\/:*?"<>|]+', "", stem).strip() or "ModHub"
    out, n = folder / f"{stem}{ext}", 2
    while out.exists():
        out, n = folder / f"{stem} ({n}){ext}", n + 1
    return out


def share_save_file(lid=None):
    c = share_code(lid)
    out = _unique(_downloads_dir(), c["name"], ".modhub")
    out.write_text(json.dumps({"format": "modhub-pack", "version": 1, "name": c["name"], "code": c["code"],
                               "made_with": f"ModHub {APP_VERSION}"}, indent=2), "utf-8")
    OPENABLE.add(str(out))
    return {"path": str(out), "file": out.name, "where": out.parent.name, "count": c["count"], "own": c["own"]}


def mrpack_job(job, lid, gv, loader):
    gv = (gv or "").strip()
    if not gv or loader not in MRPACK_LOADERS:
        raise UserError("Pick a Minecraft version and a loader.")
    _, lo = _loadout(lid)
    if not lo["favorites"]:
        raise UserError(f"\"{lo['name']}\" is empty.")
    job.log(f"Working out {lo['name']} for Minecraft {gv} ({loader})...")
    with CFG_LOCK:
        ports = dict(CFG.get("ports") or {})
    items = resolve(job, lo["favorites"], gv, loader, ports)
    ready = [i for i in items if i["status"] == "ready"]
    if not ready:
        raise UserError(f"Nothing in \"{lo['name']}\" is out for {gv} yet.")
    lv = loader_version(loader, gv)
    files, extra = [], []
    for it in ready:
        f = it["file"]
        folder = {"resourcepack": "resourcepacks", "shader": "shaderpacks"}.get(it.get("kind"), "mods")
        if f.get("local"):
            extra.append((Path(f["local"]), f"overrides/{folder}/{f['filename']}"))
        elif f.get("sha1") and f.get("sha512"):
            files.append({"path": f"{folder}/{f['filename']}", "hashes": {"sha1": f["sha1"], "sha512": f["sha512"]},
                          "env": {"client": "required", "server": "required"}, "downloads": [f["url"]], "fileSize": int(f.get("size") or 0)})
        else:
            it["notes"].append("left out: Modrinth didn't give its checksums")
    index = {"formatVersion": 1, "game": "minecraft", "versionId": "1.0", "name": lo["name"],
             "summary": f"Made with ModHub {APP_VERSION}", "files": files,
             "dependencies": {"minecraft": gv, MRPACK_LOADERS[loader]: lv}}
    out = _unique(_downloads_dir(), f"{lo['name']} {gv}", ".mrpack")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, indent=2))
        for src, arc in extra:
            if src.is_file():
                z.write(src, arc)
    OPENABLE.add(str(out))
    job.log(f"Saved {out.name}")
    return {"path": str(out), "file": out.name, "where": out.parent.name, "count": len(files) + len(extra),
            "left_out": [{"name": i["name"], "status": i["status"]} for i in items if i["status"] != "ready" and i.get("favorite")]}


# =========================================================================== #
# 4.0: the live count (only if you say yes) and the developer's stats
# =========================================================================== #
LIVE_URL = "https://abacus.jasoncameron.dev"
LIVE_NS = "modhub-mc"
LIVE_BUCKET = 300


def live_loop():
    sent, sent_periods = None, set()
    time.sleep(20)
    while True:
        try:
            b = int(time.time() // LIVE_BUCKET)
            with CFG_LOCK:
                ok = CFG.get("live_ping") is not False  # a simple tally; anyone who said no earlier stays out
            if ok and LIVE_URL and b != sent:
                req = urllib.request.Request(f"{LIVE_URL}/hit/{LIVE_NS}/live-{b}", headers={"User-Agent": USER_AGENT})
                urllib.request.urlopen(req, timeout=15).read(200)
                sent = b
                for key, period in (("hour", 3600), ("day", 86400)):
                    k = f"{key}-{int(time.time() // period)}"
                    if k not in sent_periods:
                        req = urllib.request.Request(f"{LIVE_URL}/hit/{LIVE_NS}/{k}", headers={"User-Agent": USER_AGENT})
                        urllib.request.urlopen(req, timeout=15).read(200)
                        sent_periods.add(k)
        except Exception:
            pass
        time.sleep(60)


def dev_stats():
    with CFG_LOCK:
        if not dev_on("stats"):
            raise UserError("That developer option is off.")
    from concurrent.futures import ThreadPoolExecutor
    now = int(time.time() // LIVE_BUCKET)

    def get(b):
        try:
            req = urllib.request.Request(f"{LIVE_URL}/get/{LIVE_NS}/live-{b}", headers={"User-Agent": USER_AGENT})
            return json.loads(urllib.request.urlopen(req, timeout=10).read(500)).get("value", 0)
        except urllib.error.HTTPError as e:
            return 0 if e.code == 404 else None
        except Exception:
            return None
    with ThreadPoolExecutor(max_workers=6) as pool:
        hist = list(pool.map(get, [now - i for i in range(12, -1, -1)]))  # the last hour, 5 minutes at a time
    downloads, latest = None, None
    try:
        rels = http_json("GET", f"https://api.github.com/repos/{DEFAULT_UPDATE_SOURCE}/releases?per_page=100") or []
        downloads = sum(a.get("download_count", 0) for r in rels for a in r.get("assets", []))
        latest = {"tag": rels[0].get("tag_name"), "downloads": sum(a.get("download_count", 0) for a in rels[0].get("assets", []))} if rels else None
    except Exception:
        pass
    live = max([h for h in hist[-2:] if h is not None] or [0])
    return {"live": live, "history": hist, "downloads": downloads, "latest": latest, "reachable": any(h is not None for h in hist),
            "at": now_iso()}


# =========================================================================== #
# Developer options (only after the developer code, each one switchable)
# =========================================================================== #
DEV_FEATURES = {"stats": True, "downloads": True, "history": True, "beta": False, "versions": True,
                "previews": True, "announce": True, "debug": True}
REPO = "stefantay25-ux/modhub"
NOTICE_URL = f"https://raw.githubusercontent.com/{REPO}/main/notice.json"
PIN_FILE = DATA_DIR / "app" / "keep-version"


def dev_features(cfg=None):
    cfg = CFG if cfg is None else cfg
    got = cfg.get("dev_features") if isinstance(cfg.get("dev_features"), dict) else {}
    return {k: bool(got.get(k, v)) for k, v in DEV_FEATURES.items()}


def dev_on(name, cfg=None):
    cfg = CFG if cfg is None else cfg
    return bool(cfg.get("dev_mode")) and dev_features(cfg).get(name, False)


def _need_dev(name):
    with CFG_LOCK:
        if not dev_on(name):
            raise UserError("That developer option is off.")


def _gh(path, method="GET", body=None, token=None):
    hdrs = {"Accept": "application/vnd.github+json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    return http_json(method, f"https://api.github.com/{path}", body, headers=hdrs)


def _abacus(key):
    try:
        req = urllib.request.Request(f"{LIVE_URL}/get/{LIVE_NS}/{key}", headers={"User-Agent": USER_AGENT})
        return json.loads(urllib.request.urlopen(req, timeout=10).read(500)).get("value", 0)
    except urllib.error.HTTPError as e:
        return 0 if e.code == 404 else None
    except Exception:
        return None


def dev_history(view):
    _need_dev("history")
    from concurrent.futures import ThreadPoolExecutor
    now = time.time()
    if view == "week":
        keys = [f"day-{int(now // 86400) - i}" for i in range(6, -1, -1)]
        labels = [datetime.fromtimestamp((int(now // 86400) - i) * 86400, timezone.utc).strftime("%a") for i in range(6, -1, -1)]
    elif view == "day":
        keys = [f"hour-{int(now // 3600) - i}" for i in range(23, -1, -1)]
        labels = [datetime.fromtimestamp((int(now // 3600) - i) * 3600).strftime("%H:00") for i in range(23, -1, -1)]
    else:
        keys = [f"live-{int(now // LIVE_BUCKET) - i}" for i in range(12, -1, -1)]
        labels = [datetime.fromtimestamp((int(now // LIVE_BUCKET) - i) * LIVE_BUCKET).strftime("%H:%M") for i in range(12, -1, -1)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(_abacus, keys))
    return {"view": view, "values": values, "labels": labels, "reachable": any(v is not None for v in values)}


def dev_downloads():
    _need_dev("downloads")
    rels = _gh(f"repos/{REPO}/releases?per_page=100") or []
    kinds = {"ModHub.exe": "windows", "ModHub-mac.zip": "mac", "ModHub-mac-intel.zip": "mac", "ModHub-linux.tar.gz": "linux"}
    total = {"windows": 0, "mac": 0, "linux": 0}
    rows = []
    for r in rels:
        row = {"version": r.get("tag_name", "").lstrip("v"), "windows": 0, "mac": 0, "linux": 0}
        for a in r.get("assets") or []:
            k = kinds.get(a.get("name"))
            if k:
                row[k] += a.get("download_count", 0)
                total[k] += a.get("download_count", 0)
        rows.append(row)
    return {"total": total, "all": sum(total.values()), "versions": rows[:12]}


def dev_versions():
    _need_dev("versions")
    commits = _gh(f"repos/{REPO}/commits?path=modhub.py&per_page=100") or []
    seen, out = set(), []
    for c in commits:
        m = re.match(r"ModHub (\d+(?:\.\d+)+)\b", (c.get("commit") or {}).get("message", ""))
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append({"version": m.group(1), "sha": c["sha"], "date": ((c.get("commit") or {}).get("author") or {}).get("date", "")[:10]})
    return {"versions": out, "current": APP_VERSION, "pinned": PIN_FILE.exists()}


def dev_install_version_job(job, sha, version):
    _need_dev("versions")
    if not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        raise UserError("Pick a version from the list.")
    job.log(f"Downloading ModHub {version}...")
    req = urllib.request.Request(f"https://raw.githubusercontent.com/{REPO}/{sha}/modhub.py", headers={"User-Agent": USER_AGENT})
    data = urllib.request.urlopen(req, timeout=30).read(5_000_001)
    if len(data) > 5_000_000:
        raise UserError("That file is too big to be ModHub.")
    UPDATES_DIR.mkdir(parents=True, exist_ok=True)
    tmp = UPDATES_DIR / "picked.tmp"
    tmp.write_bytes(data)
    got = read_update_file(tmp)
    if not got:
        tmp.unlink()
        raise UserError("That version couldn't be read.")
    older = version_tuple(got[0]) < version_tuple(APP_VERSION)
    apply_update(str(tmp), allow_older=True)
    try:  # keep this version: the ModHub app won't swap it for the version it carries
        PIN_FILE.parent.mkdir(parents=True, exist_ok=True)
        if older:
            PIN_FILE.write_text(got[0], "utf-8")
        elif PIN_FILE.exists():
            PIN_FILE.unlink()
    except OSError:
        pass
    for f in UPDATES_DIR.glob("modhub-*.py"):  # drop downloaded updates so they don't replace it straight away
        try:
            f.unlink()
        except OSError:
            pass
    job.log(f"Installed ModHub {got[0]}. Restarting...")
    threading.Timer(1.5, restart_app).start()
    return {"version": got[0], "older": older}


def _redacted_config():
    with CFG_LOCK:
        cfg = json.loads(json.dumps({k: v for k, v in CFG.items() if k != "favorites"}))
    if cfg.get("dev_github_token"):
        cfg["dev_github_token"] = "(hidden)"
    return cfg


def dev_debug(action):
    _need_dev("debug")
    if action == "log":
        return {"text": log_tail(400) or "The log is empty."}
    if action == "config":
        return {"text": json.dumps(_redacted_config(), indent=2)}
    if action == "clear":
        for c in (DISCOVER_CACHE, _PERF_CACHE, _SHADER_LOADER_CACHE):
            c.clear()
        UPDATE_CACHE.update(at=0, found=None)
        VERSIONS_CACHE.update(list=None)
        return {"text": "Cleared ModHub's caches. Fresh data loads the next time it's needed."}
    if action == "replay":
        with CFG_LOCK:
            for k in ("native_prompt_dismissed", "shortcut_done", "seen_newest", "mod_updates"):
                CFG.pop(k, None)
            save_config(CFG)
        return {"text": "First-run screens and prompts will show again."}
    raise UserError("Unknown debug action.")


# ---- announcements: a small file on GitHub that every copy of ModHub reads ----
def fetch_notice():
    try:
        req = urllib.request.Request(NOTICE_URL + f"?t={int(time.time() // 300)}", headers={"User-Agent": USER_AGENT})
        raw = json.loads(urllib.request.urlopen(req, timeout=15).read(20_000))
    except urllib.error.HTTPError as e:
        raw = {} if e.code == 404 else None
    except Exception:
        raw = None
    if raw is None:
        return
    notice = None
    if isinstance(raw, dict) and isinstance(raw.get("text"), str) and raw["text"].strip() and isinstance(raw.get("id"), str):
        link = raw.get("link") if isinstance(raw.get("link"), str) and raw["link"].startswith("https://") else ""
        notice = {"id": raw["id"][:40], "text": raw["text"].strip()[:280], "link": link[:300],
                  "until": raw.get("until") if isinstance(raw.get("until"), str) else ""}
    with CFG_LOCK:
        if CFG.get("notice") != notice:
            CFG["notice"] = notice
            save_config(CFG)


def current_notice(cfg):
    n = cfg.get("notice")
    if not isinstance(n, dict) or n.get("id") in (cfg.get("notices_dismissed") or []):
        return None
    if n.get("until") and n["until"] < now_iso()[:10]:
        return None
    return n


def notice_watch():
    time.sleep(15)
    while True:
        try:
            fetch_notice()
        except Exception:
            traceback.print_exc()
        time.sleep(30 * 60)


def dev_publish_notice(text, link, until, token):
    _need_dev("announce")
    import base64
    with CFG_LOCK:
        if token:
            CFG["dev_github_token"] = token.strip()
            save_config(CFG)
        token = CFG.get("dev_github_token")
    if not token:
        raise UserError("Add your GitHub access token first.")
    text = (text or "").strip()[:280]
    link = (link or "").strip()
    if link and not link.startswith("https://"):
        raise UserError("Links need to start with https://")
    body = {"id": uuid.uuid4().hex[:10], "text": text, "link": link[:300], "until": (until or "")[:10]} if text else {"id": "none", "text": ""}
    path = f"repos/{REPO}/contents/notice.json"
    try:
        sha = (_gh(path, token=token) or {}).get("sha")
    except Exception:
        sha = None
    req = {"message": "Announcement" if text else "Remove announcement",
           "content": base64.b64encode(json.dumps(body, indent=2).encode()).decode()}
    if sha:
        req["sha"] = sha
    try:
        _gh(path, "PUT", req, token=token)
    except Exception as e:
        raise UserError(f"GitHub didn't accept it ({e}). Check the token has Contents: Read and write for the modhub repo.")
    with CFG_LOCK:
        CFG["notice"] = {k: body.get(k, "") for k in ("id", "text", "link", "until")} if text else None
        save_config(CFG)
    return {"ok": True, "notice": CFG["notice"]}


def save_library_backup():
    """One file with your loadouts, the files you added yourself and your update setting."""
    with CFG_LOCK:
        loadouts = json.loads(json.dumps(CFG["loadouts"]))
        data = {"format": 1, "app": "ModHub", "app_version": APP_VERSION, "created": now_iso(),
                "loadouts": loadouts, "active_loadout": CFG.get("active_loadout"),
                "settings": {k: CFG.get(k) for k in ("update_auto", "loader") if CFG.get(k) is not None}}
    own = {}
    for lo in loadouts.values():
        for f in lo["favorites"]:
            if f.get("source") == "local" and re.fullmatch(r"[\w-]+", str(f["id"])):
                own[str(f["id"])] = [x["file"] for x in f.get("files", [])]
    home = Path.home()
    out_dir = next((d for d in (home / "Downloads", home / "Desktop") if d.is_dir()), EXPORT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"ModHub-backup-{datetime.now():%Y-%m-%d}"
    out = out_dir / f"{base}.zip"
    n = 2
    while out.exists():
        out = out_dir / f"{base}-{n}.zip"
        n += 1
    files = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(BACKUP_MARKER, json.dumps(data, indent=2))
        for iid, names in own.items():
            for name in names:
                f = LOCAL_DIR / iid / name
                if f.is_file():
                    z.write(f, f"files/{iid}/{name}")
                    files += 1
    OPENABLE.add(str(out))
    items = sum(len(lo["favorites"]) for lo in loadouts.values())
    return {"path": str(out), "file": out.name, "where": out_dir.name, "loadouts": len(loadouts), "items": items, "files": files}


def restore_library_backup(path: Path):
    """Add a backup to this ModHub. Nothing is removed: loadouts with the same name are merged."""
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        raise UserError("That isn't a ModHub backup file.")
    with z:
        if BACKUP_MARKER not in z.namelist():
            raise UserError("That isn't a ModHub backup file.")
        try:
            data = json.loads(zread(z, BACKUP_MARKER).decode("utf-8"))
        except Exception:
            raise UserError("That backup file is damaged.")
        if data.get("app") != "ModHub" or not isinstance(data.get("loadouts"), dict):
            raise UserError("That isn't a ModHub backup file.")
        # your own files first, so the library entries that point at them work straight away
        files = 0
        for name in z.namelist():
            m = re.fullmatch(r"files/([\w-]+)/([^/\\]+)", name)
            if not m or not m.group(2).lower().endswith((".jar", ".zip")):
                continue
            target = LOCAL_DIR / m.group(1) / m.group(2)
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            files += 1
    added_lo, merged_lo, items = [], [], 0
    with CFG_LOCK:
        for lo in data["loadouts"].values():
            name = (lo.get("name") or "Restored").strip()[:40]
            favs = [f for f in lo.get("favorites") or [] if isinstance(f, dict) and f.get("source") in ("modrinth", "local") and f.get("id")]
            mine = next((v for v in CFG["loadouts"].values() if v["name"].lower() == name.lower()), None)
            if mine is None:
                CFG["loadouts"][uuid.uuid4().hex[:8]] = {"name": name, "favorites": favs}
                added_lo.append(name)
                items += len(favs)
            else:
                have = {(f["source"], str(f["id"])) for f in mine["favorites"]}
                new = [f for f in favs if (f["source"], str(f["id"])) not in have]
                mine["favorites"].extend(new)
                items += len(new)
                if new:
                    merged_lo.append(name)
        CFG["favorites"] = CFG["loadouts"][CFG["active_loadout"]]["favorites"]
        save_config(CFG)
    return {"loadouts_added": added_lo, "loadouts_merged": merged_lo, "items": items, "files": files,
            "from": data.get("created", "")[:10]}


# =========================================================================== #
# Launchers
# =========================================================================== #
def official_prepare(ctx):
    mc = launcher_path(ctx["cfg"], "official")
    if not mc.is_dir():
        raise UserError(f"Couldn't find the Minecraft Launcher folder at {mc}. Set it in Settings.")
    gv, loader = ctx["gv"], ctx["loader"]
    versions = mc / "versions"
    if loader in ("fabric", "quilt"):
        lv = loader_version(loader, gv)
        meta = ("https://meta.fabricmc.net/v2" if loader == "fabric" else "https://meta.quiltmc.org/v3")
        prof = http_json("GET", f"{meta}/versions/loader/{urllib.parse.quote(gv)}/{urllib.parse.quote(lv)}/profile/json")
        if not prof:
            raise UserError(f"Couldn't get the {loader} profile for {gv}.")
        vid = prof["id"]
        vdir = versions / vid
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / f"{vid}.json").write_text(json.dumps(prof, indent=2), "utf-8")
        if not (vdir / f"{vid}.jar").exists():
            (vdir / f"{vid}.jar").write_bytes(b"")
        ctx["log"](f"Installed {loader} loader {lv} for {gv}")
    else:
        cands = [d for d in versions.iterdir() if d.is_dir() and loader in d.name.lower() and gv in d.name
                 and (loader != "forge" or "neoforge" not in d.name.lower())] if versions.is_dir() else []
        if loader == "neoforge" and not cands and versions.is_dir():
            try:
                lv = loader_version("neoforge", gv)
                cands = [d for d in versions.iterdir() if d.is_dir() and d.name.lower() == f"neoforge-{lv}"]
            except UserError:
                pass
        if not cands:
            page = ("https://files.minecraftforge.net/" if loader == "forge" else "https://neoforged.net/")
            raise UserError(f"{loader.title()} for {gv} isn't installed in the Minecraft Launcher yet. "
                            f"Download its installer from {page}, run it once (Install client), then click Install again.")
        vid = max(cands, key=lambda d: d.stat().st_mtime).name
    name = ctx["name"]
    game_dir = mc / "modhub-instances" / safe_name(name)
    game_dir.mkdir(parents=True, exist_ok=True)
    wrote = False
    for pf in ("launcher_profiles.json", "launcher_profiles_microsoft_store.json"):
        p = mc / pf
        if not p.exists():
            continue
        data = json.loads(p.read_text("utf-8"))
        shutil.copy2(p, p.with_suffix(".json.modhub-backup"))
        profiles = data.setdefault("profiles", {})
        pid = next((k for k, v in profiles.items() if v.get("gameDir") == str(game_dir)), uuid.uuid4().hex)
        profiles[pid] = {**profiles.get(pid, {}), "name": name, "type": "custom", "lastVersionId": vid,
                         "gameDir": str(game_dir), "icon": "Bookshelf", "lastUsed": now_iso(),
                         "created": profiles.get(pid, {}).get("created", now_iso())}
        p.write_text(json.dumps(data, indent=2), "utf-8")
        wrote = True
    if not wrote:
        raise UserError("Found the Minecraft folder but no launcher_profiles.json. Open the Minecraft Launcher once, then try again.")
    ctx["open"] = game_dir
    ctx["message"] = (f"Added the profile \"{name}\" to the Minecraft Launcher. "
                      "If the launcher was open, restart it to see it.")
    return game_dir / "mods"


def prism_instances_dir(cfg):
    base = launcher_path(cfg, "prism")
    if not base.is_dir():
        raise UserError(f"Couldn't find Prism Launcher at {base}. Set its folder in Settings.")
    inst = "instances"
    cfgfile = base / "prismlauncher.cfg"
    if cfgfile.exists():
        m = re.search(r"^InstanceDir=(.+)$", cfgfile.read_text("utf-8", "replace"), re.M)
        if m and m.group(1).strip():
            inst = m.group(1).strip()
    p = Path(inst)
    return p if p.is_absolute() else base / p


def prism_component_version(uid, gv):
    idx = http_json("GET", f"https://meta.prismlauncher.org/v1/{uid}/index.json") or {}
    versions = idx.get("versions") or []
    match = []
    for v in versions:
        reqs = v.get("requires") or []
        mc = [r for r in reqs if r.get("uid") == "net.minecraft"]
        if mc and not any(r.get("equals") == gv for r in mc):
            continue
        match.append(v)
    if not match:
        return None
    rec = [v for v in match if v.get("recommended")]
    return (rec or match)[0]["version"]


def prism_prepare(ctx):
    inst_root = prism_instances_dir(ctx["cfg"])
    gv, loader, name = ctx["gv"], ctx["loader"], ctx["name"]
    uid = {"fabric": "net.fabricmc.fabric-loader", "quilt": "org.quiltmc.quilt-loader",
           "forge": "net.minecraftforge", "neoforge": "net.neoforged"}[loader]
    lv = prism_component_version(uid, gv)
    if not lv:
        raise UserError(f"{loader.title()} doesn't support Minecraft {gv} yet (according to Prism).")
    comps = [{"uid": "net.minecraft", "version": gv, "important": True}]
    if loader in ("fabric", "quilt"):
        comps.append({"uid": "net.fabricmc.intermediary", "version": gv, "dependencyOnly": True})
    comps.append({"uid": uid, "version": lv})
    inst = inst_root / safe_name(name)
    inst.mkdir(parents=True, exist_ok=True)
    (inst / "mmc-pack.json").write_text(json.dumps({"formatVersion": 1, "components": comps}, indent=2), "utf-8")
    cfgp = inst / "instance.cfg"
    if not cfgp.exists():
        cfgp.write_text(f"[General]\nConfigVersion=1.2\nInstanceType=OneSix\nname={name}\niconKey=default\n", "utf-8")
    game = inst / ".minecraft"
    if not game.exists() and (inst / "minecraft").exists():
        game = inst / "minecraft"
    ctx["log"](f"Prism instance ready ({loader} {lv})")
    ctx["open"] = inst
    ctx["message"] = f"Created the Prism instance \"{name}\". If Prism was open and you don't see it, restart Prism."
    return game / "mods"


def pack_prepare(ctx):
    ctx["stage"] = Path(tempfile.mkdtemp(prefix="modhub-"))
    ctx["lv"] = loader_version(ctx["loader"], ctx["gv"])
    return ctx["stage"] / "overrides" / "mods"


def modrinth_app_finish(ctx):
    gv, loader, name, stage = ctx["gv"], ctx["loader"], ctx["name"], ctx["stage"]
    key = {"fabric": "fabric-loader", "quilt": "quilt-loader", "forge": "forge", "neoforge": "neoforge"}[loader]
    index = {"formatVersion": 1, "game": "minecraft", "versionId": datetime.now().strftime("%Y.%m.%d"),
             "name": name, "summary": "Made with ModHub", "files": [],
             "dependencies": {"minecraft": gv, key: ctx["lv"]}}
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = EXPORT_DIR / f"{safe_name(name)}.mrpack"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, indent=2))
        for f in sorted((stage / "overrides").rglob("*")):
            if f.is_file() and f.name != MANIFEST_NAME:
                z.write(f, "overrides/" + f.relative_to(stage / "overrides").as_posix())
    shutil.rmtree(stage, ignore_errors=True)
    try:
        open_path(out)
        ctx["message"] = (f"Built {out.name} and sent it to the Modrinth App. Confirm the import there. "
                          "If nothing opened: Modrinth App > + (Create instance) > From file, then pick it.")
    except Exception:
        ctx["message"] = f"Built {out.name}. In the Modrinth App: + (Create instance) > From file, then pick it."
    ctx["open"] = out


def curseforge_app_finish(ctx):
    gv, loader, name, stage = ctx["gv"], ctx["loader"], ctx["name"], ctx["stage"]
    manifest = {"minecraft": {"version": gv, "modLoaders": [{"id": f"{loader}-{ctx['lv']}", "primary": True}]},
                "manifestType": "minecraftModpack", "manifestVersion": 1, "name": name,
                "version": "1.0", "author": "ModHub", "files": [], "overrides": "overrides"}
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = EXPORT_DIR / f"{safe_name(name)}-curseforge.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        for f in sorted((stage / "overrides").rglob("*")):
            if f.is_file() and f.name != MANIFEST_NAME:
                z.write(f, "overrides/" + f.relative_to(stage / "overrides").as_posix())
    shutil.rmtree(stage, ignore_errors=True)
    ctx["open"] = out
    ctx["message"] = (f"Built {out.name}. In the CurseForge app: Minecraft > Create Custom Profile > "
                      "Import (top right), then pick this file.")


def folder_prepare(ctx):
    folder = (ctx.get("folder") or "").strip().strip('"')
    if not folder:
        raise UserError("Pick the mods folder to install into.")
    p = Path(os.path.expandvars(os.path.expanduser(folder)))
    if ctx["launcher"] == "lunar" and ctx["loader"] != "fabric":
        raise UserError("Lunar Client only runs Fabric mods. Switch the loader to Fabric.")
    if p.name.lower() != "mods" and not any(p.glob("*.jar")) and not (p / "mods").exists():
        ctx["log"](f"Note: {p} isn't called 'mods'. Installing there anyway.")
    ctx["open"] = p
    ctx["message"] = f"Copied your mods into {p}."
    if ctx["launcher"] == "lunar":
        ctx["message"] += " Lunar only loads Fabric mods it supports, so some may not show up in game."
    return p


LAUNCHERS = {
    "official": {"name": "Minecraft Launcher", "prepare": official_prepare, "finish": None, "path": "official",
                 "desc": "Adds a new profile with its own mods folder. Fabric and Quilt are fully automatic. Forge/NeoForge need the loader installed once."},
    "prism": {"name": "Prism Launcher", "prepare": prism_prepare, "finish": None, "path": "prism",
              "desc": "Creates a ready-to-play instance with the right loader."},
    "modrinth": {"name": "Modrinth App", "prepare": pack_prepare, "finish": modrinth_app_finish, "path": "modrinth_app",
                 "desc": "Builds a modpack file and opens it in the Modrinth App so you can import it."},
    "curseforge": {"name": "CurseForge App", "prepare": pack_prepare, "finish": curseforge_app_finish, "path": "curseforge_app",
                   "desc": "Builds a profile .zip. Import it with Create Custom Profile > Import."},
    "lunar": {"name": "Lunar Client", "prepare": folder_prepare, "finish": None, "path": None, "folder": True,
              "desc": "Copies Fabric mods into the Lunar mods folder you choose."},
    "folder": {"name": "Any launcher or folder", "prepare": folder_prepare, "finish": None, "path": None, "folder": True,
               "desc": "Copies mods into any mods folder. Works with every launcher."},
}


def loadout_favorites(cfg, loadout_id=None):
    lid = loadout_id if loadout_id in cfg["loadouts"] else cfg["active_loadout"]
    return lid, cfg["loadouts"][lid]["name"], cfg["loadouts"][lid]["favorites"]


def install_job(job, req, remember=True):
    gv = (req.get("version") or "").strip()
    loader = req.get("loader")
    launcher = req.get("launcher")
    if not gv:
        raise UserError("Pick a Minecraft version.")
    if loader not in LOADERS:
        raise UserError("Pick a mod loader.")
    if launcher not in LAUNCHERS:
        raise UserError("Pick a launcher.")
    with CFG_LOCK:
        cfg = json.loads(json.dumps({k: v for k, v in CFG.items() if k != "favorites"}))
        if remember:
            if gv == newest_release():  # installing the newest version counts as having seen it
                CFG["seen_newest"] = gv
            CFG["loader"] = loader
            CFG["last"] = {"version": gv, "loader": loader, "launcher": launcher,
                           "settings_from": req.get("settings_from") or "",
                           "folders": {**(CFG.get("last", {}).get("folders") or {}),
                                       **({launcher: req.get("folder")} if req.get("folder") else {})}}
            save_config(CFG)
    lid, lname, favorites = loadout_favorites(cfg, req.get("loadout"))
    if not favorites:
        raise UserError(f"The loadout \"{lname}\" is empty. Add some mods in Library first.")
    name = (req.get("name") or "").strip() or (f"ModHub {gv}" if lname == "My mods" else f"{lname} {gv}")
    L = LAUNCHERS[launcher]
    ctx = {"cfg": cfg, "gv": gv, "loader": loader, "launcher": launcher, "name": name,
           "folder": req.get("folder"), "log": job.log}

    job.log(f"Installing {lname} for Minecraft {gv} ({loader}) -> {L['name']}")
    u0 = len(job.updates)  # this install's own changes (Update all runs several in one job)
    items = resolve(job, favorites, gv, loader, cfg.get("ports") or {})
    for it in items:
        if it["key"] in (req.get("skip") or []):
            it.update(status="off", notes=it["notes"] + ["turned off for this instance"])
    ready = [i for i in items if i["status"] == "ready"]
    if not ready:
        raise UserError(f"Nothing in \"{lname}\" has a {gv} {loader} version yet. Nothing was installed.")
    job.progress = 0.48
    mods_dir = L["prepare"](ctx)
    brought = []
    src = (req.get("settings_from") or "").strip()
    if src and launcher != "lunar":
        try:
            brought = copy_settings(Path(src), mods_dir.parent, job.log)
        except UserError as e:
            job.log(f"Couldn't bring settings along: {e}")
    job.log(f"Downloading {len(ready)} items...")
    install_mods(job, mods_dir, items, managed=not L["finish"])
    job.progress = 0.93
    problems = check_and_fix(job, mods_dir, gv, loader, managed=not L["finish"])
    if L["finish"]:
        job.progress = 0.95
        L["finish"](ctx)
    if ctx.get("open"):
        OPENABLE.add(str(ctx["open"]))
    added = sum(1 for i in items if i["status"] == "ready")
    job.log(f"Done! {added} installed.")
    install_id = record_install(req, ctx, lid, lname, mods_dir, export=bool(L["finish"]), items=items, updates=job.updates[u0:])
    return {"items": items, "message": ctx.get("message", ""), "open": str(ctx.get("open") or ""),
            "changes": job.changes, "install_id": install_id, "problems": problems, "export": bool(L["finish"]),
            "brought": brought, "updates": job.updates[u0:]}


# =========================================================================== #
# Instances ModHub installed, keeping them updated, and watching for mods that catch up
# =========================================================================== #
def record_install(req, ctx, lid, lname, mods_dir, export, items, updates=None):
    launcher = ctx["launcher"]
    folder = (req.get("folder") or "").strip()
    iid = f"{launcher}:{folder.lower() if LAUNCHERS[launcher].get('folder') else ctx['name'].lower()}"
    now = now_iso()
    rec = {"id": iid, "name": ctx["name"], "launcher": launcher, "launcher_name": LAUNCHERS[launcher]["name"],
           "version": ctx["gv"], "loader": ctx["loader"], "loadout": lid, "loadout_name": lname,
           "folder": folder, "path": "" if export else str(mods_dir), "open": str(ctx.get("open") or ""),
           "export": export, "updated": now,
           "counts": {k: sum(1 for i in items if i["status"] == "ready" and i.get("kind", "mod") == k)
                      for k in ("mod", "resourcepack", "shader")}}
    with CFG_LOCK:
        installs = CFG.setdefault("installs", [])
        old = next((r for r in installs if r["id"] == iid), None)
        rec["installed"] = old.get("installed", now) if old else now
        rec["disabled"] = (old or {}).get("disabled", [])
        if not export:  # ModHub just checked this folder itself
            rec["checked_sig"] = _folder_sig(Path(mods_dir))
        if updates:  # remember the latest round of changes for "What changed"
            rec["last_changes"] = [dict(u, changelog=(u.get("changelog") or "")[:1500]) for u in updates][:40]
            rec["changes_at"] = now
        elif old:
            rec["last_changes"] = old.get("last_changes", [])
            rec["changes_at"] = old.get("changes_at")
        installs[:] = [r for r in installs if r["id"] != iid] + [rec]
        mu = CFG.get("mod_updates")
        if isinstance(mu, dict):
            mu["items"] = [u for u in mu.get("items", []) if u.get("instance") != iid]
        # watch what isn't out yet; stop watching what is
        watch = CFG.setdefault("watch", {})
        for it in items:
            if not it.get("favorite") or it["source"] != "modrinth":
                continue
            wk = f"{it['key']}|{ctx['gv']}|{ctx['loader']}"
            if it["status"] == "not_ready":
                watch[wk] = {"key": it["key"], "id": it["id"], "kind": it.get("kind", "mod"), "name": it["name"],
                             "icon": it.get("icon", ""), "url": it.get("url", ""), "version": ctx["gv"],
                             "loader": ctx["loader"], "since": watch.get(wk, {}).get("since", now)}
            else:
                watch.pop(wk, None)
                CFG["caught_up"] = [c for c in CFG.get("caught_up", [])
                                    if not (c["key"] == it["key"] and c["version"] == ctx["gv"])]
        save_config(CFG)
    return iid


def install_request(rec):
    return {"version": rec["version"], "loader": rec["loader"], "launcher": rec["launcher"],
            "name": rec["name"], "folder": rec.get("folder"), "loadout": rec.get("loadout"),
            "skip": rec.get("disabled") or []}


def update_instance_job(job, iid):
    with CFG_LOCK:
        rec = next((r for r in CFG.get("installs", []) if r["id"] == iid), None)
    if not rec:
        raise UserError("ModHub doesn't know that instance any more.")
    if not rec["export"] and rec.get("path") and not Path(rec["path"]).parent.exists():
        raise UserError(f"{rec['name']}'s folder is gone. Remove it from the list, or install it again.")
    res = install_job(job, install_request(rec), remember=False)
    return {**res, "instance": rec["name"]}


def check_instance_job(job, iid):
    with CFG_LOCK:
        rec = next((r for r in CFG.get("installs", []) if r["id"] == iid), None)
    if not rec or rec["export"] or not rec.get("path"):
        raise UserError("ModHub can only check instances it installed into a folder.")
    folder = Path(rec["path"])
    if not folder.is_dir():
        raise UserError(f"{rec['name']}'s mods folder is gone.")
    problems = check_and_fix(job, folder, rec["version"], rec["loader"], managed=True)
    _set_checked(iid, _folder_sig(folder))
    return {"problems": problems, "install_id": iid, "instance": rec["name"]}


def turn_off_mod(iid, file):
    """Turn a mod off in one instance (renamed to .disabled, which the game skips) and stop re-adding it."""
    with CFG_LOCK:
        rec = next((r for r in CFG.get("installs", []) if r["id"] == iid), None)
    if not rec or not rec.get("path"):
        raise UserError("ModHub can't change that instance.")
    folder = Path(rec["path"]).resolve()
    target = (folder / Path(file).name).resolve()
    if target.parent != folder or not target.exists() or target.suffix.lower() != ".jar":
        raise UserError("That mod isn't in this instance any more.")
    try:
        manifest = json.loads((folder / MANIFEST_NAME).read_text("utf-8"))
    except Exception:
        manifest = {}
    key = next((k for k, v in manifest.items() if v == target.name), None)
    os.replace(target, target.with_name(target.name + ".disabled"))
    with CFG_LOCK:
        for r in CFG.get("installs", []):
            if r["id"] == iid and key and key not in r.setdefault("disabled", []):
                r["disabled"].append(key)
        save_config(CFG)
    return {"ok": True, "file": target.name}


def update_all_job(job):
    with CFG_LOCK:
        recs = [r for r in CFG.get("installs", []) if not r["export"]]
    if not recs:
        raise UserError("There's nothing to update yet. Instances appear here after you install.")
    summary = []
    for n, rec in enumerate(recs, 1):
        job.log(f"--- {rec['name']} ({n} of {len(recs)})")
        before = len(job.changes)
        try:
            res = install_job(job, install_request(rec), remember=False)
            summary.append({"name": rec["name"], "changes": job.changes[before:], "install_id": rec["id"],
                            "problems": res.get("problems") or [], "updates": res.get("updates") or []})
        except UserError as e:
            summary.append({"name": rec["name"], "error": str(e)})
        job.progress = n / len(recs)
    return {"summary": summary}


WATCH_SECONDS = 3 * 60 * 60


def watch_loaders(kind, loader):
    return {"resourcepack": ["minecraft"], "shader": ["iris", "optifine", "canvas"]}.get(kind) or search_loaders(loader)


def check_watched():
    """See whether any mod that wasn't out yet has caught up."""
    with CFG_LOCK:
        watching = dict(CFG.get("watch") or {})
    found = []
    for wk, w in watching.items():
        try:
            v = mr_latest_for(w["id"], watch_loaders(w["kind"], w["loader"]), w["version"])
        except Exception:
            continue
        if v:
            found.append((wk, {**w, "at": now_iso(), "release": v.get("version_number", "")}))
    if found:
        with CFG_LOCK:
            for wk, c in found:
                CFG["watch"].pop(wk, None)
                CFG["caught_up"] = [x for x in CFG.get("caught_up", [])
                                    if not (x["key"] == c["key"] and x["version"] == c["version"])] + [c]
            save_config(CFG)
        for _, c in found:
            print(f"{c['name']} is now out for Minecraft {c['version']}")
    return [c for _, c in found]


def watch_loop():
    time.sleep(90)
    while True:
        try:
            check_watched()
        except Exception:
            traceback.print_exc()
        time.sleep(WATCH_SECONDS)


def apply_caught_up_job(job, key, version):
    """Add a mod that just came out to every instance of that version whose loadout has it."""
    with CFG_LOCK:
        c = next((x for x in CFG.get("caught_up", []) if x["key"] == key and x["version"] == version), None)
        recs = [r for r in CFG.get("installs", [])
                if r["version"] == version and not r["export"]
                and (c is None or r["loader"] == c.get("loader", r["loader"]))
                and any(f"{f['source']}:{f['id']}" == key for f in CFG["loadouts"].get(r.get("loadout"), {}).get("favorites", []))]
    if not recs:
        raise UserError("None of your instances for that version use this mod. Install for it from the Install page.")
    done = []
    for rec in recs:
        job.log(f"--- {rec['name']}")
        install_job(job, install_request(rec), remember=False)
        done.append(rec["name"])
    with CFG_LOCK:
        CFG["caught_up"] = [x for x in CFG.get("caught_up", []) if not (x["key"] == key and x["version"] == version)]
        save_config(CFG)
    return {"instances": done, "changes": job.changes}


def loadouts_view(cfg):
    return [{"id": k, "name": v["name"], "count": len(v["favorites"])} for k, v in cfg["loadouts"].items()]


def import_job(job, folder):
    p = Path(os.path.expandvars(os.path.expanduser((folder or "").strip().strip('"'))))
    if not p.is_dir():
        raise UserError(f"Folder not found: {p}")
    jars = sorted(x for x in p.iterdir() if x.suffix.lower() == ".jar")
    packs_dir = p.parent / "resourcepacks" if p.name.lower() == "mods" else p / "resourcepacks"
    packs = sorted(x for x in packs_dir.iterdir() if x.suffix.lower() == ".zip") if packs_dir.is_dir() else []
    shaders_dir = p.parent / "shaderpacks" if p.name.lower() == "mods" else p / "shaderpacks"
    shaders = sorted(x for x in shaders_dir.iterdir() if x.suffix.lower() == ".zip") if shaders_dir.is_dir() else []
    if p.name.lower() == "resourcepacks":
        packs, jars, shaders = sorted(x for x in p.iterdir() if x.suffix.lower() == ".zip"), [], []
    if p.name.lower() == "shaderpacks":
        shaders, jars, packs = sorted(x for x in p.iterdir() if x.suffix.lower() == ".zip"), [], []
    if not jars and not packs and not shaders:
        raise UserError("No mods (.jar), resource packs or shaders (.zip) in that folder.")
    job.log(f"Reading {len(jars)} mods, {len(packs)} resource packs and {len(shaders)} shaders...")
    files = jars + packs + shaders
    hashes = {sha1_of(f): f for f in files}
    job.progress = 0.4
    cur = {}
    for c in chunks(list(hashes), 100):
        cur.update(http_json("POST", f"{MODRINTH}/version_files", {"hashes": c, "algorithm": "sha1"}) or {})
    projects = mr_projects(sorted({v["project_id"] for v in cur.values()})) if cur else {}
    found = [mr_fav(pr) for pr in projects.values()]
    unknown = [f for h, f in hashes.items() if h not in cur]
    job.progress = 0.8
    loader = guess_loader(jars)
    with CFG_LOCK:
        have = {(f["source"], str(f["id"])) for f in CFG["favorites"]}
        new = [f for f in found if (f["source"], str(f["id"])) not in have]
        for f in new:
            CFG["favorites"].append({k: f.get(k) for k in ("source", "id", "slug", "name", "icon", "desc", "url", "kind")})
        if loader:
            CFG["loader"] = loader
            CFG.setdefault("last", {})["loader"] = loader
        save_config(CFG)
    job.log(f"Added {len(new)} to your library.")
    return {"added": [f["name"] for f in new], "already": len(found) - len(new), "loader": loader,
            "unknown": [{"name": f.name, "path": str(f), "guess": guess_file_version(f)} for f in unknown],
            "folder_version": guess_folder_version(p)}


# =========================================================================== #
# Your own files (for example mods and resource packs downloaded from CurseForge)
# =========================================================================== #
MC_VERSION_RE = re.compile(r"(?<![\d.])(1\.\d{1,2}(?:\.\d{1,2})?|2\d\.\d{1,2}(?:\.\d{1,2})?)(?![\d])")


def _known_versions():
    return [v["v"] for v in (VERSIONS_CACHE.get("list") or [])]


def _pick_version(cands):
    known = _known_versions()
    cands = [c for c in cands if c]
    for c in cands:
        if not known or c in known:
            return c
    return cands[0] if cands else None


def read_file_info(path: Path, display_name=None):
    """Name, kind, in-game id, icon and Minecraft version, read from inside a .jar or .zip."""
    shown = Path(display_name or path.name)
    info = {"name": shown.stem, "kind": "mod" if path.suffix.lower() == ".jar" else "resourcepack",
            "mod_ids": [], "icon": "", "version": None}
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            icon_path, cands = None, []
            if path.suffix.lower() == ".zip" and any(re.search(r"(^|/)shaders/[^/]+\.(fsh|vsh|glsl|csh|gsh|properties)$", n) for n in names):
                info["kind"] = "shader"
            elif "pack.mcmeta" in names and path.suffix.lower() == ".zip":
                info["kind"] = "resourcepack"
                icon_path = "pack.png" if "pack.png" in names else None
                try:
                    desc = json.loads(zread(z, "pack.mcmeta").decode("utf-8", "replace")).get("pack", {}).get("description")
                    if isinstance(desc, str) and desc.strip() and len(desc) < 80:
                        info["desc"] = re.sub(r"§.", "", desc)
                except Exception:
                    pass
            if "fabric.mod.json" in names or "quilt.mod.json" in names:
                meta_name = "quilt.mod.json" if "quilt.mod.json" in names else "fabric.mod.json"
                try:
                    meta = json.loads(zread(z, meta_name).decode("utf-8", "replace"), strict=False)
                    if meta_name == "quilt.mod.json":
                        ql = meta.get("quilt_loader", {})
                        info["mod_ids"] = [ql.get("id")]
                        md = ql.get("metadata", {})
                        info["name"] = md.get("name") or info["name"]
                        icon = md.get("icon")
                        deps = ql.get("depends", [])
                        for d in deps if isinstance(deps, list) else []:
                            if isinstance(d, dict) and d.get("id") == "minecraft":
                                cands += MC_VERSION_RE.findall(json.dumps(d.get("versions", "")))
                    else:
                        info["mod_ids"] = [meta.get("id")]
                        info["name"] = meta.get("name") or info["name"]
                        icon = meta.get("icon")
                        cands += MC_VERSION_RE.findall(json.dumps((meta.get("depends") or {}).get("minecraft", "")))
                    if isinstance(icon, dict) and icon:
                        icon = icon[sorted(icon, key=lambda k: int(k) if str(k).isdigit() else 0)[-1]]
                    icon_path = icon if isinstance(icon, str) else icon_path
                except Exception:
                    pass
            for toml in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
                if toml in names:
                    text = zread(z, toml).decode("utf-8", "replace")
                    info["mod_ids"] = re.findall(r'^\s*modId\s*=\s*"([^"]+)"', text, re.M)[:1] or info["mod_ids"]
                    m = re.search(r'^\s*displayName\s*=\s*"([^"]+)"', text, re.M)
                    if m:
                        info["name"] = m.group(1)
                    m = re.search(r'^\s*logoFile\s*=\s*"([^"]+)"', text, re.M)
                    if m:
                        icon_path = m.group(1)
                    m = re.search(r'modId\s*=\s*"minecraft"[^\[]*?versionRange\s*=\s*"([^"]+)"', text, re.S)
                    if m:
                        cands += MC_VERSION_RE.findall(m.group(1))
                    break
            if icon_path and icon_path.lstrip("/") in names:
                data = zread(z, icon_path.lstrip("/"))
                if len(data) < 150_000 and data[:8] == b"\x89PNG\r\n\x1a\n":
                    import base64
                    info["icon"] = "data:image/png;base64," + base64.b64encode(data).decode()
            # the file name usually says the version too, e.g. jei-1.21.1-forge-19.jar
            info["version"] = _pick_version(MC_VERSION_RE.findall(shown.name) + cands)
    except (zipfile.BadZipFile, OSError):
        raise UserError(f"{shown.name} isn't a valid mod, resource pack or shader file.")
    info["mod_ids"] = [m for m in info["mod_ids"] if m]
    return info


def guess_file_version(path: Path):
    try:
        return read_file_info(path).get("version")
    except UserError:
        return None


def guess_folder_version(folder: Path):
    """The Minecraft version of the instance a mods folder belongs to, when the launcher says so."""
    inst = folder.parent
    for up in (inst, inst.parent):
        pack = up / "mmc-pack.json"  # Prism
        if pack.exists():
            try:
                for c in json.loads(pack.read_text("utf-8")).get("components", []):
                    if c.get("uid") == "net.minecraft":
                        return c.get("version")
            except Exception:
                pass
        prof = up / "profile.json"  # Modrinth App
        if prof.exists():
            try:
                d = json.loads(prof.read_text("utf-8"))
                return d.get("game_version") or (d.get("metadata") or {}).get("game_version")
            except Exception:
                pass
    m = MC_VERSION_RE.findall(str(folder))
    return m[-1] if m else None


def local_file_for(fav, gv):
    files = fav.get("files") or []
    exact = [f for f in files if f.get("version") == gv]
    if exact:
        return exact[-1]
    anyv = [f for f in files if f.get("version") == "any"]
    return anyv[-1] if anyv else None


def add_local_file(src: Path, filename: str, version=None, item_id=None, explicit_version=False):
    """Keep a copy of a file you added and put it in your library."""
    info = read_file_info(src, filename)
    if info["kind"] in ("resourcepack", "shader") and not explicit_version:
        version = "any"  # packs and shaders usually work across versions; you can still pin one
    version = version or info["version"] or ("any" if info["kind"] in ("resourcepack", "shader") else None)
    with CFG_LOCK:
        favs = CFG["favorites"]
        item = next((f for f in favs if f.get("source") == "local" and f["id"] == item_id), None) if item_id else None
        if not item and info["mod_ids"]:
            item = next((f for f in favs if f.get("source") == "local" and
                         set(f.get("mod_ids") or []) & set(info["mod_ids"])), None)
        if not item:
            item = next((f for f in favs if f.get("source") == "local" and f.get("from_curseforge")
                         and f["name"].strip().lower() == info["name"].strip().lower()), None)
        if not item:
            item = {"source": "local", "id": uuid.uuid4().hex[:12], "name": info["name"], "icon": info["icon"],
                    "desc": info.get("desc", ""), "url": "", "kind": info["kind"], "files": [],
                    "mod_ids": info["mod_ids"]}
            favs.append(item)
        item.setdefault("files", [])
        if info["icon"] and not item.get("icon", "").startswith(("data:", "https:")):
            item["icon"] = info["icon"]
        item["mod_ids"] = item.get("mod_ids") or info["mod_ids"]
        folder = LOCAL_DIR / item["id"]
        folder.mkdir(parents=True, exist_ok=True)
        safe = safe_name(Path(filename).name)
        if not safe.lower().endswith((".jar", ".zip")):
            safe += src.suffix
        shutil.copy2(src, folder / safe)
        item["files"] = [f for f in item["files"] if f["file"] != safe]
        item["files"].append({"file": safe, "version": version or "unknown", "added": now_iso()})
        save_config(CFG)
        return {"item": item, "file": safe, "version": version, "guessed": bool(info["version"])}


def set_local_version(item_id, file, version):
    with CFG_LOCK:
        item = next((f for f in CFG["favorites"] if f.get("source") == "local" and f["id"] == item_id), None)
        if not item:
            raise UserError("That item isn't in your library any more.")
        for f in item.get("files", []):
            if f["file"] == file:
                f["version"] = (version or "").strip() or "unknown"
        save_config(CFG)
        return item


def remove_local_file(item_id, file):
    with CFG_LOCK:
        item = next((f for f in CFG["favorites"] if f.get("source") == "local" and f["id"] == item_id), None)
        if not item:
            raise UserError("That item isn't in your library any more.")
        item["files"] = [f for f in item.get("files", []) if f["file"] != file]
        try:
            (LOCAL_DIR / item_id / file).unlink()
        except OSError:
            pass
        save_config(CFG)
        return item


# =========================================================================== #
# Making things easy: find existing mods folders, native folder pickers
# =========================================================================== #
def guess_loader(jars):
    from collections import Counter
    votes = Counter()
    for j in jars:
        try:
            with zipfile.ZipFile(j) as z:
                names = set(z.namelist())
        except Exception:
            continue
        if "quilt.mod.json" in names:
            votes["quilt"] += 1
        elif "fabric.mod.json" in names:
            votes["fabric"] += 1
        elif "META-INF/neoforge.mods.toml" in names:
            votes["neoforge"] += 1
        elif "META-INF/mods.toml" in names:
            votes["forge"] += 1
    if not votes:
        return None
    if votes["quilt"] and votes["quilt"] + votes["fabric"] >= max(votes.values()):
        return "quilt"
    return votes.most_common(1)[0][0]


def _jar_count(p: Path):
    try:
        return sum(1 for x in p.iterdir() if x.suffix.lower() == ".jar")
    except OSError:
        return 0


def find_mod_folders(cfg):
    """Mods folders your launchers already have, so you can import with one click."""
    found = []

    def add(name, launcher, path):
        path = Path(path)
        n = _jar_count(path) if path.is_dir() else 0
        if n:
            found.append({"name": name, "launcher": launcher, "path": str(path), "count": n,
                          "modified": path.stat().st_mtime})

    mc = launcher_path(cfg, "official")
    add("Default (.minecraft)", "Minecraft Launcher", mc / "mods")
    for d in sorted((mc / "modhub-instances").glob("*")) if (mc / "modhub-instances").is_dir() else []:
        add(d.name, "Minecraft Launcher", d / "mods")
    try:
        prism = prism_instances_dir(cfg)
    except UserError:
        prism = None
    if prism and prism.is_dir():
        for inst in sorted(prism.iterdir()):
            name = inst.name
            cfgf = inst / "instance.cfg"
            if cfgf.exists():
                m = re.search(r"^name=(.+)$", cfgf.read_text("utf-8", "replace"), re.M)
                name = m.group(1).strip() if m else name
            for sub in (".minecraft", "minecraft"):
                if (inst / sub / "mods").is_dir():
                    add(name, "Prism Launcher", inst / sub / "mods")
                    break
    mra = launcher_path(cfg, "modrinth_app") / "profiles"
    if mra.is_dir():
        for prof in sorted(mra.iterdir()):
            add(prof.name, "Modrinth App", prof / "mods")
    cfa = launcher_path(cfg, "curseforge_app") / "Instances"
    if cfa.is_dir():
        for inst in sorted(cfa.iterdir()):
            add(inst.name, "CurseForge App", inst / "mods")
    lunar = Path.home() / ".lunarclient" / "profiles"
    if lunar.is_dir():
        for d1 in (x for x in lunar.iterdir() if x.is_dir()):
            for d2 in [d1, *(x for x in d1.iterdir() if x.is_dir())]:
                if (d2 / "mods").is_dir():
                    add(" ".join(d2.relative_to(lunar).parts), "Lunar Client", d2 / "mods")
    found.sort(key=lambda f: f["modified"], reverse=True)
    return found[:30]


def pick_path(kind="folder", title="Choose a folder", start=""):
    """Show the computer's own folder/file picker. Returns the chosen path, or None if cancelled."""
    system = platform.system()
    start = start if start and Path(start).exists() else ""
    if system == "Windows":
        if kind == "folder":
            ps = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; Add-Type -AssemblyName System.Windows.Forms; "
                  "$f = New-Object System.Windows.Forms.FolderBrowserDialog; $f.Description = $env:MH_TITLE; "
                  "$f.ShowNewFolderButton = $true; if ($env:MH_START) { $f.SelectedPath = $env:MH_START }; "
                  "$o = New-Object System.Windows.Forms.Form -Property @{TopMost=$true}; "
                  "if ($f.ShowDialog($o) -eq 'OK') { [Console]::Out.Write($f.SelectedPath) }")
        else:
            ps = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; Add-Type -AssemblyName System.Windows.Forms; "
                  "$f = New-Object System.Windows.Forms.OpenFileDialog; $f.Title = $env:MH_TITLE; "
                  "$f.Filter = $env:MH_FILTER; if ($env:MH_START) { $f.InitialDirectory = $env:MH_START }; "
                  "$o = New-Object System.Windows.Forms.Form -Property @{TopMost=$true}; "
                  "if ($f.ShowDialog($o) -eq 'OK') { [Console]::Out.Write($f.FileName) }")
        r = subprocess.run(["powershell", "-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           env={**os.environ, "MH_TITLE": title, "MH_START": start,
                                "MH_FILTER": "ModHub (modhub*.py)|modhub*.py" if kind == "py" else "Mod files (*.jar)|*.jar"},
                           capture_output=True,
                           creationflags=0x08000000, timeout=1800)
        out = r.stdout.decode("utf-8", "replace").strip()
        return out or None
    if system == "Darwin":
        what = "folder" if kind == "folder" else ('file of type {"py", "public.python-script"}' if kind == "py"
                                                      else 'file of type {"jar", "public.data"}')
        loc = f' default location (POSIX file "{start}")' if start else ""
        safe_title = title.replace('"', "'")
        r = subprocess.run(["osascript", "-e", f'POSIX path of (choose {what} with prompt "{safe_title}"{loc})'],
                           capture_output=True, text=True, timeout=1800)
        return r.stdout.strip() or None
    if shutil.which("zenity"):
        args = ["zenity", "--file-selection", f"--title={title}"]
        args += ["--directory"] if kind == "folder" else (["--file-filter=ModHub | modhub*.py"] if kind == "py"
                                                          else ["--file-filter=Mod files | *.jar"])
        if start:
            args.append(f"--filename={start.rstrip('/')}/")
        r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
        return r.stdout.strip() or None
    if shutil.which("kdialog"):
        args = ["kdialog", "--title", title]
        args += ["--getexistingdirectory", start or str(Path.home())] if kind == "folder" \
            else ["--getopenfilename", start or str(Path.home()), "*.py" if kind == "py" else "*.jar"]
        r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
        return r.stdout.strip() or None
    raise UserError("Couldn't open a folder picker on this computer. Paste the path into the box instead.")


PICK_LOCK = threading.Lock()


# =========================================================================== #
# Porting a mod with Claude Code
# =========================================================================== #
def find_port(ports, key, gv, loader):
    for p in ports.values():
        if p.get("key") == key and p.get("version") == gv and p.get("jar") and Path(p["jar"]).exists() \
                and (p.get("loader") == loader or (loader == "quilt" and p.get("loader") == "fabric")):
            return p
    return None


def normalize_repo(url):
    """Turn a project's source link into something `git clone` accepts."""
    if not url:
        return None
    u = urllib.parse.urlparse(url.strip())
    if u.scheme not in ("https", "http") or not u.netloc:
        return None
    parts = [p for p in u.path.split("/") if p]
    host = u.netloc.lower()
    if host in ("github.com", "www.github.com", "codeberg.org", "gitea.com") and len(parts) >= 2:
        name = re.sub(r"\.git$", "", parts[1])
        return "https://" + host.replace("www.", "") + "/" + parts[0] + "/" + name
    if "gitlab" in host:
        path = u.path.split("/-/")[0].rstrip("/")
        return f"https://{host}{path}"
    if host.endswith("sourcehut.org") or host.startswith("git."):
        return url.split("/tree/")[0]
    return None


def fresh_path():
    """The PATH as it is *now*. A program started before you changed PATH keeps the old one,
    so on Windows we re-read it from the registry, and everywhere we add the usual install folders."""
    parts = os.environ.get("PATH", "").split(os.pathsep)
    home = Path.home()
    if platform.system() == "Windows":
        try:
            import winreg
            for root, sub in ((winreg.HKEY_CURRENT_USER, "Environment"),
                              (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
                try:
                    with winreg.OpenKey(root, sub) as k:
                        val, _ = winreg.QueryValueEx(k, "Path")
                        parts += os.path.expandvars(val).split(";")
                except OSError:
                    pass
        except ImportError:
            pass
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        parts += [str(home / ".local" / "bin"), str(appdata / "npm"), str(local / "Microsoft" / "WinGet" / "Links"),
                  r"C:\Program Files\Git\cmd", str(local / "Programs" / "Git" / "cmd")]
    else:
        parts += [str(home / ".local" / "bin"), str(home / ".claude" / "local"), str(home / ".npm-global" / "bin"),
                  "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]
    seen, out = set(), []
    for x in parts:
        x = x.strip().strip('"')
        if x and x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
    return os.pathsep.join(out)


def find_tool(name):
    return shutil.which(name, path=fresh_path())


def tool_status():
    return {"git": bool(find_tool("git")), "claude": bool(find_tool("claude")), "java": bool(find_tool("java"))}


def port_info(key, gv, loader):
    source, pid = key.split(":", 1)
    info = {"key": key, "version": gv, "loader": loader, "tools": tool_status()}
    if source != "modrinth":
        raise UserError("Porting works for mods from Modrinth. For your own files, look for a newer file instead.")
    p = http_json("GET", f"{MODRINTH}/project/{pid}")
    if not p:
        raise UserError("Couldn't find that mod on Modrinth.")
    lic = p.get("license") or {}
    gvs = [g for g in p.get("game_versions") or [] if re.match(r"^\d+(\.\d+)+$", g)]
    info.update(name=p.get("title"), slug=p.get("slug"), url=mr_fav(p)["url"], icon=p.get("icon_url") or "",
                source_url=p.get("source_url") or "", license=lic.get("name") or lic.get("id") or "Unknown",
                license_id=(lic.get("id") or "").lower(), latest=gvs[-1] if gvs else "")
    info["repo"] = normalize_repo(info["source_url"])
    info["all_rights_reserved"] = "all-rights-reserved" in info["license_id"] or info["license_id"] == "arr"
    return info


def port_task_text(info):
    loader, gv = info["loader"], info["version"]
    docs = {"fabric": "https://fabricmc.net/develop/", "quilt": "https://quiltmc.org/en/usage/latest-versions/",
            "forge": "https://files.minecraftforge.net/", "neoforge": "https://projects.neoforged.net/neoforged/neoforge"}[loader]
    return f"""# Port task from ModHub

Port **{info['name']}** to Minecraft **{gv}** using the **{loader}** loader, so the person who started this
can use it in their own modpack.

- Mod page: {info['url']}
- Source code: {info['repo']}
- License: {info['license']}
- Newest Minecraft version it officially supports: {info.get('latest') or 'unknown'}

## Steps
1. Get to know the repo: the Gradle build files, `gradle.properties`, and the mod metadata
   (`fabric.mod.json`, `quilt.mod.json`, `META-INF/mods.toml` or `META-INF/neoforge.mods.toml`).
   Run `git branch -a`. If a branch is closer to {gv} or {loader} than the default one, start from it
   (the clone is shallow, so run `git fetch --unshallow` first if you need history or other branches).
2. Look up the right versions for Minecraft {gv}: the {loader} loader, mappings and API ({docs}).
   Update the build files and the Minecraft version range in the mod metadata.
3. Build with the Gradle wrapper (`./gradlew build`, or `gradlew.bat build` on Windows). Fix compile errors
   one at a time with the smallest change that works, in the existing code style. When an API changed,
   port to the new API rather than deleting the feature.
4. If a feature really can't be ported, disable just that part and write it down in `PORT_NOTES.md`.
5. When the build succeeds, copy the finished mod jar (not the `-sources` or `-dev` jar) into a folder
   named `{PORT_OUTPUT}` at the root of this repo. ModHub watches that folder and picks it up automatically.
6. Finish `PORT_NOTES.md`: what you changed, what you couldn't test, and anything you disabled.

## Rules
- This is for personal use only. Don't push, publish or upload anything. Don't change the license, credits or mod id.
- Only change files inside this folder.
- If the port turns out to be huge (for example, the mod depends on systems the game rewrote), stop,
  explain why in `PORT_NOTES.md`, and say so instead of forcing it.
- If a tool is missing (for example, the JDK version the build needs), say exactly what to install and where to get it.
"""


def launch_claude(folder: Path):
    """Open a terminal window running Claude Code in `folder`. Returns the command, for showing if it fails."""
    import shlex
    system = platform.system()
    claude = find_tool("claude") or "claude"
    env = {**os.environ, "PATH": fresh_path()}
    shown = f'cd "{folder}" && "{claude}" "{CLAUDE_PROMPT}"'
    try:
        if system == "Windows":
            CREATE_NEW_CONSOLE = 0x00000010
            if claude.lower().endswith((".cmd", ".bat")):
                cmd = ["cmd", "/c", claude, CLAUDE_PROMPT]
            else:
                cmd = [claude, CLAUDE_PROMPT]
            subprocess.Popen(cmd, cwd=str(folder), env=env, creationflags=CREATE_NEW_CONSOLE)
            return {"launched": True, "command": shown}
        inner = (f"export PATH={shlex.quote(env['PATH'])}; cd {shlex.quote(str(folder))} && "
                 f"{shlex.quote(claude)} {shlex.quote(CLAUDE_PROMPT)}")
        if system == "Darwin":
            esc = inner.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.Popen(["osascript", "-e", f'tell application "Terminal" to do script "{esc}"',
                              "-e", 'tell application "Terminal" to activate'])
            return {"launched": True, "command": shown}
        for term, args in (("x-terminal-emulator", ["-e"]), ("gnome-terminal", ["--"]), ("konsole", ["-e"]),
                           ("xfce4-terminal", ["-x"]), ("kitty", []), ("alacritty", ["-e"]), ("xterm", ["-e"])):
            if shutil.which(term):
                subprocess.Popen([term, *args, "bash", "-lc", inner + "; exec bash"])
                return {"launched": True, "command": shown}
    except Exception:
        traceback.print_exc()
    return {"launched": False, "command": shown}


def port_start_job(job, key, gv, loader):
    tools = tool_status()
    if not tools["git"]:
        raise UserError("Porting needs Git. Install it from https://git-scm.com/downloads, then try again.")
    if not tools["claude"]:
        raise UserError("Porting needs Claude Code. Install it from https://claude.com/claude-code, then try again.")
    info = port_info(key, gv, loader)
    if not info["repo"]:
        raise UserError(f"{info['name']} doesn't link to public source code, so there's nothing to port from.")
    pid = f"{safe_name(info['slug'] or key.replace(':', '-'))}-{gv}-{loader}".replace(" ", "-")
    folder = PORTS_DIR / pid
    PORTS_DIR.mkdir(parents=True, exist_ok=True)
    job.progress = 0.2
    if not (folder / ".git").exists():
        job.log(f"Downloading the source of {info['name']} from {info['repo']}...")
        r = subprocess.run([find_tool("git") or "git", "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
                            "clone", "--depth", "1", "--", info["repo"], str(folder)],
                           capture_output=True, text=True, timeout=600,
                           creationflags=0x08000000 if platform.system() == "Windows" else 0)
        if r.returncode != 0:
            raise UserError(f"Couldn't download the source code: {(r.stderr or r.stdout).strip()[-300:]}")
    else:
        job.log("Source already downloaded, reusing it.")
    (folder / PORT_TASK_FILE).write_text(port_task_text(info), "utf-8")
    job.progress = 0.8
    with CFG_LOCK:
        CFG.setdefault("ports", {})[pid] = {
            "id": pid, "key": key, "name": info["name"], "icon": info.get("icon", ""), "url": info["url"],
            "version": gv, "loader": loader, "dir": str(folder), "repo": info["repo"],
            "license": info["license"], "created": now_iso(), "jar": None}
        save_config(CFG)
    launch = launch_claude(folder)
    job.log("Opened Claude Code in a new terminal window." if launch["launched"]
            else "Couldn't open a terminal automatically. Run the command shown in ModHub.")
    OPENABLE.add(str(folder))
    return {"id": pid, **launch}


def ports_view():
    """List ports, picking up any jar Claude has finished since we last looked."""
    with CFG_LOCK:
        changed = False
        out = []
        for p in (CFG.get("ports") or {}).values():
            folder = Path(p["dir"])
            if folder.exists():
                OPENABLE.add(str(folder))
            jars = sorted((folder / PORT_OUTPUT).glob("*.jar"), key=lambda j: j.stat().st_mtime) if folder.exists() else []
            jars = [j for j in jars if not re.search(r"-(sources|dev|javadoc)\.jar$", j.name)]
            jar = str(jars[-1]) if jars else (p.get("jar") if p.get("jar") and Path(p["jar"]).exists() else None)
            if jar != p.get("jar"):
                p["jar"] = jar
                changed = True
            notes = folder / "PORT_NOTES.md"
            status = "built" if jar else ("missing" if not folder.exists() else "working")
            out.append({**p, "status": status, "notes": notes.read_text("utf-8", "replace")[:4000] if notes.exists() else ""})
        if changed:
            save_config(CFG)
    out.sort(key=lambda p: p.get("created", ""), reverse=True)
    return {"ports": out, "tools": tool_status(), "command_prompt": CLAUDE_PROMPT}


def port_add_jar(body):
    """Use a jar you built some other way (for example with Claude in a chat) as a port."""
    key, gv, loader, path = body.get("key"), (body.get("version") or "").strip(), body.get("loader"), body.get("path") or ""
    src = Path(os.path.expandvars(os.path.expanduser(path.strip().strip('"'))))
    if not key or not gv or loader not in LOADERS:
        raise UserError("Missing mod, version or loader.")
    if not src.is_file() or src.suffix.lower() != ".jar":
        raise UserError(f"That isn't a .jar file: {src}")
    pid = f"{key.replace(':', '-')}-{gv}-{loader}-manual"
    folder = PORTS_DIR / pid / PORT_OUTPUT
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.jar"):
        old.unlink()
    shutil.copy2(src, folder / src.name)
    with CFG_LOCK:
        CFG.setdefault("ports", {})[pid] = {
            "id": pid, "key": key, "name": body.get("name") or key, "icon": body.get("icon", ""),
            "url": body.get("url", ""), "version": gv, "loader": loader, "dir": str(folder.parent),
            "repo": "", "license": "", "created": now_iso(), "jar": str(folder / src.name)}
        save_config(CFG)
    return ports_view()


def port_remove(pid):
    with CFG_LOCK:
        p = (CFG.get("ports") or {}).pop(pid, None)
        save_config(CFG)
    if p:
        folder = Path(p["dir"]).resolve()
        if PORTS_DIR.resolve() in folder.parents:
            shutil.rmtree(folder, ignore_errors=True)
    return ports_view()


# =========================================================================== #
# Updating ModHub itself
# =========================================================================== #
_VERSION_RE = re.compile(r'^APP_VERSION\s*=\s*"([0-9][0-9.]*)"', re.M)
UPDATE_CACHE = {"at": 0, "found": None}


def version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0")) or (0,)


def read_update_file(path: Path):
    """Return (version, text) if this file is a valid ModHub, else None."""
    try:
        if not path.is_file() or path.stat().st_size > 5_000_000:
            return None
        text = path.read_text("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    m = _VERSION_RE.search(text)
    if not m or "ModHub" not in text[:400] or "def main():" not in text:
        return None
    try:
        compile(text, str(path), "exec")
    except SyntaxError:
        return None
    return m.group(1), text


def update_search_dirs():
    """Updates ModHub downloaded from GitHub itself. (It no longer picks up modhub.py files lying in Downloads:
    a website could drop one there. Install from a file is still there when you mean it.)"""
    return [UPDATES_DIR] if UPDATES_DIR.is_dir() else []


THEME_MODES = ("dark", "light", "system")
THEME_ACCENTS = ("crimson", "emerald", "ocean", "violet", "amber", "rose", "sunset", "aurora", "nether", "ender", "cherry", "mint", "lime", "rainbow", "diamond", "owl", "mono", "ghost", "gold", "redstone", "custom")
SECRETS = ("rainbow", "retro", "diamond", "nightowl", "void", "ghost", "golden", "redstone")
DEV_SALT = "06fbacc3e74c6ab2b71ad339b4f2bf6b"  # only a one-way fingerprint of the code lives here, never the code itself
DEV_HASH = "785800f460486ebdec61b52f897a6994a058e8b9e59406edd7b007c0427bb2a6"
THEME_CHOICES = {"bg": ("gradient", "vivid", "glow", "plain", "aurora", "stars", "embers", "pulse"), "font": ("normal", "mono", "pixel"), "dir": ("top", "corner", "side", "bottom"),
                 "radius": ("sharp", "rounded", "round"), "side": ("glass", "solid"),
                 "size": ("90", "100", "110", "120"), "motion": ("fluid", "full", "less", "off")}
THEME_DEFAULTS = {"mode": "dark", "accent": "crimson", "custom": "#d7263d", "bg": "gradient", "dir": "top", "strength": 55,
                  "radius": "rounded", "side": "glass", "size": "100", "motion": "fluid", "font": "normal"}


def theme_of(cfg):
    t = cfg.get("theme") if isinstance(cfg.get("theme"), dict) else {}
    out = dict(THEME_DEFAULTS)
    if t.get("mode") in THEME_MODES:
        out["mode"] = t["mode"]
    if t.get("accent") in THEME_ACCENTS:
        out["accent"] = t["accent"]
    if isinstance(t.get("custom"), str) and re.fullmatch(r"#[0-9a-fA-F]{6}", t["custom"]):
        out["custom"] = t["custom"].lower()
    for k, allowed in THEME_CHOICES.items():
        if str(t.get(k)) in allowed:
            out[k] = str(t[k])
    try:
        out["strength"] = max(10, min(100, int(t.get("strength", out["strength"]))))
    except (TypeError, ValueError):
        pass
    return out


def theme_vars(t):
    """The CSS variables for a theme, so the page opens in the right look with no flash."""
    css = [f"--bgk:{t['strength'] / 100:.2f}", f"--ui-zoom:{int(t['size']) / 100:.2f}"]
    if t["accent"] == "custom":
        h = t["custom"].lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        mix = lambda c, w, k: round(c + (w - c) * k)
        css += [f"--acc:{r} {g} {b}", f"--acc2:{mix(r, 255, .18)} {mix(g, 255, .18)} {mix(b, 255, .18)}",
                f"--acc3:{mix(r, 0, .28)} {mix(g, 0, .28)} {mix(b, 0, .28)}"]
    return ";".join(css)


def page_html():
    with CFG_LOCK:
        t = theme_of(CFG)
    attrs = (f'data-pref="{t["mode"]}" data-accent="{t["accent"]}" data-bg="{t["bg"]}" data-dir="{t["dir"]}" '
             f'data-radius="{t["radius"]}" data-side="{t["side"]}" data-motion="{t["motion"]}" data-font="{t["font"]}" style="{theme_vars(t)}"')
    return PAGE.replace("__TOKEN__", TOKEN).replace('<html lang="en">', f'<html lang="en" {attrs}>', 1)


def changes_in_text(text):
    """Read APP_CHANGES out of another copy of ModHub without running it."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "APP_CHANGES" for t in node.targets):
            try:
                raw = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                return []
            out = []
            for e in raw if isinstance(raw, list) else []:
                if isinstance(e, dict) and isinstance(e.get("version"), str) and isinstance(e.get("notes"), list):
                    out.append({"version": e["version"][:20], "notes": [str(n)[:400] for n in e["notes"][:20]]})
            return out[:50]
    return []


def changes_since(changes, version):
    return [c for c in changes if c["version"][:1].isdigit() and version_tuple(c["version"]) > version_tuple(version)]


def find_update(force=False):
    """Look for a newer modhub.py you downloaded, e.g. 'modhub (3).py' in Downloads."""
    if not force and time.time() - UPDATE_CACHE["at"] < 20:
        return UPDATE_CACHE["found"]
    me = Path(__file__).resolve()
    best = None
    for d in update_search_dirs():
        try:
            cands = [f for f in d.iterdir() if f.suffix.lower() == ".py" and f.name.lower().startswith("modhub")]
        except OSError:
            continue
        for f in cands:
            if f.resolve() == me:
                continue
            got = read_update_file(f)
            if got and version_tuple(got[0]) > version_tuple(APP_VERSION):
                if not best or version_tuple(got[0]) > version_tuple(best["version"]) or \
                        (got[0] == best["version"] and f.stat().st_mtime > Path(best["path"]).stat().st_mtime):
                    best = {"version": got[0], "path": str(f), "where": "online" if d == UPDATES_DIR else d.name}
    if best:
        try:
            best["changes"] = changes_since(changes_in_text(Path(best["path"]).read_text("utf-8")), APP_VERSION)
        except OSError:
            best["changes"] = []
    UPDATE_CACHE.update(at=time.time(), found=best)
    return best


# ---- automatic updates from an online copy (for example a GitHub repo) ----
UPDATE_CHECK_SECONDS = 30 * 60   # we ship often, so look every half hour
UPDATE_NUDGE_SECONDS = 5 * 60   # and when you come back to the window, if it's been a few minutes
UPDATE_WAKE = threading.Event()
UPDATE_LAST = {"t": 0.0}


# Where ModHub gets its updates. Everyone pulls from the official repo unless they chose another.
DEFAULT_UPDATE_SOURCE = os.environ.get("MODHUB_UPDATE_SOURCE", "stefantay25-ux/modhub")


def current_update_source(cfg=None):
    # Always the official repo. (An old setting, or a tampered backup, can't point updates somewhere else.)
    return DEFAULT_UPDATE_SOURCE.strip()


def update_source_url(src):
    """'name/repo', a github.com link, or a direct https link -> the URL of modhub.py."""
    src = (src or "").strip().strip('"')
    if not src:
        return None
    m = re.fullmatch(r"([\w.-]+)/([\w.-]+)", src)
    if m:
        return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/main/modhub.py"
    m = re.match(r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)(?:/(?:blob|tree)/([\w.-]+))?", src)
    if m:
        repo = re.sub(r"\.git$", "", m.group(2))
        return f"https://raw.githubusercontent.com/{m.group(1)}/{repo}/{m.group(3) or 'main'}/modhub.py"
    if src.startswith("https://") or re.match(r"http://(127\.0\.0\.1|localhost)[:/]", src):
        return src
    raise UserError("Use your GitHub repo's name, like yourname/modhub, or a link that starts with https://")


def check_online_update():
    """Download a newer ModHub from your update source, if there is one. It's installed on the next start."""
    UPDATE_LAST["t"] = time.time()
    with CFG_LOCK:
        url = update_source_url(current_update_source())
        if url and dev_on("beta"):  # developer's beta channel: test versions from the beta branch first
            url = url.replace("/main/modhub.py", "/beta/modhub.py")
    if not url:
        return None
    result = {"at": now_iso()}
    try:
        req = urllib.request.Request(url + ("&" if "?" in url else "?") + f"t={int(time.time())}",
                                     headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read(5_000_001)
        if len(data) > 5_000_000:
            raise UserError("the file there is too big to be ModHub")
        UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        tmp = UPDATES_DIR / "incoming.tmp"
        tmp.write_bytes(data)
        got = read_update_file(tmp)
        if not got:
            tmp.unlink()
            raise UserError("the file there isn't a working copy of ModHub")
        if version_tuple(got[0]) > version_tuple(APP_VERSION):
            os.replace(tmp, UPDATES_DIR / f"modhub-{got[0]}.py")
            result.update(status="downloaded", version=got[0])
            print(f"Downloaded ModHub {got[0]}")
        else:
            tmp.unlink()
            result.update(status="up_to_date", version=got[0])
    except urllib.error.HTTPError as e:
        result.update(status="error", message="couldn't find modhub.py there" if e.code == 404 else f"error {e.code}")
    except (urllib.error.URLError, TimeoutError, OSError):
        result.update(status="error", message="couldn't connect. Check your internet")
    except UserError as e:
        result.update(status="error", message=str(e))
    with CFG_LOCK:
        CFG["update_last_check"] = result
        save_config(CFG)
    UPDATE_CACHE.update(at=0)
    return result


def update_watch():
    time.sleep(8)
    while True:
        try:
            check_online_update()
        except Exception:
            traceback.print_exc()
        UPDATE_WAKE.wait(UPDATE_CHECK_SECONDS)
        UPDATE_WAKE.clear()


def staged_update():
    best = None
    for f in UPDATES_DIR.glob("modhub-*.py") if UPDATES_DIR.is_dir() else []:
        got = read_update_file(f)
        if got and version_tuple(got[0]) > version_tuple(APP_VERSION) and \
                (not best or version_tuple(got[0]) > version_tuple(best[0])):
            best = (got[0], f)
    return best


def apply_staged_update_on_start():
    """With automatic updates on, a downloaded update is installed as ModHub starts."""
    if "--window" in sys.argv or "--no-auto-update" in sys.argv:
        return False
    with CFG_LOCK:
        auto = CFG.get("update_auto", True)
    st = staged_update()
    if not auto or not st:
        return False
    try:
        new_version = apply_update(str(st[1]))
    except Exception:
        traceback.print_exc()
        return False
    with CFG_LOCK:
        CFG["just_updated"] = {"from": APP_VERSION, "to": new_version}
        save_config(CFG)
    args = [runner_python(), str(Path(__file__).resolve()), *[a for a in sys.argv[1:] if a != "--after-restart"], "--child"]
    subprocess.Popen(args, close_fds=True, **detached_kwargs())
    return True


def apply_update(path_str, allow_older=False):
    src = Path(os.path.expandvars(os.path.expanduser((path_str or "").strip().strip('"'))))
    got = read_update_file(src)
    if not got:
        raise UserError("That file isn't a working copy of ModHub. Download modhub.py again and try once more.")
    new_version, text = got
    if version_tuple(new_version) < version_tuple(APP_VERSION) and not allow_older:
        raise UserError(f"That file is an older version ({new_version}). You're on {APP_VERSION}.")
    me = Path(__file__).resolve()
    backups = DATA_DIR / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    shutil.copy2(me, backups / f"modhub-{APP_VERSION}.py")
    tmp = me.with_name(me.name + ".new")
    tmp.write_text(text, "utf-8")
    os.replace(tmp, me)
    # tidy the download away so Downloads doesn't fill up with copies
    if src.resolve() != me:
        try:
            shutil.move(str(src), str(backups / f"downloaded-modhub-{new_version}.py"))
        except OSError:
            pass
    UPDATE_CACHE.update(at=0, found=None)
    if version_tuple(new_version) > version_tuple(APP_VERSION):
        with CFG_LOCK:
            CFG["just_updated"] = {"from": APP_VERSION, "to": new_version}
            save_config(CFG)
    print(f"Updated ModHub {APP_VERSION} -> {new_version}")
    return new_version


def undo_update():
    backups = sorted((DATA_DIR / "backups").glob("modhub-*.py"), key=lambda f: f.stat().st_mtime)
    if not backups:
        raise UserError("There's no earlier version to go back to.")
    got = read_update_file(backups[-1])
    if not got:
        raise UserError("The backup is damaged, so ModHub can't go back to it.")
    me = Path(__file__).resolve()
    tmp = me.with_name(me.name + ".new")
    tmp.write_text(got[1], "utf-8")
    os.replace(tmp, me)
    backups[-1].unlink()
    return got[0]


# =========================================================================== #
# Web server
# =========================================================================== #
TOKEN = secrets.token_urlsafe(24)
VERSIONS_CACHE = {"list": None, "fetching": False}
VERSIONS_READY = threading.Event()


def prefetch_versions():
    """Fetch the Minecraft version list in the background so the window never waits on it for long."""
    if VERSIONS_CACHE["fetching"]:
        return
    VERSIONS_CACHE["fetching"] = True
    VERSIONS_READY.clear()  # so anyone waiting gets this fetch's result, not the last one

    def work():
        try:
            tags = http_json("GET", f"{MODRINTH}/tag/game_version", retries=2) or []
            if tags:
                VERSIONS_CACHE["list"] = [{"v": t["version"], "type": t.get("version_type", "release")} for t in tags]
                VERSIONS_CACHE["at"] = time.time()
        except Exception:
            pass  # keep the old list; try again later
        finally:
            VERSIONS_CACHE["fetching"] = False
            VERSIONS_READY.set()
        notice_new_version()
    threading.Thread(target=work, daemon=True).start()


# ---- noticing new Minecraft versions ----
VERSION_REFRESH_SECONDS = 30 * 60
READY_RECHECK_SECONDS = 6 * 60 * 60
VERSIONS_MIN_REFRESH = 60
NEWEST_CHECK = {"running": False}


def newest_release():
    for v in VERSIONS_CACHE.get("list") or []:
        if v["type"] == "release":
            return v["v"]
    return None


def notice_new_version():
    """Remember the newest release; when a newer one shows up, check how many of your mods are ready for it."""
    newest = newest_release()
    if not newest:
        return
    with CFG_LOCK:
        seen = CFG.get("seen_newest")
        if not seen:  # first run: nothing is "new" yet
            CFG["seen_newest"] = newest
            save_config(CFG)
            return
        is_new = version_tuple(newest) > version_tuple(seen)
        chk = CFG.get("newest_check") or {}
        stale = chk.get("version") != newest or time.time() - chk.get("at", 0) > READY_RECHECK_SECONDS
        favs = list(CFG["favorites"])
        loader = (CFG.get("last") or {}).get("loader") or CFG.get("loader") or "fabric"
        ports = dict(CFG.get("ports") or {})
    if is_new and stale and favs and not NEWEST_CHECK["running"]:
        threading.Thread(target=check_newest, args=(newest, favs, loader, ports), daemon=True).start()


def check_newest(gv, favs, loader, ports):
    NEWEST_CHECK["running"] = True
    try:
        items = resolve(Job(), favs, gv, loader, ports)
        mine = [i for i in items if i["favorite"]]
        ready = [i for i in mine if i["status"] == "ready"]
        with CFG_LOCK:
            CFG["newest_check"] = {"version": gv, "at": time.time(), "ready": len(ready), "total": len(mine),
                                   "not_ready": [i["name"] for i in mine if i["status"] != "ready"][:12]}
            save_config(CFG)
    except Exception:
        traceback.print_exc()
    finally:
        NEWEST_CHECK["running"] = False


def version_watch():
    """Look for new Minecraft versions every so often while ModHub is open."""
    while True:
        time.sleep(VERSION_REFRESH_SECONDS)
        prefetch_versions()


def versions_view(refresh=False):
    if refresh and time.time() - VERSIONS_CACHE.get("at", 0) > VERSIONS_MIN_REFRESH:
        prefetch_versions()
        VERSIONS_READY.wait(4)
    with CFG_LOCK:
        seen = CFG.get("seen_newest")
        chk = CFG.get("newest_check")
    newest = newest_release()
    new = newest if newest and seen and version_tuple(newest) > version_tuple(seen) else None
    return {"versions": VERSIONS_CACHE.get("list") or [], "newest": newest, "new_version": new,
            "newest_check": chk if chk and chk.get("version") == new else None, "checking": NEWEST_CHECK["running"]}


def state():
    with CFG_LOCK:
        cfg = json.loads(json.dumps(CFG))
    if VERSIONS_CACHE["list"] is None:
        prefetch_versions()
        VERSIONS_READY.wait(4)
    defaults = {k: str(v) for k, v in default_paths().items()}
    launchers = []
    for lid, L in LAUNCHERS.items():
        found = None
        if L["path"]:
            found = launcher_path(cfg, L["path"]).exists()
        elif lid == "lunar":
            found = (Path.home() / ".lunarclient").exists()
        launchers.append({"id": lid, "name": L["name"], "desc": L["desc"], "found": found,
                          "folder": bool(L.get("folder"))})
    return {"favorites": cfg["favorites"], "loader": cfg.get("loader", "fabric"), "paths": cfg.get("paths", {}), "default_paths": defaults,
            "last": cfg.get("last", {}), "versions": VERSIONS_CACHE["list"] or [], "launchers": launchers,
            "data_dir": str(DATA_DIR), "in_window": APP["proc"] is not None or APP["webview"] is not None,
            "shortcut_done": bool(cfg.get("shortcut_done")), "platform": platform.system(),
            "native": APP["webview"] is not None, "webview_installed": has_webview(),
            "native_broken": native_broken_now(cfg), "version": APP_VERSION, "update": find_update(), "changelog": APP_CHANGES,
            "has_backup": any((DATA_DIR / "backups").glob("modhub-*.py")) if (DATA_DIR / "backups").is_dir() else False,
            "loadouts": loadouts_view(CFG), "active_loadout": cfg.get("active_loadout"),
            "installs": cfg.get("installs", []), "caught_up": cfg.get("caught_up", []),
            "watching": len(cfg.get("watch") or {}), "crashes": cfg.get("crashes", []),
            "update_source": current_update_source(cfg), "update_auto": cfg.get("update_auto", True),
            "update_last_check": cfg.get("update_last_check"), "just_updated": cfg.get("just_updated"),
            "mod_updates": cfg.get("mod_updates"), "live_ping": cfg.get("live_ping"), "dev_mode": bool(cfg.get("dev_mode")), "dev_features": dev_features(cfg) if cfg.get("dev_mode") else {}, "notice": current_notice(cfg), "dev_has_token": bool(cfg.get("dev_github_token")), "pinned": PIN_FILE.exists(), "theme": theme_of(cfg), "secrets": [x for x in cfg.get("secrets", []) if x in SECRETS], "frozen": FROZEN, "os": platform.system(), "app_switch": app_switch_state(),
            "native_prompt_dismissed": bool(cfg.get("native_prompt_dismissed")), **{k: v for k, v in versions_view().items() if k != "versions"}}


def api(path, body):
    if path == "/api/state":
        return state()
    if path == "/api/search":
        qtext = (body.get("q") or "").strip()
        kind = body.get("kind") if body.get("kind") in ("resourcepack", "shader") else "mod"
        try:
            return {"results": mr_search(qtext, body.get("loader") or None, kind=kind), "errors": []}
        except Exception as e:
            return {"results": [], "errors": [f"Modrinth search didn't work: {e}"]}
    if path == "/api/discover":
        kind = body.get("kind") if body.get("kind") in ("resourcepack", "shader") else "mod"
        loader = body.get("loader") if body.get("loader") in LOADERS else "fabric"
        try:
            return discover_feed(kind, (body.get("version") or "").strip(), loader)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise UserError(f"Couldn't reach Modrinth. Check your internet. ({e})")
    if path == "/api/project":
        loader = body.get("loader") if body.get("loader") in LOADERS else "fabric"
        pid = str(body.get("id") or "").strip()
        if not re.fullmatch(r"[\w.-]{1,64}", pid):
            raise UserError("Bad project.")
        try:
            return project_page(pid, (body.get("version") or "").strip(), loader)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise UserError(f"Couldn't reach Modrinth. Check your internet. ({e})")
    if path == "/api/favorites/add":
        m = body.get("mod") or {}
        if m.get("source") != "modrinth" or not m.get("id"):
            raise UserError("Bad mod.")
        with CFG_LOCK:
            if not any(f["source"] == m["source"] and str(f["id"]) == str(m["id"]) for f in CFG["favorites"]):
                entry = {k: m.get(k) for k in ("source", "id", "slug", "name", "icon", "desc", "url", "kind")}
                entry["kind"] = entry.get("kind") or "mod"
                CFG["favorites"].append(entry)
                save_config(CFG)
        return {"favorites": CFG["favorites"]}
    if path == "/api/favorites/remove":
        with CFG_LOCK:
            gone = [f for f in CFG["favorites"] if f["source"] == body.get("source") and str(f["id"]) == str(body.get("id"))]
            CFG["favorites"][:] = [f for f in CFG["favorites"] if f not in gone]
            still_used = {str(f["id"]) for lo in CFG["loadouts"].values() for f in lo["favorites"] if f.get("source") == "local"}
            save_config(CFG)
        for f in gone:
            if f["source"] == "local" and re.fullmatch(r"[\w-]+", str(f["id"])) and str(f["id"]) not in still_used:
                shutil.rmtree(LOCAL_DIR / str(f["id"]), ignore_errors=True)
        return {"favorites": CFG["favorites"]}
    if path == "/api/loadouts/switch":
        with CFG_LOCK:
            if body.get("id") not in CFG["loadouts"]:
                raise UserError("That loadout doesn't exist.")
            CFG["active_loadout"] = body["id"]
            CFG["favorites"] = CFG["loadouts"][body["id"]]["favorites"]
            save_config(CFG)
        return state()
    if path == "/api/loadouts/create":
        name = (body.get("name") or "").strip()[:40]
        if not name:
            raise UserError("Give the loadout a name.")
        with CFG_LOCK:
            if any(v["name"].lower() == name.lower() for v in CFG["loadouts"].values()):
                raise UserError(f"You already have a loadout called {name}.")
            lid = uuid.uuid4().hex[:8]
            favs = json.loads(json.dumps(CFG["favorites"])) if body.get("copy") else []
            CFG["loadouts"][lid] = {"name": name, "favorites": favs}
            CFG["active_loadout"] = lid
            CFG["favorites"] = CFG["loadouts"][lid]["favorites"]
            save_config(CFG)
        return state()
    if path == "/api/loadouts/rename":
        name = (body.get("name") or "").strip()[:40]
        with CFG_LOCK:
            if body.get("id") not in CFG["loadouts"] or not name:
                raise UserError("Give the loadout a name.")
            if any(k != body["id"] and v["name"].lower() == name.lower() for k, v in CFG["loadouts"].items()):
                raise UserError(f"You already have a loadout called {name}.")
            CFG["loadouts"][body["id"]]["name"] = name
            for r in CFG.get("installs", []):
                if r.get("loadout") == body["id"]:
                    r["loadout_name"] = name
            save_config(CFG)
        return state()
    if path == "/api/loadouts/delete":
        with CFG_LOCK:
            lid = body.get("id")
            if lid not in CFG["loadouts"]:
                raise UserError("That loadout doesn't exist.")
            if len(CFG["loadouts"]) == 1:
                raise UserError("You need at least one loadout.")
            gone = CFG["loadouts"].pop(lid)
            if CFG["active_loadout"] == lid:
                CFG["active_loadout"] = next(iter(CFG["loadouts"]))
                CFG["favorites"] = CFG["loadouts"][CFG["active_loadout"]]["favorites"]
            still_used = {str(f["id"]) for lo in CFG["loadouts"].values() for f in lo["favorites"] if f.get("source") == "local"}
            save_config(CFG)
        for f in gone["favorites"]:
            if f.get("source") == "local" and str(f["id"]) not in still_used and re.fullmatch(r"[\w-]+", str(f["id"])):
                shutil.rmtree(LOCAL_DIR / str(f["id"]), ignore_errors=True)
        return state()
    if path == "/api/instances/update":
        return {"job": start_job(update_instance_job, body.get("id"))}
    if path == "/api/instances/check":
        return {"job": start_job(check_instance_job, body.get("id"))}
    if path == "/api/problems/turn_off":
        return turn_off_mod(body.get("id"), body.get("file") or "")
    if path == "/api/instances/update_all":
        return {"job": start_job(update_all_job)}
    if path == "/api/instances/remove":
        with CFG_LOCK:
            CFG["installs"] = [r for r in CFG.get("installs", []) if r["id"] != body.get("id")]
            save_config(CFG)
        return state()
    if path == "/api/watch/check":
        return {"found": check_watched(), **{k: v for k, v in state().items() if k in ("caught_up", "watching")}}
    if path == "/api/backup/save":
        return save_library_backup()
    if path == "/api/perf":
        return {"mods": perf_list(body.get("loader"), (body.get("version") or "").strip() or None)}
    if path == "/api/perf/add":
        added = perf_add(set(body.get("ids") or []))
        return {"added": added, "favorites": CFG["favorites"]}
    if path == "/api/settings_sources":
        with CFG_LOCK:
            cfg = json.loads(json.dumps({k: v for k, v in CFG.items() if k != "favorites"}))
        return {"sources": settings_sources(cfg)}
    if path == "/api/crashes/scan":
        scan_crashes()
        return {"crashes": CFG.get("crashes", [])}
    if path == "/api/crashes/fix":
        c = next((c for c in CFG.get("crashes", []) if c["install_id"] == body.get("id")), None)
        if not c:
            raise UserError("That crash isn't here any more.")
        try:
            text = Path(c["file"]).read_text("utf-8", "replace")[-200000:]
        except OSError:
            text = ""
        return {"job": start_autofix(c["install_id"], text)}
    if path == "/api/crashes/dismiss":
        with CFG_LOCK:
            CFG["crashes"] = [c for c in CFG.get("crashes", []) if c["install_id"] != body.get("id")]
            save_config(CFG)
        return {"crashes": CFG.get("crashes", [])}
    if path == "/api/crashes/excerpt":
        c = next((c for c in CFG.get("crashes", []) if c["install_id"] == body.get("id")), None)
        if not c:
            raise UserError("That crash isn't here any more.")
        return {"text": f"My modded Minecraft ({c['version']}, {LOADER_NAMES_PY.get(c['loader'], c['loader'])}) crashed. "
                        f"Can you tell me why and how to fix it? Here's the crash report:\n\n" + crash_excerpt(c["file"])}
    if path == "/api/caught_up/apply":
        return {"job": start_job(apply_caught_up_job, body.get("key"), body.get("version"))}
    if path == "/api/caught_up/dismiss":
        with CFG_LOCK:
            CFG["caught_up"] = [x for x in CFG.get("caught_up", [])
                                if not (x["key"] == body.get("key") and x["version"] == body.get("version"))]
            save_config(CFG)
        return state()
    if path == "/api/local/version":
        set_local_version(body.get("id"), body.get("file"), body.get("version"))
        return {"favorites": CFG["favorites"]}
    if path == "/api/local/remove_file":
        remove_local_file(body.get("id"), body.get("file"))
        return {"favorites": CFG["favorites"]}
    if path == "/api/local/add_paths":
        added = []
        for path_str in body.get("paths") or []:
            src = Path(path_str)
            if src.is_file() and src.suffix.lower() in (".jar", ".zip"):  # mods, resource packs, shaders
                added.append(add_local_file(src, src.name, body.get("version") or None)["item"]["name"])
        return {"added": added, "favorites": CFG["favorites"]}
    if path == "/api/app_switch":
        if body.get("start"):
            threading.Thread(target=switch_to_app, kwargs={"manual": True}, daemon=True).start()
            time.sleep(0.2)
        return app_switch_state()
    if path == "/api/mods/updates":
        return {"job": start_job(mod_updates_job)}
    if path == "/api/mods/updates/apply":
        ids = body.get("instances")
        return {"job": start_job(apply_mod_updates_job, ids if isinstance(ids, list) else None)}
    if path == "/api/share/code":
        return share_code(body.get("loadout"))
    if path == "/api/share/file":
        return share_save_file(body.get("loadout"))
    if path == "/api/share/mrpack":
        return {"job": start_job(mrpack_job, body.get("loadout"), body.get("version"), body.get("loader"))}
    if path == "/api/share/preview":
        return share_preview_code(str(body.get("code") or "")[:600_000])
    if path == "/api/share/import":
        return share_import(str(body.get("token") or ""), "add" if body.get("mode") == "add" else "new", body.get("name"))
    if path == "/api/live":
        with CFG_LOCK:
            CFG["live_ping"] = bool(body.get("on"))
            save_config(CFG)
        return {"live_ping": CFG["live_ping"]}
    if path == "/api/dev/stats":
        return dev_stats()
    if path == "/api/dev/leave":
        with CFG_LOCK:
            CFG["dev_mode"] = False
            CFG["dev_features"] = {**dev_features(), "beta": False}
            save_config(CFG)
        UPDATE_WAKE.set()
        return {"dev_mode": False}
    if path == "/api/dev/features":
        with CFG_LOCK:
            if not CFG.get("dev_mode"):
                raise UserError("Developer mode is off.")
            f = dev_features()
            for k, v in (body.get("set") or {}).items():
                if k in DEV_FEATURES:
                    f[k] = bool(v)
            CFG["dev_features"] = f
            save_config(CFG)
        if "beta" in (body.get("set") or {}):
            UPDATE_WAKE.set()  # look at the right channel straight away
        return {"dev_features": f}
    if path == "/api/dev/history":
        return dev_history(body.get("view") if body.get("view") in ("hour", "day", "week") else "hour")
    if path == "/api/dev/downloads":
        return dev_downloads()
    if path == "/api/dev/versions":
        return dev_versions()
    if path == "/api/dev/versions/install":
        _need_dev("versions")
        return {"job": start_job(dev_install_version_job, str(body.get("sha") or ""), str(body.get("version") or ""))}
    if path == "/api/dev/versions/unpin":
        _need_dev("versions")
        if PIN_FILE.exists():
            PIN_FILE.unlink()
        return {"pinned": False}
    if path == "/api/dev/debug":
        return dev_debug(body.get("action"))
    if path == "/api/dev/notice":
        return dev_publish_notice(body.get("text"), body.get("link"), body.get("until"), body.get("token"))
    if path == "/api/notice/dismiss":
        with CFG_LOCK:
            n = CFG.get("notice") or {}
            if n.get("id"):
                CFG["notices_dismissed"] = (CFG.get("notices_dismissed") or [])[-20:] + [n["id"]]
                save_config(CFG)
        return {"notice": None}
    if path == "/api/secret/dev":
        code = body.get("code")
        time.sleep(0.6)  # keeps guessing slow
        if not isinstance(code, str) or len(code) > 200 or not secrets.compare_digest(
                hashlib.pbkdf2_hmac("sha256", code.strip().lower().encode(), bytes.fromhex(DEV_SALT), 300000).hex(), DEV_HASH):
            return {"ok": False}
        with CFG_LOCK:
            CFG["secrets"] = list(SECRETS)
            CFG["dev_mode"] = True
            save_config(CFG)
        return {"ok": True, "secrets": list(SECRETS), "dev_mode": True}
    if path == "/api/secret":
        name = body.get("name")
        if name not in SECRETS:
            raise UserError("That's not a secret.")
        with CFG_LOCK:
            found = [x for x in CFG.get("secrets", []) if x in SECRETS]
            new = name not in found
            if new:
                CFG["secrets"] = found + [name]
                save_config(CFG)
        return {"secrets": CFG["secrets"] if new else found, "new": new}
    if path == "/api/theme":
        with CFG_LOCK:
            if body.get("reset"):
                CFG["theme"] = {"mode": theme_of(CFG)["mode"]}
            else:
                CFG["theme"] = {**theme_of(CFG), **{k: v for k, v in body.items() if k in THEME_DEFAULTS}}
            t = theme_of(CFG)
            CFG["theme"] = t
            save_config(CFG)
        return {"theme": t}
    if path == "/api/settings":
        with CFG_LOCK:
            if body.get("loader") in LOADERS:
                CFG["loader"] = body["loader"]
            if isinstance(body.get("paths"), dict):
                CFG["paths"] = {k: v.strip() for k, v in body["paths"].items() if isinstance(v, str) and v.strip()}
            save_config(CFG)
        return state()
    if path == "/api/check":
        return {"job": start_job(check_job, (body.get("version") or "").strip(), body.get("loader") or "fabric")}
    if path == "/api/install":
        return {"job": start_job(install_job, body)}
    if path == "/api/import":
        return {"job": start_job(import_job, body.get("folder"))}
    if path == "/api/job":
        job = JOBS.get(body.get("id"))
        if not job:
            raise UserError("Unknown job")
        return job.view(int(body.get("since") or 0))
    if path == "/api/open":
        p = body.get("path") or ""
        if p not in OPENABLE:
            raise UserError("Not allowed")
        target = Path(p)
        open_path(target if target.is_dir() else target.parent)
        return {"ok": True}
    if path == "/api/port/info":
        return port_info(body.get("key") or "", (body.get("version") or "").strip(), body.get("loader") or "fabric")
    if path == "/api/port/start":
        return {"job": start_job(port_start_job, body.get("key") or "", (body.get("version") or "").strip(),
                                 body.get("loader") or "fabric")}
    if path == "/api/ports":
        return ports_view()
    if path == "/api/port/relaunch":
        with CFG_LOCK:
            p = (CFG.get("ports") or {}).get(body.get("id"))
        if not p or not Path(p["dir"]).exists():
            raise UserError("That port's folder is gone.")
        return launch_claude(Path(p["dir"]))
    if path == "/api/port/add_jar":
        return port_add_jar(body)
    if path == "/api/port/remove":
        return port_remove(body.get("id"))
    if path == "/api/mod_folders":
        with CFG_LOCK:
            cfg = json.loads(json.dumps(CFG))
        return {"folders": find_mod_folders(cfg)}
    if path == "/api/pick":
        if not PICK_LOCK.acquire(blocking=False):
            raise UserError("A folder picker is already open. Look for it behind this window.")
        try:
            return {"path": pick_path(body.get("kind", "folder"), body.get("title") or "Choose a folder",
                                      body.get("start") or "")}
        finally:
            PICK_LOCK.release()
    if path == "/api/versions":
        return versions_view(refresh=bool(body.get("refresh")))
    if path == "/api/versions/seen":
        with CFG_LOCK:
            newest = newest_release()
            if newest:
                CFG["seen_newest"] = newest
            CFG.pop("newest_check", None)
            save_config(CFG)
        return versions_view()
    if path == "/api/focus":
        return {"focused": focus_native_window()}
    if path == "/api/window/setup":
        return {"job": start_job(install_webview_job)}
    if path == "/api/update/auto":
        with CFG_LOCK:
            CFG["update_auto"] = bool(body.get("on"))
            save_config(CFG)
        return state()
    if path == "/api/update/dismiss_note":
        with CFG_LOCK:
            CFG.pop("just_updated", None)
            save_config(CFG)
        return {"ok": True}
    if path == "/api/update/nudge":
        due = time.time() - UPDATE_LAST["t"] > UPDATE_NUDGE_SECONDS
        if due and current_update_source():
            UPDATE_WAKE.set()
        return {"nudged": due}
    if path == "/api/update/status":
        return {"update": find_update(), "update_last_check": CFG.get("update_last_check")}
    if path == "/api/update/check":
        if current_update_source():
            check_online_update()
        return {"update": find_update(force=True), "version": APP_VERSION, "update_last_check": CFG.get("update_last_check")}
    if path == "/api/update/apply":
        new_version = apply_update(body.get("path") or "")
        restart_app()
        return {"version": new_version}
    if path == "/api/update/undo":
        v = undo_update()
        restart_app()
        return {"version": v}
    if path == "/api/window/shown":
        WINDOW["shown"].set()
        return {"ok": True}
    if path == "/api/window/retry":
        with CFG_LOCK:
            CFG.pop("native_broken", None)
            save_config(CFG)
        restart_app()
        return {"ok": True}
    if path == "/api/log":
        return {"log": log_tail(60)}
    if path == "/api/window/restart":
        restart_app()
        return {"ok": True}
    if path == "/api/window/dismiss":
        with CFG_LOCK:
            CFG["native_prompt_dismissed"] = True
            save_config(CFG)
        return {"ok": True}
    if path == "/api/ping":
        return {"ok": True, "app": "modhub"}
    if path == "/api/shortcut":
        made = create_shortcuts()
        with CFG_LOCK:
            CFG["shortcut_done"] = True
            save_config(CFG)
        return {"made": made}
    if path == "/api/dismiss_shortcut":
        with CFG_LOCK:
            CFG["shortcut_done"] = True
            save_config(CFG)
        return {"ok": True}
    if path == "/api/quit":
        threading.Timer(0.3, shutdown).start()
        return {"ok": True}
    raise UserError("Not found")


# What ModHub's page may load: its own code, pictures from the web, nothing else.
PAGE_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; media-src 'none'; "
            "object-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


class Handler(BaseHTTPRequestHandler):
    server_version = "ModHub"

    def log_message(self, *a):
        pass

    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _origin_ok(self):
        """Requests must come from ModHub's own page, never from another website open in your browser."""
        origin = self.headers.get("Origin")
        if not origin:
            return True  # not sent by a web page (or same-origin GET)
        port = self.server.server_address[1]
        return origin in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")

    def _token_ok(self, given):
        return isinstance(given, str) and secrets.compare_digest(given.encode(), TOKEN.encode())

    def _send(self, code, payload, ctype="application/json"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if ctype.startswith("text/html"):
            self.send_header("Content-Security-Policy", PAGE_CSP)
        self.end_headers()
        self.wfile.write(data)

    def _upload(self):
        """A file dragged into ModHub (or picked with Choose files)."""
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > 300_000_000:
                raise UserError("That file is empty or too big.")
            name = safe_filename(urllib.parse.unquote(self.headers.get("X-Filename") or "file.jar"))
            if not name.lower().endswith((".jar", ".zip", ".mrpack", ".modhub")):
                raise UserError(f"{name} isn't a mod (.jar), resource pack (.zip) or modpack (.mrpack).")
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            LOCAL_DIR.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=LOCAL_DIR, suffix=Path(name).suffix)
            try:
                with os.fdopen(fd, "wb") as out:
                    left = n
                    while left:
                        chunk = self.rfile.read(min(left, 1 << 20))
                        if not chunk:
                            break
                        out.write(chunk)
                        left -= len(chunk)
                restore = urllib.parse.urlparse(self.path).path == "/api/backup/restore"
                if not restore and name.lower().endswith(".zip"):
                    try:
                        with zipfile.ZipFile(tmp) as zz:
                            restore = BACKUP_MARKER in zz.namelist()
                    except zipfile.BadZipFile:
                        pass
                if restore:
                    result = restore_library_backup(Path(tmp))
                    return self._send(200, {"restored": result, **state()})
                if name.lower().endswith((".mrpack", ".modhub")):
                    return self._send(200, {"share": share_preview_file(Path(tmp), name)})
                want = (qs.get("version") or [None])[0]
                res = add_local_file(Path(tmp), name, want, (qs.get("item") or [None])[0], explicit_version=bool(want))
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            self._send(200, {**res, "favorites": CFG["favorites"]})
        except UserError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": f"Something went wrong: {e}"})

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "forbidden"})
        u = urllib.parse.urlparse(self.path)
        if u.path == "/icon.png":
            return self._send(200, icon_png(192), "image/png")
        if u.path == "/":
            if not self._token_ok(urllib.parse.parse_qs(u.query).get("t", [""])[0]):
                return self._send(403, b"Open ModHub from its shortcut, or start it again.", "text/plain")
            return self._send(200, page_html().encode(), "text/html; charset=utf-8")
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._host_ok() or not self._origin_ok() or not self._token_ok(self.headers.get("X-Token")):
            return self._send(403, {"error": "forbidden"})
        if urllib.parse.urlparse(self.path).path in ("/api/local/upload", "/api/backup/restore"):
            return self._upload()
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n < 0 or n > 2_000_000:
                return self._send(413, {"error": "Request too big."})
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            if not isinstance(body, dict):
                raise UserError("Bad request.")
            self._send(200, api(urllib.parse.urlparse(self.path).path, body))
        except UserError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": f"Something went wrong: {e}"})


# =========================================================================== #
# Running as an app: own window, no console, one instance, shortcuts
# =========================================================================== #
APP = {"proc": None, "server": None, "webview": None}
RUNNING_FILE = DATA_DIR / "running.json"
PREFERRED_PORT = 47811


def setup_logging():
    """With pythonw there's no console, so send output to a log file instead."""
    if sys.stdout is None or sys.stderr is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        log = open(DATA_DIR / "modhub.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def relaunch_without_console():
    """On Windows, double-clicking modhub.py opens a console. Restart under pythonw so only the app window shows."""
    if platform.system() != "Windows" or "--console" in sys.argv or "--child" in sys.argv:
        return
    exe = Path(sys.executable)
    if exe.name.lower() != "python.exe":
        return
    pyw = exe.with_name("pythonw.exe")
    if not pyw.exists():
        return
    try:
        subprocess.Popen([str(pyw), str(Path(__file__).resolve()), *sys.argv[1:], "--child"],
                         creationflags=0x00000008 | 0x00000200, close_fds=True)  # DETACHED_PROCESS | NEW_PROCESS_GROUP
        sys.exit(0)
    except OSError:
        pass


def find_app_browser():
    """A Chromium-based browser that can open a page as its own app window."""
    system = platform.system()
    cands = []
    if system == "Windows":
        roots = [os.environ.get(k) for k in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
        for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe",
                    r"BraveSoftware\Brave-Browser\Application\brave.exe"):
            cands += [Path(r) / rel for r in roots if r]
    elif system == "Darwin":
        for base in (Path("/Applications"), Path.home() / "Applications"):
            for app, binary in (("Google Chrome", "Google Chrome"), ("Microsoft Edge", "Microsoft Edge"),
                                ("Brave Browser", "Brave Browser"), ("Chromium", "Chromium")):
                cands.append(base / f"{app}.app" / "Contents" / "MacOS" / binary)
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                     "microsoft-edge", "microsoft-edge-stable", "brave-browser"):
            w = shutil.which(name)
            if w:
                cands.append(Path(w))
    return next((c for c in cands if c.exists()), None)


def open_window(url):
    """Open ModHub in its own app window. Falls back to a normal browser tab."""
    exe = find_app_browser()
    if not exe or "--tab" in sys.argv:
        webbrowser.open(url)
        return None
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    args = [str(exe), f"--app={url}", f"--user-data-dir={DATA_DIR / 'window'}", "--window-size=1280,880",
            "--no-first-run", "--no-default-browser-check", "--disable-features=Translate,MediaRouter",
            "--disable-sync"]
    try:
        return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    except OSError:
        webbrowser.open(url)
        return None


# ---- Windows taskbar identity ----
# The app window is an Edge/Chrome window, so by default Windows pins it as "Microsoft Edge" with Edge's
# icon and a relaunch command pointing at an old address. We give the window ModHub's own identity
# (System.AppUserModel properties): its own taskbar group, name and icon, and a relaunch command that
# starts ModHub itself. Pinning it then pins ModHub.
APP_USER_MODEL_ID = "ModHub.MinecraftMods"


def relaunch_command():
    if FROZEN:
        return f'"{sys.executable}"'
    script = Path(__file__).resolve()
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    return f'"{pyw if pyw.exists() else exe}" "{script}"'


def _set_window_identity(hwnd, aumid, relaunch, icon, name):
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("b", ctypes.c_ubyte * 16)]

    def guid(text):
        g = GUID()
        ctypes.memmove(ctypes.byref(g), uuid.UUID(text).bytes_le, 16)
        return g

    class PROPERTYKEY(ctypes.Structure):
        _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]

    class PROPVARIANT(ctypes.Structure):
        _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort), ("r2", ctypes.c_ushort),
                    ("r3", ctypes.c_ushort), ("pwszVal", ctypes.c_wchar_p), ("pad", ctypes.c_void_p)]

    iid = guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")  # IPropertyStore
    store = ctypes.c_void_p()
    hr = ctypes.windll.shell32.SHGetPropertyStoreForWindow(wintypes.HWND(hwnd), ctypes.byref(iid), ctypes.byref(store))
    if hr != 0 or not store.value:
        return False
    vtbl = ctypes.cast(store, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    set_value = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(PROPERTYKEY),
                                   ctypes.POINTER(PROPVARIANT))(vtbl[6])
    commit = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)(vtbl[7])
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
    fmtid = "9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"  # PKEY_AppUserModel_*
    try:
        # relaunch command, relaunch icon, relaunch display name, then the ID itself
        for pid, value in ((2, relaunch), (3, icon), (4, name), (5, aumid)):
            key = PROPERTYKEY(guid(fmtid), pid)
            pv = PROPVARIANT()
            pv.vt = 31  # VT_LPWSTR
            pv.pwszVal = value
            set_value(store, ctypes.byref(key), ctypes.byref(pv))
        commit(store)
    finally:
        release(store)
    return True


def _find_app_windows(title="ModHub", own_process=False):
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []
    me = os.getpid()

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) == len(title):
            buf = ctypes.create_unicode_buffer(len(title) + 1)
            user32.GetWindowTextW(hwnd, buf, len(title) + 1)
            if buf.value != title:
                return True
            if own_process:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == (me if own_process is True else own_process):
                    found.append(hwnd)
            else:
                cls = ctypes.create_unicode_buffer(64)
                user32.GetClassNameW(hwnd, cls, 64)
                if cls.value.startswith("Chrome_WidgetWin"):
                    found.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    return found


def _set_window_icon(hwnd, ico_path):
    """Give a window ModHub's icon (title bar + taskbar)."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.LoadImageW.restype = ctypes.c_void_p
    user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, ctypes.c_void_p]
    IMAGE_ICON, LR_LOADFROMFILE, WM_SETICON = 1, 0x10, 0x80
    big = user32.LoadImageW(None, ico_path, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
    small = user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
    if big:
        user32.SendMessageW(hwnd, WM_SETICON, 1, big)
    if small:
        user32.SendMessageW(hwnd, WM_SETICON, 0, small)


def brand_app_window(seconds=20, own_process=False):
    """Watch for the ModHub window to appear and give it ModHub's taskbar identity."""
    if platform.system() != "Windows":
        return
    try:
        import ctypes
        ctypes.windll.ole32.CoInitialize(None)
        icon = str(write_icons() / "modhub.ico")
        relaunch = relaunch_command()
        done = set()
        end = time.time() + seconds
        while time.time() < end:
            for hwnd in _find_app_windows(own_process=own_process):
                if hwnd in done:
                    continue
                if own_process:
                    _set_window_icon(hwnd, icon)
                if _set_window_identity(hwnd, APP_USER_MODEL_ID, relaunch, f"{icon},0", "ModHub"):
                    done.add(hwnd)
            time.sleep(0.15 if not done else 1.0)
    except Exception:
        traceback.print_exc()


def watch_window(proc):
    """Quit when the app window is closed."""
    started = time.time()
    proc.wait()
    if time.time() - started < 5:
        # it handed off to an already-open window or failed to start; keep serving
        APP["proc"] = None
        return
    print("Window closed, stopping ModHub.")
    shutdown()


def shutdown():
    for proc in (APP["proc"], (globals().get("WINDOW") or {}).get("child")):
        try:
            if proc and proc.poll() is None:
                proc.terminate()
        except Exception:
            pass
    try:
        RUNNING_FILE.unlink()
    except OSError:
        pass
    os._exit(0)


def running_instance():
    """If ModHub is already running, return its address so we can just show its window."""
    try:
        info = json.loads(RUNNING_FILE.read_text("utf-8"))
        req = urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/ping", data=b"{}", method="POST",
                                     headers={"X-Token": info["token"], "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as r:
            if json.loads(r.read()).get("app") == "modhub":
                return f"http://127.0.0.1:{info['port']}/?t={info['token']}"
    except Exception:
        pass
    return None


# ---- icon (drawn in code so ModHub stays a single file) ----
def _png(w, h, rows):
    import struct
    import zlib

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + r for r in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


_ICON_CACHE = {}


def icon_png(n):
    """ModHub's mark as a PNG."""
    if n in _ICON_CACHE:
        return _ICON_CACHE[n]
    _ICON_CACHE[n] = _png(n, n, icon_rgba(n))
    return _ICON_CACHE[n]


def icon_rgba(n):
    """ModHub's mark: a 2x2 block of rounded squares (crimson, slate, slate, light grey) on a black tile."""
    bg, slate, amber, green = (16, 16, 19), (58, 58, 66), (215, 38, 61), (232, 230, 227)  # crimson + light grey on black
    R = n * 0.2  # tile corner radius
    pad, gap = n * 0.2, n * 0.06
    cell = (n - 2 * pad - gap) / 2
    r = cell * 0.2
    colors = [[amber, slate], [slate, green]]

    def inside(x, y, x0, y0, size, rad):
        if not (x0 <= x < x0 + size and y0 <= y < y0 + size):
            return False
        cx = min(max(x, x0 + rad), x0 + size - rad)
        cy = min(max(y, y0 + rad), y0 + size - rad)
        return (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad

    rows = []
    for py in range(n):
        row = bytearray()
        for px in range(n):
            x, y = px + 0.5, py + 0.5
            if not inside(x, y, 0, 0, n, R):
                row += b"\x00\x00\x00\x00"
                continue
            c = bg
            for i in range(2):
                for j in range(2):
                    if inside(x, y, pad + j * (cell + gap), pad + i * (cell + gap), cell, r):
                        c = colors[i][j]
            row += bytes(c) + b"\xff"
        rows.append(bytes(row))
    return rows


def classic_ico(sizes=(16, 24, 32, 48, 64)):
    """A .ico made of plain bitmaps. Windows' window code (System.Drawing) rejects PNG-based icons."""
    import struct
    blobs = []
    for n in sizes:
        rows = icon_rgba(n)
        pixels = b"".join(bytes(b for px in range(n) for b in (r[px * 4 + 2], r[px * 4 + 1], r[px * 4], r[px * 4 + 3]))
                          for r in reversed(rows))  # bottom-up BGRA
        stride = ((n + 31) // 32) * 4
        mask = bytearray()
        for r in reversed(rows):
            line = bytearray(stride)
            for px in range(n):
                if r[px * 4 + 3] == 0:
                    line[px // 8] |= 0x80 >> (px % 8)
            mask += line
        head = struct.pack("<IiiHHIIiiII", 40, n, n * 2, 1, 32, 0, len(pixels) + len(mask), 0, 0, 0, 0)
        blobs.append((n, head + pixels + bytes(mask)))
    out = struct.pack("<HHH", 0, 1, len(blobs))
    offset = 6 + 16 * len(blobs)
    entries, data = b"", b""
    for n, blob in blobs:
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(blob), offset + len(data))
        data += blob
    return out + entries + data


def write_icons():
    import struct
    d = DATA_DIR / "icons"
    d.mkdir(parents=True, exist_ok=True)
    png256 = icon_png(256)
    (d / "modhub.png").write_bytes(png256)
    # .ico holding PNG images (Windows Vista and later)
    imgs = [(s, icon_png(s)) for s in (16, 32, 48, 256)]
    head = struct.pack("<HHH", 0, 1, len(imgs))
    offset = 6 + 16 * len(imgs)
    entries, blobs = b"", b""
    for s, data in imgs:
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(data), offset + len(blobs))
        blobs += data
    (d / "modhub.ico").write_bytes(head + entries + blobs)
    (d / "modhub-window.ico").write_bytes(classic_ico())
    # .icns for macOS (PNG-based entries)
    parts = b"".join(t + struct.pack(">I", len(data) + 8) + data
                     for t, data in ((b"ic07", icon_png(128)), (b"ic08", png256), (b"ic09", icon_png(512))))
    (d / "modhub.icns").write_bytes(b"icns" + struct.pack(">I", len(parts) + 8) + parts)
    return d


def windows_shortcuts(env):
    """ModHub.lnk on the desktop and in the Start menu, from MH_TARGET / MH_ARGS / MH_DIR / MH_ICON in env."""
    ps = ("$ws = New-Object -ComObject WScript.Shell; "
          "foreach ($d in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) { "
          "$s = $ws.CreateShortcut((Join-Path $d 'ModHub.lnk')); $s.TargetPath = $env:MH_TARGET; "
          "$s.Arguments = $env:MH_ARGS; $s.WorkingDirectory = $env:MH_DIR; $s.IconLocation = $env:MH_ICON; "
          "$s.Description = 'Install your Minecraft mods into any version'; $s.Save() }")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                       env=env, capture_output=True, text=True, creationflags=0x08000000)
    if r.returncode != 0:
        raise UserError(f"Couldn't create the shortcuts: {(r.stderr or r.stdout).strip()[:300]}")


# ---- the Python version turns itself into the ModHub app (ModHub.exe) ----
# The .exe brings its own Python and window engine, so its window opens on any Windows PC.
APP_SWITCH = {"status": None, "message": ""}  # None, downloading, ready (waiting for installs), switching, error


def app_exe_url():
    m = re.fullmatch(r"([\w.-]+)/([\w.-]+)", current_update_source())
    return f"https://github.com/{m.group(1)}/{m.group(2)}/releases/latest/download/ModHub.exe" if m else None


def app_switch_cfg():
    with CFG_LOCK:
        return dict(CFG.get("app_switch") or {})


def can_switch_to_app():
    return (platform.system() == "Windows" and not FROZEN and bool(app_exe_url())
            and "--no-app" not in sys.argv and "--no-browser" not in sys.argv)


def app_switch_state():
    info = app_switch_cfg()
    return {"available": can_switch_to_app(), "status": APP_SWITCH["status"], "message": APP_SWITCH["message"],
            "gave_up": info.get("attempts", 0) >= 3 and not info.get("ok")}


def switch_to_app(manual=False):
    """Download ModHub.exe, point the shortcuts at it, then reopen ModHub as the app."""
    info = app_switch_cfg()
    if APP_SWITCH["status"] in ("downloading", "ready", "switching") or (info.get("attempts", 0) >= 3 and not manual):
        return
    APP_SWITCH.update(status="downloading", message="")
    with CFG_LOCK:
        CFG["app_switch"] = {**info, "attempts": 0 if manual else info.get("attempts", 0) + 1}
        save_config(CFG)
    try:
        folder = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "Programs" / "ModHub"
        folder.mkdir(parents=True, exist_ok=True)
        exe, tmp = folder / "ModHub.exe", folder / "ModHub.exe.download"
        req = urllib.request.Request(app_exe_url(), headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as out:
            shutil.copyfileobj(r, out, 1 << 16)
        with open(tmp, "rb") as f:
            head = f.read(2)
        if head != b"MZ" or tmp.stat().st_size < 3_000_000:
            tmp.unlink()
            raise UserError("the download wasn't a working ModHub.exe")
        os.replace(tmp, exe)
        try:
            windows_shortcuts({**os.environ, "MH_TARGET": str(exe), "MH_ARGS": "", "MH_DIR": str(folder), "MH_ICON": str(exe)})
        except Exception:
            traceback.print_exc()  # the app still works; the old shortcut just keeps opening it via modhub.py
        with CFG_LOCK:
            CFG["app_switch"] = {**CFG.get("app_switch", {}), "path": str(exe)}
            save_config(CFG)
    except (urllib.error.URLError, TimeoutError, OSError, UserError) as e:
        traceback.print_exc()
        msg = str(e) if isinstance(e, UserError) else "couldn't download it. Check your internet"
        APP_SWITCH.update(status="error", message=msg)
        return
    APP_SWITCH.update(status="ready")
    while any(not j.done for j in list(JOBS.values())):  # never interrupt an install
        time.sleep(2)
    APP_SWITCH.update(status="switching")
    time.sleep(3)  # the page shows "Switching to the ModHub app"
    print("Reopening as the ModHub app")
    subprocess.Popen([str(exe), "--after-restart", str(os.getpid())], close_fds=True, **detached_kwargs())
    threading.Timer(0.4, shutdown).start()


def open_app_instead():
    """Once the app is set up, starting modhub.py just opens the app."""
    if not can_switch_to_app() or "--after-restart" in sys.argv:
        return False
    info = app_switch_cfg()
    exe = Path(info.get("path") or "")
    if not info.get("ok") or not exe.is_file():
        return False
    try:
        subprocess.Popen([str(exe)], close_fds=True, **detached_kwargs())
        return True
    except OSError:
        return False


def create_shortcuts():
    """Add ModHub to the desktop / Start menu / Applications so it opens like any app."""
    script = Path(__file__).resolve()
    icons = write_icons()
    system = platform.system()
    if system == "Windows":
        exe = Path(sys.executable)
        pyw = exe.with_name("pythonw.exe")
        if FROZEN:  # ModHub.exe: the shortcut opens the .exe itself
            env = {**os.environ, "MH_TARGET": str(exe), "MH_ARGS": "", "MH_DIR": str(exe.parent), "MH_ICON": str(exe)}
        else:
            env = {**os.environ, "MH_TARGET": str(pyw if pyw.exists() else exe), "MH_ARGS": f'"{script}"',
                   "MH_DIR": str(script.parent), "MH_ICON": str(icons / "modhub.ico")}
        windows_shortcuts(env)
        return ["your desktop", "the Start menu"]
    if system == "Darwin" and FROZEN:
        # ModHub.app itself: copy it into Applications so it opens from Launchpad and Spotlight
        bundle = Path(sys.executable).resolve().parents[2]
        if bundle.suffix != ".app":
            raise UserError("Drag ModHub into your Applications folder to open it from Launchpad.")
        if bundle.parent in (Path("/Applications"), Path.home() / "Applications"):
            return ["Applications (it's already there)"]
        dest = Path.home() / "Applications" / "ModHub.app"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(bundle, dest, symlinks=True)
        return ["Applications (open it from Launchpad or Spotlight)"]
    if system == "Darwin":
        import shlex
        app = Path.home() / "Applications" / "ModHub.app"
        (app / "Contents" / "MacOS").mkdir(parents=True, exist_ok=True)
        (app / "Contents" / "Resources").mkdir(parents=True, exist_ok=True)
        shutil.copy2(icons / "modhub.icns", app / "Contents" / "Resources" / "ModHub.icns")
        launcher = app / "Contents" / "MacOS" / "ModHub"
        launcher.write_text(f"#!/bin/bash\nexec {shlex.quote(sys.executable)} {shlex.quote(str(script))} \"$@\"\n", "utf-8")
        launcher.chmod(0o755)
        (app / "Contents" / "Info.plist").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>ModHub</string>
<key>CFBundleDisplayName</key><string>ModHub</string>
<key>CFBundleIdentifier</key><string>local.modhub.launcher</string>
<key>CFBundleExecutable</key><string>ModHub</string>
<key>CFBundleIconFile</key><string>ModHub</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleVersion</key><string>{APP_VERSION}</string>
<key>LSUIElement</key><true/>
</dict></plist>
""", "utf-8")
        os.utime(app, None)
        return ["Applications (open it from Launchpad or Spotlight)"]
    # Linux
    apps = Path.home() / ".local" / "share" / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    if FROZEN:  # the ModHub app for Linux: keep a copy where it won't be tidied away, and point the shortcuts at it
        home_bin = Path.home() / ".local" / "share" / "ModHub" / "ModHub"
        here = Path(sys.executable).resolve()
        if here != home_bin:
            home_bin.parent.mkdir(parents=True, exist_ok=True)
            tmp = home_bin.with_suffix(".new")
            shutil.copy2(here, tmp)
            tmp.chmod(0o755)
            os.replace(tmp, home_bin)
        run = f"\"{home_bin}\""
    else:
        run = f"\"{sys.executable}\" \"{script}\""
    entry = (f"[Desktop Entry]\nType=Application\nName=ModHub\nComment=Install your Minecraft mods into any version\n"
             f"Exec={run}\nIcon={icons / 'modhub.png'}\nTerminal=false\n"
             "Categories=Game;\n")
    made = []
    (apps / "modhub.desktop").write_text(entry, "utf-8")
    (apps / "modhub.desktop").chmod(0o755)
    made.append("your app menu")
    desktop = Path.home() / "Desktop"
    if desktop.is_dir():
        (desktop / "modhub.desktop").write_text(entry, "utf-8")
        (desktop / "modhub.desktop").chmod(0o755)
        made.append("your desktop")
    return made


# ---- ModHub's own window (pywebview) ----
def has_webview():
    try:
        import webview  # noqa: F401
        return True
    except Exception:
        return False


def console_python():
    """python.exe rather than pythonw.exe, so pip's output can be read."""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and exe.with_name("python.exe").exists():
        return str(exe.with_name("python.exe"))
    return str(exe)


def install_webview_job(job):
    if FROZEN:
        raise UserError("The ModHub app already includes everything it can. Download it again if it doesn't open.")
    py = console_python()
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    cmd = [py, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check", "pywebview"]
    if not in_venv:
        cmd.insert(4, "--user")
    job.log("Installing pywebview (ModHub's own window)...")
    job.progress = 0.1
    flags = 0x08000000 if platform.system() == "Windows" else 0
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                creationflags=flags, errors="replace")
    except OSError as e:
        raise UserError(f"Couldn't run pip: {e}")
    tail = []
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            tail = (tail + [line])[-12:]
            if line.startswith(("Collecting", "Downloading", "Installing", "Successfully")):
                job.log(line[:160])
                job.progress = min(job.progress + 0.08, 0.85)
    code = proc.wait()
    if code != 0:
        text = "\n".join(tail)
        if "No module named pip" in text:
            raise UserError("Your Python doesn't have pip. Reinstall Python from python.org with pip ticked, then try again.")
        low = text.lower()
        pyver = f"{sys.version_info.major}.{sys.version_info.minor}"
        if any(k in low for k in ("retrying", "newconnectionerror", "failed to establish", "temporary failure",
                                  "connection", "timed out", "proxy")):
            raise UserError("Couldn't download the add-on. Check your internet connection and try again.")
        if "no matching distribution" in low or "requires-python" in low or "failed building wheel" in low \
                or "pythonnet" in low:
            raise UserError(f"The add-on doesn't support your Python version ({pyver}) yet. ModHub keeps using an "
                            "Edge or Chrome window for now. Installing Python 3.12 from python.org would also fix it.")
        raise UserError("Setup didn't finish, so ModHub keeps using an Edge or Chrome window.\n\nDetails:\n" + text[-600:])
    check = subprocess.run([py, "-c", "import webview"], capture_output=True, text=True, creationflags=flags)
    if check.returncode != 0:
        raise UserError("pywebview installed, but it won't load on this computer, so ModHub will keep using "
                        "an Edge/Chrome window. Details: " + (check.stderr or "")[-400:])
    job.log("Done. Restart ModHub to switch to its own window.")
    return {"ok": True}


def runner_python():
    """pythonw on Windows (no console window), otherwise the current interpreter. In ModHub.exe, the .exe itself."""
    if FROZEN:
        return sys.executable
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    return str(pyw if platform.system() == "Windows" and pyw.exists() else exe)


def detached_kwargs():
    if platform.system() == "Windows":
        return {"creationflags": 0x00000008 | 0x00000200}  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    return {"start_new_session": True}


def restart_app():
    """Start a fresh ModHub (it waits for this one to close), then quit this one."""
    args = [runner_python(), str(Path(__file__).resolve()), "--after-restart", str(os.getpid()), "--child"]
    subprocess.Popen(args, close_fds=True, **detached_kwargs())
    threading.Timer(0.4, shutdown).start()


def wait_for_previous():
    if "--after-restart" not in sys.argv:
        return
    end = time.time() + 15
    while RUNNING_FILE.exists() and time.time() < end:
        time.sleep(0.2)
    time.sleep(0.3)


def log_tail(n=40):
    try:
        lines = (DATA_DIR / "modhub.log").read_text("utf-8", "replace").splitlines()
        return "\n".join(lines[-n:])
    except OSError:
        return ""


# ---- the own window runs as a separate helper process, so if it can't start ModHub falls back ----
WINDOW = {"child": None, "shown": threading.Event(), "error": None}
NATIVE_TIMEOUT = float(os.environ.get("MODHUB_NATIVE_TIMEOUT", "25"))


def native_broken_now(cfg=None):
    """A failed window only counts for the same version of ModHub, run the same way: every update tries again."""
    with CFG_LOCK:
        nb = (cfg if cfg is not None else CFG).get("native_broken")
    if not isinstance(nb, dict) or nb.get("version") != APP_VERSION or bool(nb.get("frozen")) != FROZEN:
        return None
    return nb


def native_allowed():
    return has_webview() and not native_broken_now()


def mark_native_broken(reason):
    print(f"ModHub's own window didn't open: {reason}")
    WINDOW["error"] = reason
    with CFG_LOCK:
        CFG["native_broken"] = {"reason": reason, "when": now_iso(), "version": APP_VERSION, "frozen": FROZEN}
        save_config(CFG)


def start_window_helper(url):
    """Launch the window helper and watch it. Returns True if the window appeared."""
    WINDOW["shown"].clear()
    args = [runner_python(), str(Path(__file__).resolve()), "--window", url, "--child"]
    try:
        child = subprocess.Popen(args, close_fds=True, stdin=subprocess.DEVNULL)
    except OSError as e:
        mark_native_broken(f"couldn't start it ({e})")
        return False
    WINDOW["child"] = child
    end = time.time() + NATIVE_TIMEOUT
    while time.time() < end:
        if WINDOW["shown"].wait(0.3):
            return True
        code = child.poll()
        if code is not None:
            print(f"Window helper exited with code {code}")
            mark_native_broken("it closed as soon as it started")
            return False
    mark_native_broken(f"it didn't appear within {NATIVE_TIMEOUT} seconds")
    try:
        child.kill()
    except Exception:
        pass
    return False


def watch_window_helper():
    child = WINDOW["child"]
    child.wait()
    print("Window closed, stopping ModHub.")
    shutdown()


def open_edge_fallback(url):
    proc = open_window(url)
    threading.Thread(target=brand_app_window, daemon=True).start()
    if proc:
        APP["proc"] = proc
        threading.Thread(target=watch_window, args=(proc,), daemon=True).start()
    return proc


def focus_native_window():
    child = WINDOW.get("child")
    if not child or child.poll() is not None or not WINDOW["shown"].is_set():
        return False
    if platform.system() == "Windows":
        try:
            import ctypes
            for hwnd in _find_app_windows(own_process=child.pid):
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
    return True


def run_window_helper(url):
    """Runs in the helper process: show ModHub in its own window until it's closed."""
    import webview
    token = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("t", [""])[0]
    base = url.split("/?")[0]
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except Exception:
            pass
    if platform.system() == "Darwin" and FROZEN:
        # ModHub.app runs in the background; only its window gets a Dock icon and menu bar.
        try:
            from AppKit import NSApplication
            NSApplication.sharedApplication().setActivationPolicy_(0)
        except Exception:
            traceback.print_exc()

    def on_shown(*_):
        try:
            req = urllib.request.Request(f"{base}/api/window/shown", data=b"{}", method="POST",
                                         headers={"X-Token": token, "Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5).read()
        except Exception:
            traceback.print_exc()
        threading.Thread(target=brand_app_window, kwargs={"seconds": 6, "own_process": True}, daemon=True).start()

    win = webview.create_window("ModHub", url, width=1280, height=880, min_size=(900, 620),
                                background_color="#131316", text_select=True)
    try:
        win.events.shown += on_shown
    except Exception:
        threading.Timer(3, on_shown).start()
    icon = str(write_icons() / ("modhub-window.ico" if platform.system() == "Windows" else "modhub.png"))
    try:
        webview.start(private_mode=False, storage_path=str(DATA_DIR / "webview"), icon=icon)
    except TypeError:  # older pywebview
        webview.start()


def main():
    setup_logging()
    if "--window" in sys.argv:
        try:
            import faulthandler  # a crash inside the window engine still leaves a note in the log
            faulthandler.enable(file=sys.stderr)
        except Exception:
            pass
        print(f"Window helper starting (Python {sys.version.split()[0]}, {'app' if FROZEN else 'script'})")
        try:
            run_window_helper(sys.argv[sys.argv.index("--window") + 1])
        except Exception:
            traceback.print_exc()
            sys.exit(3)
        return
    relaunch_without_console()
    wait_for_previous()
    if open_app_instead():
        return  # ModHub.exe is set up on this PC, so open that
    if apply_staged_update_on_start():
        return  # the updated ModHub is starting

    existing = running_instance()
    if existing and "--port" not in sys.argv:
        print("ModHub is already running. Bringing its window to the front.")
        info = json.loads(RUNNING_FILE.read_text("utf-8"))
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/focus", data=b"{}", method="POST",
                                         headers={"X-Token": info["token"], "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3) as r:
                if json.loads(r.read()).get("focused"):
                    return
        except Exception:
            pass
        open_window(existing)
        brand_app_window(seconds=8)
        return

    prefetch_versions()
    threading.Thread(target=version_watch, daemon=True).start()
    threading.Thread(target=update_watch, daemon=True).start()
    threading.Thread(target=watch_loop, daemon=True).start()
    threading.Thread(target=crash_watch, daemon=True).start()
    threading.Thread(target=precheck_watch, daemon=True).start()
    threading.Thread(target=mod_updates_watch, daemon=True).start()
    threading.Thread(target=live_loop, daemon=True).start()
    threading.Thread(target=notice_watch, daemon=True).start()
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else PREFERRED_PORT
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    APP["server"] = srv
    port = srv.server_address[1]
    url = f"http://127.0.0.1:{port}/?t={TOKEN}"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RUNNING_FILE.write_text(json.dumps({"port": port, "token": TOKEN, "pid": os.getpid()}), "utf-8")
    private(RUNNING_FILE)
    print(f"ModHub {APP_VERSION} is running at {url}")
    if FROZEN and platform.system() == "Windows":  # the app started fine: modhub.py can hand over to it from now on
        with CFG_LOCK:
            sw = CFG.get("app_switch") or {}
            if not sw.get("ok") or os.path.normcase(sw.get("path", "")) != os.path.normcase(sys.executable):
                CFG["app_switch"] = {"path": sys.executable, "ok": True}
                save_config(CFG)
    elif can_switch_to_app() and not app_switch_cfg().get("ok"):
        threading.Thread(target=lambda: (time.sleep(6), switch_to_app()), daemon=True).start()

    def open_ui():
        if "--no-browser" in sys.argv:
            return
        wants_native = "--tab" not in sys.argv and "--edge" not in sys.argv and native_allowed()
        if wants_native and start_window_helper(url):
            APP["webview"] = True
            threading.Thread(target=watch_window_helper, daemon=True).start()
            return
        if not open_edge_fallback(url):
            print("No Edge/Chrome found, so ModHub opened in your browser instead. Use Stop ModHub in the app to quit.")

    threading.Thread(target=open_ui, daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            RUNNING_FILE.unlink()
        except OSError:
            pass


PAGE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ModHub</title>
<link rel="icon" href="/icon.png">
<script>(function(){var d=document.documentElement,m=d.dataset.pref||"dark";if(m==="system")m=matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";d.dataset.mode=m;})()</script>
<style>
:root{
  --deep:#0b0b0d; --stone:#131316; --stone-2:#1c1c21; --stone-3:#27272d; --stone-4:#2c2c33; --edge:#37373f; --edge-2:#4b4b55;
  --line:#24242a; --slot:#25252b; --slot-ghost:#1d1d22; --well:#19191e; --tile:#e8e6e3;
  --text:#f3f1ef; --muted:#a9a6ad; --faint:#7a7780;
  --acc:215 38 61; --acc2:236 58 80; --acc3:168 26 45;
  --accent:rgb(var(--acc)); --accent-2:rgb(var(--acc2)); --accent-3:rgb(var(--acc3)); --accent-ink:#ffffff;
  --accent-tint:color-mix(in srgb,var(--accent) 16%,var(--stone)); --accent-edge:color-mix(in srgb,var(--accent) 38%,var(--stone));
  --link:color-mix(in srgb,var(--accent-2) 65%,#fff);
  --amber:#f0a43a; --attn:#7cb8ff; --ready:#45b97c; --missing:#ff5a5f;
  --mr:#1bd96a; --cf:#f16436;
  --hi:255 255 255; --shk:1; --knob:#cfccd2; --deep-rgb:11 11 13; --glass:19 19 22; --toast:243 241 239; --toast-ink:#0b0b0d;
  color-scheme:dark;
  --display: "Segoe UI Variable Display", ui-rounded, "SF Pro Rounded", "Nunito", system-ui, sans-serif;
  --body: "Segoe UI Variable Text", "Segoe UI Variable", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
}
:root[data-mode="light"]{
  --deep:#ecebef; --stone:#f7f7f9; --stone-2:#ffffff; --stone-3:#e9e8ed; --stone-4:#e0dfe5; --edge:#d3d2d9; --edge-2:#b9b8c1;
  --line:#e4e3e8; --slot:#dcdbe1; --slot-ghost:#e7e6eb; --well:#e4e3e8; --tile:#1c1b20;
  --text:#17161a; --muted:#57545d; --faint:#7c7984;
  --link:color-mix(in srgb,var(--accent) 80%,#000);
  --amber:#a8650a; --attn:#2563c9; --ready:#1d7f4d; --missing:#d0343a;
  --hi:0 0 0; --shk:.32; --knob:#ffffff; --deep-rgb:236 235 239; --glass:252 252 253; --toast:23 22 26; --toast-ink:#ffffff;
  color-scheme:light;
}
:root[data-accent="emerald"]{--acc:14 158 90; --acc2:22 190 108; --acc3:10 110 64}
:root[data-accent="ocean"]{--acc:37 99 235; --acc2:66 133 247; --acc3:26 70 170}
:root[data-accent="violet"]{--acc:124 58 237; --acc2:147 97 250; --acc3:90 38 180}
:root[data-accent="amber"]{--acc:202 112 8; --acc2:232 142 22; --acc3:150 82 6}
:root[data-accent="rose"]{--acc:214 41 118; --acc2:236 72 153; --acc3:160 28 88}
:root[data-accent="sunset"]{--acc:244 98 32; --acc2:251 146 60; --acc3:219 39 119}
:root[data-accent="aurora"]{--acc:20 184 166; --acc2:94 234 212; --acc3:124 58 237}
:root[data-accent="nether"]{--acc:226 66 22; --acc2:255 122 48; --acc3:140 16 24}
:root[data-accent="ender"]{--acc:168 85 247; --acc2:196 140 255; --acc3:64 30 140}
:root[data-accent="cherry"]{--acc:226 84 146; --acc2:244 140 184; --acc3:176 42 104}
:root[data-accent="mint"]{--acc:14 166 116; --acc2:52 211 153; --acc3:6 116 84}
:root[data-accent="lime"]{--acc:74 196 64; --acc2:126 230 104; --acc3:34 128 36}
:root[data-accent="rainbow"]{--acc:124 58 237; --acc2:147 97 250; --acc3:90 38 180}
:root[data-accent="diamond"]{--acc:34 211 238; --acc2:125 236 250; --acc3:14 116 144}
:root[data-accent="owl"]{--acc:245 176 50; --acc2:255 210 110; --acc3:30 48 120}
:root[data-accent="mono"]{--acc:214 214 222; --acc2:255 255 255; --acc3:90 90 100; --accent-ink:#0b0b0d}
:root[data-accent="ghost"]{--acc:128 140 168; --acc2:176 186 206; --acc3:96 104 140}
:root[data-accent="gold"]{--acc:234 170 8; --acc2:252 211 77; --acc3:146 88 6; --accent-ink:#1a1204}
:root[data-accent="redstone"]{--acc:228 24 36; --acc2:255 84 74; --acc3:110 0 8}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{background:var(--stone);color:var(--text);font:15px/1.5 var(--body);-webkit-font-smoothing:antialiased}
a{color:var(--link);text-decoration:none} a:hover{text-decoration:underline}
button,input,select{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--accent-2);outline-offset:2px}
.hidden{display:none !important}

/* ---------- shell ---------- */
.app{display:grid;grid-template-columns:232px 1fr;min-height:100vh;background:linear-gradient(to right,var(--deep) 232px,transparent 232px)}
.side{background:var(--deep);padding:22px 14px;display:flex;flex-direction:column;gap:4px;position:sticky;top:0;height:100vh}
.brand{display:flex;align-items:center;gap:11px;padding:4px 10px 22px;font:800 20px/1 var(--display);letter-spacing:.2px}
.mark{width:26px;height:26px;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:2px}
.mark i{border-radius:2px;background:var(--stone-3)} .mark i:nth-child(1){background:var(--accent)} .mark i:nth-child(4){background:var(--tile)}
.nav{display:flex;align-items:center;gap:10px;width:100%;padding:10px 12px;border:0;border-radius:8px;background:none;color:var(--muted);font-weight:600;cursor:pointer;text-align:left}
.nav:hover{color:var(--text);background:rgb(var(--hi) / .03)}
.nav.on{color:var(--text);background:var(--stone-2);box-shadow:inset 3px 0 0 var(--accent)}
.nav svg{width:18px;height:18px;flex:none;opacity:.85}
.nav .n{margin-left:auto;font-size:11.5px;color:var(--muted);font-weight:700;background:var(--stone-3);border-radius:10px;padding:1px 8px;min-width:22px;text-align:center}
.nav .n:empty{display:none}
.nav .dot-new{margin-left:auto;width:8px;height:8px;border-radius:50%;background:var(--accent-2);box-shadow:0 0 0 3px rgb(var(--acc) / .25)}
.nav.on .n{color:var(--muted)}
.side .foot{margin-top:auto;padding:10px 12px;font-size:12.5px;color:var(--faint)}
.side .foot button{background:none;border:0;color:var(--muted);cursor:pointer;padding:0;font-size:12.5px;text-decoration:underline;text-underline-offset:3px}

main{padding:40px 48px 80px;max-width:1080px;width:100%}
.page-h > .actions{flex:none;flex-wrap:nowrap}
.page-h{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin-bottom:26px}
h1{font:800 34px/1.08 var(--display);margin:0 0 8px;letter-spacing:-.5px}
.lede{color:var(--muted);margin:0;max-width:62ch}
h3{font:700 18px/1.3 var(--display);margin:0}

/* ---------- controls ---------- */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:38px;padding:0 16px;border-radius:8px;border:1px solid var(--edge);background:var(--stone-2);font-weight:650;cursor:pointer;white-space:nowrap}
.btn:hover{background:var(--stone-3)}
.btn.go{background:var(--accent);border-color:var(--accent);color:var(--accent-ink);box-shadow:inset 0 -3px 0 rgb(0 0 0 / calc(.25 * var(--shk)))}
.btn.go:hover{background:var(--accent-2);border-color:var(--accent-2)}
.btn.sm{height:32px;padding:0 12px;font-size:13.5px}
.btn.quiet{background:none;border-color:transparent;color:var(--muted)} .btn.quiet:hover{color:var(--text);background:var(--stone-2)}
.btn:disabled{opacity:.45;cursor:not-allowed}
input[type=text],input[type=password],input:not([type]),select{height:40px;width:100%;padding:0 12px;border-radius:8px;border:1px solid var(--edge);background:var(--deep);outline:none}
input:focus,select:focus{border-color:var(--accent)}
input::placeholder{color:var(--faint)}
.field-label{display:block;font-weight:650;font-size:13.5px;margin-bottom:7px}
.help{color:var(--faint);font-size:13px;margin-top:7px}
.seg{display:inline-flex;background:var(--deep);border:1px solid var(--edge);border-radius:9px;padding:3px;gap:2px}
.seg button{border:0;background:none;color:var(--muted);height:32px;padding:0 13px;border-radius:6px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:7px}
.seg button.on{background:var(--stone-3);color:var(--text)}
.seg button:disabled{opacity:.45;cursor:not-allowed}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:none}
.dot.mr{background:var(--mr)} .dot.cf{background:var(--cf)}
.src{font-size:12px;font-weight:650;display:inline-flex;align-items:center;gap:5px;color:var(--muted)}

/* ---------- library ---------- */
.searchbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.searchbar .q{flex:1 1 320px;position:relative}
.searchbar .q input{height:46px;padding-left:42px;font-size:15.5px}
.searchbar .q svg{position:absolute;left:14px;top:14px;width:18px;height:18px;color:var(--faint)}
.searchbar select{width:150px;height:46px}
.results{margin-top:14px;background:var(--stone-2);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.results-h{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;color:var(--muted);font-size:13.5px;border-bottom:1px solid var(--stone-3)}
.res{display:flex;align-items:center;gap:14px;padding:12px 16px;border-bottom:1px solid var(--stone-3)}
.res:last-child{border-bottom:0}
.ico{width:44px;height:44px;border-radius:8px;flex:none;background:var(--deep);display:grid;place-items:center;overflow:hidden;font:800 18px var(--display);color:var(--faint)}
.ico img{width:100%;height:100%;object-fit:cover}
.res .body{flex:1;min-width:0}
.res .t{font-weight:700;display:flex;align-items:center;gap:10px}
.res .d{color:var(--muted);font-size:13.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.res .m{color:var(--faint);font-size:12.5px}
.added{color:var(--ready);font-weight:650;font-size:13.5px;padding:0 6px;display:inline-flex;align-items:center;gap:6px}

.inv-h{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:40px 0 16px}
.inv-h .filter{width:220px;height:34px}
.inv{display:grid;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:18px 14px;background:var(--deep);padding:22px;border-radius:14px;border:1px solid var(--line)}
.cell{display:flex;flex-direction:column;align-items:center;gap:8px;min-width:0}
.slot{position:relative;width:100%;aspect-ratio:1;border-radius:6px;background:var(--slot);transition:transform .12s ease, box-shadow .12s ease;
  box-shadow:inset 3px 3px 0 rgb(0 0 0 / calc(.6 * var(--shk))),inset -3px -3px 0 rgb(var(--hi) / .06);display:grid;place-items:center}
.slot img{width:58%;height:58%;object-fit:contain;border-radius:6px;image-rendering:auto}
.slot .letter{font:800 30px var(--display);color:var(--faint)}
.slot .srcmark{position:absolute;right:8px;bottom:8px}
.slot .rm{position:absolute;top:5px;right:5px;width:24px;height:24px;border-radius:6px;border:0;background:rgb(var(--glass) / .85);color:var(--text);cursor:pointer;display:grid;place-items:center;opacity:0}
.cell:hover .rm,.rm:focus-visible{opacity:1}
.rm:hover{background:var(--accent)}
.cell .cap{font-size:13px;text-align:center;line-height:1.3;max-width:100%;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;color:var(--text)}
.cell.ghost .slot{background:var(--slot-ghost)}
.cell:not(.ghost):hover .slot{transform:translateY(-2px);box-shadow:inset 3px 3px 0 rgb(0 0 0 / calc(.6 * var(--shk))),inset -3px -3px 0 rgb(var(--hi) / .06),0 0 0 2px var(--accent)}
.inv-empty{grid-column:1/-1;text-align:center;color:var(--muted);padding:6px 0 2px}

/* ---------- install ---------- */
.step{display:grid;grid-template-columns:40px 1fr;gap:18px;padding:26px 0;border-top:1px solid var(--stone-3)}
.step:first-of-type{border-top:0;padding-top:4px}
.num{width:32px;height:32px;border-radius:50%;display:grid;place-items:center;font:800 15px var(--display);background:var(--stone-3);color:var(--muted)}
.step.done .num{background:var(--accent);color:var(--accent-ink)}
.step h3{margin:4px 0 14px}
.row{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end}
.row > div{min-width:0}
.check{display:inline-flex;gap:8px;align-items:center;color:var(--muted);font-size:13.5px;cursor:pointer;margin-top:9px}
.check input{width:auto;height:auto;accent-color:var(--accent)}
.launchers{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.lopt{display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border-radius:10px;background:var(--stone-2);border:1px solid transparent;cursor:pointer;text-align:left;width:100%;color:inherit}
.lopt:hover{border-color:var(--edge)}
.lopt.on{border-color:var(--accent);background:var(--accent-tint)}
.radio{width:18px;height:18px;border-radius:50%;border:2px solid var(--edge);flex:none;margin-top:2px;display:grid;place-items:center}
.lopt.on .radio{border-color:var(--accent)} .lopt.on .radio::after{content:"";width:8px;height:8px;border-radius:50%;background:var(--accent)}
.lopt .t{font-weight:700;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.lopt .d{color:var(--muted);font-size:13.5px;margin-top:2px}
.tag-found{font-size:12px;color:var(--ready);font-weight:650}
.actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap}

.progress{margin-top:22px}
.bar{height:8px;border-radius:5px;background:var(--deep);overflow:hidden}
.bar div{height:100%;width:0;background:var(--accent);transition:width .35s ease}
.now{color:var(--muted);font-size:13.5px;margin-top:8px}
details.log{margin-top:8px}
details.log summary{cursor:pointer;color:var(--faint);font-size:13px}
details.log pre{margin:8px 0 0;background:var(--deep);border-radius:8px;padding:12px 14px;font:12.5px/1.55 ui-monospace,Consolas,monospace;color:var(--muted);max-height:220px;overflow:auto;white-space:pre-wrap}

.banner{display:flex;gap:14px;align-items:center;padding:16px 18px;border-radius:12px;margin-top:22px;background:var(--stone-2);border:1px solid var(--line);border-left:4px solid var(--ready)}
.banner .grow{min-width:0}
.banner.err{border-left-color:var(--missing)}
.banner.warn{border-left-color:var(--amber)}
.banner .grow{flex:1}
.banner b{display:block;margin-bottom:2px}
.banner p{margin:0;color:var(--muted)}
.group{margin-top:26px}
.group-h{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.group-h .count{color:var(--faint);font-weight:600}
.group-h .lede{font-size:13.5px}
.list{background:var(--stone-2);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.li{display:flex;align-items:center;gap:14px;padding:11px 16px;border-bottom:1px solid var(--stone-3)}
.li:last-child{border-bottom:0}
.li .ico{width:34px;height:34px;border-radius:6px;font-size:14px}
.li .body{flex:1;min-width:0}
.li .t{font-weight:650}
.li .s{color:var(--faint);font-size:13px}
.li .v{color:var(--muted);font-size:13px;white-space:nowrap}
.state{font-size:12.5px;font-weight:700;white-space:nowrap}
.state.ready{color:var(--ready)} .state.missing{color:var(--amber)} .state.attn{color:var(--attn)} .state.skip{color:var(--faint)}
.chips{display:flex;flex-wrap:wrap;gap:8px;padding:14px 16px}
.chip{display:inline-flex;align-items:center;gap:7px;padding:5px 11px 5px 6px;border-radius:7px;background:var(--stone-3);font-size:13.5px}
.chip .ico{width:22px;height:22px;border-radius:4px;font-size:11px}
.chip.port{background:var(--accent-tint);box-shadow:inset 0 0 0 1px var(--accent-edge)}

.block{padding:0 0 30px}
.block + .block{padding-top:4px}
.loader-line{color:var(--muted)}
.loader-line b{color:var(--text)}
.linkbtn{background:none;border:0;padding:0;color:var(--link);cursor:pointer;font-weight:600}
.linkbtn:hover{text-decoration:underline}
.btn.big{height:50px;padding:0 30px;font-size:16.5px;border-radius:10px}
details.more{margin-top:18px}
details.more > summary{cursor:pointer;color:var(--muted);font-weight:600;width:max-content}
details.more > summary:hover{color:var(--text)}
.more-body{display:grid;gap:18px;margin-top:14px;padding:18px;background:var(--stone-2);border-radius:12px}
.picker{display:flex;gap:8px}
.picker input{flex:1}
.folders{display:grid;gap:8px}
.folder{display:flex;align-items:center;gap:14px;padding:12px 14px;background:var(--stone-2);border-radius:10px}
.folder .body{flex:1;min-width:0}
.folder .t{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.folder .s{color:var(--faint);font-size:13px}
.fico{width:36px;height:36px;border-radius:8px;background:var(--deep);display:grid;place-items:center;flex:none;color:var(--accent-2)}
.starter{background:var(--deep);border-radius:12px;padding:22px}
.starter h3{margin-bottom:4px}
.starter .lede{font-size:14px;margin-bottom:16px}

.kindseg{margin-bottom:14px}
.lobar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 18px}
.lochip{display:inline-flex;align-items:center;gap:8px;height:36px;padding:0 6px 0 14px;border-radius:18px;border:1px solid var(--edge);background:var(--stone-2);color:var(--muted);font-weight:650;cursor:pointer;transition:border-color .2s,background .2s,color .2s,transform .15s}
.lochip:hover{color:var(--text);border-color:var(--edge-2)}
.lochip .c{font-size:11.5px;font-weight:700;background:var(--stone-3);border-radius:10px;padding:1px 8px;color:var(--muted)}
.lochip .ed{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;border:0;background:none;color:inherit;cursor:pointer;opacity:.7}
.lochip .ed:hover{background:rgb(var(--hi) / .08);opacity:1}
.lochip.on{color:var(--text);border-color:var(--accent);background:var(--accent-tint);box-shadow:0 6px 20px -12px rgb(var(--acc2) / .8)}
.lochip.on .c{background:var(--accent);color:#fff}
.lochip.add{padding:0 14px;border-style:dashed;background:none}
.lochip:not(.on):not(.add) .ed{display:none}
.lochip:not(.on):not(.add){padding-right:14px}
.inst{background:var(--stone-2);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:12px}
.inst-top{display:flex;gap:14px;align-items:flex-start}
.inst-ico{width:44px;height:44px;border-radius:10px;background:var(--deep);display:grid;place-items:center;flex:none;font:800 13px var(--display);color:var(--accent-2);border:1px solid var(--stone-4)}
.inst .body{flex:1;min-width:0}
.inst .t{font-weight:700;font-size:16px}
.inst .s{color:var(--muted);font-size:13.5px}
.inst .meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.tag{font-size:12px;font-weight:650;color:var(--muted);background:var(--stone-3);border-radius:6px;padding:2px 8px}
.tag.lo{color:var(--text);background:var(--accent-tint);box-shadow:inset 0 0 0 1px var(--accent-edge)}
.inst .actions{margin-top:14px}
.inst .res-line{margin-top:10px;font-size:13.5px;color:var(--muted)}
.inst .res-line b{color:var(--ready)}
.inst.busy{border-color:var(--accent-edge)}
.prob{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border-radius:12px;background:var(--stone-2);border:1px solid var(--line);margin-top:10px}
.prob .ic{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;flex:none;font-weight:800;font-size:14px}
.prob.open .ic{background:rgba(240,164,58,.15);color:var(--amber)}
.prob.fixed .ic{background:rgba(69,185,124,.15);color:var(--ready)}
.prob.off .ic{background:var(--stone-3);color:var(--faint)}
.prob .grow{flex:1;min-width:0}
.prob b{display:block;font-weight:650}
.prob p{margin:3px 0 0;color:var(--muted);font-size:13.5px}
.prob .actions{margin-top:10px}
.prob.fixed b{color:var(--muted);font-weight:600;text-decoration:line-through;text-decoration-color:rgba(255,255,255,.25)}
.crashn{display:flex;align-items:center;gap:14px;padding:14px 16px;margin:0 0 12px;border-radius:14px;background:linear-gradient(90deg,rgba(255,90,95,.13),var(--stone-2) 60%);border:1px solid var(--accent-edge)}
.crashn .boom{width:40px;height:40px;border-radius:10px;display:grid;place-items:center;background:rgba(255,90,95,.15);color:var(--missing);flex:none;font:800 20px var(--display)}
.crashn .grow{flex:1;min-width:0}
.crashn b{display:block}
.crashn p{margin:2px 0 0;color:var(--muted);font-size:13.5px}
.errline{font:12px/1.5 ui-monospace,Consolas,monospace;color:var(--faint);background:var(--deep);border-radius:8px;padding:8px 10px;margin-top:12px;overflow-wrap:anywhere}
.boost{display:flex;align-items:center;gap:14px;padding:14px 16px;margin:0 0 18px;border-radius:14px;background:linear-gradient(90deg,rgba(242,184,75,.10),var(--stone-2) 55%);border:1px solid color-mix(in srgb,var(--amber) 30%,var(--stone))}
.boost .bolt{width:40px;height:40px;border-radius:10px;display:grid;place-items:center;background:rgba(242,184,75,.14);color:#f2b84b;flex:none}
.boost .grow{flex:1;min-width:0}
.boost b{display:block}
.boost p{margin:2px 0 0;color:var(--muted);font-size:13.5px}
.pmod{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:10px;background:var(--stone-2);border:1px solid var(--line);margin-top:8px;cursor:pointer}
.pmod input{width:18px;height:18px;accent-color:var(--accent);flex:none}
.pmod .grow{flex:1;min-width:0}
.pmod b{display:block;font-weight:650}
.pmod p{margin:1px 0 0;color:var(--muted);font-size:13px}
.pmod.na{opacity:.5;cursor:default}
.pmod .tag{flex:none}
.carry{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:14px;padding:12px 14px;border-radius:12px;background:var(--stone-2);border:1px solid var(--line)}
.carry select{width:auto;min-width:260px;height:36px}
.chg{padding:14px 0;border-top:1px solid var(--stone-3)}
.chg:first-of-type{border-top:0}
.chg-h{display:flex;align-items:center;gap:12px}
.chg-h .grow{flex:1;min-width:0}
.chg-h b{display:block}
.chg-h .vv{color:var(--muted);font-size:13px}
.chg-h .vv span{color:var(--ready);font-weight:650}
.cl{margin:10px 0 0 46px;color:var(--muted);font-size:13.5px;line-height:1.55;max-height:9.5em;overflow:hidden;position:relative}
.cl.open{max-height:none}
.cl:not(.open)::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2.5em;background:linear-gradient(transparent,var(--stone))}
.cl ul{margin:4px 0;padding-left:18px}
.cl b{color:var(--text)}
.cl code{background:var(--deep);padding:0 5px;border-radius:4px;font-size:12.5px}
.cl-more{margin:4px 0 0 46px}
.catch{display:flex;align-items:center;gap:14px;padding:14px 16px;margin:0 0 12px;border-radius:14px;background:linear-gradient(90deg,rgba(69,185,124,.12),var(--stone-2) 60%);border:1px solid color-mix(in srgb,var(--ready) 30%,var(--stone))}
.catch .grow{flex:1;min-width:0}
.catch b{display:block}
.catch p{margin:2px 0 0;color:var(--muted);font-size:13.5px}
.newver{display:flex;align-items:center;gap:16px;padding:16px 18px;margin:0 0 24px;border-radius:14px;
  background:linear-gradient(90deg,var(--accent-tint),var(--stone-2) 70%);border:1px solid var(--accent-edge)}
.newver .big{font:800 26px/1 var(--display);color:var(--accent-2);min-width:64px;text-align:center}
.newver .grow{flex:1;min-width:0}
.newver b{display:block;font-size:16px}
.newver p{margin:2px 0 0;color:var(--muted)}
.kindseg button{height:36px;padding:0 16px;font-size:14.5px}
.dot.own{background:var(--text)}
.slot .badge{position:absolute;left:6px;top:6px;font:800 10.5px var(--body);background:var(--amber);color:#1a1205;border-radius:5px;padding:1px 5px}
.cell.own .slot{cursor:pointer}
.drop{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;border:2px dashed var(--edge);border-radius:14px;padding:30px 20px;text-align:center;color:var(--muted);cursor:pointer;margin-top:16px;transition:border-color .12s, background .12s}
.drop:hover,.drop.over{border-color:var(--accent);background:var(--accent-tint);color:var(--text)}
.drop b{color:var(--text);font-size:16px}
.howto{margin:14px 0 0;padding-left:20px;color:var(--muted);font-size:14px;display:grid;gap:4px}
.frow{display:flex;align-items:center;gap:12px;padding:10px 12px;background:var(--stone-2);border:1px solid var(--line);border-radius:10px;margin-top:8px}
.frow .body{flex:1;min-width:0}
.frow .t{font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.frow .s{color:var(--faint);font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.frow select{width:170px;height:34px}
.frow select.unset{border-color:var(--amber)}
.dropcover{position:fixed;inset:0;z-index:50;background:rgb(var(--glass) / .82);display:grid;place-items:center;pointer-events:none}
.dropcover div{border:3px dashed var(--accent);border-radius:18px;padding:40px 60px;font:800 24px var(--display);color:var(--text);background:var(--accent-tint)}

/* ---------- ports ---------- */
.port{background:var(--stone-2);border-radius:12px;padding:18px;margin-bottom:12px}
.port-top{display:flex;gap:14px;align-items:center}
.port-top .body{flex:1;min-width:0}
.port-top .t{font-weight:700;font-size:16px}
.port-top .s{color:var(--muted);font-size:13.5px}
.port .actions{margin-top:14px}
.status{display:inline-flex;align-items:center;gap:8px;font-weight:650;font-size:13.5px}
.status.working{color:var(--amber)} .status.built{color:var(--ready)} .status.missing{color:var(--missing)}
.pulse{width:9px;height:9px;border-radius:50%;background:currentColor;animation:p 1.6s ease-in-out infinite}
@keyframes p{50%{opacity:.25}}
details.notes{margin-top:12px}
details.notes summary{cursor:pointer;color:var(--muted);font-size:13.5px}
details.notes pre{white-space:pre-wrap;font:13px/1.55 var(--body);background:var(--deep);padding:12px 14px;border-radius:8px;color:var(--muted);max-height:300px;overflow:auto}
.empty{background:var(--stone-2);border-radius:12px;padding:34px;text-align:center;color:var(--muted)}
.empty h3{color:var(--text);margin-bottom:6px}

/* ---------- settings ---------- */
.settings{display:grid;gap:30px;max-width:640px}
.settings section{display:grid;gap:14px}
.ok{color:var(--ready);font-weight:650}

/* ---------- modal / toast ---------- */
.scrim{position:fixed;inset:0;background:rgb(0 0 0 / calc(.75 * var(--shk)));display:grid;place-items:center;z-index:30;padding:20px}
.modal{background:var(--stone);border:1px solid var(--edge);border-radius:14px;width:min(600px,100%);max-height:92vh;overflow:auto;padding:26px 28px}
.modal h2{font:800 22px/1.2 var(--display);margin:0 0 6px}
.facts{display:grid;grid-template-columns:auto 1fr;gap:8px 18px;margin:18px 0;font-size:14px}
.facts dt{color:var(--faint)} .facts dd{margin:0;min-width:0;overflow-wrap:anywhere}
.reqs{display:grid;gap:8px;margin:16px 0;padding:14px 16px;background:var(--deep);border-radius:10px;font-size:14px}
.req{display:flex;gap:10px;align-items:center}
.req .y{color:var(--ready);font-weight:800;width:16px} .req .x{color:var(--missing);font-weight:800;width:16px}
.cmd{display:flex;gap:8px;margin-top:10px}
.cmd code{flex:1;background:var(--deep);border-radius:8px;padding:10px 12px;font:12.5px ui-monospace,Consolas,monospace;overflow-x:auto;white-space:nowrap}
.modal .foot{display:flex;justify-content:flex-end;gap:10px;margin-top:22px}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:rgb(var(--toast));color:var(--toast-ink);padding:11px 18px 11px 14px;border-radius:10px;font-weight:650;z-index:40;box-shadow:0 10px 30px rgb(0 0 0 / calc(.5 * var(--shk)));display:flex;align-items:center;gap:10px;animation:toastIn .18s ease-out}
.toast::before{content:"";width:18px;height:18px;border-radius:50%;background:var(--accent) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 18 18'%3E%3Cpath d='M5 9.5l2.6 2.6L13 6.6' fill='none' stroke='white' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center/18px no-repeat;flex:none}
@keyframes toastIn{from{opacity:0;transform:translate(-50%,8px)}}
section.enter{animation:pageIn .16s ease-out}
@keyframes pageIn{from{opacity:0;transform:translateY(4px)}}
.version{font-size:12px;color:var(--faint);margin-top:8px}
.side .foot .upd{text-decoration:none;font-size:13px;color:var(--text);display:flex;width:100%;align-items:center;gap:8px;margin:0 0 12px;padding:10px 12px;border-radius:9px;border:1px solid var(--accent-edge);background:var(--accent-tint);color:var(--text);font-weight:650;font-size:13px;cursor:pointer;text-align:left}
.side .foot .upd:hover{border-color:var(--accent)}
.side .foot .upd b{color:var(--accent-2)}
.kbd{display:inline-block;font:600 11px ui-monospace,Consolas,monospace;color:var(--faint);border:1px solid var(--edge);border-radius:5px;padding:1px 6px;position:absolute;right:14px;top:13px}
.searchbar .q input:focus + .kbd{display:none}
code.inline{background:var(--deep);padding:1px 6px;border-radius:5px;font-size:13px}
.spin{width:16px;height:16px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;animation:s .7s linear infinite;display:inline-block;vertical-align:-3px}
@keyframes s{to{transform:rotate(360deg)}}

@media (max-width:820px){
  .app{grid-template-columns:1fr;background:var(--stone)}
  .side{position:static;height:auto;flex-direction:row;flex-wrap:wrap;padding:12px}
  .brand{padding:6px 10px;width:100%}
  .nav{width:auto}
  .side .foot{display:none}
  main{padding:24px 18px 60px}
  .launchers{grid-template-columns:1fr}
  .page-h{flex-direction:column;align-items:flex-start}
}

/* ================= premium layer ================= */
::selection{background:rgb(var(--acc) / .45);color:#fff}
*{scrollbar-width:thin;scrollbar-color:var(--stone-4) transparent}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-thumb{background:var(--stone-4);border-radius:10px;border:2px solid var(--stone)}
::-webkit-scrollbar-thumb:hover{background:var(--edge)}
body{background-attachment:fixed}
.side{border-right:1px solid var(--stone)}
h1{background:linear-gradient(180deg,var(--text) 30%,color-mix(in srgb,var(--text) 72%,var(--stone)));-webkit-background-clip:text;background-clip:text;color:transparent}
.page-h{animation:rise .5s cubic-bezier(.2,.9,.3,1) both}

/* brand mark drops in */
.mark i{animation:markIn .55s cubic-bezier(.2,1.5,.4,1) both;transition:transform .35s cubic-bezier(.3,1.4,.5,1)}
.mark i:nth-child(2){animation-delay:.07s}.mark i:nth-child(3){animation-delay:.14s}.mark i:nth-child(4){animation-delay:.21s}
@keyframes markIn{from{transform:translateY(-10px) scale(.5);opacity:0}}

/* sliding selection: sidebar + segmented controls */
#navPill{position:absolute;border-radius:8px;background:var(--stone-2);box-shadow:inset 3px 0 0 var(--accent),0 6px 18px -10px rgb(0 0 0 / calc(.8 * var(--shk)));
  transition:top .38s cubic-bezier(.3,1.25,.5,1),height .38s cubic-bezier(.3,1.25,.5,1);pointer-events:none}
.nav{position:relative;z-index:1}
.nav.on{background:transparent;box-shadow:none}
.nav svg{transition:transform .25s cubic-bezier(.3,1.4,.5,1)}
.nav:hover svg{transform:scale(1.12)}
.seg{position:relative}
.seg .segpill{position:absolute;top:3px;bottom:3px;border-radius:6px;background:var(--stone-3);box-shadow:0 2px 8px -2px rgb(0 0 0 / calc(.6 * var(--shk)));
  transition:left .32s cubic-bezier(.3,1.25,.5,1),width .32s cubic-bezier(.3,1.25,.5,1),opacity .2s;pointer-events:none}
.seg button{position:relative;z-index:1;transition:color .2s}
.seg.pilled button.on{background:transparent}

/* buttons */
.btn{transition:transform .14s ease,background .18s,border-color .18s,box-shadow .25s,color .18s}
.btn:active:not(:disabled){transform:scale(.965)}
.btn.go{background:linear-gradient(180deg,var(--accent),var(--accent-3));border-color:var(--accent);position:relative;overflow:hidden;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.2),inset 0 -3px 0 rgb(0 0 0 / calc(.22 * var(--shk))),0 8px 22px -10px rgb(var(--acc) / .7)}
.btn.go:hover:not(:disabled){background:linear-gradient(180deg,var(--accent-2),var(--accent));border-color:var(--accent-2);transform:translateY(-1px);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.25),inset 0 -3px 0 rgb(0 0 0 / calc(.2 * var(--shk))),0 14px 30px -10px rgb(var(--acc2) / .85)}
.btn.go::after{content:"";position:absolute;inset:0;background:linear-gradient(105deg,transparent 35%,rgba(255,255,255,.32) 50%,transparent 65%);
  transform:translateX(-130%);transition:transform .7s ease;pointer-events:none}
.btn.go:hover::after{transform:translateX(130%)}
.btn:not(.go):hover:not(:disabled){border-color:var(--edge-2)}

/* cards light up where the mouse is */
.lopt,.res,.folder,.frow,.port,.li,.newver,.banner{position:relative;isolation:isolate}
.lopt::before,.res::before,.folder::before,.frow::before,.port::before,.li::before,.newver::before{content:"";position:absolute;inset:0;border-radius:inherit;
  background:radial-gradient(280px circle at var(--mx,50%) var(--my,50%),rgb(var(--acc2) / .12),transparent 62%);opacity:0;transition:opacity .3s;pointer-events:none;z-index:-1}
.lopt:hover::before,.res:hover::before,.folder:hover::before,.frow:hover::before,.port:hover::before,.li:hover::before,.newver:hover::before{opacity:1}
.lopt{transition:border-color .2s,background .25s,transform .2s}
.lopt:hover{transform:translateY(-1px)}
.lopt.on .radio::after{animation:pop .3s cubic-bezier(.3,1.6,.5,1)}
@keyframes pop{from{transform:scale(0)}}

/* things ease in, one after another */
.rise{animation:rise .5s cubic-bezier(.2,.9,.3,1) both;animation-delay:calc(var(--i,0) * 32ms)}
@keyframes rise{from{opacity:0;transform:translateY(12px) scale(.98)}}

/* mod slots tilt in 3D */
.inv{perspective:900px}
.slot{transform-style:preserve-3d;will-change:transform}
.slot img,.slot .letter{transition:transform .25s cubic-bezier(.3,1.3,.5,1)}
.cell:not(.ghost):hover .slot img,.cell:not(.ghost):hover .slot .letter{transform:translateZ(22px) scale(1.07)}
.cell .cap{transition:color .2s}
.cell:not(.ghost):hover .cap{color:var(--text)}
.cell.leaving{animation:leave .28s ease forwards}
@keyframes leave{to{opacity:0;transform:scale(.7)}}

/* windows and pop-ups */
.scrim{backdrop-filter:blur(8px) saturate(120%);-webkit-backdrop-filter:blur(8px);animation:fadeIn .2s ease}
.modal{animation:modalIn .34s cubic-bezier(.2,1.25,.4,1);box-shadow:0 40px 90px -24px rgb(0 0 0 / calc(.85 * var(--shk))),0 0 0 1px rgb(var(--hi) / .04)}
@keyframes modalIn{from{opacity:0;transform:translateY(16px) scale(.95)}}
@keyframes fadeIn{from{opacity:0}}
.toast{background:rgb(var(--toast) / .9);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);animation:toastIn .4s cubic-bezier(.2,1.35,.4,1)}
@keyframes toastIn{from{opacity:0;transform:translate(-50%,18px) scale(.94)}}
.dropcover{animation:fadeIn .15s ease}
.dropcover div{animation:modalIn .3s cubic-bezier(.2,1.25,.4,1)}
.drop.over{transform:scale(1.015)}

/* progress */
.bar{height:10px;border-radius:6px;background:var(--well);box-shadow:inset 0 1px 3px rgb(0 0 0 / calc(.6 * var(--shk)))}
.bar div{background:linear-gradient(90deg,var(--accent-3),var(--accent-2));position:relative;overflow:hidden;border-radius:6px;box-shadow:0 0 18px rgb(var(--acc2) / .45);transition:width .45s cubic-bezier(.3,1,.5,1)}
.bar div::after{content:"";position:absolute;inset:0;background-image:repeating-linear-gradient(-45deg,rgba(255,255,255,.16) 0 8px,transparent 8px 16px);background-size:22.6px 22.6px;animation:stripes .7s linear infinite}
@keyframes stripes{to{background-position:22.6px 0}}
.now{transition:opacity .18s}
.now.swap{opacity:.35}

/* search placeholders */
.skel{display:flex;gap:14px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--stone-3)}
.skel i{display:block;border-radius:8px;background:linear-gradient(90deg,var(--line) 0%,var(--stone-4) 50%,var(--line) 100%);background-size:200% 100%;animation:shimmer 1.15s linear infinite}
.skel i:first-child{width:44px;height:44px;flex:none}
.skel span{flex:1;display:grid;gap:8px}
@keyframes shimmer{from{background-position:200% 0}to{background-position:-200% 0}}

/* new-version banner */
.newver{overflow:hidden;animation:rise .55s cubic-bezier(.2,.9,.3,1) both}
.newver::after{content:"";position:absolute;inset:0;background:linear-gradient(110deg,transparent 30%,rgb(var(--hi) / .06) 45%,transparent 60%);animation:sheen 4s ease-in-out infinite;pointer-events:none}
@keyframes sheen{from{transform:translateX(-100%)}to{transform:translateX(100%)}}
.newver .big{text-shadow:0 0 26px rgb(var(--acc2) / .55)}
.nav .dot-new{animation:ping 1.8s ease-out infinite}
@keyframes ping{0%{box-shadow:0 0 0 0 rgb(var(--acc2) / .55)}80%,100%{box-shadow:0 0 0 7px rgb(var(--acc2) / 0)}}

/* inputs */
input,select{transition:border-color .18s,box-shadow .2s}
input:focus,select:focus{box-shadow:0 0 0 3px rgb(var(--acc) / .2)}
.searchbar .q input:focus{box-shadow:0 0 0 3px rgb(var(--acc) / .2),0 10px 30px -14px rgb(var(--acc2) / .5)}
.searchbar .q svg{transition:color .2s}
.searchbar .q:focus-within svg{color:var(--accent-2)}

#burst{position:fixed;inset:0;pointer-events:none;z-index:60}


/* ---------- premium pass 2 ---------- */
.n,.count,.now,.tag,.version,.inst-ico,#ringPct,.pal .hint,.big{font-variant-numeric:tabular-nums}
h1{font-variation-settings:"wght" 760;letter-spacing:-.7px}

/* sidebar search pill */
.kpill{white-space:nowrap;display:flex;align-items:center;gap:9px;margin:-8px 0 14px;padding:0 10px 0 12px;height:36px;border-radius:9px;border:1px solid var(--line);background:var(--stone);color:var(--faint);cursor:pointer;font-size:13.5px;text-align:left;width:100%;transition:border-color .2s,color .2s,background .2s}
.kpill:hover{border-color:var(--edge);color:var(--muted);background:var(--stone)}
.kpill svg{width:15px;height:15px;flex:none}
.kpill kbd,.pal kbd{margin-left:auto;white-space:nowrap;font:600 11px/1 var(--body);padding:4px 6px;border-radius:5px;background:var(--stone-3);color:var(--muted);box-shadow:inset 0 -1px 0 rgb(0 0 0 / calc(.4 * var(--shk)))}

/* command palette */
.pal-scrim{position:fixed;inset:0;z-index:70;background:rgb(0 0 0 / calc(.55 * var(--shk)));backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);display:flex;justify-content:center;align-items:flex-start;padding-top:13vh;animation:fadeIn .15s ease}
.pal{width:min(620px,92vw);background:rgb(var(--glass) / .92);backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);border:1px solid rgb(var(--hi) / .08);border-radius:14px;overflow:hidden;
  box-shadow:0 50px 100px -30px rgb(0 0 0 / calc(.9 * var(--shk))),0 0 0 1px rgb(0 0 0 / calc(.5 * var(--shk))),inset 0 1px 0 rgb(var(--hi) / .05);animation:palIn .22s cubic-bezier(.2,1.2,.4,1)}
@keyframes palIn{from{opacity:0;transform:translateY(-8px) scale(.97)}}
.pal-q{display:flex;align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid rgb(var(--hi) / .06)}
.pal-q svg{width:18px;height:18px;color:var(--accent-2);flex:none}
.pal-q input{height:56px;border:0;background:none;font-size:17px;padding:0}
.pal-q input:focus{box-shadow:none}
.pal-list{max-height:min(420px,56vh);overflow:auto;padding:6px}
.pal-g{padding:10px 12px 4px;font-size:12px;color:var(--faint);font-weight:650}
.pi{display:flex;align-items:center;gap:12px;padding:9px 12px;border-radius:9px;cursor:pointer;color:var(--muted)}
.pi .pico{width:28px;height:28px;border-radius:7px;background:var(--stone-3);display:grid;place-items:center;flex:none;overflow:hidden;color:var(--text)}
.pi .pico img{width:100%;height:100%;object-fit:cover}
.pi .pico svg{width:15px;height:15px}
.pi .pt{color:var(--text);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pi .ps{font-size:12.5px;color:var(--faint);margin-left:auto;white-space:nowrap;padding-left:12px}
.pi mark{background:none;color:var(--accent-2)}
.pi.sel{background:linear-gradient(90deg,rgb(var(--acc) / .2),rgb(var(--acc) / .06));color:var(--text);box-shadow:inset 2px 0 0 var(--accent-2)}
.pi.sel .pico{background:var(--accent);color:#fff}
.pal-foot{display:flex;gap:16px;padding:9px 16px;border-top:1px solid rgb(var(--hi) / .06);font-size:12px;color:var(--faint)}
.pal-foot kbd{margin:0 4px 0 0}
.pal-none{padding:22px 16px;color:var(--faint);text-align:center}

/* switches instead of checkboxes */
.check input[type=checkbox]{appearance:none;-webkit-appearance:none;width:36px;height:21px;border-radius:21px;background:var(--stone-3);border:1px solid var(--edge);position:relative;cursor:pointer;flex:none;margin:0;
  transition:background .22s,border-color .22s,box-shadow .22s}
.check input[type=checkbox]::after{content:"";position:absolute;top:2px;left:2px;width:15px;height:15px;border-radius:50%;background:var(--knob);box-shadow:0 1px 3px rgb(0 0 0 / calc(.5 * var(--shk)));transition:transform .25s cubic-bezier(.3,1.5,.5,1),background .2s}
.check input[type=checkbox]:checked{background:var(--accent);border-color:var(--accent-2);box-shadow:0 0 14px -2px rgb(var(--acc2) / .6)}
.check input[type=checkbox]:checked::after{transform:translateX(15px);background:#fff}
.check:hover input[type=checkbox]:not(:checked){border-color:var(--edge-2)}
.check{gap:10px}

/* dropdowns with a chevron */
select{appearance:none;-webkit-appearance:none;padding-right:34px;cursor:pointer;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23a9a6ad' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 12px center}
select:hover{border-color:var(--edge-2)}
select option{background:var(--stone-2)}

/* button ripple */
.btn{position:relative;overflow:hidden;transition:background .18s,border-color .18s,transform .15s,box-shadow .2s}
.btn:active:not(:disabled){transform:translateY(0) scale(.97)}
.ripple{position:absolute;border-radius:50%;background:rgba(255,255,255,.32);transform:scale(0);animation:ripple .6s cubic-bezier(.2,.8,.3,1) forwards;pointer-events:none}
@keyframes ripple{to{transform:scale(1);opacity:0}}

/* frosted page bar on scroll */
.topbar{position:fixed;top:0;left:232px;right:0;z-index:30;height:56px;display:flex;align-items:center;gap:14px;padding:0 48px;
  background:rgb(var(--glass) / .72);backdrop-filter:blur(16px) saturate(150%);-webkit-backdrop-filter:blur(16px) saturate(150%);border-bottom:1px solid rgb(var(--hi) / .06);
  box-shadow:none;transform:translateY(-102%);visibility:hidden;transition:transform .32s cubic-bezier(.2,.9,.3,1),visibility 0s .32s,box-shadow .3s}
.topbar.show{transform:none;visibility:visible;transition:transform .32s cubic-bezier(.2,.9,.3,1),box-shadow .3s;box-shadow:0 12px 30px -18px rgb(0 0 0 / calc(.8 * var(--shk)))}
.topbar .tt{font:800 17px/1 var(--display);letter-spacing:-.2px;opacity:0;transform:translateY(8px) scale(1.25);transform-origin:left center;transition:opacity .3s .05s,transform .4s .05s cubic-bezier(.2,.9,.3,1)}
.topbar.show .tt{opacity:1;transform:none}
.topbar .top-up{margin-left:auto}

/* live install view */
.live{display:flex;gap:20px;align-items:flex-start;padding:18px 20px;border-radius:14px;background:var(--stone-2);border:1px solid var(--line)}
.ring{position:relative;width:74px;height:74px;flex:none}
.ring svg{width:100%;height:100%;transform:rotate(-90deg)}
.ring circle{fill:none;stroke-width:6}
.ring .trk{stroke:var(--deep)}
.ring .arc{stroke:url(#ringGrad);stroke-linecap:round;stroke-dasharray:175.93;stroke-dashoffset:175.93;transition:stroke-dashoffset .5s cubic-bezier(.3,1,.5,1);filter:drop-shadow(0 0 6px rgb(var(--acc2) / .55))}
.ring #ringPct{position:absolute;inset:0;display:grid;place-items:center;font:800 17px var(--display)}
.ring.done .arc{stroke:var(--ready);filter:drop-shadow(0 0 6px rgba(69,185,124,.6))}
.live .grow{flex:1;min-width:0}
.live b{font:700 17px/1.3 var(--display)}
.live .now{margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.livelist{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;max-height:132px;overflow:hidden;-webkit-mask-image:linear-gradient(to bottom,#000 75%,transparent)}
.livelist:empty{display:none}
.livelist span{font-size:12.5px;padding:4px 10px;border-radius:7px;background:var(--slot);color:var(--text);display:inline-flex;align-items:center;gap:6px;animation:chipIn .4s cubic-bezier(.2,1.4,.4,1)}
.livelist span::before{content:"";width:6px;height:6px;border-radius:2px;background:var(--ready)}
@keyframes chipIn{from{opacity:0;transform:translateY(6px) scale(.8)}}
.progress .bar{display:none}

/* hover labels on slots */
#tip{position:fixed;z-index:80;pointer-events:none;max-width:260px;padding:8px 11px;border-radius:9px;background:rgb(var(--glass) / .94);border:1px solid rgb(var(--hi) / .08);
  box-shadow:0 18px 40px -12px rgb(0 0 0 / calc(.9 * var(--shk)));font-size:12.5px;line-height:1.4;color:var(--muted);opacity:0;transform:translateY(4px);transition:opacity .14s,transform .18s}
#tip.on{opacity:1;transform:none}
#tip b{display:block;color:var(--text);font-size:13.5px;margin-bottom:1px}
#tip em{display:block;font-style:normal;color:var(--accent-2);margin-top:4px;font-size:12px}

/* empty states */
.empty .art{display:block;width:84px;height:84px;margin:0 auto 14px;image-rendering:pixelated;filter:drop-shadow(0 10px 18px rgb(0 0 0 / calc(.6 * var(--shk))))}
.empty .art .bob{animation:bob 3.2s ease-in-out infinite}
@keyframes bob{50%{transform:translateY(-3px)}}

/* start-up splash */
.cell.flash .slot{animation:flash 1.4s ease}
@keyframes flash{0%,60%{box-shadow:inset 3px 3px 0 rgb(0 0 0 / calc(.6 * var(--shk))),0 0 0 3px var(--accent-2),0 0 26px rgb(var(--acc2) / .6)}}
/* ModHub changelog */
.wn-fab{position:fixed;right:22px;bottom:22px;z-index:25;display:flex;align-items:center;gap:8px;height:40px;padding:0 15px 0 12px;border-radius:20px;cursor:pointer;
  border:1px solid rgb(var(--hi) / .08);background:rgb(var(--glass) / .82);backdrop-filter:blur(12px) saturate(140%);-webkit-backdrop-filter:blur(12px) saturate(140%);
  color:var(--muted);font-weight:650;font-size:13.5px;box-shadow:0 14px 34px -14px rgb(0 0 0 / calc(.9 * var(--shk)));transition:color .2s,border-color .2s,transform .2s,box-shadow .25s}
.wn-fab svg{width:17px;height:17px;color:var(--accent-2);transition:transform .4s cubic-bezier(.3,1.6,.5,1)}
.wn-fab:hover{color:var(--text);border-color:rgb(var(--acc2) / .45);transform:translateY(-2px);box-shadow:0 18px 40px -14px rgb(0 0 0 / calc(.9 * var(--shk))),0 0 22px -6px rgb(var(--acc2) / .5)}
.wn-fab:hover svg{transform:rotate(18deg) scale(1.12)}
.wn-dot{position:absolute;top:-2px;right:-2px;width:11px;height:11px;border-radius:50%;background:var(--accent-2);border:2px solid var(--stone);animation:ping 1.8s ease-out infinite}
.wn-pick{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0 2px}
.wn-pick button{height:30px;padding:0 12px;border-radius:15px;border:1px solid var(--edge);background:none;color:var(--muted);font-weight:600;font-size:13px;cursor:pointer}
.wn-pick button.on{background:var(--accent-tint);border-color:var(--accent);color:var(--text)}
.wn{max-height:min(460px,58vh);overflow:auto;margin:14px -6px 0;padding:0 6px}
.wn-v{position:relative;padding:0 0 18px 26px}
.wn-v::before{content:"";position:absolute;left:6px;top:10px;bottom:-4px;width:2px;background:var(--stone-3)}
.wn-v:last-child::before{display:none}
.wn-v::after{content:"";position:absolute;left:1px;top:4px;width:12px;height:12px;border-radius:3px;background:var(--stone-3);box-shadow:0 0 0 3px var(--stone-2)}
.wn-v.fresh::after{background:var(--accent);box-shadow:0 0 0 3px var(--stone-2),0 0 14px rgb(var(--acc2) / .7)}
.wn-v h4{margin:0 0 6px;font:800 16px/1.2 var(--display);display:flex;align-items:center;gap:10px}
.wn-v h4 .now-tag{font:650 11.5px/1 var(--body);padding:4px 8px;border-radius:6px;background:var(--accent-tint);color:var(--accent-2)}
.wn-v ul{margin:0;padding-left:18px;color:var(--muted);font-size:14px;line-height:1.55}
.wn-v li{margin:3px 0}
.wn-v li::marker{color:var(--faint)}
.wn-v.fresh li{color:var(--text)}
#splash{position:fixed;inset:0;z-index:90;background:var(--deep);display:grid;place-items:center;pointer-events:none;transition:opacity .4s ease}
#splash.out{opacity:0}
#splash .in{display:flex;align-items:center;gap:14px;font:800 26px/1 var(--display)}
#splash .mark{width:36px;height:36px;gap:3px}
#splash .mark i{animation:tileIn .5s cubic-bezier(.2,1.5,.4,1) both}
#splash .mark i:nth-child(2){animation-delay:.08s} #splash .mark i:nth-child(3){animation-delay:.16s} #splash .mark i:nth-child(4){animation-delay:.24s}
#splash .word{animation:rise .5s .3s cubic-bezier(.2,.9,.3,1) both}
@keyframes tileIn{from{opacity:0;transform:scale(.2) rotate(-20deg)}}
.brand .mark i{transition:transform .3s cubic-bezier(.3,1.6,.5,1)}
.brand:hover .mark i:nth-child(1){transform:translate(-1.5px,-1.5px)} .brand:hover .mark i:nth-child(2){transform:translate(1.5px,-1.5px)}
.brand:hover .mark i:nth-child(3){transform:translate(-1.5px,1.5px)} .brand:hover .mark i:nth-child(4){transform:translate(1.5px,1.5px)}



/* ---------- discover ---------- */
.disc-bar{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:8px}
.disc-for{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:14px;flex-wrap:wrap}
.disc-for select{width:auto;height:36px;padding-left:10px}
.disc-sec{margin-top:34px}
.disc-sec > h3{display:flex;align-items:baseline;gap:10px;margin-bottom:14px}
.disc-sec > h3 small{font:500 13.5px var(--body);color:var(--faint)}
.dgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
.dcard{display:flex;flex-direction:column;gap:10px;padding:16px;border-radius:14px;background:var(--stone-2);border:1px solid var(--line);cursor:pointer;text-align:left;color:inherit;min-width:0;
  transition:transform .25s cubic-bezier(.2,.8,.2,1),border-color .2s,box-shadow .25s}
.dcard:hover{transform:translateY(-3px);border-color:var(--edge);box-shadow:0 18px 40px -22px rgb(0 0 0 / calc(.9 * var(--shk)))}
.dcard .top{display:flex;gap:12px;align-items:center;min-width:0}
.dcard .ico{width:46px;height:46px}
.dcard .nm{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dcard .by{font-size:12.5px;color:var(--faint)}
.dcard .ds{font-size:13.5px;color:var(--muted);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.9em}
.dcard .why{font-size:12.5px;color:var(--link);font-weight:600}
.dcard .ft{display:flex;align-items:center;justify-content:space-between;margin-top:auto;font-size:12.5px;color:var(--faint)}
.dcard.pick{background:linear-gradient(160deg,var(--accent-tint),var(--stone-2) 70%);border-color:var(--accent-edge)}
.dskel{height:168px;border-radius:14px;background:linear-gradient(90deg,var(--stone-2) 0%,var(--stone-3) 50%,var(--stone-2) 100%);background-size:200% 100%;animation:shimmer 1.15s linear infinite}
/* mod page */
.modpage{width:min(880px,100%);max-height:min(88vh,980px);overflow:auto;padding:0}
.mp-head{display:flex;gap:18px;align-items:center;padding:28px 30px 20px}
.mp-head .ico{width:72px;height:72px;border-radius:14px;font-size:28px}
.mp-head h2{margin:0;font:800 26px/1.15 var(--display)}
.mp-head .sub{color:var(--muted);margin-top:4px}
.mp-head .grow{flex:1;min-width:0}
.mp-acts{display:flex;gap:8px;flex-wrap:wrap}
.mp-status{margin:0 30px;display:flex;align-items:center;gap:12px;padding:12px 16px;border-radius:12px;background:var(--stone-3);font-size:14px}
.mp-status b{font-weight:700}
.mp-status.ok{background:color-mix(in srgb,var(--ready) 14%,var(--stone-2));color:var(--text)}
.mp-status.no{background:color-mix(in srgb,var(--amber) 14%,var(--stone-2))}
.mp-status .dot{width:9px;height:9px}
.mp-gal{display:flex;gap:10px;overflow-x:auto;padding:20px 30px 4px;scroll-snap-type:x mandatory}
.mp-gal img{height:190px;border-radius:10px;flex:none;scroll-snap-align:start;object-fit:cover;background:var(--stone-3);cursor:zoom-in}
.mp-grid{display:grid;grid-template-columns:minmax(0,1fr) 250px;gap:28px;padding:20px 30px 30px}
.mp-body{color:var(--muted);font-size:14.5px;line-height:1.65;min-width:0;overflow-wrap:anywhere}
.mp-body h1,.mp-body h2,.mp-body h3{color:var(--text);font:700 17px/1.3 var(--display);margin:18px 0 6px;background:none;-webkit-text-fill-color:currentColor}
.mp-body p{margin:0 0 10px}
.mp-facts{display:grid;gap:14px;align-content:start;font-size:13.5px}
.mp-facts dt{color:var(--faint);font-size:12.5px;margin-bottom:3px}
.mp-facts dd{margin:0;color:var(--text)}
.mp-chip{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:7px;background:var(--stone-3);margin:0 4px 4px 0;font-size:12.5px;color:var(--text);border:0;cursor:pointer}
.mp-chip.static{cursor:default}
.mp-chip .ico{width:18px;height:18px;border-radius:4px;font-size:10px}
.mp-zoom{position:fixed;inset:0;z-index:75;background:rgb(0 0 0 / .85);display:grid;place-items:center;cursor:zoom-out;animation:fadeIn .15s}
.mp-zoom img{max-width:92vw;max-height:88vh;border-radius:10px}
@media (max-width:760px){.mp-grid{grid-template-columns:1fr}}
/* ---------- 3.0: themes and a calmer layout ---------- */
.theming,.theming *{transition:background-color .35s ease,color .35s ease,border-color .35s ease,fill .35s ease !important}
.set-row{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.set-l{width:64px;color:var(--muted);font-weight:600;font-size:14px}
.swatches{display:flex;gap:14px;flex-wrap:wrap}
.sw{display:flex;flex-direction:column;align-items:center;gap:6px;background:none;border:0;padding:0;color:var(--faint);font-size:12.5px;font-weight:600;cursor:pointer}
.sw i{width:34px;height:34px;border-radius:10px;background:var(--sw);box-shadow:0 0 0 2px var(--stone),0 0 0 2px transparent;transition:box-shadow .25s,transform .25s cubic-bezier(.3,1.5,.5,1)}
.sw:hover i{transform:translateY(-2px)}
.sw.on i{box-shadow:0 0 0 2px var(--stone),0 0 0 4px var(--sw)}
.sw.on{color:var(--text)}
.settings{gap:0}
.settings > section,.settings > details{padding:26px 0;border-top:1px solid var(--line)}
.settings > section:first-child{border-top:0;padding-top:0}
details.adv{display:grid;gap:14px}
details.adv > summary{font:700 18px/1.3 var(--display);cursor:pointer;list-style:none;display:flex;align-items:center;gap:10px}
details.adv > summary::-webkit-details-marker{display:none}
details.adv > summary::after{content:"";width:8px;height:8px;border-right:2px solid var(--faint);border-bottom:2px solid var(--faint);transform:rotate(-45deg);transition:transform .2s}
details.adv[open] > summary::after{transform:rotate(45deg)}
details.adv[open]{display:grid}
details.adv[open] > *:not(summary){margin-top:14px}
.inv-tools{display:flex;gap:10px;align-items:center}
.boostbtn svg{color:var(--amber)}
.side .foot{display:grid;gap:10px}
:root[data-mode="light"] .mark i{background:#c9c8d1} :root[data-mode="light"] .mark i:nth-child(1){background:var(--accent)} :root[data-mode="light"] .mark i:nth-child(4){background:var(--tile)}
:root[data-mode="light"] .slot{box-shadow:inset 3px 3px 0 rgb(0 0 0 / .14),inset -3px -3px 0 rgb(255 255 255 / .7)}
:root[data-mode="light"] .modal,:root[data-mode="light"] .pal{box-shadow:0 30px 80px -24px rgb(20 20 30 / .35),0 0 0 1px rgb(0 0 0 / .06)}
:root[data-mode="light"] .btn.go,:root[data-mode="light"] .nav.on{box-shadow:none}


/* tidier pages */
#tab-install > .block:not(:has(#installBtn)){padding:18px 20px 20px;margin-bottom:12px;border:1px solid var(--line);border-radius:18px;background:color-mix(in srgb,var(--stone-2) 80%,transparent)}
#tab-install > .block:not(:has(#installBtn)) + .block{padding-top:18px}
#tab-install > .block:has(#installBtn){padding-top:10px}
:root[data-radius="sharp"] #tab-install > .block{border-radius:3px}
:root[data-radius="round"] #tab-install > .block{border-radius:22px}
.page-h{margin-bottom:22px}
.inv-h{margin:34px 0 14px}

/* pictures */
.dcard.has-shot{padding-top:0;overflow:hidden}
.dcard .shot{margin:0 -16px 2px;aspect-ratio:16/7;overflow:hidden;background:var(--stone-3);position:relative}
.dcard .shot.empty{background:linear-gradient(135deg,var(--accent-tint),color-mix(in srgb,var(--stone-3) 70%,transparent))}
.dcard .shot .mid{position:absolute;inset:0;display:grid;place-items:center}
.dcard .shot .mid .ico{width:64px;height:64px;border-radius:14px;font-size:26px;box-shadow:0 12px 28px -12px rgb(0 0 0 / calc(.8 * var(--shk)))}
.dcard .shot.empty{background:radial-gradient(120% 140% at 50% 0%,var(--accent-tint),transparent 70%),repeating-linear-gradient(45deg,rgb(var(--hi) / .025) 0 10px,transparent 10px 20px),var(--stone-3)}
.dcard.has-shot .shot.empty ~ .top .ico{visibility:hidden;width:0;margin-right:-12px}
.dcard .shot > img{position:absolute;inset:0;z-index:1;width:100%;height:100%;object-fit:cover;display:block;transition:transform .5s cubic-bezier(.2,.8,.2,1)}
.dcard:hover .shot > img{transform:scale(1.05)}
.dcard.has-shot .top{position:relative;align-items:flex-end}
.dcard.has-shot .top .ico{margin-top:-30px}
.dcard.has-shot .top .ico{box-shadow:0 0 0 3px var(--stone-2),0 8px 18px -8px rgb(0 0 0 / calc(.8 * var(--shk)))}
.mp-banner{height:240px;overflow:hidden;cursor:zoom-in;position:relative;background:var(--stone-3)}
.mp-banner img{width:100%;height:100%;object-fit:cover;display:block}
.mp-banner::after{content:"";position:absolute;inset:0;background:linear-gradient(to bottom,transparent 45%,var(--stone) 100%)}
.mp-head.on-banner{margin-top:-46px;position:relative;z-index:1;align-items:flex-end}
.mp-head.on-banner .ico{box-shadow:0 0 0 4px var(--stone),0 14px 30px -12px rgb(0 0 0 / calc(.9 * var(--shk)))}
.mp-gal img{height:170px;width:auto;aspect-ratio:16/9;image-rendering:auto}
.mp-zoom{display:flex;flex-direction:column;gap:12px;align-items:center;justify-content:center}
.mp-zoom img{max-width:94vw;max-height:84vh;image-rendering:auto}
.mp-zoom span{color:#f3f1ef;font-size:14px}
.ico img{image-rendering:auto}

/* theme tiles */
.theme-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.ttile{position:relative;height:118px;border-radius:16px;border:1px solid var(--line);background:var(--tbg);overflow:hidden;cursor:pointer;padding:14px;text-align:left;
  display:flex;flex-direction:column;justify-content:flex-end;gap:2px;transition:transform .25s cubic-bezier(.2,.8,.2,1),box-shadow .25s,border-color .2s}
.ttile:hover{transform:translateY(-3px);box-shadow:0 16px 34px -18px rgb(0 0 0 / calc(.9 * var(--shk)))}
.ttile.dk{color:#f3f1ef;border-color:#26262c} .ttile.lt{color:#17161a;border-color:#dedde3}
.ttile b{font:700 15.5px/1.2 var(--display)}
.ttile small{font-size:12px;opacity:.7}
.tbars{position:absolute;top:14px;left:14px;right:14px;display:flex;gap:7px}
.tbars i{width:30px;height:7px;border-radius:4px;background:var(--tc)}
.tbars s{flex:1;height:7px;border-radius:4px;background:currentColor;opacity:.14}
.ttile.on{box-shadow:0 0 0 2px var(--stone-2),0 0 0 4px var(--tc)}
.ttile.on::after{content:"";position:absolute;top:10px;right:10px;width:20px;height:20px;border-radius:50%;background:var(--tc);
  -webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20'%3E%3Ccircle cx='10' cy='10' r='10'/%3E%3C/svg%3E");
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none' stroke='white' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5.5 10.5l3 3 6-6.5'/%3E%3C/svg%3E")}
.ttile.on .tbars{right:40px}
.ttile input[type=color]{position:absolute;opacity:0;width:1px;height:1px;bottom:0;left:0;pointer-events:none}
.ap-more{border-top:1px solid var(--line);padding-top:14px}
.ap-more > summary{cursor:pointer;list-style:none;display:flex;align-items:baseline;gap:10px;font-weight:650;color:var(--text)}
.ap-more > summary::-webkit-details-marker{display:none}
.ap-more > summary::before{content:"";width:7px;height:7px;border-right:2px solid var(--faint);border-bottom:2px solid var(--faint);transform:rotate(-45deg);transition:transform .2s;align-self:center}
.ap-more[open] > summary::before{transform:rotate(45deg)}
.ap-more > summary span{font-weight:400;font-size:13px;color:var(--faint)}
.ap-more .ap-opts{margin-top:16px}
:root[data-radius="sharp"] .ttile{border-radius:3px}
:root[data-radius="round"] .ttile{border-radius:22px}

/* tidy More options */
.ap-more .ap-opts{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-top:16px}
.ap-group{display:grid;gap:14px;align-content:start;padding:16px 18px 18px;border-radius:14px;background:color-mix(in srgb,var(--deep) 55%,transparent);border:1px solid var(--line)}
.ap-group h4{margin:0 0 2px;font:700 13px/1 var(--body);color:var(--faint);letter-spacing:.2px}
.ap-group .opt{display:grid;grid-template-columns:96px 1fr;align-items:center;gap:12px}
.ap-group .opt-l{width:auto;font-size:13px}
.ap-group .seg{justify-self:start}
.ap-group .opt .seg button{height:28px;padding:0 10px;font-size:13px}
.ap-group .range{max-width:none}
.ap-group .opt.reset{grid-template-columns:1fr;justify-items:end;margin-top:2px}
.swatches.mini{gap:8px}
.swatches.mini .sw i{width:24px;height:24px;border-radius:50%}
.swatches.mini .sw.on i{box-shadow:0 0 0 2px var(--stone-2),0 0 0 4px var(--sw)}
:root[data-radius="sharp"] .ap-group{border-radius:3px}
:root[data-radius="round"] .ap-group{border-radius:20px}

.switch-cover{position:fixed;inset:0;z-index:95;display:grid;place-items:center;text-align:center;background:var(--stone);animation:fadeIn .3s ease}
.switch-cover .mark{width:40px;height:40px;gap:3px;margin:0 auto 22px}
.switch-cover .lede{margin:0 auto}
/* how to use */
.help-btn{display:flex;align-items:center;gap:8px;width:100%;padding:8px 12px;border:0;border-radius:8px;background:none;color:var(--muted);font-weight:600;font-size:13.5px;cursor:pointer;text-align:left}
.help-btn svg{width:17px;height:17px;flex:none}
.help-btn:hover{color:var(--text);background:rgb(var(--hi) / .04)}
.howto{width:min(560px,100%)}
.steps-list{list-style:none;counter-reset:st;margin:18px 0 0;padding:0;display:grid;gap:10px}
.steps-list li{counter-increment:st;display:grid;grid-template-columns:30px 1fr auto;grid-template-rows:auto auto;column-gap:12px;align-items:center;padding:12px 14px;border-radius:12px;background:var(--stone-2);border:1px solid var(--line)}
.steps-list li::before{content:counter(st);grid-row:1 / 3;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font:800 13px var(--display);background:var(--accent-tint);color:var(--accent-2)}
.steps-list b{font-size:14.5px}
.steps-list span{grid-column:2;color:var(--muted);font-size:13px;line-height:1.45}
.steps-list .btn{grid-column:3;grid-row:1 / 3}
.howto kbd{font:600 11px/1 var(--body);padding:3px 6px;border-radius:5px;background:var(--stone-3);color:var(--muted)}

/* auto-fixed crashes */
.prob.done b{text-decoration:none;color:var(--text);font-weight:600}
.crashn.fixing{background:linear-gradient(90deg,rgb(var(--acc) / .12),var(--stone-2) 60%);border-color:var(--accent-edge)}
.crashn.fixing .boom{background:var(--accent-tint);color:var(--accent-2)}
.crashn.ok{background:linear-gradient(90deg,color-mix(in srgb,var(--ready) 14%,transparent),var(--stone-2) 60%);border-color:color-mix(in srgb,var(--ready) 32%,var(--stone))}
.crashn.ok .boom{background:color-mix(in srgb,var(--ready) 18%,transparent);color:var(--ready)}
/* ---------- 3.1: backgrounds, customisation, cards ---------- */
:root{zoom:var(--ui-zoom,1);--gdir:180deg;--gpos:50% -12%}
:root[data-dir="corner"]{--gdir:150deg;--gpos:0% 0%}
:root[data-dir="side"]{--gdir:90deg;--gpos:-8% 45%}
:root[data-dir="bottom"]{--gdir:0deg;--gpos:50% 112%}
body,.ap-prev{background-color:var(--stone)}
:root[data-bg="gradient"] :is(body,.ap-prev){background-image:linear-gradient(var(--gdir),rgb(var(--acc) / calc(.46 * var(--bgk,.55))) 0%,rgb(var(--acc) / calc(.14 * var(--bgk,.55))) 38%,transparent 72%)}
:root[data-bg="vivid"] :is(body,.ap-prev){background-image:linear-gradient(var(--gdir),rgb(var(--acc) / calc(.9 * var(--bgk,.55))) 0%,rgb(var(--acc3) / calc(.5 * var(--bgk,.55))) 48%,rgb(var(--acc3) / calc(.16 * var(--bgk,.55))) 100%)}
:root[data-mode="light"][data-bg="vivid"] :is(body,.ap-prev){background-image:linear-gradient(var(--gdir),rgb(var(--acc2) / calc(.75 * var(--bgk,.55))) 0%,rgb(var(--acc2) / calc(.28 * var(--bgk,.55))) 50%,rgb(var(--acc2) / calc(.08 * var(--bgk,.55))) 100%)}
:root[data-bg="glow"] :is(body,.ap-prev){background-image:radial-gradient(1100px 720px at var(--gpos),rgb(var(--acc) / calc(.42 * var(--bgk,.55))),transparent 64%)}
/* 3.7.1: moving backgrounds */
:root[data-bg="aurora"] :is(body,.ap-prev){background-image:radial-gradient(60% 50% at 18% 0%,rgb(var(--acc) / calc(.55 * var(--bgk,.55))),transparent 70%),radial-gradient(55% 45% at 85% 10%,rgb(var(--acc3) / calc(.5 * var(--bgk,.55))),transparent 70%),radial-gradient(70% 50% at 50% 100%,rgb(var(--acc2) / calc(.22 * var(--bgk,.55))),transparent 70%)}
:root[data-bg="aurora"] body::before{content:"";position:fixed;inset:-25%;z-index:-1;pointer-events:none;
  background:radial-gradient(28% 22% at 30% 28%,rgb(var(--acc2) / calc(.5 * var(--bgk,.55))),transparent 70%),radial-gradient(26% 20% at 70% 22%,rgb(var(--acc3) / calc(.45 * var(--bgk,.55))),transparent 70%),radial-gradient(30% 24% at 50% 40%,rgb(var(--acc) / calc(.35 * var(--bgk,.55))),transparent 70%);
  filter:blur(30px);animation:aurora 26s ease-in-out infinite alternate}
@keyframes aurora{0%{transform:translate(-6%,-3%) rotate(-4deg) scale(1)}50%{transform:translate(5%,4%) rotate(5deg) scale(1.12)}100%{transform:translate(-2%,6%) rotate(-2deg) scale(.95)}}
:root[data-bg="stars"] :is(body,.ap-prev){background-image:radial-gradient(1000px 640px at var(--gpos),rgb(var(--acc) / calc(.42 * var(--bgk,.55))),transparent 66%),radial-gradient(900px 600px at 100% 100%,rgb(var(--acc3) / calc(.4 * var(--bgk,.55))),transparent 66%)}
:root[data-bg="stars"] body::before,:root[data-bg="stars"] body::after{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
  background-image:radial-gradient(2.4px 2.4px at 12% 18%,rgb(var(--hi)),rgb(var(--hi) / 0)),radial-gradient(1.6px 1.6px at 38% 62%,rgb(var(--hi) / .85),rgb(var(--hi) / 0)),radial-gradient(2.8px 2.8px at 66% 30%,rgb(var(--hi)),rgb(var(--hi) / 0)),radial-gradient(1.6px 1.6px at 84% 74%,rgb(var(--hi) / .8),rgb(var(--hi) / 0)),radial-gradient(2.4px 2.4px at 52% 8%,rgb(var(--acc2)),rgb(var(--acc2) / 0)),radial-gradient(1.8px 1.8px at 24% 88%,rgb(var(--hi) / .85),rgb(var(--hi) / 0)),radial-gradient(2px 2px at 92% 40%,rgb(var(--acc2) / .9),rgb(var(--acc2) / 0)),radial-gradient(1.4px 1.4px at 5% 50%,rgb(var(--hi) / .8),rgb(var(--hi) / 0));
  filter:drop-shadow(0 0 3px rgb(var(--hi) / .6));
  background-size:300px 260px;animation:twinkle 5s ease-in-out infinite alternate}
:root[data-bg="stars"] body::after{background-size:520px 460px;background-position:130px 90px;animation-duration:7s;animation-delay:-3s}
@keyframes twinkle{0%{opacity:.35}100%{opacity:1}}
:root[data-bg="embers"] :is(body,.ap-prev){background-image:linear-gradient(var(--gdir),rgb(var(--acc) / calc(.7 * var(--bgk,.55))) 0%,rgb(var(--acc3) / calc(.35 * var(--bgk,.55))) 40%,transparent 80%)}
:root[data-bg="embers"] body::before,:root[data-bg="embers"] body::after{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
  background-image:radial-gradient(3.5px 3.5px at 10% 20%,rgb(var(--acc2)),rgb(var(--acc2) / 0)),radial-gradient(2.5px 2.5px at 40% 70%,rgb(var(--acc2) / .95),rgb(var(--acc2) / 0)),radial-gradient(4px 4px at 70% 40%,rgb(var(--acc2)),rgb(var(--acc) / 0)),radial-gradient(2.5px 2.5px at 85% 85%,rgb(var(--acc2) / .9),rgb(var(--acc2) / 0)),radial-gradient(3px 3px at 25% 55%,rgb(var(--hi) / .7),rgb(var(--hi) / 0)),radial-gradient(3px 3px at 58% 12%,rgb(var(--acc2) / .9),rgb(var(--acc2) / 0));
  filter:drop-shadow(0 0 4px rgb(var(--acc2) / .9));
  background-size:260px 320px;animation:rise 14s linear infinite;-webkit-mask-image:linear-gradient(to top,#000,transparent 85%);mask-image:linear-gradient(to top,#000,transparent 85%)}
:root[data-bg="embers"] body::after{background-size:380px 460px;animation-duration:22s;background-position:90px 0}
:root[data-bg="embers"][data-dir="top"] body::before,:root[data-bg="embers"][data-dir="top"] body::after{-webkit-mask-image:linear-gradient(to top,#000 30%,transparent);mask-image:linear-gradient(to top,#000 30%,transparent)}
@keyframes rise{to{background-position-y:-920px}}
/* redstone: a glow that pulses like a signal, with dust rising */
:root[data-bg="pulse"] :is(body,.ap-prev){background-image:radial-gradient(1200px 700px at var(--gpos),rgb(var(--acc) / calc(.5 * var(--bgk,.55))),transparent 65%),linear-gradient(var(--gdir),rgb(var(--acc3) / calc(.6 * var(--bgk,.55))),transparent 70%)}
:root[data-bg="pulse"] body::before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;background:radial-gradient(1000px 620px at var(--gpos),rgb(var(--acc2) / calc(.55 * var(--bgk,.55))),transparent 62%);animation:signal 2.2s ease-in-out infinite alternate}
@keyframes signal{0%{opacity:.15}100%{opacity:1}}
:root[data-bg="pulse"] body::after{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
  background-image:radial-gradient(3px 3px at 15% 30%,rgb(var(--acc2)),rgb(var(--acc2) / 0)),radial-gradient(2.5px 2.5px at 45% 75%,rgb(var(--acc2) / .9),rgb(var(--acc2) / 0)),radial-gradient(3.5px 3.5px at 75% 45%,rgb(var(--acc2)),rgb(var(--acc2) / 0)),radial-gradient(2.5px 2.5px at 90% 85%,rgb(var(--acc2) / .8),rgb(var(--acc2) / 0));
  background-size:300px 360px;filter:drop-shadow(0 0 5px rgb(var(--acc) / .9));animation:rise 16s linear infinite;-webkit-mask-image:linear-gradient(to top,#000,transparent 85%);mask-image:linear-gradient(to top,#000,transparent 85%)}
/* the blocky font */
@font-face{font-family:"ModHub Blocks";src:url(data:font/ttf;base64,AAEAAAAKAIAAAwAgT1MvMgiE7LEAAAEoAAAAYGNtYXDRF1AgAAADMAAAAOJnbHlmqtw/iAAABOwAADYIaGVhZGFvQtQAAACsAAAANmhoZWEF3gHIAAAA5AAAACRobXR419IUHgAAAYgAAAGmbG9jYSjlG6YAAAQUAAAA1m1heHAAgABWAAABCAAAACBuYW1lsykkGwAAOvQAAABycG9zdGOq7dkAADtoAAAENgABAAAAAQAAnfXgaV8PPPUAAwPoAAAAAAAAAAAAAAAAAAAAAAAy/zgCJgK8AAAAAwACAAAAAAAAAAEAAAOE/tQAAAJYADIAMgImAAEAAAAAAAAAAAAAAAAAAABpAAEAAABqAFQAFQAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAwIOAZAABQAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAAABAADAAAAAAAAAAAAAPz8/PwAAACAnEwOE/tQAAAOEASwAAAAAAAAAAAH0ArwAAAAgAAAB9AAAAZAAAAJYADICWAAyAlgAMgJYADICWAAyAlgAMgJYADICWAAyAZAAMgJYADICWAAyAlgAMgJYADICWAAyAlgAMgJYADICWAAyAlgAMgJYADICWAAyAlgAMgJYADICWAAyAlgAMgJYADICWAAyAlgAMgJYADIB9AAyAlgAMgJYADIB9AAyAlgAMgJYADIAyAAyAfQAMgH0ADIBkAAyAlgAMgJYADICWAAyAlgAMgJYADIB9AAyAlgAMgH0ADICWAAyAlgAMgJYADICWAAyAlgAMgJYADICWAAyAZAAMgJYADICWAAyAlgAMgJYADICWAAyAlgAMgJYADICWAAyAMgAMgJYADIAyAAyASwAMgDIADIBLAAyAMgAMgGQADIB9AAyAlgAMgH0ADICWAAyAlgAMgJYADIBkAAyAZAAMgGQADIBkAAyAfQAMgH0ADIB9AAyAfQAMgJYADICWAAyAlgAMgJYADICWAAyAlgAMgJYADIBLAAyAMgAMgJYADIAyAAyAMgAMgGQADIBkAAyAfQAMgJYADICWAAyAfQAMgJYADIAMgAAAAAAAgAAAAMAAAAUAAMAAQAAABQABADOAAAAHgAQAAMADgAvADkAQABaAGAAegB+IBQgGSAdICIgJiYFJxP//wAAACAAMAA6AEEAWwBhAHsgEyAYIBwgIiAmJgUnE///AAAABgAA/8EAAP+7AADgUQAA4EbgReBA2mPZVgABAB4AAAA6AAAARAAAAEwAAABQAAAAAAAAAAAAAAAAAAEAQABHAFgAXwBWAFcARgBOAE8AWgBJAEMASABCAEwARABFAFQASgBVAEEAWQBQAE0AUQBbAEsAXQBSAF4AUwBcAGEAYAAAAAAAAAAAAGcA1gEiAYkB6QI3ApwC/wM+A4QD1wQWBH4E4QU/BZQF9gZcBq0G7QdHB5cH/whOCIwI3QkqCYUJuQoVCmIKogsGC1kLgQvDDAoMOwyRDNkNIA17DdYOBw5NDowO1A8ND1UPjQ/pEC8QmRDUESIRcxHDEh8SeRK4ExkTcxObE9IT3RP0FAYUIxQ1FFEUaxSgFM0U6xUZFUQVcBWcFdwWHBZSFogWtBbgFzQXihf3GGgYxBjmGQcZGBlLGacZuRnLGecaAxodGjsaUBqSGuEbBAAAABIAMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwA/AEMARwAAEzUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUxNTMVMTUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUhNTMVlmRkZP5wZAEsZP4MZAEsZP4MZGRkZGT+DGQBLGT+DGQBLGT+DGQBLGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAAFAAyAAACJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwA7AD8AQwBHAEsATwAAEzUzFTE1MxUxNTMVMTUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVMTUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUxNTMVMTUzFTE1MxUyZGRkZP5wZAEsZP4MZAEsZP4MZGRkZP5wZAEsZP4MZAEsZP4MZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAADQAyAAACJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMAABM1MxUxNTMVMTUzFQU1MxUhNTMVBTUzFQc1MxUHNTMVBzUzFSE1MxUFNTMVMTUzFTE1MxWWZGRk/nBkASxk/gxkZGRkZGRkASxk/nBkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAASADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAPwBDAEcAABM1MxUxNTMVMTUzFTE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFTE1MxUxNTMVMTUzFTJkZGRk/nBkASxk/gxkASxk/gxkASxk/gxkASxk/gxkASxk/gxkZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAABIAMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwA/AEMARwAAEzUzFTE1MxUxNTMVMTUzFTE1MxUFNTMVBzUzFQc1MxUxNTMVMTUzFTE1MxUFNTMVBzUzFQc1MxUxNTMVMTUzFTE1MxUxNTMVMmRkZGRk/gxkZGRkZGRkZP5wZGRkZGRkZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAAA4AMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAABM1MxUxNTMVMTUzFTE1MxUxNTMVBTUzFQc1MxUHNTMVMTUzFTE1MxUxNTMVBTUzFQc1MxUHNTMVMmRkZGRk/gxkZGRkZGRkZP5wZGRkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAABIAMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwA/AEMARwAAEzUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVBzUzFTM1MxUxNTMVMTUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVMTUzFTE1MxUxNTMVlmRkZP5wZAEsZP4MZGRkZGRkZP4MZAEsZP4MZAEsZP5wZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAARADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAPwBDAAATNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVMTUzFTE1MxUxNTMVMTUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVITUzFTJkASxk/gxkASxk/gxkASxk/gxkZGRkZP4MZAEsZP4MZAEsZP4MZAEsZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAALADIAAAFeArwAAwAHAAsADwATABcAGwAfACMAJwArAAATNTMVMTUzFTE1MxUHNTMVBzUzFQc1MxUHNTMVBzUzFQc1MxUxNTMVMTUzFTJkZGTIZGRkZGRkZGRkyGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAMADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AABM1MxUxNTMVMTUzFQc1MxUHNTMVBzUzFQU1MxUzNTMVBTUzFTM1MxUFNTMVMTUzFfpkZGTIZGRkZGT+cGTIZP5wZMhk/tRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAA4AMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAABM1MxUhNTMVBTUzFTM1MxUFNTMVMzUzFQU1MxUxNTMVBzUzFTM1MxUFNTMVMzUzFQU1MxUhNTMVMmQBLGT+DGTIZP5wZGRk/tRkZMhkZGT+1GTIZP5wZAEsZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAALADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAAATNTMVBzUzFQc1MxUHNTMVBzUzFQc1MxUHNTMVMTUzFTE1MxUxNTMVMTUzFTJkZGRkZGRkZGRkZGRkZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAASADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAPwBDAEcAABM1MxUhNTMVBTUzFTE1MxUzNTMVMTUzFQU1MxUzNTMVMzUzFQU1MxUzNTMVMzUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVITUzFTJkASxk/gxkZGRkZP4MZGRkZGT+DGRkZGRk/gxkASxk/gxkASxk/gxkASxkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAEQAyAAACJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwA7AD8AQwAAEzUzFSE1MxUFNTMVMTUzFTM1MxUFNTMVMzUzFTM1MxUFNTMVMzUzFTE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUyZAEsZP4MZGTIZP4MZGRkZGT+DGTIZGT+DGQBLGT+DGQBLGT+DGQBLGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAEAAyAAACJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwA7AD8AABM1MxUxNTMVMTUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVMTUzFTE1MxWWZGRk/nBkASxk/gxkASxk/gxkASxk/gxkASxk/gxkASxk/nBkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAAPADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAABM1MxUxNTMVMTUzFTE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFTE1MxUxNTMVMTUzFQU1MxUHNTMVBzUzFTJkZGRk/nBkASxk/gxkASxk/gxkZGRk/nBkZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkABEAMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwA/AEMAABM1MxUxNTMVMTUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUzNTMVMzUzFQU1MxUzNTMVBTUzFTE1MxUzNTMVlmRkZP5wZAEsZP4MZAEsZP4MZAEsZP4MZGRkZGT+DGTIZP7UZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAASADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAPwBDAEcAABM1MxUxNTMVMTUzFTE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFTE1MxUxNTMVMTUzFQU1MxUzNTMVBTUzFTM1MxUFNTMVITUzFTJkZGRk/nBkASxk/gxkASxk/gxkZGRk/nBkZGT+1GTIZP5wZAEsZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAAPADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAABM1MxUxNTMVMTUzFTE1MxUFNTMVBzUzFRU1MxUxNTMVMTUzFRU1MxUHNTMVBTUzFTE1MxUxNTMVMTUzFZZkZGRk/gxkZGRkZGRkZGT+DGRkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAALADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAAATNTMVMTUzFTE1MxUxNTMVMTUzFQU1MxUHNTMVBzUzFQc1MxUHNTMVBzUzFTJkZGRkZP7UZGRkZGRkZGRkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAAA8AMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwAAEzUzFSE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFTE1MxUxNTMVMmQBLGT+DGQBLGT+DGQBLGT+DGQBLGT+DGQBLGT+DGQBLGT+cGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAA0AMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzAAATNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFTM1MxUHNTMVMmQBLGT+DGQBLGT+DGQBLGT+DGQBLGT+DGQBLGT+cGRkZMhkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAASADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAPwBDAEcAABM1MxUhNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUzNTMVMzUzFQU1MxUzNTMVMzUzFQU1MxUxNTMVMzUzFTE1MxUFNTMVITUzFTJkASxk/gxkASxk/gxkASxk/gxkZGRkZP4MZGRkZGT+DGRkZGRk/gxkASxkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQADQAyAAACJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMAABM1MxUhNTMVBTUzFSE1MxUFNTMVMzUzFQc1MxUHNTMVMzUzFQU1MxUhNTMVBTUzFSE1MxUyZAEsZP4MZAEsZP5wZGRkyGTIZGRk/nBkASxk/gxkASxkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAKADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwAAEzUzFSE1MxUFNTMVITUzFQU1MxUzNTMVBzUzFQc1MxUHNTMVBzUzFTJkASxk/gxkASxk/nBkZGTIZGRkZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQADwAyAAACJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwA7AAATNTMVMTUzFTE1MxUxNTMVMTUzFQc1MxUHNTMVBzUzFQc1MxUHNTMVBzUzFTE1MxUxNTMVMTUzFTE1MxUyZGRkZGRkZMhkyGTIZMhkZGRkZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQADgAyAAACJgH0AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwAAEzUzFTE1MxUxNTMVFTUzFQU1MxUxNTMVMTUzFTE1MxUFNTMVITUzFQU1MxUxNTMVMTUzFTE1MxWWZGRkZP5wZGRkZP4MZAEsZP5wZGRkZAGQZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAABAAMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwA/AAATNTMVBzUzFQc1MxUxNTMVMTUzFTE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVMTUzFTE1MxUxNTMVMmRkZGRkZGRk/nBkASxk/gxkASxk/gxkASxk/gxkZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAACQAyAAABwgH0AAMABwALAA8AEwAXABsAHwAjAAATNTMVMTUzFTE1MxUFNTMVBzUzFQc1MxUVNTMVMTUzFTE1MxWWZGRk/nBkZGRkZGRkZAGQZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAQADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAPwAAATUzFQc1MxUFNTMVMTUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFTE1MxUxNTMVMTUzFQHCZGRk/nBkZGRk/gxkASxk/gxkASxk/gxkASxk/nBkZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAADgAyAAACJgH0AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwAAEzUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVMTUzFTE1MxUxNTMVMTUzFQU1MxUVNTMVMTUzFTE1MxWWZGRk/nBkASxk/gxkZGRkZP4MZGRkZAGQZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAAAsAMgAAAcICvAADAAcACwAPABMAFwAbAB8AIwAnACsAABM1MxUxNTMVBTUzFQc1MxUxNTMVMTUzFTE1MxUFNTMVBzUzFQc1MxUHNTMV+mRk/tRkyGRkZGT+1GRkZGRkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAEgAy/zgCJgH0AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwA7AD8AQwBHAAATNTMVMTUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFTE1MxUxNTMVMTUzFQc1MxUFNTMVMTUzFTE1MxWWZGRkZP4MZAEsZP4MZAEsZP4MZAEsZP5wZGRkZGRk/nBkZGQBkGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAOADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3AAATNTMVBzUzFQc1MxUxNTMVMTUzFTE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVITUzFTJkZGRkZGRkZP5wZAEsZP4MZAEsZP4MZAEsZP4MZAEsZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAABgAyAAAAlgK8AAMABwALAA8AEwAXAAATNTMVBzUzFQc1MxUHNTMVBzUzFQc1MxUyZGRkZGRkZGRkZGQCWGRkyGRkZGRkZGRkZGRkZGRkAAALADL/OAHCArwAAwAHAAsADwATABcAGwAfACMAJwArAAABNTMVBzUzFTE1MxUHNTMVBzUzFQc1MxUHNTMVBTUzFTM1MxUFNTMVMTUzFQFeZMhkZGRkZGRkZGRk/nBkyGT+1GRkAlhkZMhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAMADIAAAHCArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AABM1MxUHNTMVBzUzFTM1MxUFNTMVMzUzFQU1MxUxNTMVBzUzFTM1MxUFNTMVMzUzFTJkZGRkZMhk/nBkZGT+1GRkyGRkZP7UZMhkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQACAAyAAABXgK8AAMABwALAA8AEwAXABsAHwAAEzUzFTE1MxUHNTMVBzUzFQc1MxUHNTMVBzUzFRU1MxUyZGRkZGRkZGRkZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAPADIAAAImAfQAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAABM1MxUxNTMVMzUzFQU1MxUzNTMVMzUzFQU1MxUzNTMVMzUzFQU1MxUzNTMVMzUzFQU1MxUzNTMVMzUzFTJkZGRk/nBkZGRkZP4MZGRkZGT+DGRkZGRk/gxkZGRkZAGQZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAADAAyAAACJgH0AAMABwALAA8AEwAXABsAHwAjACcAKwAvAAATNTMVMTUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUyZGRkZP5wZAEsZP4MZAEsZP4MZAEsZP4MZAEsZAGQZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAADAAyAAACJgH0AAMABwALAA8AEwAXABsAHwAjACcAKwAvAAATNTMVMTUzFTE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVMTUzFTE1MxWWZGRk/nBkASxk/gxkASxk/gxkASxk/nBkZGQBkGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAABAAMv84AiYB9AADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwA/AAATNTMVMTUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFTE1MxUxNTMVMTUzFQU1MxUHNTMVMmRkZGT+cGQBLGT+DGQBLGT+DGQBLGT+DGRkZGT+cGRkZAGQZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAEAAy/zgCJgH0AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwA7AD8AABM1MxUxNTMVMTUzFTE1MxUFNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVMTUzFTE1MxUxNTMVBzUzFQc1MxWWZGRkZP4MZAEsZP4MZAEsZP4MZAEsZP5wZGRkZGRkZGQBkGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAAIADIAAAHCAfQAAwAHAAsADwATABcAGwAfAAATNTMVMzUzFTE1MxUFNTMVMTUzFQc1MxUHNTMVBzUzFTJkZGRk/nBkZMhkZGRkZAGQZGRkZGRkZGRkZGRkZGRkZGRkZGQAAA0AMgAAAiYB9AADAAcACwAPABMAFwAbAB8AIwAnACsALwAzAAATNTMVMTUzFTE1MxUxNTMVBTUzFRU1MxUxNTMVMTUzFRU1MxUFNTMVMTUzFTE1MxUxNTMVlmRkZGT+DGRkZGRk/gxkZGRkAZBkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQACwAyAAABwgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAAEzUzFQc1MxUHNTMVMTUzFTE1MxUxNTMVBTUzFQc1MxUHNTMVFTUzFTE1MxWWZGRkyGRkZGT+1GRkZGRkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQADAAyAAACJgH0AAMABwALAA8AEwAXABsAHwAjACcAKwAvAAATNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUxNTMVMTUzFTE1MxUyZAEsZP4MZAEsZP4MZAEsZP4MZAEsZP5wZGRkZAGQZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAACQAyAAACJgH0AAMABwALAA8AEwAXABsAHwAjAAATNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVMzUzFQc1MxUyZAEsZP4MZAEsZP4MZAEsZP5wZGRkyGQBkGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQADAAyAAACJgH0AAMABwALAA8AEwAXABsAHwAjACcAKwAvAAATNTMVITUzFQU1MxUhNTMVBTUzFTM1MxUzNTMVBTUzFTM1MxUzNTMVBTUzFTM1MxUyZAEsZP4MZAEsZP4MZGRkZGT+DGRkZGRk/nBkZGQBkGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQACQAyAAACJgH0AAMABwALAA8AEwAXABsAHwAjAAATNTMVITUzFQU1MxUzNTMVBzUzFQc1MxUzNTMVBTUzFSE1MxUyZAEsZP5wZGRkyGTIZGRk/nBkASxkAZBkZGRkZGRkZGRkZGRkZGRkZGRkZGRkABAAMv84AiYB9AADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwA/AAATNTMVITUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUxNTMVMTUzFTE1MxUHNTMVBTUzFTE1MxUxNTMVMmQBLGT+DGQBLGT+DGQBLGT+DGQBLGT+cGRkZGRkZP5wZGRkAZBkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAANADIAAAImAfQAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwAAEzUzFTE1MxUxNTMVMTUzFTE1MxUHNTMVBzUzFQc1MxUHNTMVMTUzFTE1MxUxNTMVMTUzFTJkZGRkZMhkyGTIZMhkZGRkZAGQZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkABMAMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwA/AEMARwBLAAATNTMVMTUzFTE1MxUFNTMVITUzFQU1MxUzNTMVMTUzFQU1MxUzNTMVMzUzFQU1MxUxNTMVMzUzFQU1MxUhNTMVBTUzFTE1MxUxNTMVlmRkZP5wZAEsZP4MZMhkZP4MZGRkZGT+DGRkyGT+DGQBLGT+cGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQACgAyAAABXgK8AAMABwALAA8AEwAXABsAHwAjACcAABM1MxUHNTMVMTUzFQc1MxUHNTMVBzUzFQc1MxUHNTMVMTUzFTE1MxWWZMhkZGRkZGRkZGRkyGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAAA4AMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAABM1MxUxNTMVMTUzFQU1MxUhNTMVBzUzFQc1MxUHNTMVBzUzFQc1MxUxNTMVMTUzFTE1MxUxNTMVlmRkZP5wZAEsZGRkyGTIZMhkyGRkZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAA8AMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwAAEzUzFTE1MxUxNTMVMTUzFRU1MxUHNTMVBTUzFTE1MxUxNTMVFTUzFQc1MxUFNTMVMTUzFTE1MxUxNTMVMmRkZGRkZGT+cGRkZGRkZP4MZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAA4AMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAAAE1MxUHNTMVMTUzFQU1MxUzNTMVBTUzFTM1MxUFNTMVMTUzFTE1MxUxNTMVMTUzFQc1MxUHNTMVAV5kyGRk/tRkZGT+cGTIZP5wZGRkZGTIZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAARADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAPwBDAAATNTMVMTUzFTE1MxUxNTMVMTUzFQU1MxUHNTMVMTUzFTE1MxUxNTMVFTUzFQc1MxUFNTMVITUzFQU1MxUxNTMVMTUzFTJkZGRkZP4MZGRkZGRkZGRk/gxkASxk/nBkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAEAAyAAACJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwA7AD8AABM1MxUxNTMVMTUzFQU1MxUHNTMVBzUzFTE1MxUxNTMVMTUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVMTUzFTE1MxWWZGRk/nBkZGRkZGRkZP5wZAEsZP4MZAEsZP5wZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAACwAyAAACJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAAEzUzFTE1MxUxNTMVMTUzFTE1MxUHNTMVBzUzFQc1MxUHNTMVBzUzFQc1MxUyZGRkZGRkZMhkyGRkZGRkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQAEQAyAAACJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwA7AD8AQwAAEzUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUxNTMVMTUzFQU1MxUhNTMVBTUzFSE1MxUFNTMVMTUzFTE1MxWWZGRk/nBkASxk/gxkASxk/nBkZGT+cGQBLGT+DGQBLGT+cGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAQADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAPwAAEzUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVITUzFQU1MxUxNTMVMTUzFTE1MxUHNTMVBzUzFQU1MxUxNTMVMTUzFZZkZGT+cGQBLGT+DGQBLGT+cGRkZGRkZGRk/nBkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAAGADIAAACWArwAAwAHAAsADwATABcAABM1MxUHNTMVBzUzFQc1MxUHNTMVBzUzFTJkZGRkZGRkZGRkZAJYZGRkZGRkZGRkZGRkZGTIZGQAAAkAMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAAEzUzFTE1MxUxNTMVBTUzFSE1MxUHNTMVBzUzFQc1MxUHNTMVlmRkZP5wZAEsZGRkyGTIZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZMhkZAAAAQAyAAAAlgBkAAMAADM1MxUyZGRkAAMAMv+cAPoAyAADAAcACwAANzUzFQc1MxUHNTMVlmRkZMhkZGRkZGRkZGRkAAACADIAAACWAlgAAwAHAAATNTMVAzUzFTJkZGQB9GRk/gxkZAAEADL/nAD6AlgAAwAHAAsADwAAEzUzFQM1MxUHNTMVBzUzFZZkZGRkZMhkAfRkZP5wZGRkZGRkZGQAAgAyAfQAlgK8AAMABwAAEzUzFQc1MxUyZGRkAlhkZGRkZAAABAAyAfQBXgK8AAMABwALAA8AABM1MxUzNTMVBTUzFTM1MxUyZGRk/tRkZGQCWGRkZGRkZGRkZAAEADIBLAHCAZAAAwAHAAsADwAAEzUzFTE1MxUxNTMVMTUzFTJkZGRkASxkZGRkZGRkZAAACQAyAGQCJgJYAAMABwALAA8AEwAXABsAHwAjAAATNTMVBzUzFQU1MxUxNTMVMTUzFTE1MxUxNTMVBTUzFQc1MxX6ZGRk/tRkZGRkZP7UZGRkAfRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAgAMgDIAcIB9AADAAcACwAPABMAFwAbAB8AABM1MxUxNTMVMTUzFTE1MxUFNTMVMTUzFTE1MxUxNTMVMmRkZGT+cGRkZGQBkGRkZGRkZGRkyGRkZGRkZGRkAAUAMv+cAiYAAAADAAcACwAPABMAABc1MxUxNTMVMTUzFTE1MxUxNTMVMmRkZGRkZGRkZGRkZGRkZGQAAAcAMgAAAiYCvAADAAcACwAPABMAFwAbAAABNTMVBzUzFQc1MxUHNTMVBzUzFQc1MxUHNTMVAcJkyGRkZMhkyGRkZMhkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZAAABwAyAAACJgK8AAMABwALAA8AEwAXABsAABM1MxUVNTMVBzUzFRU1MxUVNTMVBzUzFRU1MxUyZGRkZGRkZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZAAHADIAAAFeArwAAwAHAAsADwATABcAGwAAEzUzFQc1MxUHNTMVBzUzFQc1MxUVNTMVFTUzFfpkyGTIZGRkZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGQABwAyAAABXgK8AAMABwALAA8AEwAXABsAABM1MxUVNTMVFTUzFQc1MxUHNTMVBzUzFQc1MxUyZGRkZGRkZMhkyGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkAAsAMgAAAV4CvAADAAcACwAPABMAFwAbAB8AIwAnACsAABM1MxUxNTMVMTUzFQU1MxUHNTMVBzUzFQc1MxUHNTMVBzUzFTE1MxUxNTMVMmRkZP7UZGRkZGRkZGRkZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAACwAyAAABXgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAAEzUzFTE1MxUxNTMVBzUzFQc1MxUHNTMVBzUzFQc1MxUFNTMVMTUzFTE1MxUyZGRkZGRkZGRkZGRkZP7UZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAAJADIAAAHCArwAAwAHAAsADwATABcAGwAfACMAABM1MxUxNTMVBTUzFQc1MxUHNTMVFTUzFQc1MxUVNTMVMTUzFfpkZP7UZGRkyGRkZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAAJADIAAAHCArwAAwAHAAsADwATABcAGwAfACMAABM1MxUxNTMVFTUzFQc1MxUVNTMVBzUzFQc1MxUFNTMVMTUzFTJkZGRkZGTIZGRk/tRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAAHADIAAAHCArwAAwAHAAsADwATABcAGwAAATUzFQc1MxUHNTMVBzUzFRU1MxUVNTMVFTUzFQFeZMhkyGTIZGRkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGQABwAyAAABwgK8AAMABwALAA8AEwAXABsAABM1MxUVNTMVFTUzFRU1MxUHNTMVBzUzFQc1MxUyZGRkZMhkyGTIZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGQAAA8AMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwAAEzUzFTE1MxUzNTMVBTUzFTE1MxUzNTMVBzUzFQc1MxUHNTMVBzUzFTM1MxUxNTMVBTUzFTM1MxUxNTMVMmRkyGT+DGRkZGRkZMhkyGRkZGRkZP4MZMhkZAJYZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAA8AMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwAAEzUzFTE1MxUFNTMVMzUzFQU1MxUzNTMVBzUzFQc1MxUzNTMVMzUzFQU1MxUzNTMVBTUzFTE1MxUzNTMVlmRk/tRkyGT+cGRkZMhkyGRkZGRk/gxkyGT+1GRkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAUADIAAAImArwAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAPwBDAEcASwBPAAATNTMVMzUzFQU1MxUzNTMVBTUzFTE1MxUxNTMVMTUzFTE1MxUFNTMVMzUzFQU1MxUxNTMVMTUzFTE1MxUxNTMVBTUzFTM1MxUFNTMVMzUzFZZkZGT+1GRkZP5wZGRkZGT+cGRkZP5wZGRkZGT+cGRkZP7UZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkABUAMgAAAiYCvAADAAcACwAPABMAFwAbAB8AIwAnACsALwAzADcAOwA/AEMARwBLAE8AUwAAEzUzFTE1MxUxNTMVBTUzFSE1MxUFNTMVMzUzFTE1MxUxNTMVBTUzFTM1MxUzNTMVBTUzFTM1MxUxNTMVMTUzFQU1MxUVNTMVMTUzFTE1MxUxNTMVlmRkZP5wZAEsZP4MZGRkZGT+DGRkZGRk/gxkZGRkZP4MZGRkZGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAARADIAZAImAlgAAwAHAAsADwATABcAGwAfACMAJwArAC8AMwA3ADsAPwBDAAATNTMVMzUzFTM1MxUFNTMVMTUzFTE1MxUFNTMVMTUzFTE1MxUxNTMVMTUzFQU1MxUxNTMVMTUzFQU1MxUzNTMVMzUzFTJkZGRkZP5wZGRk/nBkZGRkZP5wZGRk/nBkZGRkZAH0ZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQABQAyAZACJgK8AAMABwALAA8AEwAAEzUzFQc1MxUzNTMVBTUzFSE1MxX6ZMhkZGT+cGQBLGQCWGRkZGRkZGRkZGRkZAAFADIBLAImAfQAAwAHAAsADwATAAATNTMVMzUzFQU1MxUzNTMVMTUzFZZkyGT+DGRkZGQBkGRkZGRkZGRkZGRkAAACADIB9AD6ArwAAwAHAAATNTMVFTUzFTJkZAJYZGRkZGQACAAy/5wAlgK8AAMABwALAA8AEwAXABsAHwAAEzUzFQc1MxUHNTMVBzUzFQc1MxUHNTMVBzUzFQc1MxUyZGRkZGRkZGRkZGRkZGRkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAAEQAyAAACJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwA7AD8AQwAAEzUzFQc1MxUxNTMVMTUzFTE1MxUFNTMVMzUzFQc1MxUxNTMVMTUzFQc1MxUzNTMVBTUzFTE1MxUxNTMVMTUzFQc1MxX6ZMhkZGRk/gxkZGTIZGRkyGRkZP4MZGRkZMhkAlhkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkAAIAMgH0AJYCvAADAAcAABM1MxUHNTMVMmRkZAJYZGRkZGQAAAIAMgH0AJYCvAADAAcAABM1MxUHNTMVMmRkZAJYZGRkZGQAAAQAMgH0AV4CvAADAAcACwAPAAATNTMVMzUzFQU1MxUzNTMVMmRkZP7UZGRkAlhkZGRkZGRkZGQABAAyAfQBXgK8AAMABwALAA8AABM1MxUzNTMVBTUzFTM1MxUyZGRk/tRkZGQCWGRkZGRkZGRkZAAEADIBLAHCAZAAAwAHAAsADwAAEzUzFTE1MxUxNTMVMTUzFTJkZGRkASxkZGRkZGRkZAAABQAyASwCJgGQAAMABwALAA8AEwAAEzUzFTE1MxUxNTMVMTUzFTE1MxUyZGRkZGQBLGRkZGRkZGRkZGQAAwAyAAACJgBkAAMABwALAAAzNTMVMzUzFTM1MxUyZGRkZGRkZGRkZGQADAAyAGQBwgH0AAMABwALAA8AEwAXABsAHwAjACcAKwAvAAATNTMVMTUzFQU1MxUxNTMVMTUzFTE1MxUFNTMVMTUzFTE1MxUxNTMVBTUzFTE1MxWWZGT+1GRkZGT+cGRkZGT+1GRkAZBkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQADgAyAGQCJgK8AAMABwALAA8AEwAXABsAHwAjACcAKwAvADMANwAAEzUzFQc1MxUFNTMVMTUzFTE1MxUxNTMVMTUzFQU1MxUxNTMVMTUzFQU1MxUzNTMVBTUzFSE1MxX6ZGRk/tRkZGRkZP5wZGRk/tRkZGT+cGQBLGQCWGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZAAFADIAyAImAlgAAwAHAAsADwATAAABNTMVBzUzFQU1MxUzNTMVBzUzFQHCZMhk/nBkZGTIZAH0ZGRkZGRkZGRkZGRkZAAAAAAEADYAAQAAAAAAAQANAAAAAQAAAAAAAgAHAA0AAwABBAkAAQAaABQAAwABBAkAAgAOAC5Nb2RIdWIgQmxvY2tzUmVndWxhcgBNAG8AZABIAHUAYgAgAEIAbABvAGMAawBzAFIAZQBnAHUAbABhAHIAAAACAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGoAAAADAQIBAwEEAQUBBgEHAQgBCQEKAQsBDAENAQ4BDwEQAREBEgETARQBFQEWARcBGAEZARoBGwEcAR0BHgEfASABIQEiASMBJAElASYBJwEoASkBKgErASwBLQEuAS8BMAExATIBMwE0ATUBNgE3ATgBOQE6ATsBPAE9AT4BPwFAAUEBQgFDAUQBRQFGAUcBSAFJAUoBSwFMAU0BTgFPAVABUQFSAVMBVAFVAVYBVwFYAVkBWgFbAVwBXQFeAV8BYAFhAWIBYwFkAWUBZgFnAWgBaQd1bmkwMDQxB3VuaTAwNDIHdW5pMDA0Mwd1bmkwMDQ0B3VuaTAwNDUHdW5pMDA0Ngd1bmkwMDQ3B3VuaTAwNDgHdW5pMDA0OQd1bmkwMDRBB3VuaTAwNEIHdW5pMDA0Qwd1bmkwMDREB3VuaTAwNEUHdW5pMDA0Rgd1bmkwMDUwB3VuaTAwNTEHdW5pMDA1Mgd1bmkwMDUzB3VuaTAwNTQHdW5pMDA1NQd1bmkwMDU2B3VuaTAwNTcHdW5pMDA1OAd1bmkwMDU5B3VuaTAwNUEHdW5pMDA2MQd1bmkwMDYyB3VuaTAwNjMHdW5pMDA2NAd1bmkwMDY1B3VuaTAwNjYHdW5pMDA2Nwd1bmkwMDY4B3VuaTAwNjkHdW5pMDA2QQd1bmkwMDZCB3VuaTAwNkMHdW5pMDA2RAd1bmkwMDZFB3VuaTAwNkYHdW5pMDA3MAd1bmkwMDcxB3VuaTAwNzIHdW5pMDA3Mwd1bmkwMDc0B3VuaTAwNzUHdW5pMDA3Ngd1bmkwMDc3B3VuaTAwNzgHdW5pMDA3OQd1bmkwMDdBB3VuaTAwMzAHdW5pMDAzMQd1bmkwMDMyB3VuaTAwMzMHdW5pMDAzNAd1bmkwMDM1B3VuaTAwMzYHdW5pMDAzNwd1bmkwMDM4B3VuaTAwMzkHdW5pMDAyMQd1bmkwMDNGB3VuaTAwMkUHdW5pMDAyQwd1bmkwMDNBB3VuaTAwM0IHdW5pMDAyNwd1bmkwMDIyB3VuaTAwMkQHdW5pMDAyQgd1bmkwMDNEB3VuaTAwNUYHdW5pMDAyRgd1bmkwMDVDB3VuaTAwMjgHdW5pMDAyOQd1bmkwMDVCB3VuaTAwNUQHdW5pMDA3Qgd1bmkwMDdEB3VuaTAwM0MHdW5pMDAzRQd1bmkwMDI1B3VuaTAwMjYHdW5pMDAyMwd1bmkwMDQwB3VuaTAwMkEHdW5pMDA1RQd1bmkwMDdFB3VuaTAwNjAHdW5pMDA3Qwd1bmkwMDI0B3VuaTIwMTkHdW5pMjAxOAd1bmkyMDFDB3VuaTIwMUQHdW5pMjAxMwd1bmkyMDE0B3VuaTIwMjYHdW5pMjAyMgd1bmkyNjA1B3VuaTI3MTMAAA==) format("truetype");font-display:block}
:root[data-font="pixel"]{--display:"ModHub Blocks",ui-monospace,monospace}
:root[data-font="pixel"] :is(h1,h2,h3,.brand,.nav,.btn,.ttile b,.page-h,.sec-h,.res .t,.dcard b,.inst b,.modal h2,.modal h3,.kbd,.seg button,.pill,.toast){font-family:"ModHub Blocks",ui-monospace,monospace;font-weight:400;font-synthesis:none;letter-spacing:.02em}
:root[data-font="pixel"] :is(h1,h2,.brand,.page-h){text-shadow:.09em .09em 0 rgb(var(--acc3) / .75)}
:root[data-font="pixel"] .btn.go{text-shadow:.08em .08em 0 rgb(0 0 0 / .35)}
:root[data-font="mono"]{--display:ui-monospace,"Cascadia Mono","SF Mono",Consolas,monospace;--body:ui-monospace,"Cascadia Mono","SF Mono",Consolas,monospace}
:root[data-font="mono"] body::after{content:"";position:fixed;inset:0;z-index:2147483000;pointer-events:none;background:repeating-linear-gradient(rgb(0 0 0 / .07) 0 1px,transparent 1px 3px)}
/* easter-egg effects */
.fx{position:fixed;inset:0;pointer-events:none;z-index:2147483100;overflow:hidden}
.fx i{position:absolute;top:-30px;width:var(--w,10px);height:var(--w,10px);border-radius:2px;background:var(--c);animation:fall var(--t,2.6s) cubic-bezier(.3,.1,.6,1) forwards;animation-delay:var(--d,0s)}
@keyframes fall{to{transform:translate(var(--x,0),110vh) rotate(var(--r,540deg))}}
.fx.rain i{width:2px;height:16px;border-radius:0;background:rgb(130 170 255 / .55);animation:drop .7s linear infinite;animation-delay:var(--d)}
.fx.snow i{width:5px;height:5px;border-radius:1px;background:rgb(255 255 255 / .85);animation:drop var(--t,7s) linear infinite;animation-delay:var(--d)}
@keyframes drop{from{transform:translateY(-20px)}to{transform:translate(var(--x,0),105vh)}}
.brand.twirl .mark{animation:bspin .9s cubic-bezier(.3,1.4,.5,1)}
@keyframes bspin{to{transform:rotate(1turn) scale(1)}}
.ttile.secret small::before{content:"\2605 ";}
.ttile[data-preset="redstone"] b{font-family:"ModHub Blocks",monospace;font-weight:400;font-synthesis:none;letter-spacing:.03em}
.secret-count{margin:12px 2px 0;font-size:13px;color:var(--muted)}
.app{min-height:calc(100vh / var(--ui-zoom,1))}
.side{height:calc(100vh / var(--ui-zoom,1))}
.modal{max-height:calc(92vh / var(--ui-zoom,1))}
.modpage{max-height:min(calc(88vh / var(--ui-zoom,1)),980px)}
:root[data-side="glass"] .app{background:none}
:root[data-side="glass"] .side{background:rgb(var(--deep-rgb) / .5);backdrop-filter:blur(20px) saturate(150%);-webkit-backdrop-filter:blur(20px) saturate(150%);border-right:1px solid rgb(var(--hi) / .06)}
:root:not([data-bg="plain"]) :is(.results,.inst,.lopt,.dcard,.card,.empty,.starter,.banner,.mp-status){background-color:color-mix(in srgb,var(--stone-2) 80%,transparent)}
:root:not([data-bg="plain"]) .inv{background-color:color-mix(in srgb,var(--deep) 72%,transparent)}
:root:not([data-bg="plain"]) :is(input[type=text],input:not([type]),select,.seg){background-color:color-mix(in srgb,var(--deep) 78%,transparent)}
/* corners */
:root[data-radius="sharp"] :is(.btn,input,select,.seg,.seg button,.segpill,.res,.results,.inv,.lopt,.banner,.modal,.dcard,.inst,.empty,.card,.pal,.kpill,.lochip,.chip,.nav,#navPill,.starter,.toast,.wn-fab,.mp-status,.mp-gal img,.mp-banner,.dcard .shot,.slot,.ico,.live){border-radius:3px !important}
:root[data-radius="round"] :is(.btn,input,select,.seg,.seg button,.segpill,.kpill,.lochip,.chip,.wn-fab,.mp-status){border-radius:999px !important}
:root[data-radius="round"] :is(.res,.results,.inv,.lopt,.banner,.dcard,.inst,.empty,.card,.starter,.live){border-radius:22px !important}
:root[data-radius="round"] :is(.modal,.pal){border-radius:26px !important}
:root[data-radius="round"] :is(.nav,#navPill){border-radius:14px !important}
/* animations */
:root[data-motion="off"] *,:root[data-motion="off"] *::before,:root[data-motion="off"] *::after{animation:none !important;transition:none !important}
:root[data-motion="less"] :is(.rise,.dot-new,.wn-dot,.ping){animation:none !important}
:root[data-motion="less"] :is(.btn.go::after,.newver::after){display:none}
/* settings cards */
.settings{max-width:880px;gap:16px}
.settings > .card{padding:22px 24px;border:1px solid var(--line);border-radius:18px;background:var(--stone-2);display:grid;gap:16px;border-top:1px solid var(--line)}
.settings > section.card:first-child{padding-top:22px;border-top:1px solid var(--line)}
.card-h{display:flex;gap:14px;align-items:flex-start}
.card-h h3{margin:0 0 3px}
.card-h p{margin:0;color:var(--muted);font-size:13.5px;line-height:1.5}
.card-ico{width:38px;height:38px;border-radius:11px;flex:none;display:grid;place-items:center;background:var(--accent-tint);color:var(--accent-2)}
.card-ico svg{width:19px;height:19px}
details.card > summary.card-h{font:inherit;cursor:pointer;list-style:none}
details.card > summary.card-h::after{margin:12px 4px 0 auto}
details.card:not([open]){gap:0}
.ap-wrap{display:flex;gap:26px;flex-wrap:wrap;align-items:flex-start}
.ap-opts{flex:1 1 420px;display:grid;gap:14px;min-width:0}
.opt{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.opt-l{width:96px;flex:none;color:var(--muted);font-weight:600;font-size:13.5px}
.opt .seg button{height:30px;padding:0 11px;font-size:13.5px}
.range{display:flex;align-items:center;gap:12px;flex:1;max-width:330px}
.range input{flex:1;accent-color:var(--accent);height:auto;padding:0;border:0;background:none}
.range span{width:42px;color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
.ap-side{flex:0 0 220px;display:grid;gap:10px;justify-items:center}
.ap-prev{width:220px;height:146px;border-radius:14px;border:1px solid var(--line);overflow:hidden;display:flex;box-shadow:0 18px 40px -24px rgb(0 0 0 / calc(.9 * var(--shk)))}
.pv-side{width:54px;padding:12px 8px;display:grid;gap:6px;align-content:start;background:rgb(var(--deep-rgb) / .55)}
:root[data-side="solid"] .pv-side{background:var(--deep)}
.pv-side i{height:7px;border-radius:3px;background:var(--stone-3)} .pv-side i.on{background:var(--accent)}
.pv-main{flex:1;padding:14px 12px;display:grid;gap:7px;align-content:start}
.pv-main b{height:11px;width:60%;border-radius:3px;background:var(--text);opacity:.85}
.pv-main s{height:6px;width:85%;border-radius:3px;background:var(--muted);opacity:.5}
.pv-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:4px}
.pv-cards u{height:34px;border-radius:6px;background:color-mix(in srgb,var(--stone-2) 80%,transparent);border:1px solid var(--line)}
.pv-main em{height:14px;width:46%;border-radius:4px;background:var(--accent);margin-top:4px}
.sw.custom i{background:conic-gradient(#ff4d4d,#ffb84d,#f7ff4d,#4dff88,#4dd2ff,#7a4dff,#ff4dd2,#ff4d4d)}
.sw.custom.on i{background:var(--sw)}
.sw input[type=color]{position:absolute;opacity:0;width:0;height:0;pointer-events:none}
.sw{position:relative}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none !important;transition:none !important}}

/* ================= 3.8: cleaner, fresher ================= */
main{padding:44px 56px 90px;max-width:1120px}
.page-h{margin-bottom:30px;align-items:flex-end}
h1{font-size:36px;letter-spacing:-.8px;margin-bottom:6px}
.lede{font-size:15px;color:var(--muted);max-width:56ch}
.side{padding:24px 14px 18px;gap:2px;border-right:1px solid rgb(var(--hi) / .05)}
.brand{padding:4px 10px 26px}
.nav{padding:9px 12px;font-size:14.5px;border-radius:10px}
#navPill{border-radius:10px;box-shadow:inset 0 0 0 1px rgb(var(--hi) / .06),0 8px 20px -12px rgb(0 0 0 / calc(.8 * var(--shk)))}
#navPill::before{content:"";position:absolute;left:0;top:9px;bottom:9px;width:3px;border-radius:0 3px 3px 0;background:var(--accent)}
.side .foot{gap:2px;padding:10px 0 0;border-top:1px solid rgb(var(--hi) / .05)}
.side .foot .help-btn{text-decoration:none;font-size:13.5px;color:var(--muted);padding:8px 12px;border-radius:8px;position:relative}
.side .foot .help-btn:hover{color:var(--text);background:rgb(var(--hi) / .04)}
.side .foot .help-btn svg{width:16px;height:16px;flex:none}
.wn-side .wn-dot{position:static;margin-left:auto;width:8px;height:8px;border:0}
.version{padding:6px 12px 0;margin:0}
:is(.results,.inst,.lopt,.dcard,.card,.empty,.starter,.mp-status,.scanbox){border-radius:16px;border-color:rgb(var(--hi) / .07)}
.card{padding:22px 24px}
.btn{border-radius:10px}
.banner{border-radius:14px}
.res{padding:14px 18px}
.empty{padding:44px 24px}
.group-h{margin-top:34px}
/* ================= 3.8: Fluid motion ================= */
:root[data-motion="fluid"] section.enter{animation:fluidIn .6s cubic-bezier(.2,.9,.2,1) both}
@keyframes fluidIn{from{opacity:0;transform:translateY(22px) scale(.985);filter:blur(6px)}}
:root[data-motion="fluid"] #navPill{transition:top .55s cubic-bezier(.34,1.45,.5,1),height .55s cubic-bezier(.34,1.45,.5,1)}
:root[data-motion="fluid"] .seg .segpill{transition:left .5s cubic-bezier(.34,1.45,.5,1),width .5s cubic-bezier(.34,1.45,.5,1),opacity .2s}
:root[data-motion="fluid"] main h1{transform-origin:left bottom;will-change:transform,opacity}
:root[data-motion="fluid"] .fl-pre{opacity:0;transform:translateY(26px) scale(.97)}
:root[data-motion="fluid"] .fl-in{opacity:1;transform:none;transition:opacity .7s cubic-bezier(.2,.9,.2,1),transform .8s cubic-bezier(.2,.9,.2,1);transition-delay:var(--fd,0ms)}
:root[data-motion="fluid"] .btn{transition:transform .35s cubic-bezier(.34,1.56,.64,1),background .2s,border-color .2s,box-shadow .25s}
:root[data-motion="fluid"] .btn:active{transform:scale(.95)}
:root[data-motion="fluid"] .app{transition:transform .55s cubic-bezier(.2,.9,.2,1),border-radius .55s,filter .55s;transform-origin:50% 0}
:root[data-motion="fluid"].sheet-open .app{transform:scale(.955) translateY(14px);border-radius:18px;overflow:hidden;filter:brightness(.8)}
:root[data-motion="fluid"] .scrim{background:rgb(0 0 0 / calc(.45 * var(--shk)));animation:fadeIn .35s ease}
:root[data-motion="fluid"] .scrim .modal{animation:sheetUp .55s cubic-bezier(.2,.95,.25,1.04) both;border-radius:20px}
@keyframes sheetUp{from{opacity:0;transform:translateY(70px) scale(.94)}}
:root[data-motion="fluid"] .ttile{transition:transform .45s cubic-bezier(.34,1.56,.64,1),box-shadow .3s}
:root[data-motion="fluid"] .ttile:active{transform:scale(.95)}

/* ================= 4.0: Home, mod updates, sharing ================= */
.home-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.home-upd,.home-picks{grid-column:1 / -1}
@media (max-width:980px){.home-grid{grid-template-columns:minmax(0,1fr)}}
.home-grid .card{margin:0}
.hc-h{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.hc-h h3{margin:0;font:750 17px/1.2 var(--display)}
.hc-h small{color:var(--muted);font-size:13px}
.hc-h .grow{flex:1;min-width:0}
.hc-h .n{font:800 13px/1 var(--body);color:var(--accent-ink);background:var(--accent);border-radius:10px;padding:4px 9px}
.hrow{display:flex;align-items:center;gap:12px;padding:10px 0;border-top:1px solid rgb(var(--hi) / .06)}
.hrow:first-of-type{border-top:0}
.hrow .ico{width:34px;height:34px;border-radius:9px;flex:none}
.hrow .body{flex:1;min-width:0}
.hrow .t{font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hrow .s{color:var(--muted);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hrow .ver{font-size:12.5px;color:var(--muted);white-space:nowrap}
.hrow .ver b{color:var(--ready);font-weight:700}
.h-empty{color:var(--muted);font-size:14px;margin:4px 0 0}
.h-more{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}
.hpicks{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
.hpick{display:flex;align-items:center;gap:10px;padding:10px;border-radius:12px;background:rgb(var(--hi) / .03);border:1px solid rgb(var(--hi) / .05);cursor:pointer;text-align:left;color:inherit;font:inherit}
.hpick:hover{border-color:var(--accent-edge)}
.hpick .ico{width:38px;height:38px;border-radius:10px;flex:none}
.hpick .body{flex:1;min-width:0}
.hpick .t{font-weight:650;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hpick .s{color:var(--muted);font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.live-ask{margin-bottom:18px}
/* updates window */
.um-inst{margin-top:18px}
.um-inst h4{display:flex;align-items:center;gap:10px;margin:0 0 6px;font:700 15px/1.2 var(--display)}
.um-inst h4 small{color:var(--muted);font:500 12.5px var(--body)}
.um-inst h4 .btn{margin-left:auto}
.um-mod{border-top:1px solid rgb(var(--hi) / .06);padding:10px 0}
.um-mod summary{display:flex;align-items:center;gap:10px;cursor:pointer;list-style:none}
.um-mod summary::-webkit-details-marker{display:none}
.um-mod .ico{width:30px;height:30px;border-radius:8px;flex:none}
.um-mod .t{flex:1;min-width:0;font-weight:650}
.um-mod .ver{font-size:12.5px;color:var(--muted)}
.um-mod .ver b{color:var(--ready)}
.um-log{margin:8px 0 2px 40px;font-size:13px;color:var(--muted);max-height:180px;overflow:auto;white-space:pre-wrap}
/* sharing */
.share-tabs{margin:6px 0 18px}
.share-h{margin:20px 0 4px;font:700 15px/1.2 var(--display)}
.share-code{display:flex;gap:10px;align-items:stretch}
.share-code textarea,#shareIn{flex:1;width:100%;font:12.5px/1.45 ui-monospace,Consolas,monospace;border-radius:10px;border:1px solid var(--edge);background:var(--deep);color:var(--text);padding:10px;resize:vertical;word-break:break-all}
.share-row{display:flex;gap:16px;align-items:center;justify-content:space-between;padding:12px 0;border-top:1px solid rgb(var(--hi) / .06)}
.share-row b{font-weight:650}
.share-row .help{margin:2px 0 0}
.share-mr{display:flex;gap:8px;margin-top:8px}
.share-mr select{min-width:0}
.sp-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;margin:12px 0;max-height:240px;overflow:auto}
.sp-list .hrow{border:0;padding:6px 0}
.sp-mode{display:grid;gap:8px;margin:10px 0}
/* developer */
.dev-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:4px 0 14px}
.dev-stats > div{background:rgb(var(--hi) / .03);border:1px solid rgb(var(--hi) / .06);border-radius:12px;padding:14px}
.dev-n{display:block;font:800 26px/1.1 var(--display);font-variant-numeric:tabular-nums}
.dev-l{color:var(--muted);font-size:12.5px}
.dev-spark{display:flex;align-items:flex-end;gap:4px;height:54px;margin-bottom:8px}
.dev-spark i{flex:1;background:var(--accent);border-radius:3px 3px 0 0;min-height:2px;opacity:.8}
.dev-spark i.gap{background:rgb(var(--hi) / .1)}

/* ================= developer options ================= */
.dev-switches{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:6px 14px;margin:4px 0 6px;padding:12px 14px;border-radius:12px;background:rgb(var(--hi) / .03);border:1px solid rgb(var(--hi) / .06)}
.dev-switches label{display:flex;align-items:center;gap:8px;font-size:13.5px;cursor:pointer}
.dev-sec{margin-top:18px;padding-top:16px;border-top:1px solid rgb(var(--hi) / .06)}
.dev-sec h4{margin:0 0 4px;font:700 15px/1.2 var(--display);display:flex;align-items:center;gap:10px}
.dev-sec h4 .seg{margin-left:auto}
.dev-sec .help{margin:2px 0 10px}
.dev-table{width:100%;border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums}
.dev-table th,.dev-table td{text-align:right;padding:6px 8px;border-bottom:1px solid rgb(var(--hi) / .06)}
.dev-table th:first-child,.dev-table td:first-child{text-align:left}
.dev-table th{color:var(--muted);font-weight:600}
.dev-row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.dev-row select,.dev-row input{min-width:0}
.dev-out{white-space:pre-wrap;background:var(--deep);padding:12px 14px;border-radius:10px;font:12px/1.5 ui-monospace,Consolas,monospace;color:var(--muted);max-height:320px;overflow:auto;margin-top:10px}
.dev-form{display:grid;gap:8px}
.dev-form textarea{width:100%;border-radius:10px;border:1px solid var(--edge);background:var(--deep);color:var(--text);padding:10px;font:inherit;resize:vertical}
.dev-spark{height:64px}
.dev-labels{display:flex;justify-content:space-between;font-size:11.5px;color:var(--faint);margin-top:4px}
.notice{display:flex;align-items:center;gap:14px;padding:14px 18px;margin:0 0 22px;border-radius:14px;background:var(--accent-tint);border:1px solid var(--accent-edge)}
.notice .ni{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:var(--accent);color:var(--accent-ink);flex:none}
.notice .grow{flex:1;min-width:0;font-size:14.5px}
.notice.preview{outline:2px dashed var(--accent-edge);outline-offset:3px}
</style>
</head>
<body>
<div id="splash" aria-hidden="true"><div class="in"><div class="mark"><i></i><i></i><i></i><i></i></div><span class="word">ModHub</span></div></div>
<div class="app">
  <aside class="side">
    <div class="brand"><div class="mark"><i></i><i></i><i></i><i></i></div>ModHub</div>
    <button class="kpill" id="palBtn" title="Search everything (Ctrl+K)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>Search<kbd>Ctrl K</kbd></button>
    <button class="nav on" data-tab="home">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V20h5v-6h4v6h5V9.5"/></svg>
      Home<span class="n" id="navHome"></span></button>
    <button class="nav" data-tab="library">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
      Library<span class="n" id="navLib"></span></button>
    <button class="nav" data-tab="discover">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/></svg>
      Discover</button>
    <button class="nav" data-tab="install">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12m0 0l-5-5m5 5l5-5M4 19h16"/></svg>
      Install</button>
    <button class="nav" data-tab="instances">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/></svg>
      Instances<span class="n" id="navInst"></span></button>
    <button class="nav" data-tab="ports">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a4 4 0 0 0 5 5L21 13l-8 8-3-3 1.4-1.4a4 4 0 0 0-5-5L5 13 3 11l8-8 2 2z"/></svg>
      Ports<span class="n" id="navPorts"></span></button>
    <button class="nav" data-tab="settings">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>
      Settings</button>
    <div class="foot">
      <button class="upd hidden" id="updPill"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 19V5m0 0l-6 6m6-6l6 6"/></svg><span>Update to <b id="updVer"></b></span></button>
      <button class="help-btn" id="helpBtn"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.2-2.4 3.6M12 17h.01"/></svg>How to use</button>
      <button class="help-btn wn-side" id="wnFab"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.9 4.6L18.5 9l-4.6 1.9L12 15.5l-1.9-4.6L5.5 9l4.6-1.4z"/><path d="M19 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/></svg>What's new<i class="wn-dot hidden" id="wnDot"></i></button>
      <div class="version" id="verLabel"></div>
    </div>
  </aside>

  <div class="topbar" id="topbar"><span class="tt" id="topTitle"></span><button class="btn sm quiet top-up" id="topUp" title="Back to the top">Back to top</button></div>
  <main>
    <div class="newver hidden" id="newVer" role="status">
      <div class="big" id="newVerNum"></div>
      <div class="grow"><b id="newVerTitle"></b><p id="newVerText"></p></div>
      <button class="btn go" id="newVerGo"></button>
      <button class="btn quiet" id="newVerLater">Not now</button>
    </div>
    <div id="noticeBox"></div>
    <div id="crashBox"></div>
    <div id="catchUp"></div>
    <!-- LIBRARY -->
    <!-- HOME -->
    <section id="tab-home">
      <div class="page-h">
        <div>
          <h1 id="homeHello">Welcome back</h1>
          <p class="lede">Here's what's going on with your mods.</p>
        </div>
        <div class="actions"><button class="btn" id="homeShare">Share a modpack</button></div>
      </div>
      <div class="home-grid">
        <section class="card home-upd" id="homeUpd"></section>
        <section class="card" id="homeInst"></section>
        <section class="card" id="homeFix"></section>
        <section class="card home-picks" id="homePicks"></section>
      </div>
    </section>

    <section id="tab-library" class="hidden">
      <div class="page-h">
        <div>
          <h1>Library</h1>
          <p class="lede">The mods, packs and shaders you always play with.</p>
        </div>
        <div class="actions"><button class="btn quiet" id="libShare">Share</button><button class="btn" onclick="openImport()">Import from a launcher</button></div>
      </div>

      <div class="banner warn hidden" id="nativeBanner" style="margin:0 0 24px;border-left-color:var(--accent)">
        <div class="grow"><b>Run ModHub as its own app</b><p id="nativeText">Right now ModHub borrows a window from Edge or Chrome. A one-time setup gives it its own window, so no browser is involved.</p></div>
        <button class="btn sm go" data-native-setup>Set up</button>
        <button class="btn sm quiet" id="nativeLater">Not now</button>
      </div>
      <div class="banner warn hidden" id="shortcutBanner" style="margin:0 0 24px;border-left-color:var(--accent)">
        <div class="grow"><b>Open ModHub like any other app</b><p id="shortcutText"></p></div>
        <button class="btn sm go" data-shortcut>Add shortcut</button>
        <button class="btn sm quiet" id="shortcutLater">Not now</button>
      </div>

      <div id="starter" class="hidden" style="margin-bottom:26px"></div>
      <div id="importNote" style="margin-bottom:10px"></div>

      <div class="lobar" id="loBar" aria-label="Loadouts"></div>
      <div class="seg kindseg" id="kindSeg" role="tablist">
        <button class="on" data-kind="mod" role="tab">Mods</button><button data-kind="resourcepack" role="tab">Resource packs</button><button data-kind="shader" role="tab">Shaders</button>
      </div>
      <div class="searchbar">
        <div class="q">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
          <input id="q" placeholder="Search Modrinth for mods" autocomplete="off" aria-label="Search"><span class="kbd" title="Press / to search">/</span>
        </div>
        <select id="searchLoader" aria-label="Loader">
          <option value="">Any loader</option><option value="fabric">Fabric</option><option value="quilt">Quilt</option><option value="forge">Forge</option><option value="neoforge">NeoForge</option>
        </select>
      </div>
      <p class="help hidden" id="shaderHelp">Shaders need Iris to run (Oculus on Forge). ModHub adds it for you when you install. In game, turn shaders on under Options, Video Settings, Shader Packs.</p>
      <p class="help">Found it on CurseForge? <a href="#" onclick="openFiles();return false">Add from CurseForge</a>, or drag the file into this window.</p>
      <div id="results"></div>

      <div class="inv-h">
        <h3 id="invTitle">Your mods</h3>
        <div class="inv-tools">
          <button class="btn sm boostbtn" id="boostBtn" title="Add a trusted set of mods that make Minecraft run faster and smoother"><svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg><span id="boostCard">Performance boost</span></button>
          <input class="filter" id="libFilter" placeholder="Filter your mods" aria-label="Filter your mods">
        </div>
      </div>
      <div class="inv" id="inv"></div>
    </section>

    <!-- DISCOVER -->
    <section id="tab-discover" class="hidden">
      <div class="page-h">
        <div>
          <h1>Discover</h1>
          <p class="lede">What's popular for your version, plus picks that suit your mods.</p>
        </div>
      </div>
      <div class="disc-bar">
        <div class="seg" id="discKind" role="tablist">
          <button class="on" data-dkind="mod" role="tab">Mods</button><button data-dkind="resourcepack" role="tab">Resource packs</button><button data-dkind="shader" role="tab">Shaders</button>
        </div>
        <div class="disc-for">For Minecraft <select id="discVer" aria-label="Minecraft version"></select>
          <span id="discLoaderWrap">with <select id="discLoader" aria-label="Loader"><option value="fabric">Fabric</option><option value="quilt">Quilt</option><option value="forge">Forge</option><option value="neoforge">NeoForge</option></select></span></div>
      </div>
      <div id="discOut"></div>
    </section>

    <!-- INSTALL -->
    <section id="tab-install" class="hidden">
      <div class="page-h"><div>
        <h1>Install</h1>
        <p class="lede">Pick a version and a launcher. ModHub does the rest.</p>
      </div></div>

      <div class="block">
        <label class="field-label" for="verSel">Minecraft version</label>
        <div class="row" style="align-items:center">
          <select id="verSel" style="width:220px"></select>
          <input id="verOther" class="hidden" placeholder="Type a version, like 26.4" style="width:240px">
          <span class="loader-line">for <b id="loaderName">Fabric</b> mods <button class="linkbtn" id="changeLoader">Change</button></span>
        </div>
      </div>
      <div class="block">
        <label class="field-label" for="loSel">Loadout</label>
        <div class="row" style="align-items:center">
          <select id="loSel" style="width:260px"></select>
          <span class="help" style="margin:0" id="loHelp"></span>
        </div>
      </div>

      <div class="block">
        <span class="field-label">Where should your mods go?</span>
        <div class="launchers" id="launchers"></div>
        <button class="linkbtn hidden" id="moreLaunchers" style="margin-top:12px">Show other launchers</button>
        <div id="folderRow" class="hidden" style="margin-top:16px">
          <label class="field-label" for="folder">Mods folder</label>
          <div class="picker"><input id="folder" placeholder="Choose the mods folder"><button class="btn" data-browse="#folder" data-title="Choose the mods folder to install into">Browse</button></div>
          <p class="help" id="folderHelp"></p>
        </div>
      </div>

      <div class="block" id="carryBlock">
        <span class="field-label">Your settings</span>
        <div class="carry">
          <label class="check" style="margin:0"><input type="checkbox" id="carryOn"> Bring my settings along from</label>
          <select id="carryFrom" aria-label="Instance to copy settings from"></select>
        </div>
        <p class="help">Video settings, keybinds, your server list and mod configs. Anything the new instance already has stays as it is.</p>
      </div>

      <div class="block">
        <button class="btn go big" id="installBtn">Install mods</button>
        <details class="more" id="more">
          <summary>More options</summary>
          <div class="more-body">
            <div>
              <span class="field-label">Mod loader</span>
              <div class="seg" id="loaderSeg" role="radiogroup">
                <button data-loader="fabric">Fabric</button><button data-loader="quilt">Quilt</button><button data-loader="forge">Forge</button><button data-loader="neoforge">NeoForge</button>
              </div>
              <p class="help" id="loaderHelp">Most mods use Fabric. If your mods came from a Forge or NeoForge modpack, pick that instead.</p>
            </div>
            <div style="max-width:360px">
              <label class="field-label" for="iname">Name in your launcher</label>
              <input id="iname">
            </div>
            <label class="check"><input type="checkbox" id="snap"> Include snapshot versions in the list</label>
            <div><button class="btn" id="checkBtn">Check what's available without installing</button></div>
          </div>
        </details>

        <div class="progress hidden" id="progress">
          <div class="live">
            <div class="ring" id="ring"><svg viewBox="0 0 64 64"><defs><linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color:var(--accent-2)"/><stop offset="1" style="stop-color:var(--accent-3)"/></linearGradient></defs><circle class="trk" cx="32" cy="32" r="28"/><circle class="arc" id="ringArc" cx="32" cy="32" r="28"/></svg><span id="ringPct">0%</span></div>
            <div class="grow"><b id="liveTitle">Installing</b><div class="now" id="now"></div><div class="livelist" id="liveList"></div></div>
          </div>
          <div class="bar"><div id="barFill"></div></div>
          <details class="log"><summary>Show details</summary><pre id="log"></pre></details>
        </div>
        <div id="outcome"></div>
      </div>
    </section>

    <!-- INSTANCES -->
    <section id="tab-instances" class="hidden">
      <div class="page-h">
        <div>
          <h1>Instances</h1>
          <p class="lede">Everything ModHub has installed, ready to update.</p>
        </div>
        <div class="actions"><button class="btn go" id="updAll">Update all</button></div>
      </div>
      <div id="instAllOut"></div>
      <div id="instList"></div>
    </section>

    <!-- PORTS -->
    <section id="tab-ports" class="hidden">
      <div class="page-h"><div>
        <h1>Ports</h1>
        <p class="lede">Mods Claude is updating for you. Finished ones are added the next time you install.</p>
      </div></div>
      <div id="toolsWarn"></div>
      <div id="ports"></div>
    </section>

    <!-- SETTINGS -->
    <section id="tab-settings" class="hidden">
      <div class="page-h"><div>
        <h1>Settings</h1>
        <p class="lede">Make ModHub look and work the way you like.</p>
      </div></div>
      <div class="settings">
        <section class="card" id="appearanceCard">
          <div class="card-h"><span class="card-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="13.5" cy="6.5" r="1.5"/><circle cx="17.5" cy="10.5" r="1.5"/><circle cx="8.5" cy="7.5" r="1.5"/><circle cx="6.5" cy="12.5" r="1.5"/><path d="M12 2a10 10 0 1 0 0 20c1 0 1.7-.8 1.7-1.7 0-.4-.2-.8-.4-1.1-.3-.3-.4-.7-.4-1.1 0-.9.8-1.7 1.7-1.7H16a6 6 0 0 0 6-6C22 6 17.5 2 12 2z"/></svg></span><div><h3>Appearance</h3><p>Pick a theme. Open More options to fine-tune it.</p></div></div>
          <div class="theme-grid" id="themeGrid" role="radiogroup" aria-label="Themes"></div>
          <p class="secret-count hidden" id="secretCount"></p>
          <details class="ap-more" id="apMore">
            <summary>More options <span>Light or dark, colour, background, corners, size and animations</span></summary>
            <div class="ap-opts">
              <div class="ap-group">
                <h4>Colours</h4>
                <div class="opt"><span class="opt-l">Mode</span><div class="seg" id="themeMode" role="radiogroup" aria-label="Light or dark mode"><button data-mode="dark" role="radio">Dark</button><button data-mode="light" role="radio">Light</button><button data-mode="system" role="radio" title="Match Windows">Auto</button></div></div>
                <div class="opt"><span class="opt-l">Colour</span><div class="swatches mini" id="accentPick" role="radiogroup" aria-label="Colour"></div></div>
                <div class="opt"><span class="opt-l">Background</span><div class="seg optseg" data-opt="bg" role="radiogroup" aria-label="Background"><button data-v="gradient" role="radio">Gradient</button><button data-v="vivid" role="radio">Vivid</button><button data-v="glow" role="radio">Glow</button><button data-v="plain" role="radio">Plain</button></div></div>
                <div class="opt" data-needs-bg><span class="opt-l">Starts from</span><div class="seg optseg" data-opt="dir" role="radiogroup" aria-label="Where the gradient starts"><button data-v="top" role="radio">Top</button><button data-v="corner" role="radio">Corner</button><button data-v="side" role="radio">Side</button><button data-v="bottom" role="radio">Bottom</button></div></div>
                <div class="opt" data-needs-bg><span class="opt-l">Strength</span><div class="range"><input type="range" id="bgStrength" min="10" max="100" step="1" aria-label="Background strength"><span id="bgStrengthVal"></span></div></div>
              </div>
              <div class="ap-group">
                <h4>Layout</h4>
                <div class="opt"><span class="opt-l">Corners</span><div class="seg optseg" data-opt="radius" role="radiogroup" aria-label="Corners"><button data-v="sharp" role="radio">Sharp</button><button data-v="rounded" role="radio">Rounded</button><button data-v="round" role="radio">Round</button></div></div>
                <div class="opt"><span class="opt-l">Sidebar</span><div class="seg optseg" data-opt="side" role="radiogroup" aria-label="Sidebar"><button data-v="glass" role="radio">See-through</button><button data-v="solid" role="radio">Solid</button></div></div>
                <div class="opt"><span class="opt-l">Size</span><div class="seg optseg" data-opt="size" role="radiogroup" aria-label="Size"><button data-v="90" role="radio" title="Small">S</button><button data-v="100" role="radio" title="Normal">M</button><button data-v="110" role="radio" title="Large">L</button><button data-v="120" role="radio" title="Larger">XL</button></div></div>
                <div class="opt"><span class="opt-l">Animations</span><div class="seg optseg" data-opt="motion" role="radiogroup" aria-label="Animations"><button data-v="fluid" role="radio" title="Smooth, modern animations">Fluid</button><button data-v="full" role="radio" title="The original animations">Classic</button><button data-v="less" role="radio">Fewer</button><button data-v="off" role="radio">Off</button></div></div>
                <div class="opt reset"><button class="btn quiet sm" id="themeReset">Reset to default</button></div>
              </div>
            </div>
          </details>
        </section>
        <section class="card">
          <div class="card-h"><span class="card-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/></svg></span><div><h3>Updates</h3><p id="updText"></p></div></div>
          <button class="linkbtn hidden" id="updPeek"></button>
          <p class="help" id="updSourceStatus" style="margin:0"></p>
          <label class="check" style="margin:0"><input type="checkbox" id="updAuto" checked> Install updates by itself when ModHub starts</label>
          <div class="actions">
            <button class="btn go hidden" id="updApply">Update now</button>
            <button class="btn" id="updCheck">Check for updates</button>
            <button class="btn quiet" id="updNotes">What's new</button>
            <button class="btn quiet" id="updFile">Install from a file</button>
            <button class="btn quiet hidden" id="updUndo">Go back to the previous version</button>
          </div>
        </section>
        <section class="card hidden" id="devCard">
          <div class="card-h"><span class="card-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 9l-4 3 4 3M16 9l4 3-4 3M13.5 6l-3 12"/></svg></span><div><h3>Developer</h3><p>Only you can see this. Turn each option on or off, or leave developer mode any time.</p></div></div>
          <div class="dev-switches" id="devSwitches"></div>
          <div id="devBody"></div>
          <div class="actions" style="margin-top:14px"><button class="btn quiet" id="devLeave">Leave developer mode</button></div>
        </section>
        <section class="card">
          <div class="card-h"><span class="card-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16v16H4z"/><path d="M4 9h16M9 4v16"/></svg></span><div><h3>Your library</h3><p>Save all your loadouts and the files you added yourself in one backup file. Restore it on another PC or after a reinstall, or drag a backup onto ModHub.</p></div></div>
          <div class="actions">
            <button class="btn" id="bkSave">Save a backup</button>
            <label class="btn" style="cursor:pointer">Restore from a backup<input type="file" id="bkFile" accept=".zip" hidden></label>
          </div>
          <div id="bkOut"></div>
        </section>
        <section class="card" id="appCard">
          <div class="card-h"><span class="card-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="14" rx="2"/><path d="M8 21h8"/></svg></span><div><h3>App</h3><p id="windowMode"></p></div></div>
          <div id="windowActions"></div>
          <p class="help" style="margin:0" id="shortcutHelp"></p>
          <div><button class="btn" data-shortcut>Add shortcut</button></div>
        </section>
        <details class="card adv">
          <summary class="card-h"><span class="card-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg></span><div><h3>Launcher folders</h3><p>ModHub finds these on its own. Change them only if you moved a launcher.</p></div></summary>
          <div><label class="field-label">Minecraft Launcher (.minecraft)</label><input data-path="official"></div>
          <div><label class="field-label">Prism Launcher data folder</label><input data-path="prism"></div>
          <div><label class="field-label">Modrinth App data folder</label><input data-path="modrinth_app"></div>
          <div class="actions"><button class="btn go" id="saveSettings">Save folders</button></div>
        </details>
        <section class="card about">
          <div class="card-h"><span class="card-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg></span><div><h3>About</h3><p>ModHub <span id="aboutVer"></span>. Your library and settings are saved on this computer in <code class="inline" id="dataDir"></code>.</p></div></div>
          <p class="help" style="margin:0" id="quitHelp"></p>
          <div class="actions"><button class="btn quiet" id="aboutNotes">What's new</button><button class="btn quiet" id="quitBtn">Stop ModHub</button></div>
        </section>
      </div>
    </section>
  </main>
</div>

<!-- import modal -->
<div class="scrim hidden" id="importModal" role="dialog" aria-modal="true" aria-labelledby="impTitle">
  <div class="modal">
    <h2 id="impTitle">Import mods you already have</h2>
    <p class="lede">Pick a mods folder. ModHub adds those mods to your library and leaves the files as they are.</p>
    <div id="impFolders" style="margin-top:18px"></div>
    <div class="actions" style="margin-top:14px"><button class="btn" id="impBrowse">Choose a folder</button></div>
    <details class="more" style="margin-top:14px"><summary>Type a path instead</summary>
      <div class="picker" style="margin-top:10px"><input id="importPath" placeholder="Full path to a mods folder"><button class="btn" id="importGo">Import</button></div>
    </details>
    <div id="importOut"></div>
    <div class="foot"><button class="btn quiet" data-close>Close</button></div>
  </div>
</div>

<!-- loadout modal -->
<div class="scrim hidden" id="loModal" role="dialog" aria-modal="true" aria-labelledby="loTitle">
  <div class="modal" id="loBody"></div>
</div>

<!-- crash modal -->
<div class="scrim hidden" id="crashModal" role="dialog" aria-modal="true" aria-labelledby="crashTitle">
  <div class="modal" id="crashBody"></div>
</div>

<!-- performance boost modal -->
<div class="scrim hidden" id="boostModal" role="dialog" aria-modal="true" aria-labelledby="boostTitle">
  <div class="modal" id="boostBody"></div>
</div>

<!-- what changed -->
<div class="scrim hidden" id="chgModal" role="dialog" aria-modal="true" aria-labelledby="chgTitle">
  <div class="modal" id="chgBody" style="width:min(680px,100%)"></div>
</div>

<!-- how to use -->
<div class="scrim hidden" id="helpModal" role="dialog" aria-modal="true" aria-labelledby="helpTitle">
  <div class="modal howto">
    <h2 id="helpTitle">How to use ModHub</h2>
    <p class="lede">Four steps, and the last one happens by itself.</p>
    <ol class="steps-list">
      <li><b>Add your mods</b><span>Import the mods folder you already play with, or search Modrinth on the Library page.</span><button class="btn sm" data-help-go="library">Open Library</button></li>
      <li><b>Find more</b><span>Discover shows what's popular for your Minecraft version, and picks that go with your mods.</span><button class="btn sm" data-help-go="discover">Open Discover</button></li>
      <li><b>Install</b><span>Pick a Minecraft version and your launcher, then click Install. ModHub sets everything up.</span><button class="btn sm" data-help-go="install">Open Install</button></li>
      <li><b>Stay up to date</b><span>ModHub tells you when a missing mod comes out. Update brings an instance up to date in one click.</span><button class="btn sm" data-help-go="instances">Open Instances</button></li>
    </ol>
    <p class="help" style="margin:16px 0 0">Tip: press <kbd>Ctrl</kbd> <kbd>K</kbd> to jump to anything.</p>
    <div class="foot"><button class="btn go" data-close>Got it</button></div>
  </div>
</div>

<!-- mod page -->
<div class="scrim hidden" id="modModal" role="dialog" aria-modal="true" aria-labelledby="mpTitle">
  <div class="modal modpage" id="mpBody"></div>
</div>

<!-- ModHub's own changelog -->
<div class="scrim hidden" id="wnModal" role="dialog" aria-modal="true" aria-labelledby="wnTitle">
  <div class="modal" id="wnBody" style="width:min(600px,100%)"></div>
</div>

<!-- problems popup -->
<div class="scrim hidden" id="probModal" role="dialog" aria-modal="true" aria-labelledby="probTitle">
  <div class="modal" id="probBody"></div>
</div>

<!-- add files modal -->
<div class="scrim hidden" id="updModal" role="dialog" aria-modal="true" aria-labelledby="updMTitle">
  <div class="modal" id="updMBody" style="width:min(680px,100%)"></div>
</div>
<div class="scrim hidden" id="shareModal" role="dialog" aria-modal="true" aria-labelledby="shareTitle">
  <div class="modal" style="width:min(620px,100%)">
    <h2 id="shareTitle">Share a modpack</h2>
    <div class="seg share-tabs" role="tablist"><button class="on" data-stab="give" role="tab">Share yours</button><button data-stab="get" role="tab">Open a shared one</button></div>
    <div id="shareGive">
      <label class="lbl" for="shareLo">Loadout</label>
      <select id="shareLo"></select>
      <h4 class="share-h">Share code</h4>
      <p class="help">Send this to a friend. They paste it into ModHub under Open a shared one.</p>
      <div class="share-code"><textarea id="shareCode" readonly rows="3" aria-label="Share code"></textarea><button class="btn go" id="shareCopy">Copy</button></div>
      <p class="help" id="shareNote"></p>
      <h4 class="share-h">Files</h4>
      <div class="share-row"><div><b>ModHub file</b><p class="help">The same as the code, as a file you can send.</p></div><button class="btn" id="shareFile">Save .modhub file</button></div>
      <div class="share-row"><div><b>Modrinth modpack</b><p class="help">Opens in Prism, the Modrinth App and other launchers. Pick the version it's for.</p>
        <div class="share-mr"><select id="shareVer" aria-label="Minecraft version"></select><select id="shareLoader" aria-label="Loader"><option value="fabric">Fabric</option><option value="quilt">Quilt</option><option value="neoforge">NeoForge</option><option value="forge">Forge</option></select></div></div>
        <button class="btn" id="shareMr">Save .mrpack</button></div>
      <p class="help" id="shareSaved"></p>
    </div>
    <div id="shareGet" class="hidden">
      <label class="lbl" for="shareIn">Paste a share code</label>
      <textarea id="shareIn" rows="3" placeholder="MH1-..." spellcheck="false"></textarea>
      <div class="actions" style="margin-top:10px"><button class="btn go" id="shareOpen">Open</button><button class="btn" id="sharePick">Choose a file (.modhub or .mrpack)</button><input type="file" id="shareFileIn" accept=".modhub,.mrpack" hidden></div>
      <div id="sharePrev"></div>
    </div>
    <div class="foot"><button class="btn quiet" data-close>Close</button></div>
  </div>
</div>
<div class="scrim hidden" id="filesModal" role="dialog" aria-modal="true" aria-labelledby="filesTitle">
  <div class="modal">
    <h2 id="filesTitle">Add files from CurseForge</h2>
    <p class="lede" id="filesLede">Got a mod (.jar), resource pack or shader (.zip) from curseforge.com? Add the file here. ModHub keeps a copy and installs it whenever you install the Minecraft version it's made for.</p>
    <ol class="howto" id="filesHow">
      <li>On <a href="https://www.curseforge.com/minecraft" target="_blank" rel="noopener">curseforge.com</a>, open the mod, resource pack or shader.</li>
      <li>Open its <b>Files</b> tab, pick the file for your Minecraft version, and download it.</li>
      <li>Drop the file below, or drag it anywhere onto ModHub.</li>
    </ol>
    <label class="drop" id="drop"><input type="file" id="fileInput" multiple accept=".jar,.zip" hidden>
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 15V3m0 0l-4 4m4-4l4 4M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/></svg>
      <b>Drop files here</b><span>or click to choose them</span></label>
    <div id="filesOut"></div>
    <div class="foot"><button class="btn go" data-close>Done</button></div>
  </div>
</div>

<!-- your own item modal -->
<div class="scrim hidden" id="itemModal" role="dialog" aria-modal="true" aria-labelledby="itemTitle">
  <div class="modal" id="itemBody"></div>
</div>

<div class="dropcover hidden" id="dropCover"><div>Drop to add to ModHub</div></div>

<!-- port modal -->
<div class="scrim hidden" id="portModal" role="dialog" aria-modal="true" aria-labelledby="portTitle">
  <div class="modal" id="portBody"></div>
</div>

<div class="toast hidden" id="toast" role="status"></div>

<script>
const T = "__TOKEN__";
let S = null, launcher = null, loader = "fabric", lastResults = [], lastRun = null, portsData = null;
let libKind = "mod";
const KIND = {mod: {one: "mod", many: "mods", title: "Your mods"}, resourcepack: {one: "resource pack", many: "resource packs", title: "Your resource packs"},
              shader: {one: "shader", many: "shaders", title: "Your shaders"}};
const KIND_LABEL = {mod: "Mod", resourcepack: "Resource pack", shader: "Shader"};
const LOADER_NAMES = {fabric: "Fabric", quilt: "Quilt", forge: "Forge", neoforge: "NeoForge"};

const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = n => n >= 1e6 ? (n/1e6).toFixed(1).replace(/\.0$/, "") + "M" : n >= 1e3 ? Math.round(n/1e3) + "K" : String(n || 0);
const safeUrl = u => /^https:\/\//.test(u || "") || /^data:image\/png;base64,[A-Za-z0-9+\/=]+$/.test(u || "") ? u : "";
const ico = (m, cls = "ico") => `<div class="${cls}">${safeUrl(m.icon) ? `<img src="${esc(m.icon)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : esc((m.name || "?").trim()[0] || "?")}</div>`;
const link = (m, inner) => safeUrl(m.url) ? `<a href="${esc(m.url)}" target="_blank" rel="noopener" style="color:inherit">${inner}</a>` : inner;
const srcLabel = s => s === "modrinth" ? `<span class="src"><span class="dot mr"></span>Modrinth</span>` : `<span class="src"><span class="dot own"></span>Your file</span>`;

async function api(path, body = {}) {
  const r = await fetch(path, {method: "POST", headers: {"X-Token": T, "Content-Type": "application/json"}, body: JSON.stringify(body)});
  const j = await r.json().catch(() => ({error: r.statusText}));
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}
let toastTimer;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg;
  t.classList.add("hidden"); void t.offsetWidth; t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 3400);
}

/* ---------- navigation ---------- */
let portsPoll;
function go(tab) {
  $$(".nav").forEach(b => b.classList.toggle("on", b.dataset.tab === tab));
  ["home", "library", "discover", "install", "instances", "ports", "settings"].forEach(t => {
    const el = $("#tab-" + t), show = t === tab;
    const wasHidden = el.classList.contains("hidden");
    el.classList.toggle("hidden", !show);
    if (show && wasHidden) { el.classList.remove("enter"); void el.offsetWidth; el.classList.add("enter"); }
  });
  if (typeof settle === "function") settle();
  clearInterval(portsPoll);
  if (tab === "ports") { loadPorts(); portsPoll = setInterval(loadPorts, 4000); }
  if (tab === "install" && S) { updateSteps(); loadCarry(); }
  if (tab === "instances" && S) renderInstances();
  if (tab === "discover" && S && (!discData || discStale)) loadDiscover();
  if (tab === "home" && S) renderHome();
  window.scrollTo(0, 0);
}
$$(".nav").forEach(b => b.onclick = () => go(b.dataset.tab));
document.addEventListener("click", e => { const g = e.target.closest("[data-go]"); if (g) { e.preventDefault(); go(g.dataset.go); } });

/* ---------- library ---------- */
const isFav = m => S.favorites.some(f => f.source === m.source && String(f.id) === String(m.id));

function renderInventory() {
  const all = S.favorites;
  if (all.length) $("#starter").classList.add("hidden");
  if (typeof renderAppBits === "function" && $("#shortcutText").textContent) renderAppBits();
  $("#navLib").textContent = all.length || "";
  const lo = (S.loadouts || []).find(l => l.id === S.active_loadout);
  if (lo && lo.count !== all.length) { lo.count = all.length; if (typeof renderLoadouts === "function") renderLoadouts(); }
  const favs = all.filter(m => (m.kind || "mod") === libKind);
  const K = KIND[libKind];
  $("#invTitle").textContent = favs.length ? `${K.title} (${favs.length})` : K.title;
  $("#libFilter").classList.toggle("hidden", favs.length < 8);
  $("#libFilter").placeholder = `Filter your ${K.many}`;
  const f = $("#libFilter").value.trim().toLowerCase();
  const shown = [...favs].filter(m => !f || m.name.toLowerCase().includes(f)).sort((a, b) => a.name.localeCompare(b.name));
  let h = shown.map(m => {
    const own = m.source === "local";
    const needs = own && !(m.files || []).length;
    return `
    <div class="cell ${own ? "own" : ""}" data-k="${esc(m.source)}:${esc(m.id)}" data-tip="${esc(m.name)}" data-tip-d="${esc(m.desc || "")}" data-tip-h="${own ? "Click to see its files" : m.source === "modrinth" ? "Click to see its page" : ""}" aria-label="${esc(m.name)}" ${own ? `data-own="${esc(m.id)}"` : m.source === "modrinth" ? `data-mp="${esc(m.id)}"` : ""}>
      <div class="slot">
        ${safeUrl(m.icon) ? `<img src="${esc(m.icon)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : `<span class="letter">${esc((m.name || "?")[0])}</span>`}
        ${needs ? `<span class="badge" title="Add its file">File?</span>` : ""}
        <span class="dot ${own ? "own" : "mr"} srcmark" title="${own ? "Your file" : "Modrinth"}"></span>
        <button class="rm" aria-label="Remove ${esc(m.name)}" data-rm="${esc(m.source)}|${esc(m.id)}">
          <svg width="12" height="12" viewBox="0 0 12 12" stroke="currentColor" stroke-width="2"><path d="M2 2l8 8M10 2l-8 8"/></svg></button>
      </div>
      <div class="cap">${own ? esc(m.name) : link(m, esc(m.name))}</div>
    </div>`; }).join("");
  if (!favs.length) {
    h = `<div class="inv-empty">${libKind === "mod"
          ? "Your slots are empty. Import the mods you already play with, or search for new ones above."
          : `No ${KIND[libKind].many} yet. Search Modrinth above, or add one you downloaded from CurseForge.`}</div>` +
        Array.from({length: 7}, () => `<div class="cell ghost"><div class="slot"></div></div>`).join("");
  } else if (!shown.length) {
    h = `<div class="inv-empty">Nothing matches "${esc(f)}".</div>`;
  }
  $("#inv").innerHTML = h;
  $$("[data-rm]").forEach(b => b.onclick = async e => {
    e.stopPropagation();
    const [source, id] = b.dataset.rm.split("|");
    const item = S.favorites.find(x => x.source === source && String(x.id) === id) || {};
    if (source === "local" && (item.files || []).length && !confirm(`Remove ${item.name} and the files you added for it?`)) return;
    const cell = b.closest(".cell");
    if (cell && !REDUCED) { cell.classList.add("leaving"); await new Promise(r => setTimeout(r, 260)); }
    S.favorites = (await api("/api/favorites/remove", {source, id})).favorites;
    renderInventory(); renderResults(); renderStarter(); toast(`Removed ${item.name}`);
  });
  $$("[data-own]").forEach(c => c.onclick = () => openItem(c.dataset.own));
  $$("#inv [data-mp]").forEach(c => c.onclick = e => { if (e.target.closest(".rm")) return; const m = S.favorites.find(f => f.source === "modrinth" && String(f.id) === c.dataset.mp); if (m) openModPage(m); });
  if (typeof stagger === "function") stagger($("#inv"), ".cell", true);
}
function setKind(k) {
  libKind = k;
  $$("#kindSeg button").forEach(b => { b.classList.toggle("on", b.dataset.kind === k); b.setAttribute("aria-selected", b.dataset.kind === k); });
  $("#q").placeholder = `Search Modrinth for ${KIND[k].many}`;
  $("#shaderHelp").classList.toggle("hidden", k !== "shader");
  $("#boostBtn").classList.toggle("hidden", k !== "mod");
  $("#searchLoader").classList.toggle("hidden", k !== "mod");
  lastResults = []; $("#results").innerHTML = "";
  if ($("#q").value.trim()) search();
  renderInventory();
}
$$("#kindSeg button").forEach(b => b.onclick = () => setKind(b.dataset.kind));
$("#libFilter").oninput = renderInventory;

function renderResults() {
  const box = $("#results");
  if (!lastResults.length) return;
  box.innerHTML = `<div class="results">
    <div class="results-h"><span>${lastResults.length} results for "${esc($("#q").value.trim())}"</span><button class="btn quiet sm" id="clearRes">Clear</button></div>
    ${lastResults.map((m, i) => `
      <div class="res">${ico(m)}
        <div class="body">
          <div class="t"><button class="linkbtn mp-open" data-mpi="${i}">${esc(m.name)}</button> ${srcLabel(m.source)}</div>
          <div class="d">${esc(m.desc)}</div>
          <div class="m">${m.author ? "by " + esc(m.author) + ", " : ""}${fmt(m.downloads)} downloads</div>
        </div>
        ${isFav(m) ? `<span class="added"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M2 7.5l3 3 7-7"/></svg>In library</span>`
                   : `<button class="btn sm go" data-add="${i}">Add</button>`}
      </div>`).join("")}
  </div>`;
  if (typeof stagger === "function") stagger($("#results"), ".res");
  $$("#results [data-mpi]").forEach(b => b.onclick = () => openModPage(lastResults[+b.dataset.mpi]));
  $("#clearRes").onclick = () => { lastResults = []; $("#results").innerHTML = ""; $("#q").value = ""; $("#q").focus(); };
  $$("[data-add]").forEach(b => b.onclick = async () => {
    b.disabled = true;
    const m = lastResults[+b.dataset.add];
    S.favorites = (await api("/api/favorites/add", {mod: {...m, kind: m.kind || libKind}})).favorites;
    renderInventory(); renderResults();
  });
}

let searchTimer, searchSeq = 0;
async function search() {
  const qtext = $("#q").value.trim();
  if (!qtext) { lastResults = []; $("#results").innerHTML = ""; return; }
  const seq = ++searchSeq;
  $("#results").innerHTML = `<div class="results"><div class="results-h"><span><span class="spin"></span>&nbsp; Searching Modrinth</span></div>` +
    Array.from({length: 3}, () => `<div class="skel"><i></i><span><i style="height:12px;width:40%"></i><i style="height:10px;width:75%"></i></span></div>`).join("") + `</div>`;
  try {
    const r = await api("/api/search", {q: qtext, loader: libKind === "mod" ? $("#searchLoader").value : "", kind: libKind});
    if (seq !== searchSeq) return;
    lastResults = r.results;
    if (!lastResults.length) $("#results").innerHTML = `<div class="results"><div class="results-h">Nothing found for "${esc(qtext)}". Try a shorter name.</div></div>`;
    else renderResults();
    if (r.errors.length) $("#results").insertAdjacentHTML("afterbegin", `<div class="banner warn"><div class="grow"><b>Some results are missing</b><p>${r.errors.map(esc).join("<br>")}</p></div></div>`);
  } catch (e) {
    $("#results").innerHTML = `<div class="banner err"><div class="grow"><b>Search didn't work</b><p>${esc(e.message)}</p></div></div>`;
  }
}
$("#q").addEventListener("input", () => { clearTimeout(searchTimer); if ($("#q").value.trim().startsWith("/")) return; searchTimer = setTimeout(search, 350); });
$("#q").addEventListener("keydown", e => { if (e.key === "Enter") { clearTimeout(searchTimer); if (runCommand($("#q").value)) { $("#q").value = ""; return; } search(); } });
$("#searchLoader").onchange = search;

/* ---------- modals ---------- */
function openModal(id) { $(id).classList.remove("hidden"); }
function closeModals() { $$(".scrim").forEach(m => m.classList.add("hidden")); }
document.addEventListener("click", e => { if (e.target.matches("[data-close]") || e.target.classList.contains("scrim")) closeModals(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") { const z = $(".mp-zoom"); if (z) { z.remove(); return; } closeModals(); } });

const FOLDER_ICON = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>`;
let modFolders = null;
async function loadModFolders() {
  try { modFolders = (await api("/api/mod_folders")).folders; } catch (e) { modFolders = []; }
  return modFolders;
}
function folderList(folders, btnLabel = "Import") {
  if (!folders.length) return "";
  return `<div class="folders">${folders.map((f, i) => `
    <div class="folder"><div class="fico">${FOLDER_ICON}</div>
      <div class="body"><div class="t">${esc(f.name)}</div><div class="s">${esc(f.launcher)}, ${f.count} ${f.count === 1 ? "mod" : "mods"}</div></div>
      <button class="btn sm go" data-impf="${i}">${btnLabel}</button></div>`).join("")}</div>`;
}
async function renderStarter() {
  // first run: offer the folders we found right on the Library page
  const box = $("#starter");
  if (S.favorites.length) { box.classList.add("hidden"); return; }
  const folders = modFolders || await loadModFolders();
  box.classList.remove("hidden");
  box.innerHTML = `<div class="starter">
    <h3>Start with the mods you already have</h3>
    <p class="lede">${folders.length ? "ModHub found these mods folders on your computer. Import one to fill your library." : "Choose the mods folder of a launcher you play with, and ModHub adds those mods to your library."}</p>
    ${folderList(folders.slice(0, 5))}
    <div class="actions" style="margin-top:12px"><button class="btn" id="starterBrowse">${folders.length ? "Choose a different folder" : "Choose a folder"}</button></div>
  </div>`;
  box.querySelectorAll("[data-impf]").forEach(b => b.onclick = () => doImport(folders[+b.dataset.impf].path, box));
  $("#starterBrowse").onclick = async () => { const path = await browse("folder", "Choose a mods folder to import"); if (path) doImport(path, box); };
}
async function openImport() {
  $("#importOut").innerHTML = ""; openModal("#importModal");
  $("#impFolders").innerHTML = `<p class="now"><span class="spin"></span>&nbsp; Looking for mods folders</p>`;
  const folders = await loadModFolders();
  $("#impFolders").innerHTML = folders.length ? `<p class="help" style="margin:0 0 10px">Found on your computer:</p>` + folderList(folders) : "";
  $$("#impFolders [data-impf]").forEach(b => b.onclick = () => doImport(folders[+b.dataset.impf].path, $("#importOut")));
}
$("#impBrowse").onclick = async () => { const path = await browse("folder", "Choose a mods folder to import"); if (path) doImport(path, $("#importOut")); };
$("#importGo").onclick = () => doImport($("#importPath").value, $("#importOut"));

async function doImport(folder, outEl) {
  if (outEl && outEl.id === "starter") outEl = $("#importNote");  // the welcome panel goes away once mods are added
  outEl.insertAdjacentHTML("beforeend", "");
  const status = document.createElement("div");
  status.innerHTML = `<p class="now"><span class="spin"></span>&nbsp; Reading your mods</p>`;
  outEl.querySelectorAll(".banner, .now").forEach(n => n.remove());
  outEl.appendChild(status);
  $$("[data-impf]").forEach(b => b.disabled = true);
  try {
    const {job} = await api("/api/import", {folder});
    const res = await follow(job);
    let h = `<div class="banner"><div class="grow"><b>Added ${res.added.length} to your library</b><p>${res.already ? res.already + " were already in it. " : ""}${res.loader ? "These are " + LOADER_NAMES[res.loader] + " mods, so ModHub will install " + LOADER_NAMES[res.loader] + " versions. Resource packs and shaders in that instance were added too." : ""}</p></div></div>`;
    if (res.unknown.length) h += `<div class="banner warn"><div class="grow"><b>${res.unknown.length} ${res.unknown.length === 1 ? "file isn't" : "files aren't"} on Modrinth</b>
      <p>Probably from CurseForge: ${res.unknown.map(u => esc(u.name)).join(", ")}. Keep them as your own files so ModHub can install them too.</p>
      <div class="row" style="margin-top:10px;align-items:center"><span class="help" style="margin:0">They're for</span>
        <select class="keepVer" style="width:190px;height:34px">${versionOptions(res.folder_version || "unknown")}</select>
        <button class="btn sm go keepBtn">Keep them</button></div></div></div>`;
    status.innerHTML = h;
    const kb = status.querySelector(".keepBtn");
    if (kb) kb.onclick = async () => {
      const ver = status.querySelector(".keepVer").value;
      kb.disabled = true;
      try {
        const r = await api("/api/local/add_paths", {paths: res.unknown.map(u => u.path), version: ver === "unknown" ? null : ver});
        S.favorites = r.favorites; renderInventory();
        kb.closest(".banner").outerHTML = `<div class="banner"><div class="grow"><b>Kept ${r.added.length} as your own files</b><p>Click one in your library to see or change its Minecraft version.</p></div></div>`;
      } catch (e) { toast(e.message); kb.disabled = false; }
    };
    S = await api("/api/state");
    if (res.loader) setLoader(res.loader);
    renderInventory(); renderResults(); renderStarter();
    toast(`Added ${res.added.length} to your library`);
  } catch (e) {
    status.innerHTML = `<div class="banner err"><div class="grow"><b>Import didn't work</b><p>${esc(e.message)}</p></div></div>`;
  }
  $$("[data-impf]").forEach(b => b.disabled = false);
}

/* native folder / file picker */
async function browse(kind, title, start = "") {
  try { return (await api("/api/pick", {kind, title, start})).path; }
  catch (e) { toast(e.message); return null; }
}
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-browse]"); if (!b) return;
  const input = $(b.dataset.browse);
  b.disabled = true;
  const path = await browse(b.dataset.kind || "folder", b.dataset.title || "Choose a folder", input.value);
  b.disabled = false;
  if (path) { input.value = path; input.dispatchEvent(new Event("input")); }
});

/* ---------- your own files ---------- */
let filesTarget = null;
function versionOptions(current) {
  const rel = (S.versions || []).filter(v => v.type === "release").map(v => v.v).slice(0, 50);
  const list = [...rel];
  if (current && !["any", "unknown"].includes(current) && !list.includes(current)) list.unshift(current);
  return `${current === "unknown" || !current ? `<option value="unknown" selected>Choose version</option>` : ""}
    <option value="any" ${current === "any" ? "selected" : ""}>Any version</option>` +
    list.map(v => `<option value="${esc(v)}" ${v === current ? "selected" : ""}>Minecraft ${esc(v)}</option>`).join("");
}
function openFiles(target = null) {
  filesTarget = target;
  $("#filesOut").innerHTML = "";
  if (target) {
    $("#filesTitle").textContent = target.version ? `Add ${target.name} for ${target.version}` : `Add a file for ${target.name}`;
    $("#filesLede").innerHTML = `Download the ${target.version ? "Minecraft " + esc(target.version) + " " : ""}file for ${esc(target.name)}${safeUrl(target.url) ? ` from <a href="${esc(target.url)}" target="_blank" rel="noopener">its page</a>` : " from curseforge.com"}, then drop it here.`;
    $("#filesHow").classList.add("hidden");
  } else {
    $("#filesTitle").textContent = "Add files from CurseForge";
    $("#filesLede").textContent = "Got a mod (.jar), resource pack or shader (.zip) from curseforge.com? Add the file here. ModHub keeps a copy and installs it whenever you install the Minecraft version it's made for.";
    $("#filesHow").classList.remove("hidden");
  }
  openModal("#filesModal");
}
async function uploadFiles(files) {
  const target = filesTarget;
  for (const file of files) {
    const row = document.createElement("div");
    row.className = "frow";
    row.innerHTML = `<span class="spin"></span><div class="body"><div class="t">${esc(file.name)}</div><div class="s">Adding</div></div>`;
    $("#filesOut").appendChild(row);
    try {
      const qs = target ? `?item=${encodeURIComponent(target.id)}` + (target.version ? `&version=${encodeURIComponent(target.version)}` : "") : "";
      const r = await fetch("/api/local/upload" + qs, {method: "POST", headers: {"X-Token": T, "X-Filename": encodeURIComponent(file.name)}, body: file});
      const j = await r.json().catch(() => ({error: r.statusText}));
      if (!r.ok) throw new Error(j.error || r.statusText);
      if (j.restored) {
        const {restored, ...st} = j; S = st; renderAll();
        row.innerHTML = `<div class="body"><div class="t">${esc(file.name)}</div><div class="s" style="color:var(--ready)">Restored your library from this backup. Nothing was removed.</div></div>`;
        showRestored(restored);
        continue;
      }
      if (j.share) {
        row.innerHTML = `<div class="body"><div class="t">${esc(file.name)}</div><div class="s">A shared modpack. Opening it...</div></div>`;
        closeModals(); openShare("get"); showSharePreview(j.share);
        continue;
      }
      S.favorites = j.favorites;
      const it = j.item, v = j.version || "unknown";
      row.innerHTML = `${ico(it)}<div class="body"><div class="t">${esc(it.name)}</div><div class="s">${KIND_LABEL[it.kind] || "Mod"}, ${esc(j.file)}</div></div>
        <select class="${v === "unknown" ? "unset" : ""}" aria-label="Minecraft version for ${esc(it.name)}">${versionOptions(v)}</select>`;
      row.querySelector("select").onchange = async ev => {
        ev.target.classList.toggle("unset", ev.target.value === "unknown");
        S.favorites = (await api("/api/local/version", {id: it.id, file: j.file, version: ev.target.value})).favorites;
        toast(`${it.name} set to ${ev.target.value === "any" ? "any version" : "Minecraft " + ev.target.value}`);
      };
      if (v === "unknown") row.insertAdjacentHTML("afterend", `<p class="help" style="color:var(--amber);margin:4px 2px 0">ModHub couldn't tell which Minecraft version this is for. Pick it from the list.</p>`);
    } catch (e) {
      row.innerHTML = `<div class="body"><div class="t">${esc(file.name)}</div><div class="s" style="color:var(--missing)">${esc(e.message)}</div></div>`;
    }
  }
  renderInventory(); renderStarter();
  if (lastRun && target) toast("Added. Choose Install again to use it");
}
$("#fileInput").onchange = e => { uploadFiles([...e.target.files]); e.target.value = ""; };
const dropEl = $("#drop");
["dragenter", "dragover"].forEach(ev => dropEl.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); dropEl.classList.add("over"); }));
["dragleave", "drop"].forEach(ev => dropEl.addEventListener(ev, e => { e.preventDefault(); dropEl.classList.remove("over"); }));
dropEl.addEventListener("drop", e => { e.stopPropagation(); uploadFiles([...e.dataTransfer.files]); });
// drop anywhere in ModHub
let dragDepth = 0;
const hasFiles = e => [...(e.dataTransfer?.types || [])].includes("Files");
document.addEventListener("dragenter", e => { if (!hasFiles(e)) return; e.preventDefault(); dragDepth++; if ($("#filesModal").classList.contains("hidden")) $("#dropCover").classList.remove("hidden"); });
document.addEventListener("dragover", e => { if (hasFiles(e)) e.preventDefault(); });
document.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) $("#dropCover").classList.add("hidden"); });
document.addEventListener("drop", e => {
  if (!hasFiles(e)) return;
  e.preventDefault(); dragDepth = 0; $("#dropCover").classList.add("hidden");
  if ($("#filesModal").classList.contains("hidden")) openFiles();
  uploadFiles([...e.dataTransfer.files]);
});

function openItem(id) {
  const it = S.favorites.find(f => f.source === "local" && f.id === id);
  if (!it) return;
  const files = it.files || [];
  $("#itemBody").innerHTML = `
    <div class="row" style="align-items:center;gap:14px">${ico(it)}<div><h2 id="itemTitle" style="margin:0">${esc(it.name)}</h2>
      <p class="help" style="margin:2px 0 0">${KIND_LABEL[it.kind] || "Mod"} you added yourself${safeUrl(it.url) ? `. <a href="${esc(it.url)}" target="_blank" rel="noopener">Open its page</a>` : ""}</p></div></div>
    <p class="lede" style="margin-top:16px">${files.length ? "ModHub installs the file that matches the Minecraft version you pick. Add one file per version you play." : "This came from CurseForge, so ModHub needs its file. Download it from CurseForge and add it here."}</p>
    <div id="itemFiles">${files.map(f => `
      <div class="frow"><div class="body"><div class="t">${esc(f.file)}</div><div class="s">Added ${esc((f.added || "").slice(0, 10))}</div></div>
        <select data-ver="${esc(f.file)}" class="${f.version === "unknown" ? "unset" : ""}">${versionOptions(f.version)}</select>
        <button class="btn sm quiet" data-rmf="${esc(f.file)}">Remove</button></div>`).join("")}</div>
    <div class="foot"><button class="btn" id="itemAdd">Add a file</button><button class="btn go" data-close>Done</button></div>`;
  openModal("#itemModal");
  $$("#itemFiles [data-ver]").forEach(sel => sel.onchange = async () => {
    sel.classList.toggle("unset", sel.value === "unknown");
    S.favorites = (await api("/api/local/version", {id, file: sel.dataset.ver, version: sel.value})).favorites;
    toast("Saved");
  });
  $$("#itemFiles [data-rmf]").forEach(b => b.onclick = async () => {
    S.favorites = (await api("/api/local/remove_file", {id, file: b.dataset.rmf})).favorites;
    renderInventory(); openItem(id);
  });
  $("#itemAdd").onclick = () => { closeModals(); openFiles({id, name: it.name, url: it.url, version: null}); };
}

/* ---------- jobs ---------- */
async function follow(id, onUpdate) {
  let since = 0;
  for (;;) {
    const v = await api("/api/job", {id, since});
    since = v.next;
    if (onUpdate) onUpdate(v);
    if (v.done) { if (v.error) throw new Error(v.error); return v.result; }
    await new Promise(r => setTimeout(r, 400));
  }
}

/* ---------- install ---------- */
let showAllLaunchers = false;
function getVersion() { return $("#verSel").value === "__other" || !$("#verSel").options.length ? $("#verOther").value.trim() : $("#verSel").value; }
function renderVersions(selected) {
  const snaps = $("#snap").checked;
  const list = (S.versions || []).filter(v => snaps || v.type === "release").slice(0, 60).map(v => v.v);
  const want = selected || getVersion() || (S.last || {}).version || list[0] || "";
  const sel = $("#verSel");
  if (!list.length) { sel.classList.add("hidden"); $("#verOther").classList.remove("hidden"); $("#verOther").value = want; return; }
  sel.classList.remove("hidden");
  const opts = list.map((v, i) => `<option value="${esc(v)}">${esc(v)}${v === S.new_version ? " (new!)" : i === 0 && !snaps ? " (newest)" : ""}</option>`);
  sel.innerHTML = opts.join("") + `<option value="__other">Other version...</option>`;
  if (want && list.includes(want)) { sel.value = want; $("#verOther").classList.add("hidden"); }
  else if (want) { sel.value = "__other"; $("#verOther").classList.remove("hidden"); $("#verOther").value = want; }
}
$("#verSel").onchange = () => {
  const other = $("#verSel").value === "__other";
  $("#verOther").classList.toggle("hidden", !other);
  if (other) $("#verOther").focus();
  updateSteps();
};
$("#verOther").addEventListener("input", updateSteps);
$("#snap").onchange = () => renderVersions();

function setLoader(l) {
  loader = l;
  $$("#loaderSeg button").forEach(b => { b.classList.toggle("on", b.dataset.loader === l); b.setAttribute("aria-checked", b.dataset.loader === l); });
  $("#loaderName").textContent = LOADER_NAMES[l];
  if (typeof settle === "function") settle();
}
$$("#loaderSeg button").forEach(b => b.onclick = () => { setLoader(b.dataset.loader); updateSteps(); });
$("#changeLoader").onclick = () => { $("#more").open = true; $("#loaderSeg button.on").focus(); };

function renderLaunchers() {
  const found = S.launchers.filter(l => l.found);
  let shown = S.launchers;
  if (!showAllLaunchers && found.length) {
    shown = S.launchers.filter(l => l.found || l.id === "folder" || l.id === launcher);
  }
  $("#moreLaunchers").classList.toggle("hidden", shown.length === S.launchers.length);
  $("#launchers").innerHTML = shown.map(l => `
    <button class="lopt ${l.id === launcher ? "on" : ""}" data-l="${l.id}" role="radio" aria-checked="${l.id === launcher}">
      <span class="radio"></span>
      <span><span class="t">${esc(l.name)}${l.found ? `<span class="tag-found">On this computer</span>` : ""}</span>
      <span class="d" style="display:block">${esc(l.desc)}</span></span>
    </button>`).join("");
  $$(".lopt").forEach(c => c.onclick = () => { launcher = c.dataset.l; renderLaunchers(); updateSteps(); });
}
$("#moreLaunchers").onclick = () => { showAllLaunchers = true; renderLaunchers(); };

function updateSteps() {
  const gv = getVersion();
  const l = S.launchers.find(x => x.id === launcher);
  const lo = (S.loadouts || []).find(l => l.id === S.active_loadout);
  $("#iname").placeholder = (lo && lo.name !== "My mods" ? lo.name : "ModHub") + " " + (gv || "");
  const what = S.favorites.length ? `Install ${countText(S.favorites).replace("resource pack", "pack")}` : "Install mods";
  $("#installBtn").textContent = l ? `${what} to ${l.id === "folder" ? "a folder" : l.name}` : what;
  $("#folderRow").classList.toggle("hidden", !(l && l.folder));
  if (carryLoaded) $("#carryBlock").classList.toggle("hidden", launcher === "lunar" || !$("#carryFrom").options.length);
  if (l && l.folder) {
    const saved = (S.last.folders || {})[launcher];
    if (saved && !$("#folder").value) $("#folder").value = saved;
    $("#folderHelp").textContent = launcher === "lunar"
      ? "Choose Lunar's Fabric mods folder. In Lunar it's under Settings, then Mods. Lunar runs Fabric mods only."
      : "Choose the mods folder of the instance you want to fill. Click Browse to pick it.";
  }
}
$("#folder").addEventListener("input", updateSteps);

function resultRow(i, gv, extra = "") {
  const stateTxt = {ready: ["ready", i.ported ? "Your port" : "Ready"], not_ready: ["missing", "Not out yet"], manual: ["attn", "Download by hand"],
                    needs_file: ["attn", `Needs a file for ${gv}`], failed: ["missing", "Download failed"], duplicate: ["skip", "Skipped"]}[i.status] || ["skip", i.status];
  const sub = [i.dep_of.length ? "Needed by " + i.dep_of.join(", ") : "", i.notes.join(". ")].filter(Boolean).join(". ");
  return `<div class="li">${ico(i)}
    <div class="body"><div class="t">${link(i, esc(i.name))}</div>${sub ? `<div class="s">${esc(sub)}</div>` : ""}</div>
    ${i.version && i.status !== "not_ready" ? `<span class="v">${esc(i.version)}</span>` : ""}
    <span class="state ${stateTxt[0]}">${stateTxt[1]}</span>${extra}</div>`;
}
function countText(items) {
  const n = k => items.filter(i => (i.kind || "mod") === k).length;
  const m = n("mod"), r = n("resourcepack"), sh = n("shader");
  const parts = [];
  if (m || (!r && !sh)) parts.push(`${m} ${m === 1 ? "mod" : "mods"}`);
  if (r) parts.push(`${r} resource ${r === 1 ? "pack" : "packs"}`);
  if (sh) parts.push(`${sh} ${sh === 1 ? "shader" : "shaders"}`);
  return parts.length > 2 ? parts.slice(0, -1).join(", ") + " and " + parts[parts.length - 1] : parts.join(" and ");
}
function renderOutcome(res, gv, kind, l) {
  const by = s => res.items.filter(i => i.status === s);
  const ready = by("ready"), missing = by("not_ready"), attn = [...by("needs_file"), ...by("failed")], skipped = by("duplicate");
  let h = "";
  if (kind === "install") {
    h += `<div class="banner"><div class="grow"><b>Installed ${countText(ready)} for Minecraft ${esc(gv)}</b><p>${esc(res.message)}${res.brought && res.brought.length ? ` Brought along: ${esc(res.brought.join(", "))}.` : ""}</p></div>
      ${res.open ? `<button class="btn sm" id="openBtn">Show in folder</button>` : ""}</div>`;
  } else {
    h += `<div class="banner ${ready.length ? "" : "warn"}"><div class="grow"><b>${ready.length} of ${res.items.length} ready for Minecraft ${esc(gv)}</b><p>Nothing was installed. Pick a launcher and choose Install when you're happy.</p></div></div>`;
  }
  if (kind === "install" && ready.some(i => i.kind === "shader")) {
    h += `<p class="help" style="margin-top:12px">To use your shaders: start the game, then Options, Video Settings, Shader Packs.</p>`;
  }
  if (missing.length) {
    h += `<div class="group"><div class="group-h"><h3>Not out for ${esc(gv)} yet</h3><span class="count">${missing.length}</span></div>
      <p class="lede" style="font-size:14px;margin:-4px 0 12px">${kind === "install" ? "ModHub keeps an eye on these and tells you when they come out, so you can add them with one click." : "Choose Install again later to pick up updates."} Or have Claude port a mod for you now.</p>
      <div class="list">${missing.map(i => resultRow(i, gv, i.kind === "mod" && i.source === "modrinth" ? ` <button class="btn sm" data-port="${esc(i.key)}">Port with Claude</button>` : "")).join("")}</div></div>`;
  }
  if (attn.length) {
    h += `<div class="group"><div class="group-h"><h3>Needs you</h3><span class="count">${attn.length}</span></div>
      <div class="list">${attn.map(i => resultRow(i, gv, i.status === "needs_file" ? `${safeUrl(i.url) ? ` <a class="btn sm quiet" href="${esc(i.url)}" target="_blank" rel="noopener">Open page</a>` : ""} <button class="btn sm go" data-addfile="${esc(i.id)}">Add file</button>` : "")).join("")}</div></div>`;
  }
  if (ready.length) {
    h += `<div class="group"><div class="group-h"><h3>${kind === "install" ? "Installed" : "Ready"}</h3><span class="count">${ready.length}</span></div>
      <div class="list"><div class="chips">${ready.map(i => `<span class="chip ${i.ported ? "port" : ""}" title="${esc(i.version)}${i.dep_of.length ? " (needed by " + esc(i.dep_of.join(", ")) + ")" : ""}">${ico(i)}${esc(i.name)}</span>`).join("")}</div></div></div>`;
  }
  if (skipped.length) {
    h += `<p class="help" style="margin-top:14px">Skipped ${skipped.map(i => esc(i.name)).join(", ")}: the same mod was already in the list.</p>`;
  }
  $("#outcome").innerHTML = h;
  stagger($("#outcome"), ".banner, .group, .help");
  if (res.open) $("#openBtn").onclick = () => api("/api/open", {path: res.open}).catch(e => toast(e.message));
  $$("[data-addfile]").forEach(b => b.onclick = () => {
    const it = res.items.find(i => String(i.id) === b.dataset.addfile);
    openFiles({id: it.id, name: it.name, url: it.url, version: gv});
  });
  $$("[data-port]").forEach(b => b.onclick = () => {
    const it = res.items.find(i => i.key === b.dataset.port);
    openPort(it, gv, loader);
  });
}

async function runJob(kind) {
  const gv = getVersion();
  const l = S.launchers.find(x => x.id === launcher);
  if (!gv) { $("#outcome").innerHTML = `<div class="banner err"><div class="grow"><b>Choose a Minecraft version first</b><p>Pick one from the list at the top.</p></div></div>`; return; }
  if (kind === "install" && !l) { $("#outcome").innerHTML = `<div class="banner err"><div class="grow"><b>Choose where your mods should go</b><p>Pick a launcher above.</p></div></div>`; return; }
  if (kind === "install" && l.folder && !$("#folder").value.trim()) { $("#outcome").innerHTML = `<div class="banner err"><div class="grow"><b>Choose the mods folder</b><p>Click Browse next to Mods folder.</p></div></div>`; return; }
  const body = {version: gv, loader, launcher, name: $("#iname").value.trim() || $("#iname").placeholder, folder: $("#folder").value.trim(),
                settings_from: $("#carryOn").checked && !$("#carryBlock").classList.contains("hidden") && launcher !== "lunar" ? $("#carryFrom").value : ""};
  $("#checkBtn").disabled = $("#installBtn").disabled = true;
  $("#progress").classList.remove("hidden"); $("#log").textContent = ""; $("#barFill").style.width = "0"; $("#outcome").innerHTML = "";
  $("#now").textContent = kind === "install" ? "Starting" : "Checking your mods";
  liveReset(kind === "install" ? `Installing for Minecraft ${gv}` : `Checking Minecraft ${gv}`);
  try {
    const {job} = await api(kind === "install" ? "/api/install" : "/api/check", body);
    const res = await follow(job, v => {
      if (v.lines.length) {
        $("#log").textContent += v.lines.join("\n") + "\n";
        const now = $("#now"); now.classList.add("swap");
        setTimeout(() => { now.textContent = v.lines[v.lines.length - 1].trim(); now.classList.remove("swap"); }, 90);
        liveLines(v.lines);
      }
      $("#barFill").style.width = (v.progress * 100) + "%";
      liveProgress(v.progress);
    });
    await liveDone();
    $("#progress").classList.add("hidden");
    lastRun = {res, gv, kind};
    if (kind === "install") { refreshVersions(); api("/api/state").then(r => { S = r; renderInstances(); renderCatchUp(); renderLoadouts(); }).catch(() => {}); }
    renderOutcome(res, gv, kind, l);
    if (kind === "install") {
      const shown = showProblems(res.problems, {instanceId: res.install_id, export: res.export, name: body.name});
      if (!shown || !res.problems.some(p => p.status === "open")) burst($("#installBtn"));
    }
  } catch (e) {
    $("#progress").classList.add("hidden");
    $("#outcome").innerHTML = `<div class="banner err"><div class="grow"><b>${kind === "install" ? "Install didn't finish" : "Check didn't finish"}</b><p>${esc(e.message)}</p></div></div>`;
  }
  $("#checkBtn").disabled = $("#installBtn").disabled = false;
}
$("#checkBtn").onclick = () => runJob("check");
$("#installBtn").onclick = () => runJob("install");

/* ---------- porting ---------- */
async function openPort(item, gv, ldr) {
  const body = $("#portBody");
  body.innerHTML = `<h2>Port ${esc(item.name)} to ${esc(gv)}</h2><p class="now"><span class="spin"></span>&nbsp; Looking up its source code</p>`;
  openModal("#portModal");
  let info;
  try { info = await api("/api/port/info", {key: item.key, version: gv, loader: ldr}); }
  catch (e) { body.innerHTML = `<h2>Port ${esc(item.name)}</h2><div class="banner err"><div class="grow"><b>Couldn't look this mod up</b><p>${esc(e.message)}</p></div></div><div class="foot"><button class="btn" data-close>Close</button></div>`; return; }
  const t = info.tools;
  const canStart = info.repo && t.git && t.claude;
  const req = (ok, label, fix) => `<div class="req"><span class="${ok ? "y" : "x"}">${ok ? "✓" : "✕"}</span><span>${label}${ok ? "" : ` &nbsp;<a href="${fix}" target="_blank" rel="noopener">Get it</a>`}</span></div>`;
  body.innerHTML = `
    <h2>Port ${esc(info.name)} to ${esc(gv)}</h2>
    <p class="lede">Claude downloads the mod's source code, updates it for Minecraft ${esc(gv)} (${LOADER_NAMES[ldr]}), and builds it. You'll follow along in a terminal window and approve its steps.</p>
    <dl class="facts">
      <dt>Source code</dt><dd>${info.repo ? `<a href="${esc(info.repo)}" target="_blank" rel="noopener">${esc(info.repo.replace("https://", ""))}</a>` : `<span style="color:var(--missing)">Not public, so it can't be ported</span>`}</dd>
      <dt>License</dt><dd>${esc(info.license)}</dd>
      <dt>Supports up to</dt><dd>Minecraft ${esc(info.latest || "unknown")}</dd>
    </dl>
    ${info.all_rights_reserved ? `<div class="banner warn" style="margin:0 0 14px"><div class="grow"><b>All rights reserved</b><p>The author keeps every right to this mod. Use your port only on your own computer, and never share it.</p></div></div>` : ""}
    <div class="reqs">
      ${req(t.claude, "Claude Code", "https://claude.com/claude-code")}
      ${req(t.git, "Git", "https://git-scm.com/downloads")}
      ${req(t.java, "Java (Claude will tell you if the build needs a newer version)", "https://adoptium.net/")}
    </div>
    <p class="help">Small updates usually take a few minutes. Mods built on parts of the game that changed a lot can take much longer, and some can't be ported. Ports are for your own use only.</p>
    <div id="portOut"></div>
    <details class="notes" style="margin-top:14px"><summary>Already have an updated jar? Add it instead</summary>
      <div class="picker" style="margin-top:10px"><input id="jarPath" placeholder="Choose the .jar file"><button class="btn" data-browse="#jarPath" data-kind="file" data-title="Choose the updated mod jar">Browse</button><button class="btn go" id="addJar">Add</button></div>
    </details>
    <div class="foot">
      <button class="btn quiet" data-close>Cancel</button>
      <button class="btn go" id="portGo" ${canStart ? "" : "disabled"}>Start port</button>
    </div>`;
  $("#addJar").onclick = async () => {
    try {
      await api("/api/port/add_jar", {key: item.key, version: gv, loader: ldr, path: $("#jarPath").value, name: info.name, icon: info.icon, url: info.url});
      closeModals(); toast(`Added your jar for ${info.name}. Choose Install to use it.`); refreshPortCount();
    } catch (e) { $("#portOut").innerHTML = `<div class="banner err"><div class="grow"><p>${esc(e.message)}</p></div></div>`; }
  };
  $("#portGo").onclick = async () => {
    const b = $("#portGo"); b.disabled = true; b.innerHTML = `<span class="spin"></span> Downloading source`;
    try {
      const {job} = await api("/api/port/start", {key: item.key, version: gv, loader: ldr});
      const r = await follow(job);
      if (r.launched) { closeModals(); toast("Claude Code is open in a new terminal window"); go("ports"); }
      else {
        $("#portOut").innerHTML = `<div class="banner warn"><div class="grow"><b>Open a terminal and run this</b><p>ModHub couldn't open a terminal window on its own.</p>
          <div class="cmd"><code>${esc(r.command)}</code><button class="btn sm" id="copyCmd">Copy</button></div></div></div>`;
        $("#copyCmd").onclick = () => navigator.clipboard.writeText(r.command).then(() => toast("Copied"));
        b.textContent = "Started"; refreshPortCount();
      }
    } catch (e) {
      $("#portOut").innerHTML = `<div class="banner err"><div class="grow"><b>Couldn't start the port</b><p>${esc(e.message)}</p></div></div>`;
      b.disabled = false; b.textContent = "Start port";
    }
  };
}

async function refreshPortCount() {
  try { portsData = await api("/api/ports"); } catch (e) { return; }
  const active = portsData.ports.length;
  $("#navPorts").textContent = active || "";
}
async function loadPorts() {
  await refreshPortCount();
  if (!portsData) return;
  const t = portsData.tools;
  const missing = [!t.claude && `<a href="https://claude.com/claude-code" target="_blank" rel="noopener">Claude Code</a>`, !t.git && `<a href="https://git-scm.com/downloads" target="_blank" rel="noopener">Git</a>`].filter(Boolean);
  $("#toolsWarn").innerHTML = missing.length ? `<div class="banner warn" style="margin:0 0 18px"><div class="grow"><b>Porting needs ${missing.length > 1 ? "two programs" : "one program"}</b><p>Install ${missing.join(" and ")}, then restart ModHub.</p></div></div>` : "";
  if (!portsData.ports.length) {
    $("#ports").innerHTML = `<div class="empty">${emptyArt("anvil")}<h3>No ports yet</h3><p>When a mod isn't out for your version, choose <b>Port with Claude</b> in the Install results.</p></div>`;
    return;
  }
  const openNotes = new Set($$("details.notes[open]").map(d => d.dataset.id));
  $("#ports").innerHTML = portsData.ports.map(p => {
    const st = {working: ["working", `<span class="pulse"></span>Claude is working on it`], built: ["built", "Ready. Added on your next install"], missing: ["missing", "Folder was deleted"]}[p.status];
    return `<div class="port">
      <div class="port-top">${ico(p)}
        <div class="body"><div class="t">${link(p, esc(p.name))}</div><div class="s">For Minecraft ${esc(p.version)} with ${LOADER_NAMES[p.loader] || esc(p.loader)}</div></div>
        <span class="status ${st[0]}">${st[1]}</span>
      </div>
      ${p.notes ? `<details class="notes" data-id="${esc(p.id)}" ${openNotes.has(p.id) ? "open" : ""}><summary>Claude's notes</summary><pre>${esc(p.notes.replace(/^#+\s*/gm, ""))}</pre></details>` : ""}
      <div class="actions">
        ${p.repo && p.status !== "missing" ? `<button class="btn sm" data-relaunch="${esc(p.id)}">${p.status === "built" ? "Keep working with Claude" : "Reopen Claude"}</button>` : ""}
        ${p.status !== "missing" ? `<button class="btn sm quiet" data-openp="${esc(p.dir)}">Show folder</button>` : ""}
        <button class="btn sm quiet" data-rmport="${esc(p.id)}">Delete port</button>
      </div></div>`;
  }).join("");
  $$("[data-relaunch]").forEach(b => b.onclick = async () => {
    try { const r = await api("/api/port/relaunch", {id: b.dataset.relaunch}); toast(r.launched ? "Opened Claude Code" : "Run: " + r.command); } catch (e) { toast(e.message); }
  });
  $$("[data-openp]").forEach(b => b.onclick = () => api("/api/open", {path: b.dataset.openp}).catch(e => toast(e.message)));
  $$("[data-rmport]").forEach(b => b.onclick = async () => {
    if (!confirm("Delete this port and its folder?")) return;
    portsData = await api("/api/port/remove", {id: b.dataset.rmport}); loadPorts();
  });
}

/* ---------- own window (pywebview) ---------- */
let nativeState = "idle"; // idle | working | ready | failed
let appSwitchPoll = null;
function watchAppSwitch() {
  const sw = S.app_switch;
  if (!sw || !sw.available || sw.status === "error" || sw.gave_up || appSwitchPoll) return;
  appSwitchPoll = setInterval(async () => {
    try { S.app_switch = await api("/api/app_switch"); } catch (e) { return; }
    const st = S.app_switch.status;
    if (st === "switching") {
      clearInterval(appSwitchPoll);
      const cover = document.createElement("div"); cover.className = "switch-cover";
      cover.innerHTML = `<div><div class="mark"><i></i><i></i><i></i><i></i></div><h1>Switching to the ModHub app</h1><p class="lede">ModHub is reopening as its own app, with its own window. You can close this one.</p></div>`;
      document.body.appendChild(cover);
      setTimeout(() => window.close(), 2500);
      return;
    }
    if (st === "error") { clearInterval(appSwitchPoll); appSwitchPoll = null; }
    renderWindowBits();
  }, 2000);
}
function renderWindowBits() {
  // Only shown when something needs you: a window that didn't open, or the switch to the app.
  const sw = S.app_switch;
  if (S.frozen && !S.native && !S.webview_installed) {  // the Linux app opens in a Chrome or browser window; there's nothing to set up
    $("#nativeBanner").classList.add("hidden"); $("#appCard").classList.add("hidden"); return;
  }
  $("#appCard").classList.toggle("hidden", !!S.native);
  if (sw && sw.available && !S.native) {
    $("#nativeBanner").classList.add("hidden");
    const failed = sw.status === "error" || sw.gave_up;
    $("#windowMode").innerHTML = failed
      ? `Couldn't set up the ModHub app${sw.message ? `: ${esc(sw.message)}` : ""}. ModHub keeps using an Edge or Chrome window for now.`
      : sw.status === "ready"
        ? "The ModHub app is ready. ModHub reopens as the app as soon as your install finishes."
        : `<span class="spin"></span>&nbsp; ModHub is setting itself up as an app, with its own window. It reopens by itself in a moment.`;
    $("#windowActions").innerHTML = failed ? `<button class="btn" id="appSwitchRetry">Try again</button>` : "";
    if (failed) $("#appSwitchRetry").onclick = async e => {
      e.target.disabled = true; e.target.textContent = "Setting up...";
      try { S.app_switch = await api("/api/app_switch", {start: true}); } catch (err) { toast(err.message); }
      appSwitchPoll = null; renderWindowBits(); watchAppSwitch();
    };
    watchAppSwitch();
    return;
  }
  if (S.native_broken && !S.native) {
    $("#nativeBanner").classList.toggle("hidden", !!S.native_prompt_dismissed);
    $("#nativeBanner b").textContent = "ModHub's own window didn't open";
    $("#nativeText").textContent = `So ModHub is using an Edge or Chrome window instead (${S.native_broken.reason}). Everything else works as normal.`;
    $$("[data-native-setup]").forEach(b => { b.textContent = "Try again"; b.dataset.mode = "retry"; b.disabled = false; });
    $("#windowMode").textContent = `ModHub's own window didn't open last time (${S.native_broken.reason}), so it's using an Edge or Chrome window.`;
    $("#windowActions").innerHTML = `<div class="actions"><button class="btn" data-native-setup data-mode="retry">Try again</button><button class="btn quiet" id="showLog">Show details</button></div><pre class="hidden" id="logBox" style="white-space:pre-wrap;background:var(--deep);padding:12px 14px;border-radius:8px;font:12px/1.5 ui-monospace,Consolas,monospace;color:var(--muted);max-height:260px;overflow:auto;margin-top:10px"></pre>`;
    $("#showLog").onclick = async () => { const r = await api("/api/log"); $("#logBox").textContent = r.log || "No details were saved."; $("#logBox").classList.toggle("hidden"); };
    if (!$("#nativeBanner").classList.contains("hidden")) $("#shortcutBanner").classList.add("hidden");
    return;
  }
  const canAsk = !S.native && !S.native_prompt_dismissed && S.favorites.length;
  const ready = S.webview_installed || nativeState === "ready";
  $("#nativeBanner").classList.toggle("hidden", !(canAsk || nativeState !== "idle") || S.native);
  if (!$("#nativeBanner").classList.contains("hidden")) $("#shortcutBanner").classList.add("hidden");
  if (ready && !S.native) {
    $("#nativeText").textContent = "Setup is done. Restart ModHub to open it in its own window.";
    $$("[data-native-setup]").forEach(b => { b.textContent = "Restart ModHub"; b.dataset.mode = "restart"; b.disabled = false; });
  }
  $("#windowMode").textContent = S.native
    ? "ModHub is running in its own window. No browser is involved."
    : ready ? "Setup is done. Restart ModHub to switch to its own window."
            : "ModHub is borrowing a window from Edge or Chrome. Set up its own window to stop using the browser.";
  $("#windowActions").innerHTML = S.native ? "" :
    `<button class="btn" data-native-setup ${ready ? 'data-mode="restart"' : ""}>${ready ? "Restart ModHub" : "Set up its own window"}</button><div id="nativeOut"></div>`;
}
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-native-setup]"); if (!b) return;
  if (b.dataset.mode === "retry") {
    $$("[data-native-setup]").forEach(x => { x.disabled = true; x.textContent = "Restarting..."; });
    await api("/api/window/retry").catch(() => {});
    document.body.innerHTML = `<main style="padding:60px"><h1>Restarting ModHub</h1><p class="lede">It will reopen in a moment. You can close this window.</p></main>`;
    setTimeout(() => window.close(), 1500);
    return;
  }
  if (b.dataset.mode === "restart") {
    $$("[data-native-setup]").forEach(x => { x.disabled = true; x.textContent = "Restarting..."; });
    await api("/api/window/restart").catch(() => {});
    document.body.innerHTML = `<main style="padding:60px"><h1>Restarting ModHub</h1><p class="lede">It will open in its own window in a moment. You can close this one.</p></main>`;
    setTimeout(() => window.close(), 1500);
    return;
  }
  nativeState = "working";
  $$("[data-native-setup]").forEach(x => { x.disabled = true; x.innerHTML = `<span class="spin"></span> Setting up`; });
  const out = $("#nativeOut");
  try {
    const {job} = await api("/api/window/setup");
    await follow(job, v => { if (v.lines.length) toast(v.lines[v.lines.length - 1]); });
    nativeState = "ready";
    S.webview_installed = true;
    renderWindowBits();
    toast("Setup done. Restart ModHub to switch");
  } catch (err) {
    nativeState = "failed";
    $$("[data-native-setup]").forEach(x => { x.disabled = false; x.textContent = "Try again"; });
    $("#nativeText").textContent = "Setup didn't work, so ModHub keeps using an Edge or Chrome window. Everything else works as normal.";
    if (out) out.innerHTML = `<div class="banner err"><div class="grow"><b>Setup didn't finish</b><p style="white-space:pre-wrap">${esc(err.message)}</p></div></div>`;
    else toast("Setup didn't finish. See Settings for details");
  }
});
$("#nativeLater").onclick = () => { S.native_prompt_dismissed = true; renderWindowBits(); renderAppBits(); api("/api/window/dismiss").catch(() => {}); };

/* ---------- updates ---------- */
function renderUpdateBits() {
  const u = S.update;
  $("#verLabel").textContent = "ModHub " + S.version;
  $("#updPill").classList.toggle("hidden", !u);
  $("#updApply").classList.toggle("hidden", !u);
  $("#updUndo").classList.toggle("hidden", !S.has_backup);
  const setNav = $(".nav[data-tab=settings]");
  let dot = setNav.querySelector(".dot-new");
  if (u && !dot) setNav.insertAdjacentHTML("beforeend", `<span class="dot-new" title="Update ready"></span>`);
  if (!u && dot) dot.remove();
  if (u) {
    $("#updVer").textContent = u.version;
    $("#updText").textContent = `ModHub ${u.version} is ready to install. It was found in your ${u.where} folder. You're on ${S.version}.`;
    $("#updApply").textContent = `Update to ${u.version}`;
  } else {
    $("#updText").textContent = `You're on ModHub ${S.version}. New versions come straight from GitHub, with nothing to download.`;
  }
  const peek = $("#updPeek");
  peek.classList.toggle("hidden", !(u && u.changes && u.changes.length));
  if (u) peek.textContent = `See what's new in ${u.version}`;
  if (u && u.where === "online") $("#updText").textContent = `ModHub ${u.version} has been downloaded. ${S.update_auto ? "It installs by itself next time you open ModHub, or" : "You can"} update now.`;
  $("#updAuto").checked = S.update_auto !== false;
  const lc = S.update_last_check;
  $("#updSourceStatus").innerHTML = !lc ? "ModHub checks for updates every 30 minutes."
    : lc.status === "error" ? `<span style="color:var(--missing)">Last check didn't work: ${esc(lc.message)}.</span>`
    : lc.status === "downloaded" ? `<span class="ok">Downloaded ModHub ${esc(lc.version)}.</span>`
    : `<span class="ok">Up to date.</span> Checked ${esc(timeAgo(lc.at))}. ModHub checks every 30 minutes.`;
}
function timeAgo(iso) {
  const d = (Date.now() - Date.parse(iso)) / 1000;
  if (!(d >= 0)) return "just now";
  if (d < 90) return "just now";
  if (d < 3600) return Math.round(d / 60) + " minutes ago";
  if (d < 86400) return Math.round(d / 3600) + " hours ago";
  return Math.round(d / 86400) + " days ago";
}
$("#updAuto").onchange = async e => { Object.assign(S, await api("/api/update/auto", {on: e.target.checked})); renderUpdateBits(); };
async function applyUpdate(path, version) {
  if (!confirm(`Update ModHub to ${version}? It will close and reopen by itself. Your library and settings stay as they are.`)) return;
  try {
    const r = await api("/api/update/apply", {path});
    document.body.innerHTML = `<main style="padding:60px"><h1>Updating to ${esc(r.version)}</h1><p class="lede">ModHub will reopen in a moment. You can close this window.</p></main>`;
    setTimeout(() => window.close(), 1500);
  } catch (e) { toast(e.message); }
}
$("#updPill").onclick = () => S.update && applyUpdate(S.update.path, S.update.version);
$("#updApply").onclick = () => S.update && applyUpdate(S.update.path, S.update.version);
$("#updCheck").onclick = async () => {
  const b = $("#updCheck"); b.disabled = true; b.textContent = "Checking...";
  try {
    const r = await api("/api/update/check");
    S.update = r.update; if (r.update_last_check) S.update_last_check = r.update_last_check; renderUpdateBits();
    toast(r.update ? `ModHub ${r.update.version} is ready to install` : r.update_last_check && r.update_last_check.status === "error" ? "Couldn't reach GitHub. Check your internet" : "You're on the newest version");
  } catch (e) { toast(e.message); }
  b.disabled = false; b.textContent = "Check for updates";
};
$("#updFile").onclick = async () => {
  const path = await browse("py", "Choose the new modhub.py");
  if (path) applyUpdate(path, "the version in that file");
};
$("#updUndo").onclick = async () => {
  if (!confirm("Go back to the previous version of ModHub? It will close and reopen by itself.")) return;
  try {
    const r = await api("/api/update/undo");
    document.body.innerHTML = `<main style="padding:60px"><h1>Going back to ${esc(r.version)}</h1><p class="lede">ModHub will reopen in a moment. You can close this window.</p></main>`;
    setTimeout(() => window.close(), 1500);
  } catch (e) { toast(e.message); }
};

/* ---------- motion & polish ---------- */
const motionQuery = matchMedia("(prefers-reduced-motion: reduce)");
let REDUCED = motionQuery.matches || document.documentElement.dataset.motion === "off";
let LESS = REDUCED || document.documentElement.dataset.motion === "less";
const uiZoom = () => parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
const seenKeys = new WeakMap();
function stagger(container, sel, onlyNew = false) {
  if (!container || LESS) return;
  let seen = seenKeys.get(container);
  if (!seen) { seen = new Set(); seenKeys.set(container, seen); }
  let i = 0;
  container.querySelectorAll(sel).forEach(el => {
    const k = el.dataset.k;
    if (onlyNew && k && seen.has(k)) return;
    if (k) seen.add(k);
    el.style.setProperty("--i", Math.min(i++, 18));
    el.classList.add("rise");
  });
}
const navPill = document.createElement("div");
navPill.id = "navPill";
$(".side").appendChild(navPill);
function moveNavPill() {
  const on = $(".nav.on");
  if (!on) return;
  Object.assign(navPill.style, {top: on.offsetTop + "px", height: on.offsetHeight + "px", left: on.offsetLeft + "px", width: on.offsetWidth + "px"});
}
function moveSegPills() {
  $$(".seg").forEach(seg => {
    if (!seg.offsetParent) return;  // hidden right now
    let pill = seg.querySelector(".segpill");
    if (!pill) { pill = document.createElement("span"); pill.className = "segpill"; seg.prepend(pill); seg.classList.add("pilled"); }
    const on = seg.querySelector("button.on");
    pill.style.opacity = on ? 1 : 0;
    if (on) Object.assign(pill.style, {left: on.offsetLeft + "px", width: on.offsetWidth + "px"});
  });
}
const settle = () => requestAnimationFrame(() => { moveNavPill(); moveSegPills(); });
window.addEventListener("resize", settle);
document.addEventListener("click", e => { if (e.target.closest(".seg button, .nav")) settle(); });

// cards light up under the mouse; mod slots tilt
let tilted = null;
document.addEventListener("pointermove", e => {
  const card = e.target.closest(".lopt,.res,.folder,.frow,.port,.li,.newver");
  if (card && !LESS) {
    const r = card.getBoundingClientRect(), z = uiZoom();
    card.style.setProperty("--mx", (e.clientX - r.left) / z + "px");
    card.style.setProperty("--my", (e.clientY - r.top) / z + "px");
  }
  if (LESS) { if (tilted) { tilted.style.transform = ""; tilted = null; } return; }
  const slot = e.target.closest(".cell:not(.ghost) .slot");
  if (tilted && tilted !== slot) { tilted.style.transform = ""; tilted = null; }
  if (slot) {
    const r = slot.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
    slot.style.transform = `translateY(-3px) rotateX(${(-y * 16).toFixed(1)}deg) rotateY(${(x * 16).toFixed(1)}deg)`;
    tilted = slot;
  }
}, {passive: true});
document.addEventListener("pointerleave", () => { if (tilted) { tilted.style.transform = ""; tilted = null; } });

// a burst of little blocks when an install finishes
function burst(fromEl) {
  if (LESS || !fromEl) return;
  const c = document.createElement("canvas");
  c.id = "burst"; c.width = innerWidth * devicePixelRatio; c.height = innerHeight * devicePixelRatio;
  document.body.appendChild(c);
  const ctx = c.getContext("2d"); ctx.scale(devicePixelRatio, devicePixelRatio);
  const r = fromEl.getBoundingClientRect(), ox = r.left + r.width / 2, oy = r.top + r.height / 2;
  const cv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const colors = [cv("--accent"), cv("--accent-2"), cv("--text"), "#45b97c", "#7a7780"];
  const parts = Array.from({length: 70}, () => {
    const a = -Math.PI / 2 + (Math.random() - .5) * 2.4, v = 5 + Math.random() * 8;
    return {x: ox, y: oy, vx: Math.cos(a) * v, vy: Math.sin(a) * v, s: 4 + Math.random() * 6, r: Math.random() * 6, vr: (Math.random() - .5) * .4, c: colors[Math.random() * colors.length | 0]};
  });
  const start = performance.now();
  (function frame(t) {
    const k = (t - start) / 1400;
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    parts.forEach(p => {
      p.vy += .32; p.vx *= .985; p.x += p.vx; p.y += p.vy; p.r += p.vr;
      ctx.save(); ctx.globalAlpha = Math.max(0, 1 - k * k); ctx.translate(p.x, p.y); ctx.rotate(p.r);
      ctx.fillStyle = p.c; ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s); ctx.restore();
    });
    if (k < 1) requestAnimationFrame(frame); else c.remove();
  })(start);
}

/* ---------- loadouts ---------- */
function renderLoadouts() {
  const los = S.loadouts || [];
  $("#loBar").innerHTML = los.map(l => `
    <span class="lochip ${l.id === S.active_loadout ? "on" : ""}" data-lo="${esc(l.id)}" role="button" tabindex="0" title="${l.id === S.active_loadout ? "Your current loadout" : "Switch to " + esc(l.name)}">
      ${esc(l.name)} <span class="c">${l.count}</span>
      <button class="ed" data-loedit="${esc(l.id)}" aria-label="Rename or delete ${esc(l.name)}"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M4 20h4L19 9l-4-4L4 16v4z"/></svg></button>
    </span>`).join("") + `<span class="lochip add" id="loNew" role="button" tabindex="0">+ New loadout</span>`;
  $$("#loBar [data-lo]").forEach(c => c.onclick = e => { if (!e.target.closest("[data-loedit]")) switchLoadout(c.dataset.lo); });
  $$("#loBar [data-loedit]").forEach(b => b.onclick = e => { e.stopPropagation(); openLoadout(b.dataset.loedit); });
  $("#loNew").onclick = () => openLoadout(null);
  const sel = $("#loSel");
  if (sel) {
    sel.innerHTML = los.map(l => `<option value="${esc(l.id)}" ${l.id === S.active_loadout ? "selected" : ""}>${esc(l.name)} (${l.count})</option>`).join("");
    $("#loHelp").textContent = los.length > 1 ? "Switch to install a different set." : "Make more loadouts in Library, like PvP or Building.";
  }
}
async function switchLoadout(id) {
  if (id === S.active_loadout) return;
  S = await api("/api/loadouts/switch", {id});
  lastResults = []; $("#results").innerHTML = "";
  renderAll(); renderVersions(getVersion()); updateSteps();
  const lo = S.loadouts.find(l => l.id === id);
  toast(`Switched to ${lo ? lo.name : "loadout"}`);
}
$("#loSel").onchange = e => switchLoadout(e.target.value);
function openLoadout(id) {
  const lo = id && S.loadouts.find(l => l.id === id);
  $("#loBody").innerHTML = lo ? `
    <h2 id="loTitle">Edit loadout</h2>
    <p class="lede">${lo.count} ${lo.count === 1 ? "item" : "items"} in it.</p>
    <div style="margin-top:16px"><label class="field-label" for="loName">Name</label><input id="loName" value="${esc(lo.name)}" maxlength="40"></div>
    <div class="foot" style="justify-content:space-between">
      <button class="btn quiet" id="loDel" ${S.loadouts.length < 2 ? "disabled title='You need at least one loadout'" : ""}>Delete loadout</button>
      <span class="actions"><button class="btn quiet" data-close>Cancel</button><button class="btn go" id="loSave">Save</button></span>
    </div>` : `
    <h2 id="loTitle">New loadout</h2>
    <p class="lede">A separate set of mods, resource packs and shaders, like Survival, PvP or Building.</p>
    <div style="margin-top:16px"><label class="field-label" for="loName">Name</label><input id="loName" placeholder="Survival" maxlength="40"></div>
    <div style="margin-top:14px;display:grid;gap:8px">
      <label class="check" style="margin:0"><input type="radio" name="loStart" value="empty" checked> Start empty</label>
      <label class="check" style="margin:0"><input type="radio" name="loStart" value="copy"> Start with a copy of ${esc((S.loadouts.find(l => l.id === S.active_loadout) || {}).name || "this loadout")}</label>
    </div>
    <div class="foot"><button class="btn quiet" data-close>Cancel</button><button class="btn go" id="loSave">Create loadout</button></div>`;
  openModal("#loModal");
  setTimeout(() => { $("#loName").focus(); $("#loName").select(); }, 30);
  const save = async () => {
    try {
      S = lo ? await api("/api/loadouts/rename", {id, name: $("#loName").value})
             : await api("/api/loadouts/create", {name: $("#loName").value, copy: $("input[name=loStart]:checked").value === "copy"});
      closeModals(); renderAll(); updateSteps();
      toast(lo ? "Renamed" : `Created ${$("#loName").value.trim()}`);
    } catch (e) { toast(e.message); }
  };
  $("#loSave").onclick = save;
  $("#loName").onkeydown = e => { if (e.key === "Enter") save(); };
  const del = $("#loDel");
  if (del) del.onclick = async () => {
    if (!confirm(`Delete the loadout "${lo.name}"? Your instances stay where they are.`)) return;
    try { S = await api("/api/loadouts/delete", {id}); closeModals(); renderAll(); updateSteps(); toast(`Deleted ${lo.name}`); }
    catch (e) { toast(e.message); }
  };
}

/* ---------- instances ---------- */
function renderInstances() {
  const list = [...(S.installs || [])].sort((a, b) => (b.updated || "").localeCompare(a.updated || ""));
  $("#navInst").textContent = list.length || "";
  $("#updAll").classList.toggle("hidden", !list.some(r => !r.export));
  if (!list.length) {
    $("#instList").innerHTML = `<div class="empty">${emptyArt("chest")}<h3>Nothing installed yet</h3><p>Instances you install from the Install page show up here, so you can update them later with one click.</p></div>`;
    return;
  }
  $("#instList").innerHTML = list.map(r => {
    const c = r.counts || {};
    const what = [c.mod && `${c.mod} ${c.mod === 1 ? "mod" : "mods"}`, c.resourcepack && `${c.resourcepack} ${c.resourcepack === 1 ? "pack" : "packs"}`, c.shader && `${c.shader} ${c.shader === 1 ? "shader" : "shaders"}`].filter(Boolean).join(", ");
    return `<div class="inst" data-inst="${esc(r.id)}">
      <div class="inst-top"><div class="inst-ico">${esc(r.version)}</div>
        <div class="body"><div class="t">${esc(r.name)}</div>
          <div class="s">Minecraft ${esc(r.version)} with ${LOADER_NAMES[r.loader] || esc(r.loader)}, ${r.export ? "built for" : "in"} ${r.launcher === "folder" ? "a folder" : esc(r.launcher_name)}</div>
          <div class="meta">${(S.crashes || []).some(c => c.install_id === r.id) ? `<span class="tag" style="color:var(--missing);background:rgba(255,90,95,.12)">Crashed</span>` : ""}<span class="tag lo">${esc(r.loadout_name || "My mods")}</span>${what ? `<span class="tag">${esc(what)}</span>` : ""}<span class="tag">Updated ${esc(timeAgo(r.updated))}</span></div>
        </div></div>
      <div class="actions">
        ${r.export ? `<button class="btn" data-iup="${esc(r.id)}">Build a fresh pack</button>` : `<button class="btn go" data-iup="${esc(r.id)}">Update</button>`}
        ${r.export ? "" : `<button class="btn" data-icheck="${esc(r.id)}">Check for problems</button>`}
        ${(r.last_changes || []).length ? `<button class="btn quiet" data-ichg="${esc(r.id)}">What changed</button>` : ""}
        ${r.open ? `<button class="btn quiet" data-iopen="${esc(r.open)}">Show folder</button>` : ""}
        <button class="btn quiet" data-irm="${esc(r.id)}">Remove from list</button>
      </div>
      <div class="res-line" data-iout></div>
    </div>`;
  }).join("");
  stagger($("#instList"), ".inst");
  $$("[data-iup]").forEach(b => b.onclick = () => updateInstance(b.dataset.iup, b));
  $$("[data-icheck]").forEach(b => b.onclick = () => checkInstance(b.dataset.icheck, b));
  $$("[data-ichg]").forEach(b => b.onclick = () => { const r = (S.installs || []).find(x => x.id === b.dataset.ichg); if (r) showChanges(r.last_changes, `What changed in ${r.name}` + (r.changes_at ? ` (${timeAgo(r.changes_at)})` : "")); });
  $$("[data-iopen]").forEach(b => b.onclick = () => api("/api/open", {path: b.dataset.iopen}).catch(e => toast(e.message)));
  $$("[data-irm]").forEach(b => b.onclick = async () => {
    if (!confirm("Remove this from the list? Its files stay where they are.")) return;
    S = await api("/api/instances/remove", {id: b.dataset.irm}); renderInstances();
  });
}
function changesText(ch) {
  const uniq = [...new Set(ch || [])];
  return uniq.length ? `<b>Updated ${uniq.length}:</b> ${uniq.slice(0, 8).map(esc).join(", ")}${uniq.length > 8 ? " and more" : ""}` : "Everything was already up to date.";
}
async function updateInstance(id, btn) {
  const card = btn.closest(".inst"), out = card.querySelector("[data-iout]");
  const label = btn.textContent;
  card.classList.add("busy"); btn.disabled = true; btn.innerHTML = `<span class="spin"></span> Updating`;
  try {
    const {job} = await api("/api/instances/update", {id});
    const res = await follow(job, v => { if (v.lines.length) out.textContent = v.lines[v.lines.length - 1].trim(); });
    out.innerHTML = changesText(res.changes);
    S = await api("/api/state"); renderInstances();
    const again = $(`.inst[data-inst="${CSS.escape(id)}"] [data-iout]`);
    if (again) {
      again.innerHTML = changesText(res.changes) + ((res.updates || []).length ? ` <button class="linkbtn" data-seechg>See what changed</button>` : "");
      const sc = again.querySelector("[data-seechg]"); if (sc) sc.onclick = () => showChanges(res.updates, `What changed in ${res.instance}`);
    }
    const rec = (S.installs || []).find(r => r.id === id) || {};
    showProblems(res.problems, {instanceId: id, export: rec.export, name: rec.name});
    if (res.changes.length) burst($(`.inst[data-inst="${CSS.escape(id)}"] [data-iup]`));
  } catch (e) {
    out.innerHTML = `<span style="color:var(--missing)">${esc(e.message)}</span>`;
    btn.disabled = false; btn.textContent = label;
  }
  card.classList.remove("busy");
}
$("#updAll").onclick = async () => {
  const b = $("#updAll"); b.disabled = true; b.innerHTML = `<span class="spin"></span> Updating`;
  $("#instAllOut").innerHTML = `<div class="progress"><div class="bar"><div id="allFill"></div></div><div class="now" id="allNow"></div></div>`;
  try {
    const {job} = await api("/api/instances/update_all");
    const res = await follow(job, v => { $("#allFill").style.width = (v.progress * 100) + "%"; if (v.lines.length) $("#allNow").textContent = v.lines[v.lines.length - 1].trim(); });
    const total = res.summary.reduce((n, x) => n + (x.changes || []).length, 0);
    $("#instAllOut").innerHTML = `<div class="banner" style="margin:0 0 18px"><div class="grow"><b>${total ? `Updated ${total} ${total === 1 ? "item" : "items"}` : "Everything was already up to date"}</b>
      <p>${res.summary.map(x => `${esc(x.name)}: ${x.error ? `<span style="color:var(--missing)">${esc(x.error)}</span>` : (x.changes.length ? esc([...new Set(x.changes)].join(", ")) : "up to date")}`).join("<br>")}</p></div></div>`;
    S = await api("/api/state"); renderInstances();
    const allUpdates = res.summary.flatMap(x => x.updates || []);
    if (allUpdates.length) {
      $("#instAllOut .banner").insertAdjacentHTML("beforeend", `<button class="btn sm" id="allChg">See what changed</button>`);
      $("#allChg").onclick = () => showChanges(allUpdates, "What changed");
    }
    const withProblems = res.summary.find(x => (x.problems || []).length);
    if (withProblems) showProblems(withProblems.problems, {instanceId: withProblems.install_id, name: withProblems.name});
    else if (total) burst(b);
  } catch (e) { $("#instAllOut").innerHTML = `<div class="banner err" style="margin:0 0 18px"><div class="grow"><b>Update didn't finish</b><p>${esc(e.message)}</p></div></div>`; }
  b.disabled = false; b.textContent = "Update all";
};

/* ---------- mods that caught up ---------- */
function renderCatchUp() {
  const list = S.caught_up || [];
  const navI = $(".nav[data-tab=instances]");
  let dot = navI.querySelector(".dot-new");
  if (list.length && !dot) { navI.insertAdjacentHTML("beforeend", `<span class="dot-new" title="A mod you were waiting for is out"></span>`); $("#navInst").style.display = "none"; }
  if (!list.length && dot) { dot.remove(); $("#navInst").style.display = ""; }
  $("#catchUp").innerHTML = list.map(c => {
    const has = (S.installs || []).some(r => r.version === c.version && !r.export);
    return `<div class="catch rise" data-ck="${esc(c.key)}|${esc(c.version)}">${ico(c)}
      <div class="grow"><b>${esc(c.name)} is now out for Minecraft ${esc(c.version)}</b><p>You were waiting for it${c.release ? `. Version ${esc(c.release)}` : ""}.</p></div>
      <button class="btn go sm" data-capply>${has ? `Add it to my ${esc(c.version)} instances` : `Install for ${esc(c.version)}`}</button>
      <button class="btn quiet sm" data-cdismiss>Dismiss</button></div>`;
  }).join("");
  $$("#catchUp .catch").forEach(el => {
    const [key, version] = el.dataset.ck.split("|");
    el.querySelector("[data-cdismiss]").onclick = async () => { S = await api("/api/caught_up/dismiss", {key, version}); renderCatchUp(); };
    el.querySelector("[data-capply]").onclick = async ev => {
      const b = ev.currentTarget;
      if (!(S.installs || []).some(r => r.version === version && !r.export)) { go("install"); renderVersions(version); updateSteps(); return; }
      b.disabled = true; b.innerHTML = `<span class="spin"></span> Adding`;
      try {
        const {job} = await api("/api/caught_up/apply", {key, version});
        const res = await follow(job);
        S = await api("/api/state"); renderCatchUp(); renderInstances();
        toast(`Added to ${res.instances.join(", ")}`); burst($("#catchUp") || document.body);
      } catch (e) { toast(e.message); b.disabled = false; b.textContent = "Try again"; }
    };
  });
}
setInterval(async () => { try { const r = await api("/api/state"); if (JSON.stringify(r.caught_up) !== JSON.stringify(S.caught_up)) { S.caught_up = r.caught_up; S.installs = r.installs; renderCatchUp(); } } catch (e) {} }, 10 * 60 * 1000);

/* ---------- problems popup ---------- */
const PROB_ICON = {open: "!", fixed: "✓", off: "–"};
function showProblems(problems, ctx = {}) {
  if (!problems || !problems.length) return false;
  const open = problems.filter(p => p.status === "open"), fixed = problems.filter(p => p.status === "fixed");
  const canTurnOff = ctx.instanceId && !ctx.export;
  const row = (p, i) => {
    const btns = [];
    if (p.status === "open" && canTurnOff) {
      btns.push(`<button class="btn sm" data-off="${i}" data-file="${esc(p.file)}">Turn off ${esc(p.mod)}</button>`);
      if (p.type === "conflict" && p.on_file) btns.push(`<button class="btn sm" data-off="${i}" data-file="${esc(p.on_file)}">Turn off ${esc(p.on_name)}</button>`);
    }
    if (p.status === "open" && p.type === "missing") btns.push(`<a class="btn sm quiet" href="https://modrinth.com/mods?q=${encodeURIComponent(p.on)}" target="_blank" rel="noopener">Look for ${esc(p.on)}</a>`);
    const tip = p.status === "fixed" ? esc(p.fix || "Fixed.")
      : p.type === "conflict" ? "These two can't run together right now. Turn one off, or wait for an update."
      : p.type === "minecraft" ? "Turn it off for now, or wait for an update for this version."
      : p.type === "missing" ? "ModHub couldn't find it on Modrinth. Add it yourself, or turn this mod off."
      : "Turn it off for now, or wait for an update.";
    return `<div class="prob ${p.status}" data-prow="${i}"><div class="ic">${PROB_ICON[p.status] || "!"}</div>
      <div class="grow"><b>${esc(p.message)}</b><p>${tip}</p>${btns.length ? `<div class="actions">${btns.join("")}</div>` : ""}</div></div>`;
  };
  $("#probBody").innerHTML = `
    <h2 id="probTitle">${open.length ? (open.length === 1 ? "One thing needs you" : `${open.length} things need you`) : `ModHub fixed ${fixed.length === 1 ? "a problem" : fixed.length + " problems"}`}</h2>
    <p class="lede">${open.length
      ? `Some mods in ${esc(ctx.name || "this instance")} don't work together, so the game would show an error. ${fixed.length ? `ModHub already fixed ${fixed.length}.` : ""}`
      : `Some mods in ${esc(ctx.name || "this instance")} didn't work together. ModHub sorted it out, so the game should start normally.`}</p>
    ${open.map(p => row(p, problems.indexOf(p))).join("")}
    ${fixed.map(p => row(p, problems.indexOf(p))).join("")}
    ${open.length && ctx.export ? `<p class="help" style="margin-top:12px">This was built as a modpack file, so remove one of the mods from your loadout and build it again.</p>` : ""}
    <div class="foot"><button class="btn go" data-close>${open.length ? "Done" : "Great"}</button></div>`;
  openModal("#probModal");
  $$("#probBody [data-off]").forEach(b => b.onclick = async () => {
    const rowEl = b.closest(".prob");
    b.disabled = true;
    try {
      await api("/api/problems/turn_off", {id: ctx.instanceId, file: b.dataset.file});
      rowEl.className = "prob off";
      rowEl.querySelector(".ic").textContent = "–";
      rowEl.querySelector(".actions").innerHTML = `<span class="help" style="margin:0">Turned off ${esc(b.textContent.replace("Turn off ", ""))} in this instance. ModHub won't add it back here.</span>`;
      toast("Turned off");
    } catch (e) { toast(e.message); b.disabled = false; }
  });
  return true;
}
async function checkInstance(id, btn) {
  const label = btn.textContent; btn.disabled = true; btn.innerHTML = `<span class="spin"></span> Checking`;
  try {
    const {job} = await api("/api/instances/check", {id});
    const res = await follow(job);
    if (!showProblems(res.problems, {instanceId: id, name: res.instance})) toast(`No problems in ${res.instance}`);
  } catch (e) { toast(e.message); }
  btn.disabled = false; btn.textContent = label;
}

/* ---------- crash helper ---------- */
let crashPoll = null;
function crashLine(c) {
  const fx = c.autofix || {};
  if (fx.status === "fixing") return {cls: "fixing", icon: `<span class="spin"></span>`, title: `Fixing ${c.instance}`,
    text: "Minecraft said some mods don't work together. ModHub is sorting it out by itself.", show: ""};
  if (c.kind === "precheck" && fx.status === "fixed") return {cls: "ok", icon: "✓", title: `Fixed ${c.instance} before you play`,
    text: `${c.instance}'s mods changed, so ModHub checked them. ${fx.fixed.length === 1 ? fx.fixed[0] : `It made ${fx.fixed.length} fixes so they work together.`}`, show: "See what changed"};
  if (c.kind === "precheck") return {cls: "", icon: "!", title: `${c.instance} has mods that won't work together`,
    text: fx.fixed && fx.fixed.length ? `ModHub fixed ${fx.fixed.length}, but ${fx.still.length} ${fx.still.length === 1 ? "problem needs" : "problems need"} you before you play.` : "ModHub couldn't fix this by itself. Have a look before you play.", show: "See what's left"};
  if (fx.status === "fixed") return {cls: "ok", icon: "✓", title: `Fixed ${c.instance}`,
    text: `${fx.fixed.length === 1 ? fx.fixed[0] : `ModHub made ${fx.fixed.length} fixes so your mods work together.`} Start Minecraft again.`, show: "See what changed"};
  if (fx.status === "partly") return {cls: "", icon: "!", title: `Fixed part of ${c.instance}`,
    text: `ModHub fixed ${fx.fixed.length}, but ${fx.still.length} ${fx.still.length === 1 ? "problem needs" : "problems need"} you.`, show: "See what's left"};
  return {cls: "", icon: "!", title: `${c.instance} crashed ${timeAgo(c.at)}`, text: `${c.title}.`, show: "See what happened"};
}
function renderCrashes() {
  const list = S.crashes || [];
  $("#crashBox").innerHTML = list.map(c => { const l = crashLine(c); return `
    <div class="crashn rise ${l.cls}" data-crash="${esc(c.install_id)}"><div class="boom">${l.icon}</div>
      <div class="grow"><b>${esc(l.title)}</b><p>${esc(l.text)}</p></div>
      ${l.show ? `<button class="btn ${l.cls === "ok" ? "" : "go"} sm" data-cshow>${l.show}</button>` : ""}
      ${l.cls === "fixing" ? "" : `<button class="btn quiet sm" data-cdis>Dismiss</button>`}</div>`; }).join("");
  clearTimeout(crashPoll);
  if (list.some(c => (c.autofix || {}).status === "fixing")) crashPoll = setTimeout(refreshCrashes, 2500);
  $$("#crashBox .crashn").forEach(el => {
    const id = el.dataset.crash;
    const sh = el.querySelector("[data-cshow]"), di = el.querySelector("[data-cdis]");
    if (sh) sh.onclick = () => openCrash(id);
    if (di) di.onclick = async () => { S.crashes = (await api("/api/crashes/dismiss", {id})).crashes; renderCrashes(); renderInstances(); };
  });
  const navI = $(".nav[data-tab=instances]");
  if (list.length && !navI.querySelector(".dot-new")) navI.insertAdjacentHTML("beforeend", `<span class="dot-new" title="An instance crashed"></span>`);
}
function openCrash(id) {
  const c = (S.crashes || []).find(x => x.install_id === id);
  if (!c) return;
  const fx = c.autofix || {};
  const culprits = fx.status ? [] : (c.culprits || []);
  const fixedRows = (fx.fixed || []).map(t => `<div class="prob fixed done"><div class="ic">✓</div><div class="grow"><b>${esc(t)}</b></div></div>`).join("");
  const stillRows = (fx.still || []).map(p => `<div class="prob open"><div class="ic">!</div><div class="grow"><b>${esc(p.message)}</b>
      ${p.file ? `<div class="actions"><button class="btn sm" data-coff="${esc(p.file)}">Turn off ${esc(p.mod || "this mod")}</button></div>` : ""}</div></div>`).join("");
  $("#crashBody").innerHTML = `
    <h2 id="crashTitle">${esc(fx.status === "fixed" ? `ModHub fixed ${c.instance}` : c.title)}</h2>
    <p class="lede">${esc(c.instance)}, Minecraft ${esc(c.version)} with ${LOADER_NAMES[c.loader] || esc(c.loader)}. ${esc(c.kind === "precheck"
      ? (fx.status === "fixed" ? "Its mods changed, so ModHub checked them before you play. Here's what it did." : "Its mods changed, so ModHub checked them. ModHub fixed what it could. The rest needs you.")
      : fx.status === "fixed" ? "Minecraft said some mods didn't work together. Here's what ModHub did. Start the game again." : fx.status === "partly" ? "ModHub fixed what it could. The rest needs you." : c.explain)}</p>
    ${fixedRows}${stillRows}
    ${culprits.map(m => `<div class="prob open"><div class="ic">!</div><div class="grow"><b>${esc(m.name)}</b><p>Named in the crash report.</p>
        <div class="actions"><button class="btn sm" data-coff="${esc(m.file)}">Turn off ${esc(m.name)}</button></div></div></div>`).join("")}
    ${c.error ? `<div class="errline">${esc(c.error)}</div>` : ""}
    <div class="foot" style="justify-content:space-between;flex-wrap:wrap">
      <span class="actions">${c.file ? `<button class="btn quiet" id="crashCopy">Copy for Claude</button><button class="btn quiet" id="crashOpen">Open crash report</button>` : ""}</span>
      <span class="actions">${c.fix_check && fx.status !== "fixed" ? `<button class="btn go" id="crashFix">${fx.status ? "Try again" : "Fix it"}</button>` : ""}<button class="btn ${c.fix_check && fx.status !== "fixed" ? "" : "go"}" data-close>Done</button></span>
    </div>`;
  openModal("#crashModal");
  $$("#crashBody [data-coff]").forEach(b => b.onclick = async () => {
    b.disabled = true;
    try {
      await api("/api/problems/turn_off", {id, file: b.dataset.coff});
      b.closest(".prob").className = "prob off"; b.closest(".prob").querySelector(".ic").textContent = "–";
      b.parentElement.innerHTML = `<span class="help" style="margin:0">Turned off in this instance. Start the game again.</span>`;
      toast("Turned off");
    } catch (e) { toast(e.message); b.disabled = false; }
  });
  if ($("#crashCopy")) $("#crashCopy").onclick = async () => {
    try { const r = await api("/api/crashes/excerpt", {id}); await navigator.clipboard.writeText(r.text); toast("Copied. Paste it into a chat with Claude"); }
    catch (e) { toast(e.message); }
  };
  if ($("#crashOpen")) $("#crashOpen").onclick = () => api("/api/open", {path: c.file}).catch(e => toast(e.message));
  const fix = $("#crashFix");
  if (fix) fix.onclick = async () => {
    fix.disabled = true; fix.innerHTML = `<span class="spin"></span> Fixing`;
    try {
      const {job} = await api("/api/crashes/fix", {id});
      await follow(job, () => {});
    } catch (e) { toast(e.message); }
    await refreshCrashes(true);
    openCrash(id);
  };
}
async function refreshCrashes(force = false) {
  try {
    const r = await api("/api/crashes/scan");
    if (force || JSON.stringify(r.crashes) !== JSON.stringify(S.crashes)) {
      const was = (S.crashes || []).filter(c => (c.autofix || {}).status === "fixing").map(c => c.install_id);
      S.crashes = r.crashes; renderCrashes(); renderInstances();
      r.crashes.filter(c => was.includes(c.install_id) && (c.autofix || {}).status === "fixed").forEach(c => { toast(`Fixed ${c.instance}. Start Minecraft again`); burst($(`#crashBox [data-crash="${CSS.escape(c.install_id)}"]`)); });
    }
  } catch (e) {}
}
setInterval(refreshCrashes, 60 * 1000);
window.addEventListener("focus", refreshCrashes);

/* ---------- performance boost ---------- */
$("#boostBtn").onclick = async () => {
  $("#boostBody").innerHTML = `<h2 id="boostTitle">Performance boost</h2><p class="now"><span class="spin"></span>&nbsp; Checking which ones work with ${LOADER_NAMES[loader]}</p>`;
  openModal("#boostModal");
  let mods;
  try { mods = (await api("/api/perf", {loader, version: getVersion()})).mods; }
  catch (e) { $("#boostBody").innerHTML = `<h2>Performance boost</h2><div class="banner err"><div class="grow"><b>Couldn't load the list</b><p>${esc(e.message)}</p></div></div><div class="foot"><button class="btn" data-close>Close</button></div>`; return; }
  $("#boostBody").innerHTML = `
    <h2 id="boostTitle">Performance boost</h2>
    <p class="lede">Popular, trusted mods that make Minecraft faster. They're picked to work together, for ${LOADER_NAMES[loader]}${getVersion() ? " and Minecraft " + esc(getVersion()) : ""}.</p>
    ${mods.map((m, i) => `<label class="pmod ${m.available ? "" : "na"}">
        <input type="checkbox" data-pm="${esc(m.id)}" ${m.in_library ? "checked disabled" : m.available ? "checked" : "disabled"}>
        ${ico(m)}<div class="grow"><b>${esc(m.name)}</b><p>${esc(m.why)}</p></div>
        ${m.in_library ? `<span class="tag">In library</span>` : !m.available ? `<span class="tag">${esc(m.reason)}</span>` : ""}</label>`).join("")}
    <div class="foot"><button class="btn quiet" data-close>Cancel</button><button class="btn go" id="boostAdd"></button></div>`;
  const upd = () => { const n = $$("#boostBody [data-pm]:checked:not(:disabled)").length; $("#boostAdd").textContent = n ? `Add ${n} ${n === 1 ? "mod" : "mods"}` : "Nothing to add"; $("#boostAdd").disabled = !n; };
  $$("#boostBody [data-pm]").forEach(c => c.onchange = upd); upd();
  $("#boostAdd").onclick = async () => {
    const ids = $$("#boostBody [data-pm]:checked:not(:disabled)").map(c => c.dataset.pm);
    const r = await api("/api/perf/add", {ids});
    S.favorites = r.favorites; closeModals(); renderInventory();
    toast(`Added ${r.added.length} performance ${r.added.length === 1 ? "mod" : "mods"}`);
  };
};

/* ---------- bring my settings along ---------- */
let carryLoaded = false;
async function loadCarry() {
  const sel = $("#carryFrom");
  try {
    const {sources} = await api("/api/settings_sources");
    const want = (S.last || {}).settings_from;
    sel.innerHTML = sources.map(x => `<option value="${esc(x.path)}" ${x.path === want ? "selected" : ""}>${esc(x.name)} (${esc(x.launcher)})</option>`).join("");
    $("#carryBlock").classList.toggle("hidden", !sources.length);
    if (!carryLoaded) $("#carryOn").checked = !!sources.length && (want !== "" || !(S.installs || []).length);
    carryLoaded = true;
  } catch (e) { $("#carryBlock").classList.add("hidden"); }
}
$("#carryOn").onchange = () => { $("#carryFrom").disabled = !$("#carryOn").checked; };

/* ---------- what changed ---------- */
function mdLite(text) {
  // a tiny, safe subset of Markdown for changelogs
  const lines = esc(text || "").replace(/\r/g, "").split("\n");
  let html = "", inList = false;
  for (let raw of lines) {
    let l = raw.trim();
    if (!l || /^!\[/.test(l) || /^-{3,}$/.test(l)) { if (inList) { html += "</ul>"; inList = false; } continue; }
    l = l.replace(/\[([^\]]+)\]\((?:[^)]+)\)/g, "$1").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/__([^_]+)__/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
    const li = l.match(/^[-*+]\s+(.*)/);
    if (li) { if (!inList) { html += "<ul>"; inList = true; } html += `<li>${li[1]}</li>`; continue; }
    if (inList) { html += "</ul>"; inList = false; }
    const h = l.match(/^#{1,6}\s+(.*)/);
    html += h ? `<div><b>${h[1]}</b></div>` : `<div>${l}</div>`;
  }
  return (inList ? html + "</ul>" : html) || "<div>No notes for this update.</div>";
}
function showChanges(updates, title) {
  if (!updates || !updates.length) return false;
  const seen = new Map();
  updates.forEach(u => { if (!seen.has(u.key)) seen.set(u.key, u); });
  const list = [...seen.values()];
  $("#chgBody").innerHTML = `
    <h2 id="chgTitle">${esc(title || "What changed")}</h2>
    <p class="lede">${list.length} ${list.length === 1 ? "item was" : "items were"} updated. Here's what their authors say is new.</p>
    <div style="margin-top:8px">${list.map((u, i) => `
      <div class="chg"><div class="chg-h">${ico(u)}<div class="grow"><b>${safeUrl(u.url) ? `<a href="${esc(u.url)}" target="_blank" rel="noopener" style="color:inherit">${esc(u.name)}</a>` : esc(u.name)}</b>
        <div class="vv">${u.from ? esc(u.from) + " to " : ""}<span>${esc(u.to)}</span></div></div></div>
        <div class="cl" id="cl${i}">${mdLite(u.changelog)}</div>
        <button class="linkbtn cl-more hidden" data-more="${i}">Show more</button></div>`).join("")}</div>
    <div class="foot"><button class="btn go" data-close>Done</button></div>`;
  openModal("#chgModal");
  requestAnimationFrame(() => list.forEach((u, i) => {
    const el = $("#cl" + i);
    if (el.scrollHeight > el.clientHeight + 4) $(`[data-more="${i}"]`).classList.remove("hidden"); else el.classList.add("open");
  }));
  $$("#chgBody [data-more]").forEach(b => b.onclick = () => { $("#cl" + b.dataset.more).classList.toggle("open"); b.textContent = b.textContent === "Show more" ? "Show less" : "Show more"; });
  return true;
}

/* ---------- how to use ---------- */
$("#helpBtn").onclick = () => openModal("#helpModal");
$$("[data-help-go]").forEach(b => b.onclick = () => { closeModals(); go(b.dataset.helpGo); });

/* ---------- ModHub's own changelog ---------- */
function showWhatsNew(entries, title, lede, fresh = [], action = null) {
  if (!entries || !entries.length) return false;
  $("#wnBody").innerHTML = `
    <h2 id="wnTitle">${esc(title)}</h2>
    ${lede ? `<p class="lede">${esc(lede)}</p>` : ""}
    <div class="wn">${entries.map(e => `<div class="wn-v ${fresh.includes(e.version) ? "fresh" : ""}">
      <h4>ModHub ${esc(e.version)}${e.version === S.version ? `<span class="now-tag">You have this</span>` : ""}</h4>
      <ul>${e.notes.map(n => `<li>${esc(n)}</li>`).join("")}</ul></div>`).join("")}</div>
    <div class="foot">${action ? `<button class="btn" data-close>Not now</button><button class="btn go" id="wnGo">${esc(action.label)}</button>` : `<button class="btn go" data-close>Got it</button>`}</div>`;
  openModal("#wnModal");
  stagger($("#wnBody"), ".wn-v");
  if (action) $("#wnGo").onclick = () => { closeModals(); action.run(); };
  return true;
}
const RECENT = 4;
function showHistory(all = false) {
  const log = S.changelog || [];
  const list = all ? log : log.slice(0, RECENT);
  showWhatsNew(list, "What's new in ModHub", `You're on ModHub ${S.version}. Here's what ${all ? "every update" : `the last ${list.length} updates`} brought.`, log.length ? [log[0].version] : []);
  if (log.length > RECENT) {
    $("#wnBody .wn").insertAdjacentHTML("beforebegin", `<div class="wn-pick"><button class="${all ? "" : "on"}" data-wnall="0">Recent updates</button><button class="${all ? "on" : ""}" data-wnall="1">All updates</button></div>`);
    $$("[data-wnall]").forEach(b => b.onclick = () => showHistory(b.dataset.wnall === "1"));
  }
  markNotesSeen();
}
const SEEN_KEY = "modhub.notesSeen";
function markNotesSeen() { try { localStorage.setItem(SEEN_KEY, S.version); } catch (e) {} $("#wnDot").classList.add("hidden"); }
function renderNotesDot() {
  let seen = null; try { seen = localStorage.getItem(SEEN_KEY); } catch (e) { return; }
  $("#wnDot").classList.toggle("hidden", seen === S.version || !(S.changelog || []).length);
}
$("#wnFab").onclick = () => showHistory();
function showJustUpdated(ju) {
  const vt = v => (v.match(/\d+/g) || [0]).map(Number);
  const newer = (a, b) => { const x = vt(a), y = vt(b); for (let i = 0; i < Math.max(x.length, y.length); i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0); } return false; };
  const list = (S.changelog || []).filter(e => newer(e.version, ju.from) && !newer(e.version, ju.to));
  markNotesSeen();
  showWhatsNew(list, `ModHub updated to ${ju.to}`, `Here's what's new since ${ju.from}.`, list.map(e => e.version));  // small fixes update silently
}
$("#updNotes").onclick = () => showHistory();
$("#aboutNotes").onclick = () => showHistory();
$("#updPeek").onclick = () => {
  const u = S.update; if (!u) return;
  showWhatsNew(u.changes, `What's coming in ModHub ${u.version}`, `You're on ${S.version}. Updating keeps your library and settings.`, (u.changes || []).map(e => e.version),
    {label: `Update to ${u.version}`, run: () => applyUpdate(u.path, u.version)});
};

/* ---------- library backups ---------- */
$("#bkSave").onclick = async () => {
  const b = $("#bkSave"); b.disabled = true;
  try {
    const r = await api("/api/backup/save");
    $("#bkOut").innerHTML = `<div class="banner" style="margin-top:12px"><div class="grow"><b>Saved ${esc(r.file)}</b><p>In your ${esc(r.where)} folder: ${r.loadouts} ${r.loadouts === 1 ? "loadout" : "loadouts"}, ${r.items} items and ${r.files} of your own files. Copy it to your other PC, then Restore it there.</p></div><button class="btn sm" id="bkShow">Show in folder</button></div>`;
    $("#bkShow").onclick = () => api("/api/open", {path: r.path}).catch(e => toast(e.message));
    toast("Backup saved");
  } catch (e) { toast(e.message); }
  b.disabled = false;
};
function showRestored(r) {
  const parts = [];
  if (r.loadouts_added.length) parts.push(`added ${r.loadouts_added.map(esc).join(", ")}`);
  if (r.loadouts_merged.length) parts.push(`added new items to ${r.loadouts_merged.map(esc).join(", ")}`);
  const text = parts.length
    ? `ModHub ${parts.join(", and ")}. ${r.items} ${r.items === 1 ? "item" : "items"} and ${r.files} of your own files came back. Nothing was removed.`
    : "Everything in this backup was already here, so nothing changed.";
  $("#bkOut").innerHTML = `<div class="banner" style="margin-top:12px"><div class="grow"><b>Restored your library${r.from ? " from " + esc(r.from) : ""}</b><p>${text}</p></div></div>`;
  toast("Library restored");
}
$("#bkFile").onchange = async e => {
  const file = e.target.files[0]; e.target.value = "";
  if (!file) return;
  try {
    const r = await fetch("/api/backup/restore", {method: "POST", headers: {"X-Token": T, "X-Filename": encodeURIComponent(file.name)}, body: file});
    const j = await r.json(); if (!r.ok) throw new Error(j.error || r.statusText);
    const {restored, ...st} = j; S = st; renderAll(); showRestored(restored);
  } catch (err) { $("#bkOut").innerHTML = `<div class="banner err" style="margin-top:12px"><div class="grow"><b>Couldn't restore</b><p>${esc(err.message)}</p></div></div>`; }
};

/* ---------- new Minecraft versions ---------- */
let newVerPoll;
function renderNewVersion() {
  const v = S.new_version, box = $("#newVer");
  const navI = $(".nav[data-tab=install]");
  let dot = navI.querySelector(".dot-new");
  if (v && !dot) navI.insertAdjacentHTML("beforeend", `<span class="dot-new" title="Minecraft ${esc(v)} is out"></span>`);
  if (!v && dot) dot.remove();
  box.classList.toggle("hidden", !v);
  if (!v) return;
  $("#newVerNum").textContent = v;
  $("#newVerTitle").textContent = `Minecraft ${v} is out`;
  const c = S.newest_check;
  const n = S.favorites.length;
  $("#newVerText").textContent = c
    ? (c.ready === c.total ? `All ${c.total} of your items are ready for it.`
       : `${c.ready} of ${c.total} of your items are ready for it.` + (c.not_ready.length ? ` Not out yet: ${c.not_ready.slice(0, 4).join(", ")}${c.not_ready.length > 4 ? " and more" : ""}.` : ""))
    : (S.checking || n ? "Checking which of your mods are ready for it..." : "Add some mods to your library, then install them for it.");
  $("#newVerGo").textContent = `Install for ${v}`;
  clearTimeout(newVerPoll);
  if (!c && n) newVerPoll = setTimeout(refreshVersions, 4000);  // the check runs in the background
}
async function refreshVersions(force = false) {
  try {
    const r = await api("/api/versions", {refresh: force});
    const changed = JSON.stringify((S.versions || []).map(x => x.v)) !== JSON.stringify(r.versions.map(x => x.v));
    Object.assign(S, r);
    if (changed) renderVersions(getVersion());
    renderNewVersion();
  } catch (e) {}
}
$("#newVerGo").onclick = () => {
  const v = S.new_version;
  go("install");
  renderVersions(v);
  updateSteps();
  $("#installBtn").focus();
  toast(`Set to Minecraft ${v}. Pick where to install, then Install`);
};
$("#newVerLater").onclick = async () => { Object.assign(S, await api("/api/versions/seen")); renderNewVersion(); renderVersions(getVersion()); };
setInterval(() => refreshVersions(true), 15 * 60 * 1000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshVersions(true); });
// updates: pick up anything the background check found, and check again when you come back after a while
async function pollUpdate() {
  try {
    const r = await api("/api/update/status");
    const was = S.update && S.update.version;
    S.update = r.update; if (r.update_last_check) S.update_last_check = r.update_last_check;
    renderUpdateBits();
    if (r.update && r.update.version !== was) toast(`ModHub ${r.update.version} is ready. It installs next time you open ModHub, or update now in Settings.`);
  } catch (e) {}
}
setInterval(pollUpdate, 5 * 60 * 1000);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) return;
  api("/api/update/nudge").then(r => { if (r.nudged) setTimeout(pollUpdate, 20000); else pollUpdate(); }).catch(() => {});
});
window.addEventListener("focus", () => refreshVersions(true));

/* "/" jumps to search */
document.addEventListener("keydown", e => {
  if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) {
    e.preventDefault(); go("library"); $("#q").focus();
  }
});

/* ---------- app shortcut ---------- */
function shortcutWhere() {
  return {Windows: "your desktop and Start menu", Darwin: "your Applications folder, so it shows up in Launchpad and Spotlight"}[S.platform] || "your app menu and desktop";
}
function renderAppBits() {
  $("#shortcutText").textContent = `Add ModHub to ${shortcutWhere()}, so it opens in its own window without running the script.`;
  $("#shortcutHelp").textContent = `Adds ModHub to ${shortcutWhere()}. If you move ${S.frozen ? (/Mac/.test(navigator.userAgent) ? "ModHub" : "ModHub.exe") : "modhub.py"}, add the shortcut again.`;
  $("#shortcutBanner").classList.toggle("hidden", !!S.shortcut_done || !S.favorites.length);
  renderWindowBits();
  $("#quitHelp").textContent = S.in_window ? "Closing the ModHub window also stops it." : "ModHub keeps running in the background until you stop it.";
}
async function addShortcut(b) {
  if (b) b.disabled = true;
  try {
    const r = await api("/api/shortcut");
    S.shortcut_done = true; renderAppBits();
    toast("Added ModHub to " + r.made.join(" and "));
  } catch (err) { toast(err.message); }
  if (b) b.disabled = false;
}
document.addEventListener("click", e => { const b = e.target.closest("[data-shortcut]"); if (b) addShortcut(b); });
$("#shortcutLater").onclick = async () => { S.shortcut_done = true; renderAppBits(); api("/api/dismiss_shortcut").catch(() => {}); };

/* ---------- settings ---------- */
function renderSettings() {
  $("#dataDir").textContent = S.data_dir;
  $("#aboutVer").textContent = S.version;
  $$("[data-path]").forEach(i => { i.value = S.paths[i.dataset.path] || ""; i.placeholder = S.default_paths[i.dataset.path] || ""; });
}
$("#saveSettings").onclick = async () => {
  const btn = $("#saveSettings");
  const body = {paths: {}};
  $$("[data-path]").forEach(i => body.paths[i.dataset.path] = i.value);
  btn.disabled = true; btn.textContent = "Saving...";
  try {
    S = await api("/api/settings", body);
    renderAll(); toast("Folders saved");
  } catch (e) {
    toast(e.message);
  }
  btn.disabled = false; btn.textContent = "Save folders";
};

$("#quitBtn").onclick = async () => {
  if (!confirm("Stop ModHub? You can open it again any time.")) return;
  await api("/api/quit").catch(() => {});
  setTimeout(() => window.close(), 150);
  document.body.innerHTML = `<main style="padding:60px"><h1>ModHub has stopped</h1><p class="lede">You can close this tab.</p></main>`;
};


/* ---------- premium pass 2 ---------- */
// live install view
let liveBase = "", liveN = 0, ringShown = 0, ringAnim = 0;
const RING_C = 175.93;
function liveReset(title) {
  liveBase = title; liveN = 0; ringShown = 0;
  $("#liveTitle").textContent = title; $("#liveList").innerHTML = "";
  $("#ring").classList.remove("done"); $("#ringArc").style.strokeDashoffset = RING_C; $("#ringPct").textContent = "0%";
}
function liveProgress(p) {
  p = Math.max(0, Math.min(1, p || 0));
  $("#ringArc").style.strokeDashoffset = RING_C * (1 - p);
  const from = ringShown, to = Math.round(p * 100), t0 = performance.now();
  cancelAnimationFrame(ringAnim);
  if (REDUCED) { ringShown = to; $("#ringPct").textContent = to + "%"; return; }
  (function tick(t) {
    const k = Math.min(1, (t - t0) / 450), v = Math.round(from + (to - from) * (1 - Math.pow(1 - k, 3)));
    ringShown = v; $("#ringPct").textContent = v + "%";
    if (k < 1) ringAnim = requestAnimationFrame(tick);
  })(t0);
}
function liveLines(lines) {
  const list = $("#liveList");
  lines.forEach(l => {
    if (!l.startsWith("  + ")) return;
    const sp = document.createElement("span"); sp.textContent = l.slice(4).trim();
    list.append(sp); liveN++;
  });
  while (list.children.length > 18) list.firstElementChild.remove();
  if (liveN) $("#liveTitle").textContent = `${liveBase} (${liveN} added so far)`;
}
async function liveDone() {
  liveProgress(1); $("#ring").classList.add("done");
  $("#liveTitle").textContent = liveN ? `Done, ${liveN} added` : "Done";
  if (!REDUCED) await new Promise(r => setTimeout(r, 600));
}

// a soft ripple where you click a button
document.addEventListener("pointerdown", e => {
  const b = e.target.closest(".btn");
  if (!b || b.disabled || LESS) return;
  const z = uiZoom(), r = b.getBoundingClientRect(), size = Math.max(r.width, r.height) * 2.2 / z;
  const rp = document.createElement("span");
  rp.className = "ripple";
  Object.assign(rp.style, {width: size + "px", height: size + "px", left: ((e.clientX - r.left) / z - size / 2) + "px", top: ((e.clientY - r.top) / z - size / 2) + "px"});
  b.appendChild(rp); setTimeout(() => rp.remove(), 650);
});

// the page title turns into a frosted bar when you scroll
function checkTopbar() {
  const sec = $$("main > section").find(x => !x.classList.contains("hidden"));
  const h1 = sec && sec.querySelector("h1");
  const show = !!h1 && h1.getBoundingClientRect().bottom < 8;
  if (show) $("#topTitle").textContent = h1.textContent;
  $("#topbar").classList.toggle("show", show);
}
window.addEventListener("scroll", checkTopbar, {passive: true});
$("#topUp").onclick = () => window.scrollTo({top: 0, behavior: REDUCED ? "auto" : "smooth"});

// hover labels on library slots
const tip = document.createElement("div"); tip.id = "tip"; document.body.appendChild(tip);
let tipTimer, tipFor = null;
function hideTip() { clearTimeout(tipTimer); tip.classList.remove("on"); tipFor = null; }
document.addEventListener("pointerover", e => {
  const el = e.target.closest("[data-tip]");
  if (el === tipFor) return;
  hideTip();
  if (!el) return;
  tipFor = el;
  tipTimer = setTimeout(() => {
    const d = el.dataset.tipD, h = el.dataset.tipH;
    tip.innerHTML = `<b>${esc(el.dataset.tip)}</b>${d ? esc(d.length > 140 ? d.slice(0, 137) + "..." : d) : ""}${h ? `<em>${esc(h)}</em>` : ""}`;
    const r = el.getBoundingClientRect(), tr = tip.getBoundingClientRect();
    let x = r.left + r.width / 2 - tr.width / 2, y = r.top - tr.height - 10;
    if (y < 8) y = r.bottom + 10;
    x = Math.max(8, Math.min(innerWidth - tr.width - 8, x));
    const z = uiZoom();
    Object.assign(tip.style, {left: x / z + "px", top: y / z + "px"});
    tip.classList.add("on");
  }, 280);
});
["scroll", "pointerdown", "keydown"].forEach(ev => document.addEventListener(ev, hideTip, {passive: true, capture: true}));

// small blocky pictures for empty pages
function emptyArt(kind) {
  const ART = {
    chest: ["................", ".KKKKKKKKKKKKKK.", ".KbbbbbbbbbbbbK.", ".KbBBBBBBBBBBbK.", ".KbBBBBBBBBBBbK.", ".KKKKKKKKKKKKKK.", ".KbbbbbGGbbbbbK.",
            ".KBBBBBGGBBBBBK.", ".KbBBBBBBBBBBbK.", ".KbBBBBBBBBBBbK.", ".KbBBBBBBBBBBbK.", ".KbbbbbbbbbbbbK.", ".KKKKKKKKKKKKKK.", "................"],
    anvil: ["................", "................", ".KKKKKKKKKKKKK..", "KAAAAAAAAAAAAAK.", "KAaaaaaaaaaaaAK.", ".KKKKAAAAAKKKK..", "....KAaaaAK.....",
            "....KAaaaAK.....", "...KKAAAAAKK....", "..KAAAAAAAAAK...", "..KAaaaaaaaaAK..", "..KKKKKKKKKKKK..", "................", "................"],
  };
  const C = {K: "#121216", b: "#3b3b44", B: "#2b2b32", G: getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#d7263d", A: "#4a4a53", a: "#34343b"};
  let rects = "";
  ART[kind].forEach((row, y) => [...row].forEach((ch, x) => { if (C[ch]) rects += `<rect x="${x}" y="${y}" width="1.02" height="1.02" fill="${C[ch]}"/>`; }));
  const sparks = kind === "anvil" ? `<g class="bob"><rect x="12" y="0" width="1" height="1" style="fill:var(--accent-2)"/><rect x="14" y="1" width="1" height="1" fill="#f0a43a"/><rect x="11" y="1" width="1" height="1" fill="#f0a43a" opacity=".6"/></g>` : "";
  return `<svg class="art" viewBox="0 0 16 14" shape-rendering="crispEdges" aria-hidden="true">${rects}${sparks}</svg>`;
}

// command palette (Ctrl+K)
const ICON = {
  bolt: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/></svg>`,
  plus: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M12 5v14M5 12h14"/></svg>`,
  search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>`,
  save: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14"/></svg>`,
  swap: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M7 4L3 8l4 4M3 8h14M17 20l4-4-4-4M21 16H7"/></svg>`,
  file: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M14 3H6v18h12V7l-4-4z"/><path d="M14 3v4h4"/></svg>`,
};
const navIcon = t => ($(`.nav[data-tab="${t}"] svg`) || {}).outerHTML || "";
const after = fn => setTimeout(fn, 260);
function palItems(q) {
  const out = [];
  const add = (g, t, run, o = {}) => out.push({g, t, run, s: o.s || "", ico: o.ico || "", rank: o.rank || 0});
  [["library", "Library"], ["discover", "Discover"], ["install", "Install"], ["instances", "Instances"], ["ports", "Ports"], ["settings", "Settings"]]
    .forEach(([id, n]) => add("Pages", n, () => go(id), {ico: navIcon(id), s: "Page"}));
  const live = (S.installs || []).filter(r => !r.export);
  add("Actions", "Install my mods", () => go("install"), {ico: navIcon("install")});
  if (live.length) add("Actions", "Update all my instances", () => { go("instances"); after(() => $("#updAll").click()); }, {ico: ICON.bolt, s: `${live.length} ${live.length === 1 ? "instance" : "instances"}`});
  add("Actions", "Import mods from a launcher", () => openImport(), {ico: ICON.plus});
  add("Actions", "Add files from CurseForge", () => openFiles(), {ico: ICON.file});
  add("Actions", "New loadout", () => openLoadout(), {ico: ICON.plus});
  add("Actions", "Save a library backup", () => { go("settings"); after(() => $("#bkSave").click()); }, {ico: ICON.save});
  const dark = document.documentElement.dataset.mode !== "light";
  add("Actions", dark ? "Switch to light mode" : "Switch to dark mode", () => setTheme({mode: dark ? "light" : "dark"}), {ico: ICON.swap});
  if (q) ACCENTS.filter(a => a[0] !== (S.theme || {}).accent).forEach(([id, n, c]) =>
    add("Colours", `${n} colour theme`, () => setTheme({accent: id}), {ico: `<i style="width:14px;height:14px;border-radius:4px;background:${c}"></i>`}));
  add("Actions", "Add ModHub to the desktop and Start menu", () => addShortcut(), {ico: ICON.plus});
  add("Actions", "How to use ModHub", () => openModal("#helpModal"), {ico: ICON.file});
  add("Actions", "What's new in ModHub", () => showHistory(), {ico: ICON.file, s: `Version ${S.version}`});
  add("Actions", "Check for ModHub updates", () => { go("settings"); after(() => $("#updCheck").click()); }, {ico: ICON.search});
  (S.loadouts || []).filter(l => l.id !== S.active_loadout).forEach(l =>
    add("Loadouts", `Switch to ${l.name}`, () => switchLoadout(l.id), {ico: ICON.swap, s: `${l.count || 0} items`}));
  live.forEach(r => add("Instances", `Update ${r.name}`, () => { go("instances"); after(() => { const b = $(`[data-iup="${CSS.escape(r.id)}"]`); if (b) { b.scrollIntoView({block: "center"}); b.click(); } }); },
    {ico: navIcon("instances"), s: `Minecraft ${r.version}`}));
  if (q) {
    S.favorites.forEach(m => add("Your library", m.name, () => {
      if (m.source === "local") { openItem(m.id); return; }
      openModPage(m);
    }, {ico: ico(m, "x").replace(/^<div class="x">|<\/div>$/g, ""), s: KIND_LABEL[m.kind || "mod"]}));
  }
  return out;
}
function palScore(text, q) {
  const t = text.toLowerCase();
  const i = t.indexOf(q);
  if (i >= 0) return 200 - i - (i > 0 && t[i - 1] !== " " ? 40 : 0);
  let j = 0;
  for (const ch of t) if (ch === q[j]) j++;
  return j === q.length ? 20 : -1;
}
function palMark(text, q) {
  const i = q ? text.toLowerCase().indexOf(q) : -1;
  return i < 0 ? esc(text) : esc(text.slice(0, i)) + `<mark>${esc(text.slice(i, i + q.length))}</mark>` + esc(text.slice(i + q.length));
}
let palSel = 0, palShown = [];
function palRender() {
  const q = $("#palQ").value.trim().toLowerCase();
  let items = palItems(q);
  if (q) {
    items = items.map(x => ({...x, rank: palScore(x.t, q)})).filter(x => x.rank >= 0);
    const order = ["Pages", "Actions", "Loadouts", "Instances", "Colours", "Your library"];
    items.sort((a, b) => b.rank - a.rank || order.indexOf(a.g) - order.indexOf(b.g));
    items = items.slice(0, 12);
    items.push({g: "Modrinth", t: `Search Modrinth for "${$("#palQ").value.trim()}"`, ico: ICON.search, s: "Library", run: () => { go("library"); $("#q").value = $("#palQ").value.trim(); search(); }});
  }
  palShown = items; palSel = Math.min(palSel, items.length - 1);
  if (!items.length) { $("#palList").innerHTML = `<div class="pal-none">Nothing matches.</div>`; return; }
  let h = "", g = null;
  items.forEach((x, i) => {
    if (!q && x.g !== g) { g = x.g; h += `<div class="pal-g">${esc(g)}</div>`; }
    h += `<div class="pi ${i === palSel ? "sel" : ""}" data-pi="${i}" role="option"><span class="pico">${x.ico}</span><span class="pt">${palMark(x.t, q)}</span><span class="ps">${esc(x.s)}</span></div>`;
  });
  $("#palList").innerHTML = h;
  const sel = $(".pi.sel"); if (sel) sel.scrollIntoView({block: "nearest"});
}
function palRun(i) {
  const x = palShown[i]; if (!x) return;
  closePal(); x.run();
}
function openPal() {
  if ($("#pal")) return;
  hideTip();
  const d = document.createElement("div");
  d.className = "pal-scrim"; d.id = "pal";
  d.innerHTML = `<div class="pal" role="dialog" aria-label="Jump to anything">
    <div class="pal-q">${ICON.search}<input id="palQ" placeholder="Type a page, a mod, a loadout or an action" autocomplete="off" spellcheck="false"></div>
    <div class="pal-list" id="palList" role="listbox"></div>
    <div class="pal-foot"><span><kbd>&uarr;</kbd><kbd>&darr;</kbd>to move</span><span><kbd>Enter</kbd>to open</span><span><kbd>Esc</kbd>to close</span></div></div>`;
  document.body.appendChild(d);
  palSel = 0; palRender();
  const inp = $("#palQ"); inp.focus();
  inp.oninput = () => { palSel = 0; palRender(); };
  inp.onkeydown = e => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); palSel = (palSel + (e.key === "ArrowDown" ? 1 : -1) + palShown.length) % Math.max(palShown.length, 1); palRender(); }
    else if (e.key === "Enter") { e.preventDefault(); palRun(palSel); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closePal(); }
  };
  d.onclick = e => { const it = e.target.closest("[data-pi]"); if (it) palRun(+it.dataset.pi); else if (!e.target.closest(".pal")) closePal(); };
  d.onpointermove = e => { const it = e.target.closest("[data-pi]"); if (it && +it.dataset.pi !== palSel) { palSel = +it.dataset.pi; $$(".pi").forEach(x => x.classList.toggle("sel", +x.dataset.pi === palSel)); } };
}
function closePal() { const d = $("#pal"); if (d) d.remove(); }
$("#palBtn").onclick = openPal;
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) { e.preventDefault(); $("#pal") ? closePal() : openPal(); }
});

// start-up splash
const splashT0 = performance.now();
function hideSplash() {
  const sp = $("#splash"); if (!sp) return;
  if (REDUCED) { sp.remove(); return; }
  setTimeout(() => { sp.classList.add("out"); setTimeout(() => sp.remove(), 450); }, Math.max(0, 700 - (performance.now() - splashT0)));
}
setTimeout(hideSplash, 4000);

/* ---------- discover ---------- */
let discKind = "mod", discSeq = 0, discData = null, discStale = true;
const LOADER_LABEL = {fabric: "Fabric", quilt: "Quilt", forge: "Forge", neoforge: "NeoForge"};
function discOptions() {
  const list = (S.versions || []).filter(v => v.type === "release").slice(0, 40).map(v => v.v);
  const want = $("#discVer").value || getVersion() || list[0] || "";
  if (want && !list.includes(want)) list.unshift(want);
  $("#discVer").innerHTML = list.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join("");
  if (want) $("#discVer").value = want;
  if (!$("#discLoader").dataset.set) $("#discLoader").value = loader || "fabric";
}
async function loadDiscover() {
  discOptions(); discStale = false;
  $("#discLoaderWrap").classList.toggle("hidden", discKind !== "mod");
  const seq = ++discSeq, out = $("#discOut");
  out.innerHTML = `<div class="disc-sec"><div class="dgrid">${Array.from({length: 8}, () => `<div class="dskel"></div>`).join("")}</div></div>`;
  try {
    const d = await api("/api/discover", {kind: discKind, version: $("#discVer").value, loader: $("#discLoader").value});
    if (seq !== discSeq) return;
    discData = d; renderDiscover();
  } catch (e) {
    if (seq !== discSeq) return;
    out.innerHTML = `<div class="banner err"><div class="grow"><b>Couldn't load Discover</b><p>${esc(e.message)}</p></div><button class="btn sm" id="discRetry">Try again</button></div>`;
    $("#discRetry").onclick = loadDiscover;
  }
}
function dcard(m, i, pick, shots) {
  const art = `<span class="mid">${ico(m)}</span>`;
  return `<div class="dcard ${shots ? "has-shot" : ""} ${pick ? "pick" : ""}" data-dk="${i}" role="button" tabindex="0" aria-label="${esc(m.name)}">
    ${shots ? "" : "<!--"}<div class="shot ${safeUrl(m.shot) ? "" : "empty"}">${safeUrl(m.shot) ? `<img src="${esc(m.shot)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.parentElement.classList.add('empty');this.remove()">` : ""}${art}</div>${shots ? "" : "-->"}
    <div class="top">${ico(m)}<div style="min-width:0"><div class="nm">${esc(m.name)}</div><div class="by">${m.author ? "by " + esc(m.author) : "Modrinth"}</div></div></div>
    ${pick && m.why ? `<div class="why">${esc(m.why)}</div>` : `<div class="ds">${esc(m.desc)}</div>`}
    <div class="ft"><span>${fmt(m.downloads)} downloads</span>${isFav(m) ? `<span class="added"><svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M2 7.5l3 3 7-7"/></svg>In library</span>` : `<button class="btn sm go" data-dadd>Add</button>`}</div>
  </div>`;
}
function renderDiscover() {
  const d = discData; if (!d) return;
  const v = esc($("#discVer").value), K = {mod: "mods", resourcepack: "resource packs", shader: "shaders"}[discKind];
  const all = [];
  const sec = (title, small, list, pick) => {
    if (!list || !list.length) return "";
    const shots = list.filter(m => safeUrl(m.shot)).length >= list.length / 2;
    return `<div class="disc-sec"><h3>${title}<small>${small}</small></h3><div class="dgrid">${list.map(m => { all.push(m); return dcard(m, all.length - 1, pick, shots); }).join("")}</div></div>`;
  };
  const ids = new Set((d.popular || []).map(m => m.id));
  let h = sec("Goes with your library", "Picked for what you already have", d.picks, true)
        + sec(`Popular for ${v}`, `The most followed ${K} that are out for ${v}`, d.popular)
        + sec("Recently updated", `Just updated for ${v}`, (d.updated || []).filter(m => !ids.has(m.id)));
  if (!h) h = `<div class="empty" style="margin-top:24px">${emptyArt("chest")}<h3>Nothing out for ${v} yet</h3><p>Mods take a little while to catch up after a new Minecraft version. Try an earlier version, or check back in a few days.</p></div>`;
  $("#discOut").innerHTML = h;
  stagger($("#discOut"), ".dcard");
  $$("#discOut [data-dk]").forEach(c => {
    const m = all[+c.dataset.dk];
    c.onclick = e => { const b = e.target.closest("[data-dadd]"); if (b) addToLibrary(m, b); else openModPage(m); };
    c.onkeydown = e => { if (e.key === "Enter" && e.target === c) openModPage(m); };
  });
}
async function addToLibrary(m, btn) {
  if (btn) btn.disabled = true;
  try {
    S.favorites = (await api("/api/favorites/add", {mod: {source: "modrinth", id: m.id, slug: m.slug, name: m.name, desc: m.desc, icon: m.icon, url: m.url, kind: m.kind || "mod"}})).favorites;
    renderInventory(); if (discData) renderDiscover(); if (lastResults.length) renderResults();
    toast(`Added ${m.name} to your library`);
    return true;
  } catch (e) { toast(e.message); if (btn) btn.disabled = false; return false; }
}
$$("#discKind button").forEach(b => b.onclick = () => { discKind = b.dataset.dkind; $$("#discKind button").forEach(x => x.classList.toggle("on", x === b)); settle(); loadDiscover(); });
$("#discVer").onchange = loadDiscover;
$("#discLoader").onchange = () => { $("#discLoader").dataset.set = "1"; loadDiscover(); };

/* ---------- mod pages ---------- */
let mpSeq = 0;
function pageContext() {
  const onDisc = !$("#tab-discover").classList.contains("hidden");
  return onDisc ? {version: $("#discVer").value, loader: $("#discLoader").value} : {version: getVersion(), loader: loader || "fabric"};
}
function plainBody(md) {
  return (md || "").replace(/<!--[\s\S]*?-->/g, "").replace(/<br\s*\/?>/gi, "\n").replace(/<\/(p|div|h\d|li)>/gi, "\n").replace(/<[^>]+>/g, "")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "").replace(/&nbsp;/g, " ").replace(/\n{3,}/g, "\n\n").trim();
}
async function openModPage(m) {
  const ctx = pageContext(), seq = ++mpSeq;
  $("#mpBody").innerHTML = `<div class="mp-head">${ico(m)}<div class="grow"><h2 id="mpTitle">${esc(m.name)}</h2><div class="sub"><span class="spin"></span>&nbsp; Loading its page</div></div></div><div style="padding:0 30px 30px"><div class="dskel" style="height:190px"></div></div>`;
  openModal("#modModal");
  try {
    const p = await api("/api/project", {id: m.id, version: ctx.version, loader: ctx.loader});
    if (seq === mpSeq) renderModPage(p, ctx);
  } catch (e) {
    if (seq === mpSeq) $("#mpBody").innerHTML = `<div class="mp-head"><div class="grow"><h2 id="mpTitle">${esc(m.name)}</h2></div></div><div style="padding:0 30px 30px"><div class="banner err" style="margin:0"><div class="grow"><b>Couldn't load this page</b><p>${esc(e.message)}</p></div></div><div class="foot"><button class="btn" data-close>Close</button></div></div>`;
  }
}
function fallBack(img, url) { if (img && url) img.onerror = () => { img.onerror = null; if (img.src !== url) img.src = url; }; }
function renderModPage(p, ctx) {
  const fav = isFav(p), kind = p.kind || "mod", v = esc(ctx.version || "");
  const ldr = kind === "mod" ? ` with ${LOADER_LABEL[ctx.loader] || ""}` : "";
  const status = !ctx.version ? "" : p.ready
    ? `<div class="mp-status ok"><span class="dot" style="background:var(--ready)"></span><span><b>Ready for Minecraft ${v}</b>${esc(ldr)}. Version ${esc(p.ready.version)}${p.ready.type !== "release" ? " (beta)" : ""}.</span></div>`
    : `<div class="mp-status no"><span class="dot" style="background:var(--amber)"></span><span><b>Not out for Minecraft ${v}${esc(ldr)} yet.</b> ${p.newest_mc ? `It supports up to ${esc(p.newest_mc)}. ` : ""}${fav ? "ModHub tells you when it comes out." : "Add it anyway and ModHub tells you when it comes out."}</span></div>`;
  const body = plainBody(p.body);
  const short = body.length > 4000 ? body.slice(0, 4000).replace(/\s+\S*$/, "") + "..." : body;
  const links = Object.entries(p.links || {}).map(([k, u]) => `<a class="mp-chip" href="${esc(u)}" target="_blank" rel="noopener">${{source_url: "Source code", issues_url: "Report a bug", wiki_url: "Wiki", discord_url: "Discord"}[k]}</a>`).join("");
  const hero = p.gallery[0];
  $("#mpBody").innerHTML = `
    ${hero ? `<div class="mp-banner" data-zoom="0"><img src="${esc(hero.full || hero.url)}" alt="${esc(hero.title)}" decoding="async" referrerpolicy="no-referrer"></div>` : ""}
    <div class="mp-head ${hero ? "on-banner" : ""}">${ico(p)}
      <div class="grow"><h2 id="mpTitle">${esc(p.name)}</h2><div class="sub">${esc(p.desc)}</div>${p.author ? `<div class="help" style="margin-top:4px">by ${esc(p.author)}</div>` : ""}</div>
    </div>
    <div class="mp-acts" style="padding:0 30px 18px">
      ${fav ? `<span class="added"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M2 7.5l3 3 7-7"/></svg>In your library</span>` : `<button class="btn go" id="mpAdd">Add to my library</button>`}
      ${safeUrl(p.url) ? `<a class="btn quiet" href="${esc(p.url)}" target="_blank" rel="noopener">Open on Modrinth</a>` : ""}
      <button class="btn quiet" data-close style="margin-left:auto">Close</button>
    </div>
    ${status}
    ${p.gallery.length > 1 ? `<div class="mp-gal">${p.gallery.slice(1).map((g, i) => `<img src="${esc(g.url)}" alt="${esc(g.title)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-zoom="${i + 1}">`).join("")}</div>` : ""}
    <div class="mp-grid">
      <div class="mp-body">${body ? mdLite(short).replace("<div>No notes for this update.</div>", "") : `<p>${esc(p.desc)}</p>`}
        ${body.length > 4000 && safeUrl(p.url) ? `<p style="margin-top:12px"><a href="${esc(p.url)}" target="_blank" rel="noopener">Read the full description on Modrinth</a></p>` : ""}</div>
      <dl class="mp-facts">
        <div><dt>Downloads</dt><dd>${fmt(p.downloads)}, followed by ${fmt(p.followers)}</dd></div>
        ${p.needs.length ? `<div><dt>Needs</dt><dd>${p.needs.map((n, i) => `<button class="mp-chip" data-need="${i}">${ico(n)}${esc(n.name)}</button>`).join("")}</dd></div>` : ""}
        ${kind === "mod" && p.loaders.length ? `<div><dt>Works with</dt><dd>${p.loaders.filter(l => LOADER_LABEL[l]).map(l => LOADER_LABEL[l]).join(", ") || esc(p.loaders.join(", "))}</dd></div>` : ""}
        ${p.newest_mc ? `<div><dt>Newest Minecraft</dt><dd>${esc(p.newest_mc)}</dd></div>` : ""}
        ${p.categories.length ? `<div><dt>Tags</dt><dd>${p.categories.map(c => `<span class="mp-chip static">${esc(c.replace(/-/g, " "))}</span>`).join("")}</dd></div>` : ""}
        ${p.license ? `<div><dt>Licence</dt><dd>${esc(p.license)}</dd></div>` : ""}
        ${p.updated ? `<div><dt>Last updated</dt><dd>${esc(timeAgo(p.updated))}</dd></div>` : ""}
        ${links ? `<div><dt>Links</dt><dd>${links}</dd></div>` : ""}
      </dl>
    </div>`;
  $("#mpBody").scrollTop = 0;
  if ($("#mpAdd")) $("#mpAdd").onclick = async () => { if (await addToLibrary(p, $("#mpAdd"))) renderModPage(p, ctx); };
  $$("#mpBody [data-need]").forEach(b => b.onclick = () => openModPage(p.needs[+b.dataset.need]));
  if (hero) fallBack($(".mp-banner img"), hero.url);
  $$("#mpBody [data-zoom]").forEach(el => el.onclick = () => {
    const g = p.gallery[+el.dataset.zoom]; if (!g) return;
    const z = document.createElement("div"); z.className = "mp-zoom";
    z.innerHTML = `<img src="${esc(g.full || g.url)}" alt="${esc(g.title)}" referrerpolicy="no-referrer">${g.title ? `<span>${esc(g.title)}</span>` : ""}`;
    fallBack(z.querySelector("img"), g.url);
    z.onclick = () => z.remove(); document.body.appendChild(z);
  });
}

/* ---------- themes ---------- */
const ACCENTS = [["crimson", "Crimson", "#d7263d"], ["rose", "Rose", "#d62976"], ["violet", "Violet", "#7c3aed"], ["ocean", "Ocean", "#2563eb"], ["emerald", "Emerald", "#0e9e5a"], ["amber", "Amber", "#ca7008"],
  ["sunset", "Sunset", "#f46220", "#db2777"], ["aurora", "Aurora", "#14b8a6", "#7c3aed"], ["nether", "Nether", "#e24216", "#8c1018"], ["ender", "The End", "#a855f7", "#401e8c"],
  ["cherry", "Cherry", "#e25492", "#b02a68"], ["mint", "Mint", "#0ea674", "#067454"]];
const SECRET_ACCENTS = [["lime", "Retro green", "#4ac440", "#228024", "retro"], ["rainbow", "Rainbow", "#7c3aed", "#ec4899", "rainbow"],
  ["diamond", "Diamond", "#22d3ee", "#0e7490", "diamond"], ["owl", "Night owl", "#f5b032", "#1e3078", "nightowl"], ["mono", "Void", "#d6d6de", "#5a5a64", "void"],
  ["ghost", "Ghost", "#808ca8", "#60688c", "ghost"], ["gold", "Gold", "#eaaa08", "#925806", "golden"], ["redstone", "Redstone", "#e41824", "#6e0008", "redstone"]];
const THEME_DEFAULT = {mode: "dark", accent: "crimson", custom: "#d7263d", bg: "gradient", dir: "top", strength: 55, radius: "rounded", side: "glass", size: "100", motion: "fluid", font: "normal"};
const lightQuery = matchMedia("(prefers-color-scheme: light)");
function accentTriplets(hex) {
  const n = parseInt(hex.slice(1), 16), c = [n >> 16 & 255, n >> 8 & 255, n & 255];
  const mix = (w, k) => c.map(v => Math.round(v + (w - v) * k)).join(" ");
  return [c.join(" "), mix(255, .18), mix(0, .28)];
}
function applyTheme(t, animate = false) {
  t = {...THEME_DEFAULT, ...t};
  const d = document.documentElement;
  if (animate && !REDUCED) { d.classList.add("theming"); setTimeout(() => d.classList.remove("theming"), 420); }
  Object.assign(d.dataset, {pref: t.mode, accent: t.accent, bg: t.bg, dir: t.dir, radius: t.radius, side: t.side, motion: t.motion, font: t.font || "normal"});
  d.dataset.mode = t.mode === "system" ? (lightQuery.matches ? "light" : "dark") : t.mode;
  d.style.setProperty("--bgk", (t.strength / 100).toFixed(2));
  d.style.setProperty("--ui-zoom", (+t.size / 100).toFixed(2));
  if (t.accent === "custom") { const [a, b, c] = accentTriplets(t.custom); d.style.setProperty("--acc", a); d.style.setProperty("--acc2", b); d.style.setProperty("--acc3", c); }
  else ["--acc", "--acc2", "--acc3"].forEach(v => d.style.removeProperty(v));
  clearInterval(window.rainbowTimer);
  if (t.accent === "rainbow" && t.motion !== "off" && !motionQuery.matches) {
    let h = 270; const hx = (h, l) => { const f = n => { const k = (n + h / 30) % 12, a = .62 * Math.min(l, 1 - l); return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))); }; return `${f(0)} ${f(8)} ${f(4)}`; };
    window.rainbowTimer = setInterval(() => { h = (h + 1.2) % 360; d.style.setProperty("--acc", hx(h, .52)); d.style.setProperty("--acc2", hx(h + 25, .62)); d.style.setProperty("--acc3", hx(h + 70, .42)); }, 60);
  }
  REDUCED = motionQuery.matches || t.motion === "off";
  LESS = REDUCED || t.motion === "less";
  if (typeof settle === "function") { settle(); setTimeout(settle, 60); }
}
lightQuery.addEventListener("change", () => { if (S && S.theme && S.theme.mode === "system") applyTheme(S.theme, true); });
function renderTheme() {
  const t = {...THEME_DEFAULT, ...(S.theme || {})};
  $$("#themeMode button").forEach(b => { b.classList.toggle("on", b.dataset.mode === t.mode); b.setAttribute("aria-checked", b.dataset.mode === t.mode); });
  $$("[data-opt]").forEach(g => g.querySelectorAll("button").forEach(b => { const on = String(t[g.dataset.opt]) === b.dataset.v; b.classList.toggle("on", on); b.setAttribute("aria-checked", on); }));
  $("#accentPick").innerHTML = ACCENTS.concat(SECRET_ACCENTS.filter(x => (S.secrets || []).includes(x[4]))).map(([id, n, c]) => `<button class="sw ${id === t.accent ? "on" : ""}" data-accent="${id}" style="--sw:${c}" role="radio" aria-checked="${id === t.accent}" title="${n}" aria-label="${n}"><i></i></button>`).join("")
    + `<label class="sw custom ${t.accent === "custom" ? "on" : ""}" style="--sw:${t.custom}" title="Pick any colour"><i></i><input type="color" id="customColor" value="${t.custom}" aria-label="Pick any colour"></label>`;
  $$("#accentPick [data-accent]").forEach(b => b.onclick = () => setTheme({accent: b.dataset.accent}));
  const cc = $("#customColor");
  cc.oninput = () => { const v = cc.value; cc.parentElement.style.setProperty("--sw", v); S.theme = {...t, accent: "custom", custom: v}; applyTheme(S.theme); $$("#accentPick .sw").forEach(x => x.classList.toggle("on", x.classList.contains("custom"))); };
  cc.onchange = () => setTheme({accent: "custom", custom: cc.value});
  $("#bgStrength").value = t.strength; $("#bgStrengthVal").textContent = t.strength + "%";
  renderThemeTiles(t);
  $$("[data-needs-bg]").forEach(r => r.classList.toggle("hidden", t.bg === "plain"));
  settle();
}
const PRESETS = [
  {id: "crimson", n: "Crimson", m: "Dark, gradient", t: {mode: "dark", accent: "crimson", bg: "gradient", dir: "top"}},
  {id: "rose", n: "Rose", m: "Dark, vivid", t: {mode: "dark", accent: "rose", bg: "vivid", dir: "corner"}},
  {id: "violet", n: "Violet", m: "Light, gradient", t: {mode: "light", accent: "violet", bg: "gradient", dir: "top"}},
  {id: "ocean", n: "Ocean", m: "Dark, glow", t: {mode: "dark", accent: "ocean", bg: "glow", dir: "corner"}},
  {id: "emerald", n: "Emerald", m: "Light, from the side", t: {mode: "light", accent: "emerald", bg: "gradient", dir: "side"}},
  {id: "amber", n: "Amber", m: "Dark, from the bottom", t: {mode: "dark", accent: "amber", bg: "gradient", dir: "bottom"}},
  {id: "midnight", n: "Midnight", m: "Dark, plain", t: {mode: "dark", accent: "crimson", bg: "plain", dir: "top"}},
  {id: "snow", n: "Snow", m: "Light, plain", t: {mode: "light", accent: "ocean", bg: "plain", dir: "top"}},
  {id: "sunset", n: "Sunset", m: "Dark, orange to pink", t: {mode: "dark", accent: "sunset", bg: "vivid", dir: "corner"}},
  {id: "aurora", n: "Aurora", m: "Dark, drifting lights", t: {mode: "dark", accent: "aurora", bg: "aurora", dir: "top"}},
  {id: "nether", n: "Nether", m: "Dark, rising embers", t: {mode: "dark", accent: "nether", bg: "embers", dir: "bottom"}},
  {id: "end", n: "The End", m: "Dark, twinkling stars", t: {mode: "dark", accent: "ender", bg: "stars", dir: "top"}},
  {id: "deepsea", n: "Deep sea", m: "Dark, rising bubbles", t: {mode: "dark", accent: "ocean", bg: "embers", dir: "top"}},
  {id: "cherry", n: "Cherry", m: "Light, blossom pink", t: {mode: "light", accent: "cherry", bg: "aurora", dir: "top"}},
  {id: "mint", n: "Mint", m: "Light, fresh glow", t: {mode: "light", accent: "mint", bg: "glow", dir: "corner"}},
];
const SECRET_PRESETS = {
  rainbow: {id: "rainbow", n: "Rainbow", m: "Secret: every colour", t: {mode: "dark", accent: "rainbow", bg: "aurora", dir: "top"}},
  retro: {id: "retro", n: "Retro", m: "Secret: old-school screen", t: {mode: "dark", accent: "lime", bg: "glow", dir: "corner", font: "mono"}},
  diamond: {id: "diamond", n: "Diamond", m: "Secret: ice-cold sparkle", t: {mode: "dark", accent: "diamond", bg: "stars", dir: "corner"}},
  nightowl: {id: "nightowl", n: "Night owl", m: "Secret: for late nights", t: {mode: "dark", accent: "owl", bg: "stars", dir: "top"}},
  void: {id: "void", n: "Void", m: "Secret: nothing but black", t: {mode: "dark", accent: "mono", bg: "plain", dir: "top"}},
  ghost: {id: "ghost", n: "Ghost", m: "Secret: pale and see-through", t: {mode: "light", accent: "ghost", bg: "aurora", dir: "top"}},
  golden: {id: "golden", n: "Gold", m: "Secret: for big collections", t: {mode: "dark", accent: "gold", bg: "embers", dir: "bottom"}},
  redstone: {id: "redstone", n: "Redstone", m: "Secret: powered up, blocky letters", t: {mode: "dark", accent: "redstone", bg: "pulse", dir: "bottom", font: "pixel"}},
};
const SECRET_NAMES = {rainbow: "Rainbow", retro: "Retro", diamond: "Diamond", nightowl: "Night owl", void: "Void", ghost: "Ghost", golden: "Gold", redstone: "Redstone"};
const ACCENT_HEX = Object.fromEntries(ACCENTS.concat(SECRET_ACCENTS).map(a => [a[0], a[2]]));
const ACCENT_HEX2 = Object.fromEntries(ACCENTS.concat(SECRET_ACCENTS).map(a => [a[0], a[3] || a[2]]));
function tileBg(t, hex) {
  const dark = t.mode !== "light", base = dark ? "#0b0b0d" : "#f7f7f9", clear = dark ? "rgba(11,11,13,0)" : "rgba(247,247,249,0)";
  const deg = {top: "180deg", corner: "150deg", side: "90deg", bottom: "0deg"}[t.dir] || "180deg";
  const pos = {top: "50% 0%", corner: "0% 0%", side: "0% 50%", bottom: "50% 100%"}[t.dir] || "50% 0%";
  const h2 = ACCENT_HEX2[t.accent] || hex;
  if (t.accent === "rainbow") return `linear-gradient(135deg, #ef4444aa, #f59e0baa, #22c55eaa, #3b82f6aa, #a855f7aa), ${base}`;
  if (t.bg === "aurora") return `radial-gradient(70% 80% at 15% 0%, ${hex}${dark ? "bb" : "77"}, ${clear} 70%), radial-gradient(70% 70% at 90% 20%, ${h2}${dark ? "aa" : "66"}, ${clear} 70%), ${base}`;
  if (t.bg === "stars") return `radial-gradient(1.5px 1.5px at 20% 30%, #fff, transparent), radial-gradient(1.5px 1.5px at 70% 20%, #fff, transparent), radial-gradient(1px 1px at 45% 60%, #fff, transparent), radial-gradient(1.5px 1.5px at 85% 55%, #fff, transparent), radial-gradient(1px 1px at 30% 80%, #fff, transparent), radial-gradient(110% 80% at 50% 0%, ${hex}99, ${clear} 70%), radial-gradient(90% 70% at 100% 100%, ${h2}99, ${clear} 70%), ${base}`;
  if (t.bg === "embers") return `radial-gradient(2px 2px at 20% 70%, ${hex}, transparent), radial-gradient(2px 2px at 60% 50%, ${hex}, transparent), radial-gradient(1.5px 1.5px at 80% 80%, ${hex}, transparent), radial-gradient(1.5px 1.5px at 40% 35%, ${hex}, transparent), linear-gradient(${t.dir === "top" ? "180deg" : "0deg"}, ${hex}aa, ${h2}55 45%, ${clear} 85%), ${base}`;
  if (t.bg === "pulse") return `radial-gradient(120% 80% at 50% 110%, ${hex}dd, ${clear} 70%), radial-gradient(2px 2px at 30% 60%, ${hex}, transparent), radial-gradient(2px 2px at 70% 40%, ${hex}, transparent), ${base}`;
  if (t.bg === "plain") return base;
  if (t.bg === "glow") return `radial-gradient(130% 95% at ${pos}, ${hex}${dark ? "8c" : "5e"}, ${clear} 70%), ${base}`;
  if (t.bg === "vivid") return dark ? `linear-gradient(${deg}, ${hex}, ${hex}66 55%, ${base})` : `linear-gradient(${deg}, ${hex}bb, ${hex}33 60%, ${base})`;
  return `linear-gradient(${deg}, ${hex}${dark ? "8c" : "61"}, ${clear} 75%), ${base}`;
}
function tileHtml(id, name, sub, t, hex, on, extra = "", tag = "button") {
  const dark = t.mode !== "light";
  return `<${tag} class="ttile ${on ? "on" : ""} ${dark ? "dk" : "lt"}" data-preset="${id}" role="radio" aria-checked="${on}" style="--tbg:${tileBg(t, hex)};--tc:${hex}">
    <span class="tbars" aria-hidden="true"><i></i><s></s></span><b>${esc(name)}</b><small>${esc(sub)}</small>${extra}</${tag}>`;
}
function renderThemeTiles(t) {
  const resolved = t.mode;
  const match = p => p.t.mode === resolved && p.t.accent === t.accent && p.t.bg === t.bg && (p.t.bg === "plain" || p.t.dir === t.dir) && (p.t.font || "normal") === (t.font || "normal");
  const secrets = (S.secrets || []).map(k => SECRET_PRESETS[k]).filter(Boolean);
  const sc = $("#secretCount"); if (sc) { sc.classList.toggle("hidden", !secrets.length); sc.textContent = `\u2605 ${secrets.length} of ${Object.keys(SECRET_PRESETS).length} secret themes found` + (secrets.length === Object.keys(SECRET_PRESETS).length ? ". You found them all!" : ""); }
  const custom = t.accent === "custom";
  $("#themeGrid").innerHTML = PRESETS.concat(secrets).map(p => tileHtml(p.id, p.n, p.m, p.t, ACCENT_HEX[p.t.accent], !custom && match(p)).replace('class="ttile', SECRET_PRESETS[p.id] ? 'class="ttile secret' : 'class="ttile')).join("")
    + tileHtml("custom", "Your colour", custom ? "Click to change it" : "Any colour you pick", {mode: t.mode === "light" ? "light" : "dark", bg: t.bg === "plain" ? "gradient" : t.bg, dir: t.dir}, t.custom, custom,
      `<input type="color" id="customTile" value="${t.custom}" aria-label="Pick your colour">`, "label");
  $$("#themeGrid button[data-preset]").forEach(b => b.onclick = () => { const p = PRESETS.find(x => x.id === b.dataset.preset) || SECRET_PRESETS[b.dataset.preset]; setTheme({font: "normal", ...p.t}); });
  const ct = $("#customTile");
  ct.oninput = () => { S.theme = {...t, accent: "custom", custom: ct.value, bg: t.bg === "plain" ? "gradient" : t.bg}; applyTheme(S.theme); };
  ct.onchange = () => setTheme({accent: "custom", custom: ct.value, bg: t.bg === "plain" ? "gradient" : t.bg});
}
let themeSave;
async function setTheme(patch, quiet = false) {
  S.theme = {...THEME_DEFAULT, ...(S.theme || {}), ...patch};
  applyTheme(S.theme, !quiet); renderTheme();
  clearTimeout(themeSave);
  themeSave = setTimeout(async () => { try { S.theme = (await api("/api/theme", patch)).theme; } catch (e) { toast(e.message); } }, quiet ? 250 : 0);
}
$$("#themeMode button").forEach(b => b.onclick = () => setTheme({mode: b.dataset.mode}));
$$("[data-opt]").forEach(g => g.addEventListener("click", e => { const b = e.target.closest("button[data-v]"); if (b) setTheme({[g.dataset.opt]: g.dataset.opt === "strength" ? +b.dataset.v : b.dataset.v}); }));
$("#bgStrength").oninput = e => { const v = +e.target.value; $("#bgStrengthVal").textContent = v + "%"; document.documentElement.style.setProperty("--bgk", (v / 100).toFixed(2)); };
$("#bgStrength").onchange = e => setTheme({strength: +e.target.value}, true);
$("#themeReset").onclick = async () => {
  try { S.theme = (await api("/api/theme", {reset: true})).theme; applyTheme(S.theme, true); renderTheme(); toast("Appearance reset"); } catch (e) { toast(e.message); }
};

function renderAll() { renderHome(); renderDev(); renderTheme(); renderCrashes(); renderLoadouts(); renderCatchUp(); renderInstances(); renderNewVersion(); renderUpdateBits(); renderAppBits(); renderInventory(); renderSettings(); renderLaunchers(); updateSteps(); }

(async function init() {
  S = await api("/api/state");
  if (S.theme) applyTheme(S.theme);
  if (S.just_updated) { const ju = S.just_updated; setTimeout(() => showJustUpdated(ju), 1000); api("/api/update/dismiss_note").catch(() => {}); }
  const last = S.last || {};
  setLoader(last.loader || S.loader || "fabric");
  launcher = last.launcher || (S.launchers.find(l => l.found && l.id !== "lunar") || {}).id || null;
  renderAll();
  renderVersions(last.version);
  updateSteps();
  renderStarter();
  refreshPortCount();
  if (S.favorites.length && last.version) go("install");
  settle(); setTimeout(settle, 300);
  hideSplash();
  renderNotesDot();
})();

/* ---------- easter eggs ---------- */
function fxLayer(cls, html, ms) {
  const el = document.createElement("div"); el.className = "fx " + cls; el.setAttribute("aria-hidden", "true"); el.innerHTML = html;
  document.body.appendChild(el); if (ms) setTimeout(() => el.remove(), ms); return el;
}
function blockParty(n = 90) {
  if (REDUCED) return;
  const cols = ["rgb(var(--acc))", "rgb(var(--acc2))", "#45b97c", "#f0a43a", "#7cb8ff", "#f3f1ef", "#8a5a3c"];
  let h = "";
  for (let i = 0; i < n; i++) h += `<i style="left:${Math.random() * 100}%;--w:${6 + Math.random() * 10 | 0}px;--c:${cols[i % cols.length]};--d:${(Math.random() * .7).toFixed(2)}s;--t:${(2 + Math.random() * 1.6).toFixed(2)}s;--x:${(Math.random() * 160 - 80) | 0}px;--r:${(Math.random() * 900 - 450) | 0}deg"></i>`;
  fxLayer("party", h, 4200);
}
let weatherEl = null;
function weather(kind, ms) {
  if (weatherEl) { weatherEl.remove(); weatherEl = null; }
  if (!kind || REDUCED) return;
  let h = "";
  const n = kind === "rain" ? 110 : 70;
  for (let i = 0; i < n; i++) h += `<i style="left:${Math.random() * 100}%;--d:-${(Math.random() * (kind === "rain" ? .7 : 7)).toFixed(2)}s;--t:${(5 + Math.random() * 5).toFixed(1)}s;--x:${kind === "snow" ? (Math.random() * 80 - 40 | 0) : -30}px"></i>`;
  weatherEl = fxLayer(kind, h, ms || 0);
  if (ms) setTimeout(() => { weatherEl = null; }, ms);
}
async function unlockSecret(name, how) {
  try {
    const r = await api("/api/secret", {name});
    S.secrets = r.secrets; renderTheme();
    const title = SECRET_NAMES[name];
    toast(r.new ? `${how} You unlocked the ${title} theme. It's in Settings, under Appearance.` : `${how} You already have the ${title} theme.`);
    return r.new;
  } catch (e) { toast(e.message); }
}
function runCommand(raw) {
  const c = raw.trim().toLowerCase().replace(/\s+/g, " ");
  if (!c.startsWith("/")) return false;
  const say = m => toast(m);
  if (c === "/time set night" || c === "/time set midnight") { setTheme({mode: "dark"}); say("Set the time to night."); }
  else if (c === "/time set day" || c === "/time set noon") { setTheme({mode: "light"}); say("Set the time to day."); }
  else if (c === "/weather rain" || c === "/weather thunder") { weather("rain", 20000); say("Changing to rainy weather."); }
  else if (c === "/weather clear") { weather(null); say("Changing to clear weather."); }
  else if (c === "/gamemode creative") { blockParty(); say("Set own game mode to Creative Mode."); }
  else if (c === "/gamemode survival") { say("Set own game mode to Survival Mode. Your mods are still safe."); }
  else if (c === "/gamemode spectator") { document.documentElement.animate([{opacity: 1}, {opacity: .35}, {opacity: 1}], {duration: 2200}); unlockSecret("ghost", "Set own game mode to Spectator Mode."); }
  else if (c.startsWith("/give") && c.includes("diamond")) { blockParty(60); unlockSecret("diamond", "You got a diamond!"); }
  else if (c.startsWith("/give") && c.includes("redstone")) { document.documentElement.animate([{filter: "brightness(1)"}, {filter: "brightness(1.6) saturate(1.4)"}, {filter: "brightness(1)"}], {duration: 700, iterations: 2}); unlockSecret("redstone", "Powered up!"); }
  else if (c.startsWith("/give")) { blockParty(40); say("There are no diamonds here, but here are some blocks."); }
  else if (c === "/kill" || c === "/kill @s") { document.documentElement.animate([{filter: "brightness(1)"}, {filter: "brightness(0)"}, {filter: "brightness(1)"}], {duration: 1600}); unlockSecret("void", "ModHub fell out of the world."); }
  else if (c === "/seed") { say("Seed: [" + (Math.random() * 2 ** 53 | 0) * (Math.random() < .5 ? -1 : 1) + "]"); }
  else if (c === "/help" || c === "/?") { say("Try /time set night, /weather rain, /gamemode creative, /seed and a few more you'll have to find."); }
  else say(`Unknown command: ${raw.trim()}. Try /help.`);
  return true;
}
// up, up, down, down, left, right, left, right, B, A
(() => {
  const code = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "b", "a"]; let at = 0;
  addEventListener("keydown", e => {
    const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    at = k === code[at] ? at + 1 : (k === code[0] ? 1 : 0);
    if (at === code.length) { at = 0; blockParty(140); unlockSecret("rainbow", "Cheat code accepted!"); }
  });
})();
// click the logo five times in a row
(() => {
  const b = $(".brand"); if (!b) return; let n = 0, t;
  b.style.cursor = "default";
  b.addEventListener("click", () => {
    clearTimeout(t); t = setTimeout(() => n = 0, 1400);
    b.classList.remove("twirl"); void b.offsetWidth; b.classList.add("twirl");
    if (++n === 5) { n = 0; unlockSecret("retro", "Old-school mode found!"); }
    b.querySelector(".mark").addEventListener("animationend", () => b.classList.remove("twirl"), {once: true});
  });
})();
// night owls and big collections
(() => {
  const has = k => (S && S.secrets || []).includes(k);
  const check = () => {
    if (!S || !S.favorites) return;
    const h = new Date().getHours();
    if (h >= 2 && h < 5 && !has("nightowl")) unlockSecret("nightowl", "Still up?");
    if (S.favorites.length >= 25 && !has("golden")) unlockSecret("golden", "25 mods in your library!");
  };
  setTimeout(check, 4000); setInterval(check, 30000);
})();
(() => {
  const lab = $("#verLabel"); if (!lab) return; let n = 0, t;
  lab.addEventListener("click", e => {
    if (!(e.altKey && e.shiftKey)) { n = 0; return; }
    const onSettings = $(".nav[data-tab=settings]") && $(".nav[data-tab=settings]").classList.contains("on");
    if (!onSettings) { n = 0; return; }
    clearTimeout(t); t = setTimeout(() => n = 0, 2000);
    if (++n < 3) return; n = 0;
    const box = document.createElement("input");
    box.type = "password"; box.autocomplete = "off"; box.spellcheck = false; box.setAttribute("aria-label", "›");
    box.style.cssText = "width:100%;background:transparent;border:0;border-bottom:1px solid rgb(var(--hi) / .15);color:var(--muted);font:inherit;padding:2px 0;outline:none";
    lab.replaceWith(box); box.focus();
    const done = () => { box.replaceWith(lab); };
    box.addEventListener("blur", () => setTimeout(done, 150));
    box.addEventListener("keydown", async ev => {
      if (ev.key === "Escape") return done();
      if (ev.key !== "Enter") return;
      const code = box.value; box.value = ""; box.disabled = true;
      try {
        const r = await api("/api/secret/dev", {code});
        if (r.ok) { S.secrets = r.secrets; S.dev_mode = true; renderTheme(); renderDev(); blockParty(160); toast("Developer code accepted. Every secret theme is unlocked, and the Developer card is in Settings."); }
      } catch (e) {}
      done();
    });
  });
})();
// a little snow at the end of the year
(() => { const d = new Date(); if (d.getMonth() === 11 && d.getDate() >= 20) setTimeout(() => weather("snow", 30000), 2500); })();

/* ---------- Fluid motion trial ---------- */
const FLUID = () => document.documentElement.dataset.motion === "fluid" && !motionQuery.matches;
// big titles shrink and fade as you scroll, like an iPhone's large titles
function fluidTitle() {
  if (!FLUID()) return;
  const sec = $$("main > section").find(x => !x.classList.contains("hidden")), h1 = sec && sec.querySelector("h1");
  if (!h1) return;
  const k = Math.min(1, Math.max(0, window.scrollY / 110));
  h1.style.transform = `translateY(${(k * 10).toFixed(1)}px) scale(${(1 - k * .28).toFixed(3)})`;
  h1.style.opacity = (1 - k * .9).toFixed(3);
}
window.addEventListener("scroll", () => requestAnimationFrame(fluidTitle), {passive: true});
// cards ease in as they come into view
const FLUID_SEL = ".card, .inst, .dcard, .res, .lopt, .empty, .ttile, .starter, .results, .banner, .slot";
const flIO = "IntersectionObserver" in window ? new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return; flIO.unobserve(e.target); e.target.classList.add("fl-in"); e.target.classList.remove("fl-pre");
  setTimeout(() => { e.target.classList.remove("fl-in"); e.target.style.removeProperty("--fd"); }, 1400);
}), {threshold: .08}) : null;
function fluidReveal(root) {
  if (!FLUID() || !flIO || !root) return;
  let i = 0;
  root.querySelectorAll(FLUID_SEL).forEach(el => {
    if (el.closest(".fl-pre") || !el.offsetParent) return;
    el.classList.add("fl-pre"); el.style.setProperty("--fd", Math.min(i++, 10) * 45 + "ms"); flIO.observe(el);
  });
}
const _go = go;
go = function (tab) {
  $$("main h1").forEach(h => { h.style.transform = ""; h.style.opacity = ""; });
  _go(tab);
  if (FLUID()) requestAnimationFrame(() => fluidReveal($("#tab-" + tab)));
};
$$(".nav").forEach(b => b.onclick = () => go(b.dataset.tab));
// pop-ups slide up like sheets, and the app shrinks back behind them
const sheetMO = new MutationObserver(() => {
  const open = $$(".scrim").some(m => !m.classList.contains("hidden"));
  document.documentElement.classList.toggle("sheet-open", open && FLUID());
});
$$(".scrim").forEach(m => sheetMO.observe(m, {attributes: true, attributeFilter: ["class"]}));

/* ---------- 4.0: Home ---------- */
let homePicks = null, homePicksFor = "", modCheckRunning = false;
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
function renderHome() {
  if (!S || !$("#tab-home")) return;
  const h = new Date().getHours();
  $("#homeHello").textContent = h < 5 ? "Up late?" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  const mu = S.mod_updates || null, ups = (mu && mu.items) || [];
  const inst = (S.installs || []).filter(r => !r.export);
  const navH = $("#navHome"); if (navH) navH.textContent = ups.length ? ups.length : "";
  // live count question, asked once
  // updates
  let u = `<div class="hc-h"><div class="grow"><h3>Mod updates</h3><small>${mu ? `Checked ${esc(timeAgo(mu.at))}` : inst.length ? "Not checked yet" : ""}</small></div>${ups.length ? `<span class="n">${ups.length}</span>` : ""}</div>`;
  if (!inst.length) u += `<p class="h-empty">Install your mods once and ModHub keeps an eye on updates for them here.</p><div class="h-more"><button class="btn go" data-go="install">Install my mods</button></div>`;
  else if (modCheckRunning) u += `<p class="h-empty"><span class="spin"></span> Checking ${plural(inst.length, "instance", "instances")} for newer versions...</p>`;
  else if (!ups.length) u += `<p class="h-empty">${mu ? "Everything's up to date." : "ModHub hasn't looked for updates yet."}</p><div class="h-more"><button class="btn" id="homeCheck">Check now</button></div>`;
  else {
    u += ups.slice(0, 5).map(x => `<div class="hrow">${ico(x)}<div class="body"><div class="t">${esc(x.name)}</div><div class="s">${esc(x.instance_name)}</div></div><div class="ver">${esc(x.from)} &rarr; <b>${esc(x.to)}</b></div></div>`).join("");
    u += `<div class="h-more"><button class="btn go" id="homeUpdAll">Update all</button><button class="btn" id="homeUpdSee">See what's new${ups.length > 5 ? ` (${ups.length})` : ""}</button><button class="btn quiet" id="homeCheck">Check again</button></div>`;
  }
  $("#homeUpd").innerHTML = u;
  // instances
  const recent = inst.slice().sort((a, b) => (b.updated || "").localeCompare(a.updated || "")).slice(0, 4);
  $("#homeInst").innerHTML = `<div class="hc-h"><div class="grow"><h3>Your instances</h3><small>${inst.length ? plural(inst.length, "instance", "instances") : ""}</small></div></div>`
    + (recent.length ? recent.map(r => `<div class="hrow"><div class="ico">${esc((r.launcher_name || "?")[0])}</div><div class="body"><div class="t">${esc(r.name)}</div><div class="s">Minecraft ${esc(r.version)} with ${esc(({fabric: "Fabric", quilt: "Quilt", forge: "Forge", neoforge: "NeoForge"})[r.loader] || r.loader)}, ${esc(r.launcher_name)}</div></div><div class="ver">${esc(timeAgo(r.updated))}</div></div>`).join("")
       + `<div class="h-more"><button class="btn" data-go="instances">See all</button></div>`
      : `<p class="h-empty">Nothing installed yet.</p><div class="h-more"><button class="btn" data-go="install">Install</button></div>`);
  // recent fixes
  const fixes = (S.crashes || []).filter(c => c.autofix && (c.autofix.fixed || []).length).slice(-3).reverse();
  $("#homeFix").innerHTML = `<div class="hc-h"><div class="grow"><h3>Recent fixes</h3><small>Problems ModHub sorted out for you</small></div></div>`
    + (fixes.length ? fixes.map(c => `<div class="hrow"><div class="ico" style="color:var(--ready)">&#10003;</div><div class="body"><div class="t">${esc(c.instance || "An instance")}</div><div class="s">${plural((c.autofix.fixed || []).length, "fix", "fixes")}${c.kind === "precheck" ? " before you played" : " after a crash"}</div></div><div class="ver">${esc(timeAgo(c.at || c.time || ""))}</div></div>`).join("")
      : `<p class="h-empty">Nothing's needed fixing lately. ModHub checks your mods whenever they change.</p>`);
  // picks
  renderHomePicks();
  $("#homeCheck") && ($("#homeCheck").onclick = checkModUpdates);
  $("#homeUpdAll") && ($("#homeUpdAll").onclick = () => applyModUpdates());
  $("#homeUpdSee") && ($("#homeUpdSee").onclick = openModUpdates);
  // look for updates when they're old
  if (inst.length && !modCheckRunning && (!mu || Date.now() - Date.parse(mu.at) > 6 * 3600e3) && !renderHome.asked) { renderHome.asked = true; checkModUpdates(true); }
}
async function renderHomePicks() {
  const box = $("#homePicks"); if (!box) return;
  const v = (S.last || {}).version || ((S.versions || []).find(x => x.type === "release") || {}).v || "", ld = (S.last || {}).loader || S.loader || "fabric";
  const head = `<div class="hc-h"><div class="grow"><h3>Worth a look</h3><small>${v ? `Picked for Minecraft ${esc(v)} and the mods you have` : ""}</small></div><button class="btn quiet sm" data-go="discover">Discover</button></div>`;
  if (!S.favorites.length) { box.innerHTML = head + `<p class="h-empty">Add a few mods to your library and ModHub suggests ones that go with them.</p>`; return; }
  const key = v + "|" + ld + "|" + S.favorites.length;
  if (homePicks && homePicksFor === key) return paint();
  box.innerHTML = head + `<div class="hpicks">${Array.from({length: 4}, () => `<div class="dskel" style="height:60px"></div>`).join("")}</div>`;
  try { const d = await api("/api/discover", {kind: "mod", version: v, loader: ld}); homePicks = (d.picks && d.picks.length ? d.picks : d.popular || []).filter(m => !isFav(m)).slice(0, 6); homePicksFor = key; }
  catch (e) { box.innerHTML = head + `<p class="h-empty">Couldn't load suggestions right now.</p>`; return; }
  paint();
  function paint() {
    box.innerHTML = head + (homePicks.length ? `<div class="hpicks">${homePicks.map((m, i) => `<button class="hpick" data-hp="${i}">${ico(m)}<div class="body"><div class="t">${esc(m.name)}</div><div class="s">${esc(m.why || m.desc || "")}</div></div></button>`).join("")}</div>` : `<p class="h-empty">You've already got the popular ones. Nice.</p>`);
    $$("#homePicks [data-hp]").forEach(b => b.onclick = () => openModPage(homePicks[+b.dataset.hp]));
  }
}
async function checkModUpdates(quiet) {
  if (modCheckRunning) return;
  modCheckRunning = true; renderHome();
  try {
    const r = await follow((await api("/api/mods/updates")).job);
    S.mod_updates = r;
    if (quiet !== true) toast(r.items.length ? `${plural(r.items.length, "update", "updates")} waiting` : "Everything's up to date");
  } catch (e) { if (quiet !== true) toast(e.message); }
  modCheckRunning = false; renderHome();
}
function openModUpdates() {
  const ups = (S.mod_updates || {}).items || [];
  const by = {}; ups.forEach(x => (by[x.instance] = by[x.instance] || []).push(x));
  $("#updMBody").innerHTML = `<h2 id="updMTitle">Mod updates</h2><p class="lede">${plural(ups.length, "newer version", "newer versions")} across ${plural(Object.keys(by).length, "instance", "instances")}. Open one to see what changed.</p>`
    + Object.entries(by).map(([iid, list]) => `<div class="um-inst"><h4>${esc(list[0].instance_name)}<small>Minecraft ${esc(list[0].version)}</small><button class="btn sm" data-umi="${esc(iid)}">Update</button></h4>`
      + list.map(x => `<details class="um-mod"><summary>${ico(x)}<span class="t">${esc(x.name)}</span><span class="ver">${esc(x.from)} &rarr; <b>${esc(x.to)}</b></span></summary><div class="um-log">${x.changelog ? esc(x.changelog.replace(/!\[[^\]]*\]\([^)]*\)/g, "").replace(/[#*`]/g, "").trim()) : "No changelog for this version."}</div></details>`).join("") + `</div>`).join("")
    + `<div class="foot"><button class="btn quiet" data-close>Close</button><button class="btn go" id="umAll">Update all</button></div>`;
  openModal("#updModal");
  $("#umAll").onclick = () => { closeModals(); applyModUpdates(); };
  $$("#updMBody [data-umi]").forEach(b => b.onclick = () => { closeModals(); applyModUpdates([b.dataset.umi]); });
}
async function applyModUpdates(ids) {
  toast("Updating your mods...");
  try {
    const r = await follow((await api("/api/mods/updates/apply", ids ? {instances: ids} : {})).job);
    const n = (r.summary || []).reduce((a, x) => a + ((x.updates || []).length), 0), bad = (r.summary || []).filter(x => x.error);
    S = await api("/api/state"); renderAll();
    toast(bad.length ? `${bad[0].name}: ${bad[0].error}` : `Updated ${plural(n, "mod", "mods")}. Restart Minecraft to use them.`);
  } catch (e) { toast(e.message); }
}
$("#homeShare").onclick = () => openShare("give");
$("#libShare").onclick = () => openShare("give");

/* ---------- 4.0: sharing ---------- */
function openShare(tab) {
  $("#shareLo").innerHTML = (S.loadouts || []).map(l => `<option value="${esc(l.id)}" ${l.id === S.active_loadout ? "selected" : ""}>${esc(l.name)}</option>`).join("");
  const vs = (S.versions || []).filter(v => v.type === "release").slice(0, 40).map(v => v.v);
  $("#shareVer").innerHTML = vs.map(v => `<option>${esc(v)}</option>`).join("");
  if ((S.last || {}).version && vs.includes(S.last.version)) $("#shareVer").value = S.last.version;
  $("#shareLoader").value = (S.last || {}).loader || S.loader || "fabric";
  $("#shareSaved").textContent = ""; $("#sharePrev").innerHTML = ""; $("#shareIn").value = "";
  shareTab(tab || "give"); openModal("#shareModal"); settle();
  if ((tab || "give") === "give") loadShareCode();
}
function shareTab(t) {
  $$("[data-stab]").forEach(b => { b.classList.toggle("on", b.dataset.stab === t); b.setAttribute("aria-selected", b.dataset.stab === t); });
  $("#shareGive").classList.toggle("hidden", t !== "give"); $("#shareGet").classList.toggle("hidden", t !== "get"); settle();
}
$$("[data-stab]").forEach(b => b.onclick = () => { shareTab(b.dataset.stab); if (b.dataset.stab === "give") loadShareCode(); });
async function loadShareCode() {
  $("#shareCode").value = ""; $("#shareNote").textContent = "";
  try {
    const r = await api("/api/share/code", {loadout: $("#shareLo").value});
    $("#shareCode").value = r.code;
    $("#shareNote").textContent = `${plural(r.count, "mod", "mods")} from ${r.name}.` + (r.own ? ` ${plural(r.own, "file you added yourself isn't", "files you added yourself aren't")} included. Share a .mrpack to bring them along.` : "");
  } catch (e) { $("#shareNote").textContent = e.message; }
}
$("#shareLo").onchange = loadShareCode;
$("#shareCopy").onclick = async () => { const t = $("#shareCode").value; if (!t) return; try { await navigator.clipboard.writeText(t); } catch (e) { $("#shareCode").select(); document.execCommand("copy"); } toast("Share code copied"); };
function savedLine(r) {
  $("#shareSaved").innerHTML = `Saved <b>${esc(r.file)}</b> in your ${esc(r.where)} folder. <button class="linkbtn" id="shareShow">Show it</button>`;
  $("#shareShow").onclick = () => api("/api/open", {path: r.path}).catch(e => toast(e.message));
}
$("#shareFile").onclick = async () => { try { savedLine(await api("/api/share/file", {loadout: $("#shareLo").value})); } catch (e) { toast(e.message); } };
$("#shareMr").onclick = async () => {
  const b = $("#shareMr"); b.disabled = true; $("#shareSaved").innerHTML = `<span class="spin"></span> Making the modpack...`;
  try {
    const r = await follow((await api("/api/share/mrpack", {loadout: $("#shareLo").value, version: $("#shareVer").value, loader: $("#shareLoader").value})).job);
    savedLine(r);
    if ((r.left_out || []).length) $("#shareSaved").insertAdjacentHTML("beforeend", `<br>Left out because they aren't out for ${esc($("#shareVer").value)} yet: ${r.left_out.map(x => esc(x.name)).join(", ")}.`);
  } catch (e) { $("#shareSaved").textContent = e.message; }
  b.disabled = false;
};
$("#shareOpen").onclick = async () => {
  const code = $("#shareIn").value.trim(); if (!code) return $("#shareIn").focus();
  $("#sharePrev").innerHTML = `<p class="help"><span class="spin"></span> Looking up the mods...</p>`;
  try { showSharePreview(await api("/api/share/preview", {code})); } catch (e) { $("#sharePrev").innerHTML = `<p class="help" style="color:var(--missing)">${esc(e.message)}</p>`; }
};
$("#sharePick").onclick = () => $("#shareFileIn").click();
$("#shareFileIn").onchange = async e => {
  const file = e.target.files[0]; e.target.value = ""; if (!file) return;
  $("#sharePrev").innerHTML = `<p class="help"><span class="spin"></span> Reading ${esc(file.name)}...</p>`;
  try {
    const r = await fetch("/api/local/upload", {method: "POST", headers: {"X-Token": T, "X-Filename": encodeURIComponent(file.name)}, body: file});
    const j = await r.json().catch(() => ({error: r.statusText}));
    if (!r.ok) throw new Error(j.error || r.statusText);
    if (!j.share) throw new Error("That file isn't a shared modpack.");
    showSharePreview(j.share);
  } catch (err) { $("#sharePrev").innerHTML = `<p class="help" style="color:var(--missing)">${esc(err.message)}</p>`; }
};
function showSharePreview(p) {
  const active = (S.loadouts || []).find(l => l.id === S.active_loadout) || {name: "your library"};
  const n = p.items.length + (p.own || []).length;
  $("#sharePrev").innerHTML = `<h4 class="share-h">${esc(p.name)}</h4><p class="help">${plural(n, "item", "items")}${p.missing ? `. ${plural(p.missing, "mod couldn't", "mods couldn't")} be found on Modrinth and won't be added` : ""}.</p>
    <div class="sp-list">${p.items.map(m => `<div class="hrow">${ico(m)}<div class="body"><div class="t">${esc(m.name)}</div></div></div>`).join("")}${(p.own || []).map(f => `<div class="hrow"><div class="ico">+</div><div class="body"><div class="t">${esc(f)}</div><div class="s">Included file</div></div></div>`).join("")}</div>
    <div class="sp-mode"><label class="check"><input type="radio" name="spMode" value="new" checked> Add as a new loadout called <input id="spName" value="${esc(p.name)}" maxlength="40" style="margin-left:6px;width:200px"></label>
    <label class="check"><input type="radio" name="spMode" value="add"> Add to ${esc(active.name)}</label></div>
    <div class="actions"><button class="btn go" id="spGo">Add to ModHub</button></div>`;
  $("#spGo").onclick = async () => {
    try {
      const mode = ($("input[name=spMode]:checked") || {}).value || "new";
      const r = await api("/api/share/import", {token: p.token, mode, name: $("#spName").value.trim()});
      const {added, own, loadout, ...st} = r; S = st; renderAll(); closeModals(); go("library");
      toast(`Added ${plural(added + own, "item", "items")} to ${loadout}`);
    } catch (e) { toast(e.message); }
  };
}


/* ---------- announcements (everyone) ---------- */
function renderNotice(n, preview) {
  n = n || (S && S.notice);
  const box = $("#noticeBox"); if (!box) return;
  if (!n || !n.text) { box.innerHTML = ""; return; }
  box.innerHTML = `<div class="notice ${preview ? "preview" : ""}" role="status"><span class="ni"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11v2a1 1 0 0 0 1 1h2l5 4V6L6 10H4a1 1 0 0 0-1 1z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/></svg></span>
    <div class="grow">${esc(n.text)}${preview ? ` <b style="color:var(--muted)">(preview, only you can see this)</b>` : ""}</div>
    ${safeUrl(n.link) ? `<a class="btn sm" href="${esc(n.link)}" target="_blank" rel="noopener">Learn more</a>` : ""}<button class="btn sm quiet" id="noticeX">${preview ? "Close preview" : "Dismiss"}</button></div>`;
  $("#noticeX").onclick = async () => { if (!preview) { await api("/api/notice/dismiss").catch(() => {}); S.notice = null; } renderNotice(); };
}

/* ---------- developer options ---------- */
const DEV_LABELS = {stats: "Live stats", history: "Longer live history", downloads: "Download breakdown", beta: "Beta channel",
                    versions: "Version picker", previews: "Previews", announce: "Announcements", debug: "Debug tools"};
let devTimer = null, devView = "hour";
function renderDev() {
  const card = $("#devCard"); if (!card || !S) return;
  card.classList.toggle("hidden", !S.dev_mode);
  clearInterval(devTimer);
  renderNotice();
  if (!S.dev_mode) return;
  const f = S.dev_features || {};
  $("#devSwitches").innerHTML = Object.entries(DEV_LABELS).map(([k, l]) => `<label><input type="checkbox" data-devf="${k}" ${f[k] ? "checked" : ""}> ${l}</label>`).join("");
  $$("#devSwitches [data-devf]").forEach(c => c.onchange = async () => {
    try { S.dev_features = (await api("/api/dev/features", {set: {[c.dataset.devf]: c.checked}})).dev_features; renderDev();
      if (c.dataset.devf === "beta") toast(c.checked ? "Beta channel on. ModHub now gets test versions from the beta branch." : "Beta channel off. Back to public updates."); }
    catch (e) { toast(e.message); }
  });
  const sec = (k, title, inner) => f[k] ? `<div class="dev-sec" id="dev-${k}"><h4>${title}</h4>${inner}</div>` : "";
  const versions = (S.changelog || []).map(e => e.version);
  $("#devBody").innerHTML =
    sec("stats", `Live${f.history ? `<div class="seg" role="tablist"><button data-dv="hour" class="${devView === "hour" ? "on" : ""}">Hour</button><button data-dv="day" class="${devView === "day" ? "on" : ""}">Day</button><button data-dv="week" class="${devView === "week" ? "on" : ""}">Week</button></div>` : ""}`,
      `<div class="dev-stats"><div><span class="dev-n" id="devLive">-</span><span class="dev-l">using ModHub right now</span></div><div><span class="dev-n" id="devDl">-</span><span class="dev-l">downloads, all versions</span></div><div><span class="dev-n" id="devLatest">-</span><span class="dev-l" id="devLatestL">downloads of the newest version</span></div></div>
       <div class="dev-spark" id="devSpark"></div><div class="dev-labels" id="devLabels"></div><p class="help" id="devNote"></p>`)
    + sec("downloads", "Downloads by platform", `<div id="devDls"><p class="help"><span class="spin"></span> Loading...</p></div>`)
    + sec("beta", "Beta channel", `<p class="help">Your copy checks the <b>beta</b> branch on GitHub for test versions, so you get them before anyone else. ${S.update_last_check ? `Last check: ${esc(S.update_last_check.status === "error" ? "didn't work (" + S.update_last_check.message + ")" : S.update_last_check.status === "downloaded" ? "downloaded " + S.update_last_check.version : "up to date")}.` : ""}</p><div class="dev-row"><button class="btn" id="devBetaCheck">Check the beta branch now</button></div>`)
    + sec("versions", "Version picker", `<p class="help">Install any version of ModHub. ModHub restarts on it.${S.pinned ? " <b>You're on a version you picked</b>, so the ModHub app won't swap it for its own." : ""}</p><div class="dev-row"><select id="devVerSel"><option>Loading...</option></select><button class="btn go" id="devVerGo">Install</button>${S.pinned ? `<button class="btn quiet" id="devUnpin">Back to normal updates</button>` : ""}</div><p class="help" id="devVerNote"></p>`)
    + sec("previews", "Previews", `<p class="help">See what players see. These only show on your screen and change nothing.</p><div class="dev-row"><select id="devPvVer">${versions.map(v => `<option>${esc(v)}</option>`).join("")}</select><button class="btn" id="pvWn">What's new</button><button class="btn" id="pvFix">Fix banner</button><button class="btn" id="pvMc">New Minecraft version</button><button class="btn" id="pvUpd">Mod updates</button><button class="btn" id="pvNotice">Announcement</button></div>`)
    + sec("announce", "Announcement", `<p class="help">Shows at the top of everyone's ModHub within about 30 minutes, until they dismiss it.${S.notice ? ` Live now: "${esc(S.notice.text)}"` : ""}</p>
       <div class="dev-form"><textarea id="anText" rows="2" maxlength="280" placeholder="Minecraft 26.5 support is coming this week!"></textarea>
       <div class="dev-row"><input id="anLink" placeholder="Link (optional, https://...)" style="flex:1"><label class="help" style="margin:0">Hide after <input type="date" id="anUntil"></label></div>
       ${S.dev_has_token ? `<p class="help" style="margin:0">GitHub access is set up. <button class="linkbtn" id="anTokChange">Change token</button></p><input id="anToken" type="password" class="hidden" placeholder="New GitHub token">` : `<input id="anToken" type="password" placeholder="GitHub access token (needed once)">`}
       <div class="dev-row"><button class="btn" id="anPreview">Preview here</button><button class="btn go" id="anPublish">Publish to everyone</button>${S.notice ? `<button class="btn quiet" id="anRemove">Remove the live one</button>` : ""}</div><p class="help" id="anOut"></p></div>`)
    + sec("debug", "Debug tools", `<div class="dev-row"><button class="btn" data-dbg="log">Show log</button><button class="btn" data-dbg="config">Show settings file</button><button class="btn" data-dbg="clear">Clear caches</button><button class="btn" data-dbg="replay">Replay first-run screens</button></div><pre class="dev-out hidden" id="dbgOut"></pre>`);
  wireDev();
}
function wireDev() {
  const f = S.dev_features || {};
  if (f.stats) { loadDev(); devTimer = setInterval(() => { if (!$("#tab-settings").classList.contains("hidden")) loadDev(); }, 60000); }
  $$("[data-dv]").forEach(b => b.onclick = () => { devView = b.dataset.dv; $$("[data-dv]").forEach(x => x.classList.toggle("on", x === b)); loadDev(); });
  if (f.downloads) api("/api/dev/downloads").then(d => {
    const n = x => Number(x).toLocaleString();
    $("#devDls").innerHTML = `<table class="dev-table"><tr><th>Version</th><th>Windows</th><th>Mac</th><th>Linux</th><th>Total</th></tr>`
      + d.versions.map(r => `<tr><td>${esc(r.version)}</td><td>${n(r.windows)}</td><td>${n(r.mac)}</td><td>${n(r.linux)}</td><td>${n(r.windows + r.mac + r.linux)}</td></tr>`).join("")
      + `<tr><th>All versions</th><th>${n(d.total.windows)}</th><th>${n(d.total.mac)}</th><th>${n(d.total.linux)}</th><th>${n(d.all)}</th></tr></table>`;
  }).catch(e => { $("#devDls").innerHTML = `<p class="help">${esc(e.message)}</p>`; });
  if ($("#devBetaCheck")) $("#devBetaCheck").onclick = async () => { try { const r = await api("/api/update/check"); S.update = r.update; if (r.update_last_check) S.update_last_check = r.update_last_check; renderUpdateBits(); renderDev(); toast(r.update ? `ModHub ${r.update.version} is ready to install` : "No newer version on the beta branch"); } catch (e) { toast(e.message); } };
  if (f.versions) api("/api/dev/versions").then(d => {
    $("#devVerSel").innerHTML = d.versions.map(v => `<option value="${esc(v.sha)}" data-v="${esc(v.version)}" ${v.version === d.current ? "selected" : ""}>ModHub ${esc(v.version)}${v.version === d.current ? " (current)" : ""}, ${esc(v.date)}</option>`).join("");
  }).catch(e => { $("#devVerNote").textContent = e.message; });
  if ($("#devVerGo")) $("#devVerGo").onclick = async () => {
    const o = $("#devVerSel").selectedOptions[0]; if (!o || !o.value) return;
    if (!confirmDanger(`Install ModHub ${o.dataset.v}? ModHub restarts on it.`)) return;
    $("#devVerNote").innerHTML = `<span class="spin"></span> Installing ModHub ${esc(o.dataset.v)}...`;
    try { await follow((await api("/api/dev/versions/install", {sha: o.value, version: o.dataset.v})).job);
      document.body.innerHTML = `<main style="padding:60px"><h1>Switching to ModHub ${esc(o.dataset.v)}</h1><p class="lede">ModHub reopens in a moment. You can close this window.</p></main>`;
      setTimeout(() => window.close(), 2000);
    } catch (e) { $("#devVerNote").textContent = e.message; }
  };
  if ($("#devUnpin")) $("#devUnpin").onclick = async () => { await api("/api/dev/versions/unpin"); S.pinned = false; await api("/api/update/check").catch(() => {}); toast("Back to normal updates. The newest version installs next time you open ModHub."); renderDev(); };
  if ($("#pvWn")) {
    $("#pvWn").onclick = () => { const v = $("#devPvVer").value, i = (S.changelog || []).findIndex(e => e.version === v), prev = (S.changelog[i + 1] || {}).version || v; showJustUpdated({from: prev, to: v}); };
    $("#pvFix").onclick = () => { S.crashes = (S.crashes || []).concat([{id: "preview", install_id: "preview", kind: "precheck", instance: "Preview instance", at: new Date().toISOString(), file: "", autofix: {status: "fixed", fixed: ["Turned off the extra copy of Sodium, kept sodium-26.4.jar.", "Added Fabric API."], still: []}}]); renderCrashes(); go("home"); window.scrollTo(0, 0); setTimeout(() => { S.crashes = S.crashes.filter(c => c.id !== "preview"); }, 100); };
    $("#pvMc").onclick = () => { const was = S.new_version; S.new_version = "99.1"; renderNewVersion(); go("home"); window.scrollTo(0, 0); setTimeout(() => { S.new_version = was; }, 100); toast("Showing a pretend Minecraft 99.1. It goes away when you refresh."); };
    $("#pvUpd").onclick = () => { const was = S.mod_updates; S.mod_updates = {at: new Date().toISOString(), items: [{instance: "x", instance_name: "Preview instance", version: "26.4", name: "Sodium", icon: "", from: "0.9.2", to: "0.9.3", changelog: "Fixes a crash in the Nether.\nAbout 15% more FPS in caves."}, {instance: "x", instance_name: "Preview instance", version: "26.4", name: "Iris Shaders", icon: "", from: "1.11.7", to: "1.12.1", changelog: "Better shadows."}]}; go("home"); renderHome(); openModUpdates(); setTimeout(() => { S.mod_updates = was; }, 200); };
    $("#pvNotice").onclick = () => { renderNotice({text: ($("#anText") && $("#anText").value.trim()) || "This is how an announcement looks.", link: ($("#anLink") && $("#anLink").value.trim()) || ""}, true); go("home"); window.scrollTo(0, 0); };
  }
  if ($("#anPreview")) {
    $("#anPreview").onclick = () => { const t = $("#anText").value.trim(); if (!t) return $("#anText").focus(); renderNotice({text: t, link: $("#anLink").value.trim()}, true); window.scrollTo({top: 0, behavior: "smooth"}); };
    if ($("#anTokChange")) $("#anTokChange").onclick = () => $("#anToken").classList.remove("hidden");
    const publish = async (text) => {
      $("#anOut").innerHTML = `<span class="spin"></span> Publishing...`;
      try { const r = await api("/api/dev/notice", {text, link: $("#anLink").value.trim(), until: $("#anUntil").value, token: $("#anToken").value.trim()});
        S.notice = r.notice; S.dev_has_token = true; renderDev(); toast(text ? "Published. Everyone sees it within about 30 minutes." : "Removed the announcement."); }
      catch (e) { $("#anOut").textContent = e.message; }
    };
    $("#anPublish").onclick = () => { const t = $("#anText").value.trim(); if (!t) return $("#anText").focus(); if (confirmDanger("Show this message to everyone who uses ModHub?")) publish(t); };
    if ($("#anRemove")) $("#anRemove").onclick = () => publish("");
  }
  $$("[data-dbg]").forEach(b => b.onclick = async () => {
    try { const r = await api("/api/dev/debug", {action: b.dataset.dbg}); const o = $("#dbgOut"); o.textContent = r.text; o.classList.remove("hidden");
      if (b.dataset.dbg === "replay") { try { localStorage.removeItem(SEEN_KEY); } catch (e) {} S = await api("/api/state"); renderAll(); }
    } catch (e) { toast(e.message); }
  });
}
function confirmDanger(msg) { return window.confirm(msg); }
async function loadDev() {
  const f = S.dev_features || {}, num = n => n == null ? "-" : Number(n).toLocaleString();
  try {
    const d = await api("/api/dev/stats");
    $("#devLive").textContent = d.reachable ? num(d.live) : "-";
    $("#devDl").textContent = num(d.downloads);
    $("#devLatest").textContent = d.latest ? num(d.latest.downloads) : "-";
    $("#devLatestL").textContent = d.latest ? `downloads of ${d.latest.tag}` : "downloads of the newest version";
    let vals = d.history, labels = [], note = "The last hour, 5 minutes at a time.";
    if (f.history && devView !== "hour") {
      const h = await api("/api/dev/history", {view: devView}); vals = h.values; labels = h.labels;
      note = devView === "day" ? "The last 24 hours. Each bar counts the copies open during that hour." : "The last 7 days. Each bar counts the copies open that day.";
    }
    const max = Math.max(1, ...vals.filter(x => x != null));
    $("#devSpark").innerHTML = vals.map((x, i) => x == null ? `<i class="gap" style="height:4px"></i>` : `<i style="height:${Math.max(4, x / max * 64)}px" title="${labels[i] ? esc(labels[i]) + ": " : ""}${x}"></i>`).join("");
    $("#devLabels").innerHTML = labels.length ? `<span>${esc(labels[0])}</span><span>${esc(labels[labels.length - 1])}</span>` : "";
    $("#devNote").textContent = d.reachable ? `${note} Updated ${timeAgo(d.at)}.` : "Couldn't reach the live counter right now.";
  } catch (e) { if ($("#devNote")) $("#devNote").textContent = e.message; }
}
$("#devLeave").onclick = async () => { await api("/api/dev/leave"); S.dev_mode = false; renderDev(); toast("Left developer mode. Your developer code brings it back, with the same options."); };
</script>
</body>
</html>
'''

if __name__ == "__main__":
    main()
