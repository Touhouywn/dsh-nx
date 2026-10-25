---
name: nx
description: Use Siemens NX 2512 locally through NXOpen journals, the nx_bridge PowerShell CLI, or the NX MCP tools. Route 建模/modeling requests to NXOpen.Features and 仿真/simulation/CAE requests to NXOpen.CAE.
---

# NX

Use this skill when the user wants Codex to operate Siemens NX 2512, create or edit NX part files, inspect the local NX session, or translate local chat instructions into NXOpen automation.

## Preflight Rules

- Assume the local project root is `%USERPROFILE%\Documents\Codex\NX2512` unless `NX2512_PROJECT_ROOT` or `DC2512_PROJECT_ROOT` is set. Resolve the plugin root from the installed plugin directory or `NX2512_PLUGIN_ROOT`.
- Use the bundled environment setup in `scripts\nx_env.ps1`; do not hand-roll NX path setup unless debugging that script.
- Do not assume a specific local NX install path. Resolve NX/DC through `-NxRoot`, `DC2512_BIN`, `DC2512_ROOT`, `NX2512_ROOT`, `UGII_BASE_DIR`, `UGII_ROOT_DIR`, Windows registry install locations, common Siemens folders on fixed drives, and finally global `NXBIN` search. `-NxRoot` may be either the install root or the `NXBIN` folder.
- Every NX plugin tool call must first ensure NX is online. Use MCP `nx_prepare_session` for task work; it starts NX if needed, waits for the live bridge, routes the prompt, and prepares the target application.
- When a request mentions 建模, 模型, 零件, 特征, 草图, 拉伸, 倒角, 圆角, 实体, 曲面, 装配, modeling, model, part, feature, sketch, extrude, chamfer, fillet, or assembly, treat it as a Modeling request and generate NXOpen journals with `NXOpen.Features` and `session.ApplicationSwitchImmediate("UG_APP_MODELING")`.
- When a request mentions 仿真, 有限元, CAE, FEA, 网格, 载荷, 约束, 求解, 应力, 应变, 位移, 模态, 热分析, simulation, mesh, solver, load, stress, or modal, treat it as a Simulation request and generate NXOpen journals with `NXOpen.CAE`; verify CAE module availability before creating meshes, loads, constraints, solves, or post-processing objects.
- If the route is unclear, call the MCP `nx_route_intent` tool with the user prompt before writing a journal.
- Before visible-window work, ping the live bridge first. The MCP `nx_live_*` tools and `scripts\nx_live_cli.ps1` automatically start NX when no `ugraf`/`nx` process is running.
- If an NX process is already running but the live bridge is not reachable, ask the user to restart NX or run `NX2512 Control > Start Codex Live Bridge`; use `scripts\start_live_bridge_via_ui.ps1` only when UI automation is acceptable.
- Use `scripts\nx_bridge.ps1` for external file/background `run_journal.exe` sessions. Do not expect those sessions to change the already open NX window.

## Startup Variables

The plugin derives these variables from `.mcp.json`, `scripts\nx_env.ps1`, or `scripts\install_nx_loader.ps1`:

- `NX2512_ROOT`, `DC2512_ROOT`, `UGII_BASE_DIR`: resolved install root.
- `DC2512_BIN`, `UGII_ROOT_DIR`: resolved `NXBIN` folder.
- `UGII_CUSTOM_DIRECTORY_FILE`: generated under `%LOCALAPPDATA%\Codex\NX2512\custom_dirs.dat` and points to `<plugin-root>\nx_runtime`.
- `NX2512_PLUGIN_ROOT`: installed plugin root.
- `NX2512_PROJECT_ROOT`, `DC2512_PROJECT_ROOT`: project/output directory, defaulting to `%USERPROFILE%\Documents\Codex\NX2512`.
- `NX2512_LIVE_PORT=25121`
- `NX2512_AUTO_LAUNCH=true`
- `NX2512_AUTO_LAUNCH_TIMEOUT=120`
- `NX2512_REQUIRE_ONLINE=true`
- `NX2512_DELETE_GENERATED_SCRIPTS=true`
- `NX2512_GENERATED_SCRIPT_ROOT=<plugin-root>\scripts\generated`
- `CODEX_PYTHON`: optional Python override; otherwise the plugin tries Codex bundled Python, `python.exe`, then `py.exe -3`.

## Commands

Install or refresh the NX startup loader:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <plugin-root>\scripts\install_nx_loader.ps1
```

Build the live .NET bridge:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <plugin-root>\scripts\build_dotnet_bridge.ps1 -Force
```

Check external NX status:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <plugin-root>\scripts\nx_bridge.ps1 -Action status
```

Ping the visible NX window live bridge:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <plugin-root>\scripts\nx_live_cli.ps1 -Command ping -NoBuild
```

