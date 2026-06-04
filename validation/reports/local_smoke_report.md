# local_smoke 测试报告

- 本地路径：`D:/cardioconsult_dense_validation/datasets/local_smoke`
- 官方入口：N/A
- 下载/导入方式：`generated`
- 验证阶段：`phase1_bmode, phase2_doppler, phase3_end_to_end`
- 扫描到的媒体文件：`12`
- 已处理特征行：`34`
- 已处理端到端行：`12`
- 错误数：`0`

## 数据状态

- 特征表：`D:\cardioconsult_dense_validation\results\local_smoke\features.csv` 存在
- 端到端表：`D:\cardioconsult_dense_validation\results\local_smoke\end_to_end.csv` 存在
- 说明：由本地 CardioConsult 自检图像生成器创建的合成 smoke-test 数据集。

## 第一阶段：B-Mode / GLDM 特征验证

| 指标 | 结果 |
|---|---|
| available | `True` |
| n | `9` |
| unit | `case_level` |
| classes | `['low_contractility_proxy', 'normal', 'regurgitation_proxy']` |
| accuracy | `0.3333333333333333` |
| macro_f1 | `0.3333333333333333` |
| confusion_matrix | `[[0, 3, 0], [3, 0, 0], [0, 0, 3]]` |

## 回归 / EF 相关验证

| 指标 | 结果 |
|---|---|
| available | `True` |
| n | `9` |
| unit | `case_level` |
| rmse | `14.752602997919318` |
| mae | `12.964890750138649` |
| pearson_r | `-0.42580706737637564` |
| pearson_p | `0.2531596209712036` |
| spearman_r | `-0.2738612787525831` |
| spearman_p | `0.4757972385180242` |

## 特征显著性检验

| feature                       | test           |   statistic |   p_value |   p_bonferroni |
|:------------------------------|:---------------|------------:|----------:|---------------:|
| bmode_9                       | Kruskal-Wallis |     6.48889 | 0.0389902 |              1 |
| gldm_dependence_nonuniformity | Kruskal-Wallis |     6.48889 | 0.0389902 |              1 |
| gldm_mean_dependence          | Kruskal-Wallis |     5.95556 | 0.0509058 |              1 |
| doppler_11                    | Kruskal-Wallis |     5.91515 | 0.0519447 |              1 |
| gldm_lde                      | Kruskal-Wallis |     5.6     | 0.0608101 |              1 |
| doppler_13                    | Kruskal-Wallis |     5.6     | 0.0608101 |              1 |
| doppler_0                     | Kruskal-Wallis |     5.6     | 0.0608101 |              1 |
| bmode_11                      | Kruskal-Wallis |     5.6     | 0.0608101 |              1 |
| doppler_4                     | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| doppler_3                     | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| doppler_2                     | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| doppler_6                     | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| doppler_8                     | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| doppler_5                     | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| psnr                          | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| doppler_9                     | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| doppler_7                     | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| gldm_contrast                 | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| doppler_10                    | Kruskal-Wallis |     5.42222 | 0.0664629 |              1 |
| gldm_lgze                     | Kruskal-Wallis |     4.62222 | 0.099151  |              1 |

## 第三阶段：端到端系统测试

| 指标 | 结果 |
|---|---|
| available | `True` |
| n | `12` |
| mean_runtime_ms | `461.72334166476503` |
| median_runtime_ms | `382.8621000284329` |
| mean_quality_score | `0.4841226635291241` |
| unique_pred_labels | `['中度三尖瓣反流', '图像证据不足', '左心室收缩功能减低']` |
| coarse_accuracy | `0.5` |
| coarse_macro_f1 | `0.375` |

## 解释

本报告由验证工作台自动生成。若数据集缺少标签，分类、回归或显著性检验会标记为不可用；这不代表程序失败，而是说明当前数据目录缺少相应金标准字段。
