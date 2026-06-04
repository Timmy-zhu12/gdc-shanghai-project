# 数据集来源与使用边界

CardioConsult 以源代码和原型仓库形式提交。本仓库不再分发公开数据集原始文件、受限研究数据集、私有教学病例或模型权重。

除非文件特别说明，仓库内示例均为合成或生成的演示资产。真实病人数据必须完成脱敏，并且只能在用户所在机构授权范围内使用。

## 数据集清单

| 数据集 | 来源 | 主要内容 | 在本项目中的用途 | 再分发状态 |
|---|---|---|---|---|
| CAMUS | [CREATIS CAMUS database](https://www.creatis.insa-lyon.fr/Challenge/camus/databases.html) | 500 例匿名心脏超声，含 A2C/A4C、ED/ES 帧、分割标签、EF 与容积信息 | B-mode 验证、ED/ES 相位逻辑、低 EF 校准、左室功能标签设计 | 不随仓库分发 |
| EchoNet-Dynamic | [Stanford EchoNet-Dynamic](https://echonet.github.io/dynamic/) 与 [AIMI 数据页](https://aimi.stanford.edu/datasets/echonet-dynamic-cardiac-ultrasound) | 10,030 个 A4C 心超视频，含 EF、EDV、ESV 和左室追踪 | 动图兼容、EF/容积评估、动态帧流程与 V5 校准 | 不分发；遵守 Stanford 研究使用条款 |
| EchoNet-LVH | [Stanford EchoNet-LVH](https://echonet.github.io/lvh/) | 12,000 个 PLAX 心超视频，含室壁厚度测量 | 左室肥厚标签层级和 PLAX 测量路线 | 不分发；遵守 Stanford 研究使用条款 |
| TMED-2 | [Tufts Medical Echocardiogram Dataset](https://tmed.cs.tufts.edu/tmed_v2.html) | PLAX/PSAX/A2C/A4C/其他切面标签，以及主动脉瓣狭窄分级 | 切面标签、主动脉瓣狭窄分级和文档设计 | 不随仓库分发 |
| HMC-QU | [HMC-QU 论文](https://arxiv.org/abs/2010.02281) 与 [数据集摘要](https://hyper.ai/en/datasets/38456/) | A4C/A2C 心肌梗死心超记录和左室壁分割 | 心肌梗死/区域室壁运动异常验证计划 | 不随仓库分发 |
| EchoXFlow | [arXiv:2605.05447](https://arxiv.org/abs/2605.05447) | beamspace 心超、Doppler 流、ECG 与标注 | Color Doppler 和向量血流路线图；不作为仓库内训练数据 | 不随仓库分发 |
| 二尖瓣反流彩色多普勒图像 | [二尖瓣反流分割与评估研究](https://pmc.ncbi.nlm.nih.gov/articles/PMC11591529/) | 367 张 A4C 彩色多普勒图，文献中分为轻/中/重度 MR | MR 分级标签体系参考；本仓库没有下载分发该数据 | 不随仓库分发 |
| MIMIC-IV-ECHO | [PhysioNet MIMIC-IV-ECHO](https://physionet.org/content/mimic-iv-echo/) | 与 MIMIC-IV 临床记录关联的超声测量和 DICOM 文件 | 宽病症层级、Doppler 测量、报告-图像一致性后续验证 | 不分发；需 PhysioNet 认证访问 |
| ECHOVIEW | [PhysioNet ECHOVIEW](https://www.physionet.org/content/echoview/) | MIMIC-IV-ECHO 视频细粒度切面标注 | 切面分类扩展和 FoCUS 完整性路线图 | 不分发；需 PhysioNet 认证访问 |
| CACTUS | [Academic Torrents CACTUS](https://academictorrents.com/details/329c0ee4a0037a2628e2f2dba826066f764f193c) 与 [论文](https://arxiv.org/abs/2503.05604) | 心脏超声仿体图像、切面与质量分级 | 初学者图像质量和扫查引导路线图 | 不随仓库分发 |
| 本地教学集 | 用户授权提供的脱敏教学图像 | PNG/DICOM，例如轻度二尖瓣反流、轻度三尖瓣反流病例 | 本地 smoke test 和规则调参 | 不提交、不再分发 |

## 这些来源如何影响产品

本项目不声明临床验证诊断能力。公开数据集主要用于塑造和测试教学原型：

- CAMUS 与 EchoNet-Dynamic 用于 B-mode 分支、ED/ES 相位、EF 相关教学标签和动图支持。
- TMED-2 与 EchoNet-LVH 用于 PLAX/PSAX/A2C/A4C 工作流中的切面和病症层级扩展。
- EchoXFlow 与彩色多普勒文献用于 Doppler 向量路线图，以及当前 HSV/血流向量代理特征。
- MIMIC-IV-ECHO、ECHOVIEW 和 CACTUS 列为后续验证与标签扩展方向，尤其是切面分类、图像质量和报告关联疾病类别。
- 本地脱敏样例只用于本机 smoke test，不离开本地机器。

## 数据与合规规则

- 不提交原始 DICOM、原始数据集下载、病人图像、生成诊断报告或模型权重。
- 不共享 Stanford EchoNet 下载链接或文件；每个使用者需自行注册并遵守数据集条款。
- 不再分发 MIMIC-IV-ECHO、ECHOVIEW 等 PhysioNet 认证数据集。
- 不尝试重新识别病人。
- 所有临床相关表述均限定为医学教学、算法演示和基层参考支持。
- 超出教学/原型评估的使用，必须重新经过伦理审查、医疗器械合规审查和临床医师验证。

## APA 引用来源

以下条目保留 APA 原文题名、期刊名、DOI 与 URL，便于评审核验来源；中文说明已在上文给出。

Leclerc, S., Smistad, E., Pedrosa, J., Ostvik, A., Cervenansky, F., Espinosa, F., Espeland, T., Berg, E. A. R., Jodoin, P.-M., Grenier, T., Lartizien, C., D'Hooge, J., Lovstakken, L., & Bernard, O. (2019). Deep learning for segmentation using an open large-scale dataset in 2D echocardiography. *IEEE Transactions on Medical Imaging*. https://www.creatis.insa-lyon.fr/Challenge/camus/databases.html

Ouyang, D., He, B., Ghorbani, A., Yuan, N., Ebinger, J., Langlotz, C. P., Heidenreich, P. A., Harrington, R. A., Liang, D. H., Ashley, E. A., & Zou, J. Y. (2020). Video-based AI for beat-to-beat assessment of cardiac function. *Nature*. https://echonet.github.io/dynamic/

Duffy, G., Cheng, P. P., Yuan, N., He, B., Kwan, A. C., Shun-Shin, M. J., ... & Ouyang, D. (2022). High-throughput precision phenotyping of left ventricular hypertrophy with cardiovascular deep learning. *JAMA Cardiology*. https://echonet.github.io/lvh/

Huang, Z., Long, W., Li, B., et al. (2022). TMED-2: A dataset for semi-supervised classification of echocardiograms. https://tmed.cs.tufts.edu/tmed_v2.html

Stenhede, E., Sulkowska, J., Orstad, E. B., Schirmer, H., & Ranjbar, A. (2026). EchoXFlow: A beamspace echocardiography dataset for cardiac motion, flow, and function. *arXiv*. https://arxiv.org/abs/2605.05447

Gow, B., Pollard, T., Greenbaum, N., Moody, B., Han, A., Waks, J. W., Johnson, A., Herbst, E., Eslami, P., Chaudhari, A., Carbonati, T., Berkowitz, S., Mark, R., & Horng, S. (2026). *MIMIC-IV-ECHO: Echocardiogram matched subset* (Version 1.0). PhysioNet. https://doi.org/10.13026/nrjh-5r77

Rapuri, S., Dias, S. S., Carvalho, M. S., Lizzappi, M., Harris, C., & Stevens, R. (2026). *Structured viewing classification annotations from the MIMIC-IV-ECHO dataset (ECHOVIEW)* (Version 0.1). PhysioNet. https://doi.org/10.13026/ywz0-5b62

Elmekki, H., Alagha, A., Sami, H., Spilkin, A., Zanuttini, A. M., Zakeri, E., Bentahar, J., Kadem, J., Xie, W. F., Pibarot, P., Mizouni, R., Otrok, H., Singh, S., & Mourad, A. (2025). CACTUS: An open dataset and framework for automated cardiac assessment and classification of ultrasound images using deep transfer learning. *Computers in Biology and Medicine, 190*, 110003. https://doi.org/10.1016/j.compbiomed.2025.110003
