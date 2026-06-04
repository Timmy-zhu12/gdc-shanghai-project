# 数据与模型政策

本仓库有意保持为“源代码 + 文档 + 验证摘要”仓库。

完整数据集来源、用途和边界见 [../DATASETS.md](../DATASETS.md)。

不要提交：

- GGUF 模型权重
- 真实病人 DICOM 文件
- 原始医学图像数据集
- 数据集下载缓存
- 本地诊断导出结果
- `config.json`
- 本地 SDK 或 IDE 配置文件
- 任何包含病人身份信息的文件

推荐本地路径：

| 资源 | 本地示例 |
|---|---|
| PC 模型权重 | `models/` 或外部模型存储目录 |
| 验证数据集 | `D:/cardioconsult_dense_validation/datasets` |
| 验证生成结果 | `D:/cardioconsult_dense_validation/results` |

所有第三方数据集、SDK、超声软件、应用商店资产、商标和模型权重仍受各自条款约束。

本项目只使用数据集衍生的验证摘要和人工编写的标签映射，不再分发 CAMUS、EchoNet-Dynamic、EchoNet-LVH、TMED-2、HMC-QU、EchoXFlow、MIMIC-IV-ECHO、ECHOVIEW、CACTUS、私有教学数据或任何原始 DICOM/PNG 病人文件。
