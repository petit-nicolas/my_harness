# res/phy/demo_templates — HTML5 交互演示模板库

存放可参数化复用的 HTML5 物理演示模板。由 `render_demo(template, params)` 工具按参数渲染成实例 HTML，供对话或仪表盘 iframe 嵌入。

## 目标模板（V5 填充 6 个核心）

| 模板 | 领域 | 物理引擎 |
|------|------|----------|
| `projectile.html` | 斜抛运动 | p5.js |
| `pendulum.html` | 单摆 / 双摆 | matter.js |
| `spring.html` | 弹簧振子 | matter.js |
| `circuit.html` | 简单电路（欧姆定律） | p5.js |
| `wave.html` | 机械波叠加 | p5.js |
| `orbit.html` | 天体运动 | p5.js |

## 模板约定

- 单文件 `.html`（内联 CSS/JS），便于沙箱嵌入
- 顶部 HTML 注释标注：`<!-- params: {"v0": number, "angle": number} -->`
- 参数通过 `window.__PARAMS__` 注入（`render_demo` 填充）
- 画布尺寸默认 800×500，响应式

## 安全

- 不得引用外部 CDN（离线可用 + 防注入）
- iframe 嵌入时带 `sandbox="allow-scripts"` 属性

## 当前状态

**空目录**，V5 开始填充。
