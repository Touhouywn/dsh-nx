#!/usr/bin/env node
/**
 * dsh-nx setup: 把本机绝对路径写入 cordis.patch.yml。
 * 用法: node node_modules/dsh-nx/bin/setup.mjs [--project <dir>]
 */
import { readFileSync, writeFileSync, existsSync, readdirSync, mkdirSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { homedir } from 'node:os'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const vendor = join(root, 'vendor')
const home = homedir()

function arg(name) {
  const i = process.argv.indexOf(name)
  return i >= 0 ? process.argv[i + 1] : undefined
}

function findPython() {
  if (process.env.CODEX_PYTHON && existsSync(process.env.CODEX_PYTHON)) return process.env.CODEX_PYTHON
  const runtimes = join(home, '.dsh', 'dsh-runtimes')
  if (existsSync(runtimes)) {
    for (const dir of readdirSync(runtimes)) {
      const p = join(runtimes, dir, 'dependencies', 'python', 'python.exe')
      if (existsSync(p)) return p
    }
  }
  return 'python'
}

const projectRoot = resolve(arg('--project') || process.env.NX2512_PROJECT_ROOT || join(home, 'Documents', 'Codex', 'NX2512'))
if (!existsSync(projectRoot)) mkdirSync(projectRoot, { recursive: true })

const powershell = process.env.SystemRoot
  ? join(process.env.SystemRoot, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
  : 'powershell.exe'
const python = findPython()
const port = process.env.NX2512_LIVE_PORT || '25121'

const yaml = [
  '# 由 dsh-nx setup 生成；换机器或换路径后重新运行本脚本即可。',
  '# 注意：新增插件必须用 insert 列表形式，顶层 - id: 会被 DSH 静默忽略。',
  '- insert:',
  '    - id: mcp-nx',
  "      name: '@deepseek-ai/dsh-mcp-client'",
  '      config:',
  '        serverName: nx',
  '        transport: stdio',
  `        command: '${powershell.replace(/\\/g, '\\\\')}'`,
  `        args: ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', '${join(vendor, 'scripts', 'start_mcp.ps1').replace(/\\/g, '\\\\')}']`,
  `        cwd: '${vendor.replace(/\\/g, '\\\\')}'`,
  '        env:',
  `          CODEX_PYTHON: '${python.replace(/\\/g, '\\\\')}'`,
  `          NX2512_LIVE_PORT: '${port}'`,
  `          NX2512_PROJECT_ROOT: '${projectRoot.replace(/\\/g, '\\\\')}'`,
  "          NX2512_AUTO_LAUNCH: 'false'",
  "          NX2512_REQUIRE_ONLINE: 'true'",
  "          NX2512_DELETE_GENERATED_SCRIPTS: 'false'",
  '        toolCallTimeoutMs: 900000',
  '        failOnStartupError: false',
  ''
].join('\n')

writeFileSync(join(root, 'cordis.patch.yml'), yaml, 'utf8')
console.log('dsh-nx: cordis.patch.yml 已写入')
console.log('  vendor  :', vendor)
console.log('  python  :', python)
console.log('  project :', projectRoot)
console.log('  port    :', port)
console.log('下一步：重启 DeepSeek Harness，然后在对话里用 nx_live_ping 验证。')
