# dsh-nx

**Siemens NX 2512 inside DeepSeek Harness** — run NXOpen journals in the *open* NX window from chat, and get an **NX** panel in the left sidebar.

English | [中文](README.zh.md)

---

## What you get

- **MCP tools** (`mcp__nx__*`, 15 of them): `nx_live_ping`, `nx_live_status`, `nx_live_run_python`, `nx_live_module_list`, `nx_run_journal`, `nx_create_part`, `nx_open_part`, `nx_modeling_plan_template`, …
- **Left-sidebar panel**: bridge endpoint, tool list and copy-ready gear commands.
- **Self-contained runtime**: the MCP server (with NDJSON + Content-Length framing), the .NET live-bridge client and the NX menus ship in `vendor/`; nothing else needs to be installed.

## Requirements

| Item | Requirement |
|---|---|
| OS | Windows x64 |
| NX | Siemens NX / Designcenter **2512**, installed and able to start |
| NX session | NX must be open before the tools are used; the bridge listens on `127.0.0.1:25121` |
| Python | Any of: the DSH bundled runtime (auto-detected), `CODEX_PYTHON`, or `python` on `PATH` |

## Install

```powershell
# 1) extract into a writable folder (do NOT install the .tgz directly:
#    pnpm hard-links tarballs into a read-only store, and setup must write a file)
tar -xzf dsh-nx-0.1.0.tgz
dsh plugin --profile desktop add D:\tools\dsh-nx

# 2) resolve machine-specific absolute paths (once; rerun after moving the folder)
node D:\tools\dsh-nx\bin\setup.mjs
#    optional: --project "D:\my\prj"

# 3) restart DeepSeek Harness
```

If NX is already running but the bridge is not up, run `NX2512 Control > Start Codex Live Bridge` in NX.

## Use

Ask in chat:

> Use `nx_live_ping` to check the bridge.

> Use `nx_live_run_python` to run `nx\gear_build.py` with `{"m":20,"z":20,"b":200}`.

`gear_build.py` (placed in `<project>\nx\`) accepts:

| Key | Meaning |
|---|---|
| `m` / `z` / `b` | module / teeth / face width |
| `alpha` `ha` `c` `rho` `x` | pressure angle and tooth-system factors (defaults 20 / 1 / 0.25 / 0.38 / 0) |
| `bore` `key_w` `key_t` | centre bore, key width, hub keyway depth (GB/T 1096) |
| `out_dir` `name` | output folder and part name |

Every build is verified numerically: volume (≤3 % from the analytic value), tip radius = da/2, face width = b, root-cylinder count = tooth count.

Example result for `m=20, z=20, b=200` (GB/T 1356-2001 / GB/T 1357-2008):

```
d  400.000   db 375.877   da 440.000   df 350.000
volume 24,726,253 mm3  (analytic 24,522,114, +0.83 % from the root fillet)
faces: 60 parametric / 20 cylindrical / 2 planar
```

## Uninstall

```powershell
dsh plugin --profile desktop remove dsh-nx
```

## Notes

- The panel is informational (display + copy); execution happens through the MCP tools in chat.
- `vendor/` contains the NX menu and launcher scripts derived from the codex-NX project, used under its MIT license; see `NOTICE` and `vendor/LICENSE`.

## Third-party notices

- `vendor/` is derived from the **codex-NX** plugin bundle, which declares MIT in its manifest. Its MIT text ships as `vendor/LICENSE`; provenance and the list of modifications are in `NOTICE`.
- **Siemens NX** is a trademark of Siemens AG. This package is an independent integration, not affiliated with or endorsed by Siemens; it ships no Siemens binaries or artwork and only drives an NX installation you already license.

## License

MIT — see [LICENSE](LICENSE).
