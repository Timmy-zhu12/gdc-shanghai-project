# 在线演示

在线演示源码保存在 `docs/`，因此 GitHub Pages 可以直接从同一个 PC 提交仓库提供服务。

- 本地文件：`docs/index.html`
- 已发布公开地址：`https://timmy-zhu12.github.io/gdc-shanghai-project/`
- 演示范围：单文件浏览器规则匹配，并保持同样的诊断输出合同
- 完整离线 Gemma4 4B 推理：需要在 Windows PC V5 应用中放置本地 GGUF 文件并运行

浏览器演示不会把病人文件上传到服务器。原始数据集、病人 DICOM 文件和模型权重均不包含在本仓库中。

本地常驻服务验证已整合到仓库文档：

- `docs/service_validation.md`
- `validation_speedopt/server_smoke_general_20260604.json`
- `validation_speedopt/server_pipeline_case1_240tok_20260604.json`

该验证覆盖 `llama-server.exe` 端口就绪、`/completion` smoke、EchoBench 单例服务诊断链路、必需字段检查和多智能体审计生成。
