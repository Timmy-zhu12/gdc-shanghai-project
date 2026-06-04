# CardioConsult 密集验证总报告

## 三阶段计划

1. 第一阶段：B-Mode 算法验证，覆盖预处理、GLDM 特征、PSNR/SNR、特征与分类/回归代理任务的关系。
2. 第二阶段：彩色多普勒算法验证，覆盖 Doppler 活跃区、连通域、喷流宽度、方向一致性、散度和涡量代理；当 EchoXFlow 或 MR 数据导入后，可扩展速度场误差和 Q 判据。
3. 第三阶段：系统集成与端到端测试，统计诊断文本标签、运行时间、质量分和粗粒度一致性。

## 数据集报告

- `CAMUS`: D:\cardioconsult_dense_validation\reports\CAMUS_report.md
- `EchoNet-Dynamic`: D:\cardioconsult_dense_validation\reports\EchoNet-Dynamic_report.md
- `HMC-QU`: D:\cardioconsult_dense_validation\reports\HMC-QU_report.md
- `EchoXFlow`: D:\cardioconsult_dense_validation\reports\EchoXFlow_report.md
- `MR_Ultrasound_Images`: D:\cardioconsult_dense_validation\reports\MR_Ultrasound_Images_report.md
- `local_smoke`: D:\cardioconsult_dense_validation\reports\local_smoke_report.md

## 合规说明

本工作台不会绕过医学数据集许可。EchoNet-Dynamic、HMC-QU、EchoXFlow 或 MR Ultrasound Images 如需账号、申请或机构授权，应由授权用户取得后放入 manifest 指定目录。