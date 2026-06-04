# 部署说明

本仓库是当前单一提交入口。被维护、可直接运行的目标是 Windows PC V5 应用；较早的平台原型不需要用于复现或评审当前结果。

| 目标 | 目录 | 主入口 | 状态 |
|---|---|---|---|
| Windows PC V5 应用 | 仓库根目录 | `run_cardio_pc_v5.bat` | 当前维护的离线参考实现 |
| 热启动 GGUF 推理服务 | 仓库根目录 | `run_cardio_pc_v4_fast_server.bat` | 可选常驻 `llama-server` 模式，用于多次本地 Gemma4 4B 调用 |
| 规则自检 | 仓库根目录 | `python app.py --self-test-rule-only` | 没有 GGUF 权重时的快速验证 |
| 静态在线演示 | `docs/` | `index.html` | 单文件浏览器规则匹配演示，可由 GitHub Pages 提供服务，也可直接打开 |
| 技术报告包 | `submission/technical_report/` 和 `docs/v5_benchmark/` | `.docx`、`.pdf`、`.md`、图表 | 提交报告、benchmark 叙述和可视化结果 |

推荐演示顺序：

1. 打开 `docs/index.html`，或启用 Pages 后打开公开 URL。
2. 导入 PNG/DICOM/DCOM/cine 示例，并展示输出合同。
3. 运行 `run_cardio_pc_v5.bat` 展示完整 PC 工作流。
4. 将本地 Gemma4 4B GGUF 文件放入 `models/`，使用 `llama-cli` 或常驻 `llama-server` 完成离线生成。
5. 展示 `DATASETS.md`、`SUBMISSION.md` 和技术报告包，说明数据来源、验证限制和安全边界。
