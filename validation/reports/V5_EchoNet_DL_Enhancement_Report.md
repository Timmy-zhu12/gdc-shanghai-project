# CardioConsult PC V5 EchoNet-Dynamic 增强报告

生成日期：2026-06-04

## 目标

V5 在保持 V4 输入输出行为不变的基础上，新增本地训练流程和轻量级动态心脏超声校准层。目标是在不背离本地、低成本、边缘可计算设计的前提下，扩大系统对心脏超声可见问题的覆盖范围。

## 改动内容

- 创建隔离的 V5 开发目录，并将可运行 PC 参考实现同步到本仓库。
- 复用 V4 PC 应用行为，不修改历史 V4 快照。
- 新增 `cardio_pc/v5_echonet.py`。
- 新增 `tools/train_echonet_v5.py`。
- 新增 V5 启动和训练 BAT 脚本。
- 新增训练后模型文件：`models/echonet_v5_lowef_mlp.joblib`。
- 新增 V5 运行时后备：如果训练模型不可用，V5 会退回 V4 行为。

## 数据集使用

新增使用的数据集是 EchoNet-Dynamic：

- `FileList.csv`：10,030 个视频，含 EF、ESV、EDV、FPS、帧数和 TRAIN/VAL/TEST 划分。
- `VolumeTracings.csv`：专家左室追踪帧。
- `Videos`：10,030 个 A4C `.avi` 心脏超声视频。

EchoNet-Dynamic 只用于动态 B-mode EF / 左室收缩功能校准，不用于训练瓣膜反流标签。

## 模型设计

V5 特征向量包含：

- B-mode 均值和标准差特征。
- 腔室面积与时间差分特征。
- 面向左室的暗腔面积、质心、宽度和高度特征。
- 最小面积帧、最大面积帧和平均帧的低维缩略图特征。

候选模型包括 Ridge 回归、HistGradientBoostingRegressor、MLPRegressor、LogisticRegression、HistGradientBoostingClassifier、RandomForestClassifier 和 MLPClassifier。最终选择 EF 用 HistGradientBoostingRegressor，低 EF 用 LogisticRegression。MLP 候选模型已训练和评估，但最终选择依据验证集指标。

## 训练运行

| 运行 | train | validation | test | 摘要 |
|---|---:|---:|---:|---|
| Smoke Run | 120 | 40 | 40 | 链路验证通过，样本过少 |
| Balanced Run | 600 | 160 | 160 | EF MAE 7.82，EF 相关系数 0.541，低 EF F1 0.413，AUC 0.697 |
| Large Run | 1200 | 300 | 300 | 每个视频最多 16 帧，作为最终报告指标 |

最终 large-run 指标：

| 指标 | 数值 |
|---|---:|
| EF MAE | 7.271 |
| EF RMSE | 9.603 |
| EF 相关系数 | 0.647 |
| 低 EF 准确率 | 0.770 |
| 低 EF 精确率 | 0.479 |
| 低 EF 召回率 | 0.515 |
| 低 EF F1 | 0.496 |
| 低 EF AUC | 0.764 |

## 本地 60 例回归验证

启用 V5 模型后，重新运行了本地 60 例报告链接验证。60/60 例运行成功，总耗时 221.564 秒，平均 3.68785 秒/例，未调用 GGUF。

| 标签 | F1 |
|---|---:|
| 任意瓣膜异常 | 1.000 |
| MR | 0.964 |
| TR | 1.000 |
| AR | 0.700 |
| 低 EF | 0.857 |
| RWMA | 0.500 |
| 左房扩大 | 0.696 |

V5 动态校准没有破坏既有本地瓣膜反流结果。

## 取舍、限制与建议

V5 没有训练大型端到端 CNN/Transformer，而是采用轻量候选模型 + 验证集选择 + 可审计规则后备的混合设计。这牺牲了理论最高精度，换取本地可部署性、可复现性和低运行成本。

低 EF 分类器有教学参考价值，但还不是临床级 EF 估计器。下一步若目标设备预算允许，应训练真正轻量的分割模型，或基于 EchoNet 追踪标注训练 ONNX/TFLite 模型。

V5 推荐用于动态 B-mode/cine 输入、EF/左室收缩功能减低教学标签，以及移动端迁移前的回归测试。若只展示瓣膜反流行为，可继续把 V4 作为稳定后备。
