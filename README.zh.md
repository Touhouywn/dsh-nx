# dsh-nx

把 **Siemens NX 2512** 接进 DeepSeek Harness：在对话里直接让 NX 建零件，左侧栏多一个 **NX** 面板。

[English](README.md) | 中文

---

## 能力

- **MCP 工具**（前缀 `mcp__nx__`，共 15 个）：`nx_live_ping`、`nx_live_status`、`nx_live_run_python`、`nx_live_module_list`、`nx_run_journal`、`nx_create_part`、`nx_open_part`、`nx_modeling_plan_template` 等；
- **左侧栏面板**：桥地址、工具清单、可直接复制的齿轮命令；
- **自带运行时**：MCP 服务器（含 NDJSON / Content-Length 双帧补丁）、.NET live 客户端、NX 菜单都在 `vendor/`，不依赖其它目录。

## 前提

| 项 | 要求 |
|---|---|
| 系统 | Windows x64 |
| NX | Siemens NX / Designcenter **2512**，能正常启动 |
| NX 会话 | 用工具前先把 NX 打开；桥监听 `127.0.0.1:25121` |
| Python | 任选其一：DSH 自带运行时（自动探测）、`CODEX_PYTHON`、或 PATH 里的 `python` |

## 安装

```powershell
# 1) 解压到可写目录（不要直接装 .tgz：pnpm 会硬链接进只读存储，setup 写不进去）
tar -xzf dsh-nx-0.1.0.tgz
dsh plugin --profile desktop add D:\tools\dsh-nx

# 2) 生成本机绝对路径（一次即可，换目录后重跑）
node D:\tools\dsh-nx\bin\setup.mjs
#    可指定工程目录： --project "D:\my\prj"

# 3) 重启 DeepSeek Harness
```

NX 已开但桥没起时，在 NX 菜单执行 `NX2512 Control > Start Codex Live Bridge`。

## 使用

对话里直接说：

> 用 `nx_live_ping` 看看桥在不在。

> 用 `nx_live_run_python` 跑 `nx\gear_build.py`，参数 `{"m":20,"z":20,"b":200}`。

`gear_build.py`（放在 `<工程目录>\nx\`）支持的键：

| 键 | 含义 |
|---|---|
| `m` / `z` / `b` | 模数 / 齿数 / 齿宽 |
| `alpha` `ha` `c` `rho` `x` | 压力角与齿制系数（默认 20 / 1 / 0.25 / 0.38 / 0） |
| `bore` `key_w` `key_t` | 中心孔直径、平键宽、轮毂槽深（GB/T 1096） |
| `out_dir` `name` | 输出目录与零件名 |

每次生成后自动校验：体积（与解析值偏差 ≤3%）、齿顶半径 = da/2、齿宽 = b、齿根圆柱面数 = 齿数。

`m=20, z=20, b=200` 的实测结果（GB/T 1356-2001 / GB/T 1357-2008）：

```
d  400.000   db 375.877   da 440.000   df 350.000
体积 24,726,253 mm³（解析 24,522,114，+0.83% 来自齿根圆角）
面构成 60 参数曲面 / 20 圆柱面 / 2 平面
```

## 卸载

```powershell
dsh plugin --profile desktop remove dsh-nx
```

## 说明

- 面板只做展示与复制，执行发生在对话里的 MCP 工具调用；
- `vendor/` 内的 NX 菜单与启动脚本源自 codex-NX 项目，按其 MIT 许可使用，详见 `NOTICE` 与 `vendor/LICENSE`。

## 第三方声明

- `vendor/` 源自 **codex-NX** 插件包（其 manifest 声明 MIT），MIT 全文见 `vendor/LICENSE`，来源与修改记录见 `NOTICE`；
- **Siemens NX** 为西门子商标，本包为独立集成、与西门子无隶属或背书关系，不打包西门子二进制与图标。

## 许可

MIT，见 [LICENSE](LICENSE)。
