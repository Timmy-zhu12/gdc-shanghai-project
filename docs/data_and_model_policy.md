# 数据与模型政策

本仓库有意保持为“源代码 + 文档 + 验证摘要 + 可复现脚本”仓库，不保存需要额外授权的医学原始数据或大模型权重。

完整数据集来源、用途和再分发边界见 [../DATASETS.md](../DATASETS.md)。

## 不应提交的内容

- GGUF 模型权重
- 真实病人 DICOM 文件
- 原始医学图像数据集
- 数据集下载缓存和解压缓存
- 本地诊断导出结果
- `config.json`
- 本地 SDK、IDE 或虚拟环境配置文件
- 任何包含病人身份信息、检查号、姓名、出生日期、联系方式或机构内部编号的文件

## 推荐本地路径

| 资源 | 本地示例 |
|---|---|
| PC 模型权重 | `models/` 或外部模型存储目录 |
| 验证数据集 | `D:/cardioconsult_dense_validation/datasets` |
| 验证生成结果 | `D:/cardioconsult_dense_validation/results` |
| 本地病例导出 | 仓库外的脱敏临时目录 |

## 模型复现建议

Gemma4 4B GGUF 文件需由使用者通过授权渠道自行获取。默认配置期望：

```text
models/gemma-4-4b-it-Q4_K_M.gguf
```

为了让离线复现可审查，建议在本地记录模型文件名、量化格式、来源页面、下载日期和 SHA256：

```powershell
Get-FileHash .\models\gemma-4-4b-it-Q4_K_M.gguf -Algorithm SHA256
```

仓库内的 `config.example.json` 只给出路径模板，不包含真实密钥、账号、病人路径或私有下载地址。

## 数据使用边界

所有第三方数据集、SDK、超声软件、应用商店资产、商标和模型权重仍受各自许可证与使用条款约束。

本项目只保存由数据集衍生的验证摘要、统计结果、图表和人工编写的标签映射，不再分发 CAMUS、EchoNet-Dynamic、EchoNet-LVH、TMED-2、HMC-QU、EchoXFlow、MIMIC-IV-ECHO、ECHOVIEW、CACTUS、私有教学数据或任何原始 DICOM/PNG 病人文件。
