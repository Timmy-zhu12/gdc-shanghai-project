# 数据集下载状态

更新时间：2026-06-01

## 已完成

### CAMUS

- 状态：已通过官方 Girder API 全量下载完成。
- 本地目录：`D:\cardioconsult_dense_validation\datasets\CAMUS\girder_items`
- 完整性校验：`7501 / 7501` 个远程文件尺寸匹配，缺失 `0`，异常 `.part` 文件 `0`。
- NIfTI 媒体文件：`6000` 个。
- 总字节数：`3833308612`。
- 许可：`CC BY-NC-SA 4.0`，仅非商业科研用途，并需引用 CAMUS 原论文。
- 清单：`D:\cardioconsult_dense_validation\datasets\CAMUS\camus_girder_manifest.json`
- 下载摘要：`D:\cardioconsult_dense_validation\datasets\CAMUS\camus_download_summary.json`
- 官方入口：`https://www.creatis.insa-lyon.fr/Challenge/camus/`

## 需要凭据或授权

### HMC-QU

- 状态：本机未检测到 Kaggle 凭据，尚未下载。
- 官方入口：`https://www.kaggle.com/datasets/aysendegerli/hmcqu-dataset`
- 本地目标目录：`D:\cardioconsult_dense_validation\datasets\HMC-QU`
- 需要你提供：Kaggle API token，通常放在 `%USERPROFILE%\.kaggle\kaggle.json`，或设置 `KAGGLE_USERNAME` / `KAGGLE_KEY`。
- 凭据配置后运行：

```powershell
Set-Location D:\cardioconsult_dense_validation
.\.venv\Scripts\python.exe -m pip install -r requirements-optional.txt
.\.venv\Scripts\python.exe scripts\download_datasets.py --manifest config\datasets.json --try-kaggle
```

### EchoNet-Dynamic

- 状态：官方要求通过 Stanford AIMI / EchoNet-Dynamic research-use agreement 获取；未使用第三方镜像。
- 官方入口：`https://echonet.github.io/dynamic/`
- AIMI 入口：`https://aimi.stanford.edu/datasets/echonet-dynamic-cardiac-ultrasound`
- 本地目标目录：`D:\cardioconsult_dense_validation\datasets\EchoNet-Dynamic`
- 需要你提供：完成 Stanford/AIMI 授权后的下载文件或官方 portal 下载入口。该数据集条款明确不应共享个人下载链接，因此脚本不会绕过此流程。

## 暂未发现可直接下载入口

### EchoXFlow

- 状态：已检索公开入口，当前只确认论文/摘要公开，未确认可匿名批量下载数据包。
- 论文入口：`https://arxiv.org/abs/2605.05447`
- 本地目标目录：`D:\cardioconsult_dense_validation\datasets\EchoXFlow`
- 需要你提供：作者或机构发布的正式数据入口、授权文件，或本地已获授权的数据副本。

### MR Ultrasound Images

- 状态：公开论文说明多为私有或机构数据；未确认有标准开放批量下载包。
- 参考入口：`https://pmc.ncbi.nlm.nih.gov/articles/PMC11591529/`
- 本地目标目录：`D:\cardioconsult_dense_validation\datasets\MR_Ultrasound_Images`
- 需要你提供：已授权的二尖瓣反流 Color Doppler 图像/视频与标签，或该数据集的正式开放下载入口。

## 已完成的验证运行

- CAMUS：已处理，`features.csv` 生成 `1152` 行，端到端抽样 `250` 行，错误 `0`。
- local_smoke：已处理，`features.csv` 生成 `34` 行，端到端 `12` 行，错误 `0`。
- 总报告：`D:\cardioconsult_dense_validation\reports\MASTER_VALIDATION_REPORT.md`
- CAMUS 报告：`D:\cardioconsult_dense_validation\reports\CAMUS_report.md`
