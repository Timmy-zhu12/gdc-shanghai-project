# Data And Model Policy

This repository is intentionally source-code-only.

Full dataset attribution and use boundaries are maintained in [../DATASETS.md](../DATASETS.md).

Do not commit:

- GGUF model weights
- Real patient DICOM files
- Raw medical image datasets
- Dataset download caches
- Local diagnosis exports
- `config.json`
- local SDK or IDE configuration files
- Any file containing patient identifiers

Recommended local paths:

| Resource | Local example |
|---|---|
| PC model weights | `models/` or external model storage |
| Validation datasets | `D:/cardioconsult_dense_validation/datasets` |
| Validation generated results | `D:/cardioconsult_dense_validation/results` |

All third-party datasets, SDKs, ultrasound software, app-store assets, trademarks, and model weights remain governed by their own terms.

The project uses dataset-derived validation summaries and hand-authored label mappings only. It does not redistribute CAMUS, EchoNet-Dynamic, EchoNet-LVH, TMED-2, HMC-QU, EchoXFlow, MIMIC-IV-ECHO, ECHOVIEW, CACTUS, private teaching data, or any raw DICOM/PNG patient files.
