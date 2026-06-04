# Gemma4 开发者大赛提交检查表

本文件是评审进入 CardioConsult 项目的中文总入口。

官方页面：[Gemma 4 Hackathon 2026](https://hackathon.googdg.cn/?lang=en)

本仓库采用 Windows PC V5 作为唯一稳定、可复现的离线参考实现。这里的 PC 被定义为可直接接入超声机器或超声工作站的本地分析终端，可通过 USB、局域网共享目录、DICOM 工作站导出目录或无线超声软件导出文件读取资料，并在本机完成规则后备、GGUF 推理、数据来源披露、技术报告、验证结果和单文件在线规则演示。

## 必交材料

| 要求 | CardioConsult 对应材料 | 状态 |
|---|---|---|
| 代码仓库 | 本仓库：`https://github.com/Timmy-zhu12/gdc-shanghai-project` | 已准备 |
| 5 分钟内演示视频 | 视频上传后，将公开视频链接填入提交表单 | 待最终上传 |
| 技术报告 | [DOCX](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.docx)、[PDF](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.pdf)、[Markdown](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.md) | 已准备 |
| 在线演示链接 | 单文件规则匹配网页已发布：`https://timmy-zhu12.github.io/gdc-shanghai-project/`；源码位于 [docs/index.html](docs/index.html) | 已上线 |
| 训练/验证数据来源披露 | [DATASETS.md](DATASETS.md) 和 [docs/data_and_model_policy.md](docs/data_and_model_policy.md) | 已准备 |
| 技术亮点说明 | [docs/competitive_edge.md](docs/competitive_edge.md) | 已准备 |
| 本地服务验证 | [docs/service_validation.md](docs/service_validation.md)，包含 `llama-server` 端口、`/completion` smoke、项目诊断链路和多智能体审计检查 | 已通过 |
| 许可证 | [Apache License 2.0](LICENSE) 与 [NOTICE](NOTICE) | 已准备 |

## 仓库范围

本仓库就是当前提交仓库。PC V5 是本次提交中唯一积极维护、可直接运行的版本；较早的平台原型只作为后续迁移方向，不作为评审复现当前结果的必要材料。

## 评审维度对应关系

| 评审维度 | 权重 | 建议检查内容 |
|---|---:|---|
| 真实影响 | 30% | 医学教学与基层心脏超声参考流程；PC 可部署在超声设备旁直接读取导出资料；README 和 UI 中的安全边界；脱敏本地处理流程 |
| 技术能力 | 25% | B-mode GLDM/纹理代理、SRAD/CLAHE 预处理、Color Doppler HSV/向量代理、动图/DICOM 支持、EchoNet-Dynamic EF 校准、本地 Gemma4 4B |
| 完整性 | 20% | 可运行 PC V5 仓库、在线规则演示、示例文件、验证报告、启动脚本、技术报告、规则自检、多智能体审计 JSON |
| 创新性 | 15% | 边缘特征 + Gemma4 报告生成、层级病症标签、离线优先医学教学流程 |
| 展示质量 | 10% | APA 技术报告、验证材料包、README 部署说明、单文件在线演示 |

## 离线演示路径

建议评审演示顺序：

1. 打开 `docs/index.html` 或启用 GitHub Pages 后的在线演示链接。
2. 克隆或打开本仓库，运行 `run_cardio_pc_v5.bat`。
3. 演示 PC V5 从超声机器/工作站导出目录读取 PNG、DICOM、DCOM、cine/视频输入，以及一致的诊断输出合同。
4. 多次本地 Gemma4 演示时，可按 `docs/service_validation.md` 手动复用已加载的 `llama-server`。
5. 展示 [docs/service_validation.md](docs/service_validation.md) 中的普通本地服务测试：`/completion` 两次短请求均成功，EchoBench 第 1 例服务诊断输出包含 `教学参考病症判断：`、`最小病症：` 和 `逻辑链：`。
6. 说明模型权重和原始数据因许可证与隐私原因不随仓库分发，然后展示验证摘要和安全边界。

## 技术强项

- 真实离线路径：PC V5 使用本地 Gemma4 4B GGUF，可通过 `llama-cli` 或常驻 `llama-server` 调用，并定位为超声设备旁的离线分析终端。
- 动态心超增强：EchoNet-Dynamic 特征增强 EF / 左室收缩功能减低识别，同时保留可审计的瓣膜反流规则。
- 轻量多智能体：InputAgent、FeatureAgent、DiagnosisAgent、ReportAgent 和 SafetyAuditAgent 在本地串联，不额外调用云服务。
- 超声专用预处理：B-mode 与 Color Doppler 分支分别提取边缘、纹理、血流方向、喷流宽度、涡量等代理特征。
- 层级医学输出：报告必须包含大方向、中方向、最小病症、分级、证据充分度和逻辑链。
- 演示稳定性：即使现场没有大模型权重，规则后备仍能保持同样的输入输出合同。
- 数据透明：所有公开数据集和文献来源均列于 `DATASETS.md`；原始数据、病人图像和模型权重不再分发。

## 本地快速自检

Windows PC：

```powershell
git clone https://github.com/Timmy-zhu12/gdc-shanghai-project.git
Set-Location gdc-shanghai-project
.\install_deps.bat
.\.venv\Scripts\python.exe app.py --self-test-rule-only
.\run_cardio_pc_v5.bat
```

## 医学安全边界

CardioConsult 是医学教学和算法演示原型，不是医疗器械，不能作为最终临床诊断、治疗建议、急诊分诊指令或医嘱。正式判断仍需完整标准心脏超声切面、DICOM 标尺信息、连续动态帧、病史、体征和有资质医师复核。

## 提交前人工检查项

- 录制或上传演示视频，并把公开视频链接填入提交表单。
- 确认在线演示 URL `https://timmy-zhu12.github.io/gdc-shanghai-project/` 仍可访问。
- 确认本仓库为公开仓库，或评审可访问。
- 确认没有提交原始病人数据、模型权重、`config.json`、包含密钥的本地路径或数据集下载缓存。