The same command starts NX first when no visible NX process exists. Pass `-NoAutoLaunch` only when checking bridge availability without starting NX.

Run a prepared journal in an external `run_journal` session:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <plugin-root>\scripts\nx_bridge.ps1 -Action run-journal -JournalPath <journal.py>
```

Create a part in a background session:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <plugin-root>\scripts\nx_bridge.ps1 -Action create-part -PartPath <file.prt>
```

Create or edit geometry in the visible NX window:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <plugin-root>\scripts\nx_live_cli.ps1 -Command create-block -ParamsJson '{"length":80,"width":50,"height":25,"save":true}' -NoBuild
```

Classify a prompt before choosing modules:

```text
MCP tool: nx_route_intent
Arguments: {"prompt":"用户的 NX 请求"}
```

Prepare NX before generating or running scripts:

```text
MCP tool: nx_prepare_session
Arguments: {"prompt":"用户的 NX 请求"}
```

## Intent Routing

- Modeling route: use `NXOpen`, `NXOpen.Features`, and optional `NXOpen.Assemblies` or `NXOpen.GeometricUtilities`. Switch to `UG_APP_MODELING`. Prefer `nx_live_create_modeling_part`, `nx_live_create_block`, or `nx_live_run_python`.
- Simulation route: use `NXOpen`, `NXOpen.CAE`, and optional `NXOpen.SIM` or `NXOpen.Fields`. Do not use the Modeling route for finite-element setup. Prefer `nx_live_module_list` first, then `nx_live_run_python`.
- If a prompt contains both modeling and simulation terms, satisfy prerequisites in order: create or open the model first, then run the simulation/CAE workflow.

## History-Preserving Modeling Mode

When the user expects NX to show human-like modeling steps in the left Part Navigator, use history-preserving parameterized modeling by default.

- Before writing a modeling journal, call `nx_modeling_plan_template` or use `scripts\templates\history_feature_model.py` as the pattern.
- Generate a short ordered modeling plan with IDs like `01`, `02`, `03`; each step must map to a named NX object or feature.
- Use visible undo marks: `session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "01 Base sketch")`.
- Use editable dimensions through NX expressions for important sizes instead of only numeric literals.
- Prefer sketches, datum planes/axes, FeatureBuilder commits, hole/chamfer/fillet/shell/pattern features, and boolean features over final dumb bodies.
- Name every committed feature and important construction object with `SetName`, using ordered names such as `01_Base_Profile_Sketch`, `02_Base_Extrude`, `03_Mounting_Holes`, `04_Edge_Fillets`.
- For complex parts, run stages separately with `nx_live_run_python`: reference geometry, base body, main cuts/additions, patterns, finishing features, validation.
- Avoid faceted-only output, unlabelled default feature names, or one huge journal that produces an opaque body unless the user explicitly asks for a non-editable import.

## Staged Generation

- Large modeling jobs should be split into stages: base body, main features, detail features, finishing/check.
- Before each stage, call `nx_prepare_session` with the current user prompt or refined stage prompt.
- Generate stage scripts under `<plugin-root>\scripts\generated` or `.work\generated`.
- Run stage scripts with `nx_live_run_python` and pass `stage_name`; leave `delete_after_run` unset so successful temporary scripts are deleted automatically.
- After each stage, inspect the returned Work/Display Part and Listing Window result. Continue with the next stage only after the current state matches the intended geometry well enough.
- If a stage fails, keep the failed script for diagnosis by rerunning with `delete_after_run=false` or by using a script path outside the generated-script roots.

## Journal Pattern

Generated journals should use this shape:

```python
import NXOpen


def main():
    session = NXOpen.Session.GetSession()
    work_part = session.Parts.Work
    session.ListingWindow.Open()
    session.ListingWindow.WriteLine("NX automation started.")


if __name__ == "__main__":
    main()
```

Import specific NXOpen modules only when needed, such as:

- `NXOpen.Assemblies` for assembly operations.
- `NXOpen.Features` for modeling features.
- `NXOpen.CAE` for simulation and preprocessing.
- `NXOpen.CAM` for manufacturing operations.
- `NXOpen.Drawings` and `NXOpen.Annotations` for drafting.
- `NXOpen.UF` for lower-level UFSession access.

## Safety Rules

- Never overwrite an existing `.prt`, export, CAM output, or drawing without explicit confirmation.
- Save only when the user asks to save or the command name implies file creation.
- Avoid running journals while NX has an open modal dialog.
- Use the live bridge for user-visible work and `run_journal.exe` for background/file processing.
- Keep journal output in the NX Listing Window and summarize important messages back to the user.
