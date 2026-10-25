# Changelog

## 0.1.0 — 2026-10-25

First public release.

- MCP server `nx` (15 tools) exposing the Siemens NX 2512 live bridge to DeepSeek Harness:
  `nx_live_ping`, `nx_live_status`, `nx_live_run_python`, `nx_live_run_script_file`,
  `nx_live_module_list`, `nx_live_create_modeling_part`, `nx_live_create_block`,
  `nx_run_journal`, `nx_create_part`, `nx_open_part`, `nx_status`,
  `nx_prepare_session`, `nx_route_intent`, `nx_modeling_plan_template`.
- Left-sidebar `NX` panel (display + copy).
- `bin/setup.mjs` writes machine-specific absolute paths into `cordis.patch.yml`
  (PowerShell, Python, project root, bridge port).
- Vendored NX runtime (0.2 MB) with dual transport framing: newline-delimited JSON
  for the DSH MCP client and `Content-Length` for the original Codex client.
- Verified end-to-end on NX 2512 with a GB/T standard gear: M20 × Z20 × b200,
  φ400 pitch / φ440 tip / φ350 root, volume check +0.83 % (root fillet).
