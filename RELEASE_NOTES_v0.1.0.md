## dsh-nx 0.1.0

Siemens NX 2512 for DeepSeek Harness — MCP bridge + left-sidebar panel.

### Highlights

- **15 MCP tools** (`mcp__nx__*`) that drive the NX window you already have open:
  ping/status, run NXOpen Python journals, create/open parts, history-preserving
  modeling plans, and intent routing for modeling vs. simulation.
- **NX panel** in the left sidebar: bridge endpoint, tool list, copy-ready gear commands.
- **One-command setup** (`bin/setup.mjs`) resolves PowerShell, Python and your project
  folder; no hand-edited YAML.
- **Verified**: M20 × Z20 × b200 GB/T gear built in ~4 s, φ440 tip / φ350 root,
  volume within 0.83 % of the analytic value.

### Install

```powershell
tar -xzf dsh-nx-0.1.0.tgz
dsh plugin --profile desktop add D:\tools\dsh-nx
node D:\tools\dsh-nx\bin\setup.mjs
# restart DeepSeek Harness
```

### Requirements

Windows x64 · Siemens NX/Designcenter 2512 · NX window open while using the tools.

### License

MIT. `vendor/` is derived from the codex-NX plugin (MIT); see `NOTICE` and `vendor/LICENSE`.
