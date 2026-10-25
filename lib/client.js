window.__ModuleLoader__.load({
	id: "dsh-nx",
	factory: (require) => {
		var module = { exports: {} };
		var exports = module.exports;
		Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
		const React = require("react");
		const jsxRuntime = require("react/jsx-runtime");
		const jsx = jsxRuntime.jsx;
		const jsxs = jsxRuntime.jsxs;

		const PANEL_ID = "nx";
		const BG = "var(--dsw-alias-bg-layer-1, #fff)";
		const BORDER = "var(--dsw-alias-border-l3, #e5e5e5)";
		const TEXT = "var(--dsw-alias-label-primary, #111)";
		const SUB = "var(--dsw-alias-label-secondary, #666)";
		const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

		function NxIcon() {
			return jsx("svg", {
				width: 18, height: 18, viewBox: "0 0 24 24", fill: "none",
				stroke: "currentColor", strokeWidth: 1.6, "aria-hidden": true
			}, jsx("circle", { cx: 12, cy: 12, r: 3.2 }), jsx("path", {
				d: "M12 2.6v3M12 18.4v3M2.6 12h3M18.4 12h3M5.4 5.4l2.1 2.1M16.5 16.5l2.1 2.1M18.6 5.4l-2.1 2.1M7.5 16.5l-2.1 2.1"
			}));
		}

		function Row(props) {
			return jsxs("div", {
				style: { display: "flex", gap: 8, padding: "5px 0", fontSize: 12, lineHeight: 1.5 }
			}, jsx("span", { style: { color: SUB, minWidth: 76 } }, props.k),
			   jsx("span", { style: { color: TEXT, fontFamily: MONO, wordBreak: "break-all" } }, props.v));
		}

		function Code(props) {
			const [copied, setCopied] = React.useState(false);
			return jsxs("div", { style: { position: "relative", margin: "6px 0" } },
				jsx("pre", {
					style: {
						margin: 0, padding: "8px 10px", fontSize: 11.5, lineHeight: 1.55,
						fontFamily: MONO, background: "rgba(127,127,127,0.08)",
						border: "0.5px solid " + BORDER, borderRadius: 6,
						whiteSpace: "pre-wrap", wordBreak: "break-all", color: TEXT
					}
				}, props.text),
				jsx("button", {
					onClick: () => {
						try { navigator.clipboard.writeText(props.text); } catch (e) {}
						setCopied(true);
						setTimeout(() => setCopied(false), 1200);
					},
					style: {
						position: "absolute", top: 6, right: 6, fontSize: 11, padding: "2px 8px",
						borderRadius: 5, border: "0.5px solid " + BORDER, background: BG,
						color: SUB, cursor: "pointer"
					}
				}, copied ? "已复制" : "复制"));
		}

		function Section(props) {
			return jsx("div", { style: { marginTop: 14 } },
				jsx("div", { style: { fontSize: 12, fontWeight: 600, color: TEXT, marginBottom: 4 } }, props.title),
				props.children);
		}

		function NxPanel() {
			return jsx("div", {
				style: { height: "100%", overflow: "auto", padding: "18px 20px", boxSizing: "border-box", background: BG }
			}, jsxs("div", { style: { maxWidth: 720 } },
				jsx("div", { style: { fontSize: 15, fontWeight: 600, color: TEXT } }, "Siemens NX 2512"),
				jsx("div", { style: { fontSize: 12, color: SUB, marginTop: 2 } },
					"通过 live 桥把 NXOpen 日志送进正在运行的 NX 窗口，齿轮等零件由对话直接生成"),
				jsxs("div", { style: { marginTop: 12, border: "0.5px solid " + BORDER, borderRadius: 8, padding: "10px 12px" } },
					jsx(Row, { k: "桥地址", v: "http://localhost:25121/NXOpenSession" }),
					jsx(Row, { k: "MCP 服务器", v: "nx（工具前缀 mcp__nx__）" }),
					jsx(Row, { k: "工程目录", v: "环境变量 NX2512_PROJECT_ROOT" }),
					jsx(Row, { k: "前提", v: "NX 2512 已打开；Windows" })),
				jsx(Section, { title: "常用工具" },
					jsx(Code, { text: "nx_live_ping          检查桥是否在线\nnx_live_status        读 Work/Display Part\nnx_live_run_python    在 NX 里跑日志（path + params_json）" })),
				jsx(Section, { title: "生成一个国标齿轮" },
					jsx(Code, { text: "path: <工程目录>\\nx\\gear_build.py\nparams_json: {\"m\":20,\"z\":20,\"b\":200}" })),
				jsx(Section, { title: "说明" },
					jsx("div", { style: { fontSize: 12, color: SUB, lineHeight: 1.6 } },
						"面板只做展示与复制，执行由对话里的 MCP 工具完成。齿轮参数按 GB/T 1356-2001 与 " +
						"GB/T 1357-2008 取值，生成后自动做体积、齿顶圆、齿宽、齿数四项校验。"))));
		}

		const inject = ["slots"];

		function apply(ctx) {
			ctx.slots.inject("sidebar.panellist", () => ctx.slots.register({
				name: "sidebar.panellist",
				id: PANEL_ID,
				order: 100,
				label: "NX"
			}, NxIcon));
			ctx.slots.inject("main", () => ctx.slots.register({
				name: "main",
				key: PANEL_ID
			}, NxPanel));
		}

		exports.apply = apply;
		exports.inject = inject;
		return module.exports;
	}
});
