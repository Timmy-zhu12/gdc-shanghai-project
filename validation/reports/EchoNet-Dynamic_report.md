# EchoNet-Dynamic 测试报告

- 本地路径：`D:/cardioconsult_dense_validation/datasets/EchoNet-Dynamic`
- 官方入口：https://echonet.github.io/dynamic/
- 下载/导入方式：`manual_authorized`
- 验证阶段：`phase1_bmode, phase3_end_to_end`
- 扫描到的媒体文件：`0`
- 已处理特征行：`0`
- 已处理端到端行：`0`
- 错误数：`0`

## 数据状态

- 特征表：`D:\cardioconsult_dense_validation\results\EchoNet-Dynamic\features.csv` 缺失
- 端到端表：`D:\cardioconsult_dense_validation\results\EchoNet-Dynamic\end_to_end.csv` 缺失
- 说明：EchoNet-Dynamic 需要接受 Stanford/AIMI 研究用途条款。请将已授权视频和元数据放在该目录下。

## 第一阶段：B-Mode / GLDM 特征验证

| 指标 | 结果 |
|---|---|
| available | `False` |
| reason | `缺少 feature CSV` |

## 回归 / EF 相关验证

| 指标 | 结果 |
|---|---|
| available | `False` |
| reason | `缺少 feature CSV` |

## 特征显著性检验

当前没有足够标签或样本执行 Mann-Whitney U / Kruskal-Wallis 检验。

## 第三阶段：端到端系统测试

| 指标 | 结果 |
|---|---|
| available | `False` |
| reason | `缺少 end-to-end CSV` |

## 解释

本报告由验证工作台自动生成。若数据集缺少标签，分类、回归或显著性检验会标记为不可用；这不代表程序失败，而是说明当前数据目录缺少相应金标准字段。
