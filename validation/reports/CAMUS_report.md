# CAMUS 测试报告

- 本地路径：`D:/cardioconsult_dense_validation/datasets/CAMUS`
- 官方入口：https://www.creatis.insa-lyon.fr/Challenge/camus/
- 下载/导入方式：`public_tool_or_manual`
- 验证阶段：`phase1_bmode, phase3_end_to_end`
- 扫描到的媒体文件：`3000`
- 已处理特征行：`1747`
- 已处理端到端行：`250`
- 错误数：`0`

## 数据状态

- 特征表：`D:\cardioconsult_dense_validation\results\CAMUS\features.csv` 存在
- 端到端表：`D:\cardioconsult_dense_validation\results\CAMUS\end_to_end.csv` 存在
- 说明：CAMUS contains 2D echocardiographic sequences from 500 patients in NIfTI format. zea can download it with python -m zea.data.convert camus <src> <dst> --download, but this validation suite also accepts manually extracted CAMUS folders.

## 第一阶段：B-Mode / GLDM 特征验证

| 指标 | 结果 |
|---|---|
| available | `True` |
| n | `250` |
| unit | `case_level` |
| classes | `['low_contractility_proxy', 'normal']` |
| accuracy | `0.672` |
| macro_f1 | `0.6423337288017308` |
| confusion_matrix | `[[120, 50], [32, 48]]` |
| auc | `0.6813970588235294` |

## 回归 / EF 相关验证

| 指标 | 结果 |
|---|---|
| available | `True` |
| n | `250` |
| unit | `case_level` |
| rmse | `13.531533232147135` |
| mae | `10.745935389034429` |
| pearson_r | `0.23119423313752346` |
| pearson_p | `0.00022668032057760406` |
| spearman_r | `0.2697416658211638` |
| spearman_p | `1.5320072687686246e-05` |

## 特征显著性检验

| feature        | test           |   statistic |     p_value |   p_bonferroni |
|:---------------|:---------------|------------:|------------:|---------------:|
| psnr           | Mann-Whitney U |        3646 | 3.36787e-09 |    1.38083e-07 |
| snr            | Mann-Whitney U |        3708 | 6.77794e-09 |    2.77895e-07 |
| bmode_10       | Mann-Whitney U |        9872 | 8.46952e-09 |    3.4725e-07  |
| bmode_13       | Mann-Whitney U |        9829 | 1.36107e-08 |    5.58039e-07 |
| bmode_11       | Mann-Whitney U |        9559 | 2.3162e-07  |    9.4964e-06  |
| gldm_hgze      | Mann-Whitney U |        4065 | 2.94415e-07 |    1.2071e-05  |
| gldm_mean_gray | Mann-Whitney U |        4134 | 5.8043e-07  |    2.37976e-05 |
| bmode_1        | Mann-Whitney U |        4308 | 2.99183e-06 |    0.000122665 |
| bmode_8        | Mann-Whitney U |        8986 | 4.17353e-05 |    0.00171115  |
| bmode_0        | Mann-Whitney U |        4632 | 4.82587e-05 |    0.00197861  |
| gldm_contrast  | Mann-Whitney U |        8915 | 7.35399e-05 |    0.00301514  |
| bmode_2        | Mann-Whitney U |        8782 | 0.000203069 |    0.00832584  |
| gldm_lgze      | Mann-Whitney U |        8740 | 0.000276453 |    0.0113346   |
| bmode_4        | Mann-Whitney U |        8654 | 0.000510517 |    0.0209312   |
| gldm_energy    | Mann-Whitney U |        8542 | 0.00109393  |    0.044851    |
| bmode_5        | Mann-Whitney U |        8507 | 0.00137636  |    0.0564309   |
| gldm_entropy   | Mann-Whitney U |        5151 | 0.00199607  |    0.0818388   |
| gldm_sde       | Mann-Whitney U |        5333 | 0.00596717  |    0.244654    |
| bmode_3        | Mann-Whitney U |        8233 | 0.00723493  |    0.296632    |
| bmode_6        | Mann-Whitney U |        8195 | 0.00893358  |    0.366277    |

## 第三阶段：端到端系统测试

| 指标 | 结果 |
|---|---|
| available | `True` |
| n | `250` |
| mean_runtime_ms | `1041.6438180021942` |
| median_runtime_ms | `952.9987999703736` |
| mean_quality_score | `0.6823245356072982` |
| unique_pred_labels | `['左心室收缩功能减低', '未见明确心脏超声异常']` |
| coarse_accuracy | `0.744` |
| coarse_macro_f1 | `0.63639669120989` |

## 解释

本报告由验证工作台自动生成。若数据集缺少标签，分类、回归或显著性检验会标记为不可用；这不代表程序失败，而是说明当前数据目录缺少相应金标准字段。