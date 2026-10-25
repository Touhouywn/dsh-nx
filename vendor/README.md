# NX

Local Codex plugin for operating Siemens NX 2512 through NXOpen journals and a live .NET Remoting bridge.

The plugin provides:

- `.codex-plugin/plugin.json` manifest metadata for the `NX` Codex plugin.
- `.mcp.json` MCP server entry for Codex tool calls.
- `scripts/nx_bridge.ps1` command line bridge to NX `run_journal.exe` for external file/background work.
- `scripts/nx_live_cli.ps1` live command line bridge for the already open NX window.
- `scripts/nx_mcp_server.py` prompt intent routing through `nx_route_intent`, including 建模/modeling -> `NXOpen.Features` and 仿真/simulation/CAE -> `NXOpen.CAE`.
- `scripts/build_dotnet_bridge.ps1` compiles the NX live .NET server/client.
- `nx_runtime/` Siemens NX custom directory loaded by a generated `UGII_CUSTOM_DIRECTORY_FILE`; the live server DLL is built into `nx_runtime/startup` so new NX sessions can auto-start it.
- `scripts/nx_mcp_server.py` minimal MCP stdio server with intent routing, fast native status/module scanning, and direct live-client calls.
- `scripts/nx_env.ps1` shared environment bootstrap for NX and Codex entrypoints.
- `skills/nx/SKILL.md` usage guidance for chat-driven NX work.

## Requirements

- Siemens NX/DC 2512 installed locally with a valid `NXBIN` folder. The plugin auto-discovers NX from explicit `-NxRoot`, `DC2512_BIN`, `DC2512_ROOT`, `NX2512_ROOT`, `UGII_BASE_DIR`, `UGII_ROOT_DIR`, Windows uninstall registry entries, common Siemens install folders on fixed drives, and finally a global `NXBIN` search.
- NX license available.
- For direct operations against the active NX UI, keep NX idle and out of modal dialogs. Live commands auto-launch NX when no `ugraf`/`nx` process exists, then wait for the live bridge configured through the generated `UGII_CUSTOM_DIRECTORY_FILE`; use `NX2512 Control > Start Codex Live Bridge` as a manual recovery path when NX is already running without the bridge.
- A Python runtime for MCP. The bridge itself is PowerShell-only; MCP uses Python for JSON-RPC stdio.
- .NET Framework 4.x C# compiler, normally available at `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`.

## Quick Checks

Install the NX loader for the current Windows user:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_nx_loader.ps1
```

Build the live bridge:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_dotnet_bridge.ps1
```

Restart or launch NX with the plugin environment:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch_nx_with_plugin.ps1
```

The live .NET bridge should auto-start from `nx_runtime/startup`. If NX is already open, use:

```text
NX2512 Control > Start Codex Live Bridge
```

Then test the live bridge:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nx_live_cli.ps1 -Command ping
```

List available NXOpen modules:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nx_live_cli.ps1 -Command module-list
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nx_bridge.ps1 -Action status
```

The same status command can be pointed directly at any local `NXBIN` folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nx_bridge.ps1 -Action status -NxRoot "<path-to-NXBIN>"
```

Run an NXOpen Python journal in an external `run_journal` session:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nx_bridge.ps1 -Action run-journal -JournalPath .\scripts\examples\create_demo_block.py
```

Create a new part:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nx_bridge.ps1 -Action create-part -PartPath "$env:USERPROFILE\Documents\Codex\NX2512\demo.prt"
```

Open an existing part:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nx_bridge.ps1 -Action open-part -PartPath "$env:USERPROFILE\Documents\Codex\NX2512\demo.prt"
```

## Live Commands

Create a modeling part in the visible NX session:

```powershell
$params = @{ part_path = "$env:USERPROFILE\Documents\Codex\NX2512\nx_codex_smoke_manual.prt"; save = $true } | ConvertTo-Json -Compress
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nx_live_cli.ps1 -Command create-modeling-part -ParamsJson $params
```

Create a block in the current Work Part:

```powershell
$params = @{ length = 80; width = 50; height = 25; save = $true } | ConvertTo-Json -Compress
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nx_live_cli.ps1 -Command create-block -ParamsJson $params
```

Run a reviewed Python script in the visible NX session:

```powershell
$params = @{ path = ".\scripts\examples\create_demo_block.py" } | ConvertTo-Json -Compress
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nx_live_cli.ps1 -Command run-python -ParamsJson $params
```

## Chat-Driven Workflow

1. Ask Codex for the target operation in plain language.
2. Codex translates the request into a focused NXOpen Python journal.
3. For file/background work, the bridge runs the journal with NX `run_journal.exe`.
4. For work in the already open NX window, use the live .NET bridge and `scripts/nx_live_cli.ps1`.
5. Codex reports the result and any NX journal output.

## Human-Like Modeling History

For editable models that look like they were built by a human, use the history-preserving modeling mode. Codex should create an ordered modeling plan first, then run staged NXOpen journals that commit named features. The left NX Part Navigator will show steps such as:

```text
01_Base_Profile_Sketch
02_Base_Extrude
03_Main_Bore
04_Mounting_Holes
05_Hole_Pattern
06_Chamfers
07_Edge_Fillets
```

The MCP helper `nx_modeling_plan_template` returns the required plan schema and naming rules. The journal pattern lives at:

```text
scripts\templates\history_feature_model.py
```

Use `session.SetUndoMark(...)`, NX expressions, sketches, datum objects, and `NXOpen.Features` builders. Name every committed feature with `SetName(...)`. Avoid creating only a final dumb body when the user expects editable feature history.

## Important NX Session Boundary

`run_journal.exe` does not reliably attach to the already open Designcenter/NX window. A command-line journal may create `.prt` files without changing the Work Part or Display Part in the visible NX window.

Use the live bridge for visible-window work. To verify the visible NX window without Codex, use the NX menu:

```text
NX2512 Control > Create Codex Smoke Part
```

It switches the current NX window to Modeling, creates a part under `Documents\Codex\NX2512`, adds a small block, sets it as Work/Display Part, fits the view, and writes a message to the Listing Window.

Review generated journals before running destructive actions such as save-overwrite, delete, mass feature edits, CAM post processing, or export into production folders.
