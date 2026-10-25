#!/usr/bin/env python3
"""Minimal MCP stdio server for the NX 2512 bridge."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


NX_INSTALL_NAMES = ("NX 2512", "NX2512", "Siemens NX 2512", "NX")
DEFAULT_PROJECT_ROOT = Path.home() / "Documents" / "Codex" / "NX2512"
DEFAULT_LIVE_PORT = 25121
DEFAULT_AUTO_LAUNCH_TIMEOUT_SECONDS = 120


def plugin_root() -> Path:
    env_root = os.environ.get("NX2512_PLUGIN_ROOT")
    if env_root:
        path = Path(env_root)
        if path.exists():
            return path.resolve()
    return Path(__file__).resolve().parents[1]


ROOT = plugin_root()
BRIDGE = ROOT / "scripts" / "nx_bridge.ps1"
LIVE_CLI = ROOT / "scripts" / "nx_live_cli.ps1"
LIVE_CLIENT = ROOT / "scripts" / "dotnet_bridge" / "bin" / "NXCodexLiveBridgeClient.exe"
LAUNCH_NX = ROOT / "scripts" / "launch_nx_with_plugin.ps1"
START_LIVE_BRIDGE = ROOT / "scripts" / "start_live_bridge_via_ui.ps1"


TOOLS = [
    {
        "name": "nx_route_intent",
        "description": (
            "Classify a CAD request before generating NXOpen journals. "
            "Use this when the prompt mentions 建模/modeling/model/features or 仿真/simulation/CAE/FEA, "
            "so Codex selects the correct NXOpen module route."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The user request or task description to classify.",
                }
            },
        },
    },
    {
        "name": "nx_prepare_session",
        "description": (
            "Ensure NX is online, classify the prompt, enter the matching NX module when possible, "
            "and return current Work/Display Part state before journal generation. "
            "For modeling, the response includes a history-preserving feature plan policy so the Part Navigator "
            "looks like human-authored NX modeling steps."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": {"type": "string"},
                "auto_launch": {
                    "type": "boolean",
                    "description": "Start NX automatically when no visible NX process is running. Defaults to true.",
                },
                "launch_timeout_seconds": {"type": "integer"},
                "nx_root": {"type": "string"},
            },
        },
    },
    {
        "name": "nx_modeling_plan_template",
        "description": (
            "Return the required history-preserving modeling plan schema and NXOpen journal rules. "
            "Use this before generating modeling journals when the user expects editable, human-readable "
            "Part Navigator steps on the left side of NX."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The user's modeling request, used only to echo context in the returned plan shell.",
                },
                "part_name": {
                    "type": "string",
                    "description": "Optional short part name used in suggested feature names.",
                },
            },
        },
    },
    {
        "name": "nx_status",
        "description": "Check local Siemens NX 2512 paths and running NX processes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nx_root": {
                    "type": "string",
                    "description": "Optional Siemens NX 2512 root path.",
                }
            },
        },
    },
    {
        "name": "nx_run_journal",
        "description": "Run an NXOpen Python journal through NX run_journal.exe.",
        "inputSchema": {
            "type": "object",
            "required": ["journal_path"],
            "properties": {
                "journal_path": {"type": "string"},
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional arguments passed after -args.",
                },
                "nx_root": {"type": "string"},
            },
        },
    },
    {
        "name": "nx_create_part",
        "description": "Create and save a new NX part file.",
        "inputSchema": {
            "type": "object",
            "required": ["part_path"],
            "properties": {
                "part_path": {"type": "string"},
                "nx_root": {"type": "string"},
            },
        },
    },
    {
        "name": "nx_open_part",
        "description": "Open an existing NX part file.",
        "inputSchema": {
            "type": "object",
            "required": ["part_path"],
            "properties": {
                "part_path": {"type": "string"},
                "nx_root": {"type": "string"},
            },
        },
    },
    {
        "name": "nx_live_ping",
        "description": "Ping the .NET live bridge started from the visible NX window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "auto_launch": {
                    "type": "boolean",
                    "description": "Start NX automatically when no visible NX process is running. Defaults to true.",
                },
                "launch_timeout_seconds": {"type": "integer"},
            },
        },
    },
    {
        "name": "nx_live_status",
        "description": "Read Work Part and Display Part from the visible NX window through the .NET live bridge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "auto_launch": {
                    "type": "boolean",
                    "description": "Start NX automatically when no visible NX process is running. Defaults to true.",
                },
                "launch_timeout_seconds": {"type": "integer"},
            },
        },
    },
    {
        "name": "nx_live_module_list",
        "description": "List locally installed NXOpen modules and verify core module availability.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nx_root": {
                    "type": "string",
                    "description": "Optional Siemens NX 2512 root path.",
                }
            },
        },
    },
    {
        "name": "nx_live_create_modeling_part",
        "description": "Create a new modeling part in the already open NX window through the .NET live bridge. Prefer for 建模/modeling/model creation tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "part_path": {"type": "string"},
                "save": {"type": "boolean"},
                "allow_overwrite": {"type": "boolean"},
                "auto_launch": {"type": "boolean"},
                "launch_timeout_seconds": {"type": "integer"},
            },
        },
    },
    {
        "name": "nx_live_create_block",
        "description": "Create a block feature in the current Work Part of the visible NX window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "length": {"type": "number"},
                "width": {"type": "number"},
                "height": {"type": "number"},
                "save": {"type": "boolean"},
                "auto_launch": {"type": "boolean"},
                "launch_timeout_seconds": {"type": "integer"},
            },
        },
    },
    {
        "name": "nx_live_run_python",
        "description": "Run a reviewed Python script file inside the visible NX window through NX Session.Execute. For 建模/modeling use NXOpen.Features; for 仿真/simulation/CAE use NXOpen.CAE.",
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string"},
                "params_json": {"type": "string"},
                "allow_external": {"type": "boolean"},
                "allow_dangerous": {"type": "boolean"},
                "delete_after_run": {"type": "boolean"},
                "stage_name": {"type": "string"},
                "auto_launch": {"type": "boolean"},
                "launch_timeout_seconds": {"type": "integer"},
            },
        },
    },
    {
        "name": "nx_live_run_script_file",
        "description": "Backward-compatible alias for nx_live_run_python.",
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string"},
                "params_json": {"type": "string"},
                "allow_external": {"type": "boolean"},
                "allow_dangerous": {"type": "boolean"},
                "delete_after_run": {"type": "boolean"},
                "stage_name": {"type": "string"},
                "auto_launch": {"type": "boolean"},
                "launch_timeout_seconds": {"type": "integer"},
            },
        },
    },
]


_FRAMING = {"mode": "content-length"}


def read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if line == b"":
            return None
        line = line.strip()
        if not line:
            break
        if not headers and line[:1] in (b"{", b"["):
            _FRAMING["mode"] = "ndjson"
            try:
                return json.loads(line.decode("utf-8"))
            except Exception:
                return None
        key, _, value = line.decode("ascii", "replace").partition(":")
        headers[key.lower()] = value.strip()

    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))


def write_message(payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if _FRAMING["mode"] == "ndjson":
        sys.stdout.buffer.write(body + b"\n")
    else:
        sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
        sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def normalize_nx_root(candidate: Any = None) -> Path | None:
    if not candidate:
        return None

    path = Path(str(candidate)).expanduser()
    if not path.exists():
        return None

    resolved = path.resolve()
    if resolved.is_dir():
        if resolved.name.casefold() == "nxbin":
            return resolved.parent
        if (
            (resolved / "run_journal.exe").exists()
            or (resolved / "ugraf.exe").exists()
            or (resolved / "managed" / "NXOpen.dll").exists()
        ):
            return resolved.parent
        return resolved

    if resolved.name.casefold() in {"run_journal.exe", "ugraf.exe", "nxopen.dll"}:
        parent = resolved.parent
        if parent.name.casefold() == "managed":
            parent = parent.parent
        if parent.name.casefold() == "nxbin":
            return parent.parent

    return None


def fixed_drive_roots() -> list[Path]:
    if sys.platform != "win32":
        return [Path("/")]

    try:
        import ctypes

        mask = ctypes.windll.kernel32.GetLogicalDrives()
        roots: list[Path] = []
        for index in range(26):
            if mask & (1 << index):
                root = Path(f"{chr(65 + index)}:\\")
                if root.exists():
                    roots.append(root)
        return roots
    except Exception:
        return [Path(f"{letter}:\\") for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{letter}:\\").exists()]


def registry_nx_candidates() -> list[str]:
    if sys.platform != "win32":
        return []

    try:
        import winreg
    except Exception:
        return []

    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    candidates: list[str] = []
    for hive, key_path in roots:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                count = winreg.QueryInfoKey(key)[0]
                for index in range(count):
                    try:
                        sub_name = winreg.EnumKey(key, index)
                        with winreg.OpenKey(key, sub_name) as sub_key:
                            values: dict[str, str] = {}
                            for value_name in ("DisplayName", "InstallLocation", "DisplayIcon"):
                                try:
                                    values[value_name] = str(winreg.QueryValueEx(sub_key, value_name)[0])
                                except OSError:
                                    pass
                            display = values.get("DisplayName", "")
                            install = values.get("InstallLocation", "")
                            if (
                                "NX" in display.upper()
                                or "DESIGNCENTER" in display.upper()
                                or "\\SIEMENS\\" in install.upper()
                            ):
                                if install:
                                    candidates.append(install)
                                icon = values.get("DisplayIcon")
                                if icon:
                                    candidates.append(str(Path(icon.strip('"')).parent))
                    except OSError:
                        continue
        except OSError:
            continue
    return candidates


def common_nx_candidates() -> list[str]:
    candidates: list[str] = []
    for name in ("DC2512_ROOT", "DC2512_BIN", "NX2512_ROOT", "UGII_BASE_DIR", "UGII_ROOT_DIR", "NX_ROOT", "NXBIN", "SIEMENS_NX_ROOT"):
        value = os.environ.get(name)
        if value:
            candidates.append(value)

    bases: list[Path] = []
    for name in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(name)
        if value:
            bases.append(Path(value) / "Siemens")

    for drive in fixed_drive_roots():
        bases.extend(
            [
                drive / "Program Files" / "Siemens",
                drive / "Program Files (x86)" / "Siemens",
                drive / "Siemens",
            ]
        )

    candidates.extend(registry_nx_candidates())
    seen_bases: set[str] = set()
    for base in bases:
        key = str(base).casefold()
        if key in seen_bases:
            continue
        seen_bases.add(key)
        candidates.append(str(base))
        for install_name in NX_INSTALL_NAMES:
            candidates.append(str(base / install_name))
            candidates.append(str(base / install_name / "NXBIN"))
        if base.exists():
            try:
                for child in base.iterdir():
                    if child.is_dir() and (
                        child.name.upper().startswith("NX")
                        or child.name.upper().startswith("SIEMENS NX")
                        or child.name.upper().startswith("DESIGNCENTER")
                    ):
                        candidates.append(str(child))
            except OSError:
                pass
    return candidates


def check_nx_root(root: Path, require: str) -> bool:
    checks = {
        "run_journal": root / "NXBIN" / "run_journal.exe",
        "managed": root / "NXBIN" / "managed" / "NXOpen.dll",
        "ugraf": root / "NXBIN" / "ugraf.exe",
        "any": root / "NXBIN",
    }
    return checks.get(require, checks["any"]).exists()


def global_nx_search(require: str) -> list[Path]:
    if os.environ.get("NX2512_SKIP_GLOBAL_SEARCH", "").casefold() in {"1", "true", "yes", "on"}:
        return []

    roots: list[Path] = []
    for drive in fixed_drive_roots():
        visited = 0
        for current, dirs, _files in os.walk(drive, topdown=True):
            visited += 1
            if visited > 250000:
                break
            dirs[:] = [d for d in dirs if d not in {"$Recycle.Bin", "System Volume Information", "Windows\\WinSxS"}]
            if "NXBIN" not in {d.upper(): d for d in dirs}:
                continue
            nxbin_name = {d.upper(): d for d in dirs}.get("NXBIN")
            if not nxbin_name:
                continue
            root = normalize_nx_root(Path(current) / nxbin_name)
            if root and check_nx_root(root, require):
                roots.append(root.resolve())
    return roots


def resolve_nx_root(requested: Any = None, require: str = "run_journal") -> Path:
    candidates = [requested]
    candidates.extend(common_nx_candidates())
    seen: set[str] = set()
    for item in candidates:
        root = normalize_nx_root(item)
        if root is None:
            continue
        key = str(root).lower()
        if key in seen:
            continue
        seen.add(key)
        if check_nx_root(root, require):
            return root.resolve()

    for root in global_nx_search(require):
        return root.resolve()

    raise RuntimeError("NX/DC 2512 root not found. Set DC2512_BIN, DC2512_ROOT, NX2512_ROOT, UGII_BASE_DIR, UGII_ROOT_DIR, or pass nx_root. The resolver checked environment variables, registry install locations, common Siemens folders on fixed drives, and global NXBIN search.")


def bridge_env(nx_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    nx_bin = nx_root / "NXBIN"
    runtime_root = ROOT / "nx_runtime"
    project_root = Path(env.get("NX2512_PROJECT_ROOT") or env.get("DC2512_PROJECT_ROOT") or str(DEFAULT_PROJECT_ROOT))
    env["NX2512_ROOT"] = str(nx_root)
    env["DC2512_ROOT"] = str(nx_root)
    env["DC2512_BIN"] = str(nx_bin)
    env["UGII_BASE_DIR"] = str(nx_root)
    env["UGII_ROOT_DIR"] = str(nx_bin)
    env["UGII_CUSTOM_DIRECTORY_FILE"] = str(runtime_root / "custom_dirs.dat")
    env["NX2512_PLUGIN_ROOT"] = str(ROOT)
    env["NX2512_PROJECT_ROOT"] = str(project_root)
    env["DC2512_PROJECT_ROOT"] = str(project_root)
    env["NX2512_GENERATED_SCRIPT_ROOT"] = str(ROOT / "scripts" / "generated")
    env.setdefault("NX2512_LIVE_PORT", str(DEFAULT_LIVE_PORT))
    current_path = env.get("PATH", "")
    parts = [part for part in current_path.split(os.pathsep) if part]
    if not any(part.lower().rstrip("\\/") == str(nx_bin).lower().rstrip("\\/") for part in parts):
        env["PATH"] = str(nx_bin) + os.pathsep + current_path
    return env


def nx_paths(nx_root: Path) -> dict[str, str]:
    nx_bin = nx_root / "NXBIN"
    return {
        "nxRoot": str(nx_root),
        "runJournal": str(nx_bin / "run_journal.exe"),
        "ugraf": str(nx_bin / "ugraf.exe"),
        "pythonModules": str(nx_bin / "python"),
    }


def tasklist_processes() -> list[dict[str, Any]]:
    if sys.platform == "win32":
        try:
            return win32_processes()
        except Exception:
            pass

    processes: list[dict[str, Any]] = []
    import csv
    import io

    for image_name in ("ugraf.exe", "nx.exe", "run_journal.exe"):
        completed = subprocess.run(
            ["tasklist.exe", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV", "/NH"],
            text=True,
            capture_output=True,
            timeout=5,
        )
        if completed.returncode != 0:
            continue
        text = completed.stdout.strip()
        if not text or text.startswith("INFO:"):
            continue
        for row in csv.reader(io.StringIO(text)):
            if len(row) < 2:
                continue
            try:
                pid = int(row[1])
            except ValueError:
                continue
            processes.append(
                {
                    "ProcessName": Path(row[0]).stem,
                    "Id": pid,
                    "MainWindowTitle": "",
                }
            )
    return processes


def nx_gui_processes() -> list[dict[str, Any]]:
    return [
        process
        for process in tasklist_processes()
        if str(process.get("ProcessName", "")).lower() in {"ugraf", "nx"}
    ]


def win32_processes() -> list[dict[str, Any]]:
    import ctypes
    from ctypes import wintypes

    target_names = {"ugraf.exe", "nx.exe", "run_journal.exe"}
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    processes: list[dict[str, Any]] = []

    try:
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            exe_name = entry.szExeFile
            if exe_name.lower() in target_names:
                processes.append(
                    {
                        "ProcessName": Path(exe_name).stem,
                        "Id": int(entry.th32ProcessID),
                        "MainWindowTitle": "",
                    }
                )
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)

    return processes


def quick_status(arguments: dict[str, Any]) -> str:
    nx_root = resolve_nx_root(arguments.get("nx_root"), require="run_journal")
    processes = tasklist_processes()
    result = nx_paths(nx_root)
    result["nxProcessCount"] = len(processes)
    result["nxProcesses"] = processes
    return json.dumps(result, ensure_ascii=False, indent=2)


def module_list(arguments: dict[str, Any]) -> str:
    nx_root = resolve_nx_root(arguments.get("nx_root"), require="managed")
    stubs_dir = nx_root / "UGOPEN" / "pythonStubs" / "NXOpen"
    python_dir = nx_root / "NXBIN" / "python"
    managed_dir = nx_root / "NXBIN" / "managed"

    modules: set[str] = {"NXOpen"}
    if stubs_dir.exists():
        modules.update(f"NXOpen.{path.name}" for path in stubs_dir.iterdir() if path.is_dir())
    if python_dir.exists():
        modules.update(f"NXOpen.{path.stem.replace('NXOpen_', '')}" for path in python_dir.glob("NXOpen_*.pyd"))

    all_modules = sorted(modules)
    required = {
        name: name in modules or (name == "NXOpen.UF" and (python_dir / "NXOpen_UF.pyd").exists())
        for name in ("NXOpen.Features", "NXOpen.Assemblies", "NXOpen.Drawings", "NXOpen.CAM", "NXOpen.CAE", "NXOpen.UF")
    }
    managed_assemblies = []
    if managed_dir.exists():
        managed_assemblies = sorted(
            path.name
            for path in managed_dir.glob("*.dll")
            if "Open" in path.stem or "NXOpen" in path.stem or "Snap" in path.stem
        )

    payload = {
        "ok": True,
        "result": {
            "nxRoot": str(nx_root),
            "moduleCount": len(all_modules),
            "modules": all_modules,
            "required": required,
            "sources": {
                "pythonStubs": str(stubs_dir),
                "pythonPyd": str(python_dir),
                "managed": str(managed_dir),
            },
            "managedAssemblies": managed_assemblies,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def modeling_plan_template(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = dict(arguments or {})
    prompt = str(arguments.get("prompt") or "")
    part_name = str(arguments.get("part_name") or "NX_Model").strip() or "NX_Model"
    template_path = ROOT / "scripts" / "templates" / "history_feature_model.py"
    return {
        "mode": "history_preserving_parameterized_modeling",
        "prompt": prompt,
        "partName": part_name,
        "goal": (
            "Create editable NXOpen feature history so the NX Part Navigator shows a clear, human-readable "
            "sequence of modeling steps instead of one final dumb body."
        ),
        "requiredBeforeJournal": [
            "Write a short ordered modeling plan before running code.",
            "Split complex parts into stages: reference geometry, base body, main cuts/additions, patterns, finishing features, validation.",
            "Use nx_prepare_session before each execution stage when running through MCP.",
        ],
        "partNavigatorPolicy": {
            "mustUse": [
                "NXOpen expressions for key dimensions",
                "Datum planes, datum axes, or coordinate systems when they clarify design intent",
                "Sketches for profile-driven geometry whenever practical",
                "NXOpen.Features builders such as Extrude, Revolve, Hole, EdgeBlend, Chamfer, Shell, Pattern, Boolean",
                "session.SetUndoMark(..., '<step name>') for visible human-sized operations",
                "SetName on every committed sketch, datum, expression group surrogate, and feature",
            ],
            "avoid": [
                "Creating only final faceted or dumb BRep geometry",
                "Unlabeled default feature names",
                "One huge journal stage for a complex model",
                "Deleting construction objects that explain the modeling intent unless the user asks for a clean final tree",
            ],
        },
        "namingConvention": {
            "format": "NN_Short_Action_Object",
            "examples": [
                f"01_{part_name}_Datum_CSYS",
                "02_Base_Profile_Sketch",
                "03_Base_Extrude",
                "04_Main_Bore_RevolveCut",
                "05_Mounting_Holes_Pattern",
                "06_Edge_Fillets",
                "07_Final_Check",
            ],
        },
        "planSchema": {
            "part_name": part_name,
            "units": "Millimeters",
            "design_intent": "What the model represents and which dimensions remain editable.",
            "expressions": [{"name": "base_length", "formula": "100", "unit": "mm", "purpose": "drives base feature"}],
            "steps": [
                {
                    "id": "01",
                    "navigator_name": "01_Base_Profile_Sketch",
                    "operation": "sketch",
                    "nxopen_modules": ["NXOpen", "NXOpen.Features"],
                    "inputs": ["datum plane", "expressions"],
                    "creates": ["named sketch/profile"],
                    "validation": "Sketch exists and is constrained enough for the next feature.",
                },
                {
                    "id": "02",
                    "navigator_name": "02_Base_Extrude",
                    "operation": "feature_builder",
                    "nxopen_modules": ["NXOpen", "NXOpen.Features"],
                    "inputs": ["01_Base_Profile_Sketch"],
                    "creates": ["solid feature"],
                    "validation": "Feature appears in Part Navigator and body dimensions match intent.",
                },
            ],
        },
        "journalTemplatePath": str(template_path),
        "journalTemplateUsage": "Copy the helper pattern from this file into generated journals when creating staged, named NXOpen features.",
    }


def modeling_plan_template_text(arguments: dict[str, Any] | None = None) -> str:
    return json.dumps({"ok": True, "result": modeling_plan_template(arguments)}, ensure_ascii=False, indent=2)


INTENT_ROUTES: dict[str, dict[str, Any]] = {
    "modeling": {
        "displayName": "Modeling / 建模",
        "keywords": [
            "建模",
            "模型",
            "零件",
            "实体",
            "特征",
            "草图",
            "拉伸",
            "旋转",
            "扫掠",
            "放样",
            "倒角",
            "圆角",
            "孔",
            "凸台",
            "壳",
            "曲面",
            "装配",
            "modeling",
            "model",
            "part",
            "solid",
            "feature",
            "sketch",
            "extrude",
            "revolve",
            "sweep",
            "loft",
            "block",
            "hole",
            "chamfer",
            "fillet",
            "assembly",
        ],
        "nxApplication": "UG_APP_MODELING",
        "primaryModules": ["NXOpen", "NXOpen.Features"],
        "optionalModules": ["NXOpen.Assemblies", "NXOpen.GeometricUtilities"],
        "preferredTools": ["nx_live_create_modeling_part", "nx_live_create_block", "nx_live_run_python"],
        "journalGuidance": (
            "Switch to UG_APP_MODELING and build editable, history-preserving NX features. "
            "Prefer sketches, datum objects, expressions, FeatureBuilder commits, visible undo marks, and ordered "
            "SetName calls over final dumb bodies. Every significant operation must appear as a named Part Navigator "
            "step such as 01_Base_Sketch, 02_Base_Extrude, 03_Mounting_Hole, 04_Edge_Fillets."
        ),
        "historyMode": "parameterized_feature_tree",
    },
    "simulation": {
        "displayName": "Simulation / 仿真",
        "keywords": [
            "仿真",
            "有限元",
            "有限元素",
            "分析",
            "网格",
            "求解",
            "载荷",
            "边界条件",
            "约束",
            "应力",
            "应变",
            "位移",
            "模态",
            "频率",
            "热分析",
            "结构分析",
            "后处理",
            "cae",
            "fea",
            "simulation",
            "simulate",
            "analysis",
            "mesh",
            "solver",
            "load",
            "constraint",
            "stress",
            "strain",
            "displacement",
            "modal",
            "thermal",
        ],
        "nxApplication": "CAE workflow",
        "primaryModules": ["NXOpen", "NXOpen.CAE"],
        "optionalModules": ["NXOpen.SIM", "NXOpen.Fields"],
        "preferredTools": ["nx_live_module_list", "nx_live_run_python"],
        "journalGuidance": "Import NXOpen.CAE and verify CAE module availability before creating simulation objects, meshes, loads, constraints, solves, or post-processing.",
    },
}


def route_intent(arguments: dict[str, Any]) -> str:
    prompt = str(arguments.get("prompt") or "")
    folded = prompt.casefold()
    ranked: list[tuple[int, str, list[str]]] = []
    for route_name, route in INTENT_ROUTES.items():
        matches: list[str] = []
        score = 0
        for keyword in route["keywords"]:
            key = str(keyword).casefold()
            if key and key in folded:
                matches.append(str(keyword))
                score += 3 if len(key) >= 3 else 1
        ranked.append((score, route_name, matches))

    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, best_route_name, matched_keywords = ranked[0]
    if best_score <= 0:
        response = {
            "ok": True,
            "intent": "general",
            "confidence": "low",
            "matchedKeywords": [],
            "nxApplication": None,
            "primaryModules": ["NXOpen"],
            "optionalModules": [],
            "preferredTools": ["nx_status", "nx_live_status", "nx_live_run_python"],
            "journalGuidance": "No modeling or simulation keywords were detected. Use the generic NXOpen pattern and inspect the requested operation before choosing modules.",
        }
    else:
        route = INTENT_ROUTES[best_route_name]
        response = {
            "ok": True,
            "intent": best_route_name,
            "confidence": "high" if best_score >= 6 else "medium",
            "matchedKeywords": matched_keywords,
            "nxApplication": route["nxApplication"],
            "primaryModules": route["primaryModules"],
            "optionalModules": route["optionalModules"],
            "preferredTools": route["preferredTools"],
            "journalGuidance": route["journalGuidance"],
        }
        if "historyMode" in route:
            response["historyMode"] = route["historyMode"]
            response["modelingPlanTemplate"] = modeling_plan_template({"prompt": prompt})
    return json.dumps(response, ensure_ascii=False, indent=2)


def route_intent_data(prompt: str) -> dict[str, Any]:
    return json.loads(route_intent({"prompt": prompt}))


def bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def run_bridge(action: str, arguments: dict[str, Any]) -> str:
    nx_root = resolve_nx_root(arguments.get("nx_root"), require="run_journal")
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(BRIDGE),
        "-Action",
        action,
        "-NxRoot",
        str(nx_root),
    ]

    if action == "run-journal":
        command.extend(["-JournalPath", str(arguments["journal_path"])])
        journal_args = arguments.get("args") or []
        if journal_args:
            command.append("-JournalArgs")
            command.extend(str(item) for item in journal_args)
    elif action in {"create-part", "open-part"}:
        command.extend(["-PartPath", str(arguments["part_path"])])

    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        env=bridge_env(nx_root),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=3600,
    )

    output = completed.stdout.strip()
    error = completed.stderr.strip()
    if completed.returncode != 0:
        raise RuntimeError(error or output or f"Bridge failed with exit code {completed.returncode}")
    return output or "OK"


def invoke_live_client(command: str, arguments: dict[str, Any], nx_root: Path, port: int, timeout: int = 3600) -> str:
    params_json = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
    params_base64 = base64.b64encode(params_json.encode("utf-8")).decode("ascii")
    completed = subprocess.run(
        [
            str(LIVE_CLIENT),
            "-Command",
            command,
            "-ParamsJsonBase64",
            params_base64,
            "-NxRoot",
            str(nx_root),
            "-Port",
            str(port),
        ],
        cwd=str(ROOT),
        env=bridge_env(nx_root),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )

    response_text = completed.stdout.strip()
    error_text = completed.stderr.strip()
    if completed.returncode != 0:
        raise RuntimeError(error_text or response_text or f"Live bridge failed with exit code {completed.returncode}")
    if not response_text:
        raise RuntimeError("Live bridge returned no response.")
    return response_text


def ping_live_bridge(nx_root: Path, port: int) -> bool:
    try:
        response_text = invoke_live_client("ping", {}, nx_root, port, timeout=10)
        response = json.loads(response_text)
        return bool(response.get("ok"))
    except Exception:
        return False


def auto_launch_enabled(arguments: dict[str, Any]) -> bool:
    if "auto_launch" in arguments:
        return bool(arguments.pop("auto_launch"))
    return bool_env("NX2512_AUTO_LAUNCH", True)


def launch_timeout(arguments: dict[str, Any]) -> int:
    raw = arguments.pop("launch_timeout_seconds", os.environ.get("NX2512_AUTO_LAUNCH_TIMEOUT"))
    if raw is None:
        return DEFAULT_AUTO_LAUNCH_TIMEOUT_SECONDS
    try:
        return max(10, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_AUTO_LAUNCH_TIMEOUT_SECONDS


def ensure_nx_for_live_command(nx_root: Path, port: int, enabled: bool, timeout_seconds: int) -> None:
    if not enabled or nx_gui_processes():
        return
    if not LAUNCH_NX.exists():
        raise RuntimeError(f"NX is not running and launch script is missing: {LAUNCH_NX}")

    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(LAUNCH_NX),
            "-NxRoot",
            str(nx_root),
        ],
        cwd=str(ROOT),
        env=bridge_env(nx_root),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=max(30, timeout_seconds),
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Failed to auto-launch NX.")

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if ping_live_bridge(nx_root, port):
            return
        time.sleep(3)

    raise RuntimeError(
        f"NX was auto-launched, but the live bridge did not respond on port {port} within {timeout_seconds} seconds."
    )


def start_bridge_in_existing_nx(nx_root: Path, timeout_seconds: int) -> None:
    if not START_LIVE_BRIDGE.exists():
        raise RuntimeError(f"NX is running, but live bridge is offline and recovery script is missing: {START_LIVE_BRIDGE}")

    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(START_LIVE_BRIDGE),
            "-NxRoot",
            str(nx_root),
            "-TimeoutSeconds",
            str(max(10, timeout_seconds)),
        ],
        cwd=str(ROOT),
        env=bridge_env(nx_root),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=max(30, timeout_seconds + 15),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or completed.stdout.strip()
            or "NX is running, but the live bridge could not be started automatically."
        )


def ensure_nx_online(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = dict(arguments or {})
    if not bool_env("NX2512_REQUIRE_ONLINE", True):
        return {"required": False, "online": False}

    nx_root = resolve_nx_root(arguments.get("nx_root"), require="managed")
    port = int(arguments.get("port", os.environ.get("NX2512_LIVE_PORT", DEFAULT_LIVE_PORT)))
    enabled = auto_launch_enabled(arguments)
    timeout_seconds = launch_timeout(arguments)

    if not LIVE_CLIENT.exists():
        raise RuntimeError(f"Missing live bridge client: {LIVE_CLIENT}. Run scripts\\build_dotnet_bridge.ps1.")

    if ping_live_bridge(nx_root, port):
        return {"required": True, "online": True, "launched": False, "recoveredBridge": False, "nxRoot": str(nx_root), "port": port}

    if not enabled:
        raise RuntimeError("NX live bridge is offline and auto-launch is disabled.")

    launched = False
    recovered = False
    if not nx_gui_processes():
        ensure_nx_for_live_command(nx_root, port, True, timeout_seconds)
        launched = True
    else:
        start_bridge_in_existing_nx(nx_root, timeout_seconds)
        recovered = True

    if not ping_live_bridge(nx_root, port):
        raise RuntimeError(f"NX process exists, but live bridge is not online on port {port}.")

    return {"required": True, "online": True, "launched": launched, "recoveredBridge": recovered, "nxRoot": str(nx_root), "port": port}


def prepare_session(arguments: dict[str, Any]) -> str:
    prompt = str(arguments.get("prompt") or "")
    route = route_intent_data(prompt)
    online = ensure_nx_online(arguments)

    nx_root = resolve_nx_root(arguments.get("nx_root"), require="managed")
    port = int(arguments.get("port", os.environ.get("NX2512_LIVE_PORT", DEFAULT_LIVE_PORT)))
    prepare_args = {
        "intent": route.get("intent", "general"),
        "prompt": prompt,
        "nx_application": route.get("nxApplication"),
        "primary_modules": route.get("primaryModules", ["NXOpen"]),
        "optional_modules": route.get("optionalModules", []),
    }
    response_text = invoke_live_client("prepare-session", prepare_args, nx_root, port)
    response = json.loads(response_text)
    if not response.get("ok"):
        raise RuntimeError(response.get("error") or response_text)

    payload = {
        "ok": True,
        "online": online,
        "route": route,
        "session": response.get("result"),
    }
    if route.get("intent") == "modeling":
        payload["modelingPlanPolicy"] = modeling_plan_template({"prompt": prompt})
    return json.dumps(payload, ensure_ascii=False, indent=2)


def run_live(command: str, arguments: dict[str, Any]) -> str:
    if command == "module-list":
        return module_list(arguments)

    call_args = dict(arguments)
    nx_root = resolve_nx_root(call_args.pop("nx_root", None), require="managed")
    port = int(call_args.pop("port", os.environ.get("NX2512_LIVE_PORT", DEFAULT_LIVE_PORT)))
    if not LIVE_CLIENT.exists():
        raise RuntimeError(f"Missing live bridge client: {LIVE_CLIENT}. Run scripts\\build_dotnet_bridge.ps1.")

    response_text = invoke_live_client(command, call_args, nx_root, port)

    response = json.loads(response_text)
    if not response.get("ok"):
        raise RuntimeError(response.get("error") or response_text)
    return json.dumps(response.get("result"), ensure_ascii=False, indent=2)


def tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    offline_tools = {"nx_route_intent", "nx_modeling_plan_template"}
    if name not in offline_tools:
        ensure_nx_online(arguments)
    action_map = {
        "nx_run_journal": "run-journal",
        "nx_create_part": "create-part",
        "nx_open_part": "open-part",
    }
    if name == "nx_route_intent":
        text = route_intent(arguments)
    elif name == "nx_modeling_plan_template":
        text = modeling_plan_template_text(arguments)
    elif name == "nx_prepare_session":
        text = prepare_session(arguments)
    elif name == "nx_status":
        text = quick_status(arguments)
    elif name in action_map:
        text = run_bridge(action_map[name], arguments)
    else:
        live_map = {
            "nx_live_ping": "ping",
            "nx_live_status": "status",
            "nx_live_module_list": "module-list",
            "nx_live_create_modeling_part": "create-modeling-part",
            "nx_live_create_block": "create-block",
            "nx_live_run_python": "run-python",
            "nx_live_run_script_file": "run-python",
        }
        if name not in live_map:
            raise ValueError(f"Unknown tool: {name}")
        text = run_live(live_map[name], arguments)
    return {"content": [{"type": "text", "text": text}]}


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}

    if request_id is None:
        return None

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "nx", "version": "0.1.4"},
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            result = tool_call(params.get("name", ""), params.get("arguments") or {})
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:  # noqa: BLE001 - surfaced to MCP client
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": str(exc)},
        }


def main() -> None:
    while True:
        request = read_message()
        if request is None:
            break
        response = handle(request)
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    main()
