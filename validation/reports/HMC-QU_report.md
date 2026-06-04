# HMC-QU 测试报告

- 本地路径：`D:/cardioconsult_dense_validation/datasets/HMC-QU`
- 官方入口：https://www.kaggle.com/datasets/aysendegerli/hmcqu-dataset
- 下载/导入方式：`kaggle_api_or_manual`
- 验证阶段：`phase1_bmode, phase3_end_to_end`
- 扫描到的媒体文件：`0`
- 已处理特征行：`0`
- 已处理端到端行：`0`
- 错误数：`0`

## 数据状态

- 特征表：`D:\cardioconsult_dense_validation\results\HMC-QU\features.csv` 缺失
- 端到端表：`D:\cardioconsult_dense_validation\results\HMC-QU\end_to_end.csv` 缺失
- 说明：需要 Kaggle 凭据。配置 `kaggle.json` 后，本验证套件可调用 `kaggle datasets download` 下载。

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
