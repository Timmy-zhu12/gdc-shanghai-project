# Competition Alignment

Official page checked: [Gemma 4 Hackathon 2026](https://hackathon.googdg.cn/?lang=en)

## Parsed Requirements

The official Track C description emphasizes Edge AI: fully offline deployment of E2B/E4B-class models on phones, Raspberry Pi, or embedded hardware, with a real-device demo. The final submission requires:

- code repository
- demo video within 5 minutes
- technical report
- online demo URL
- disclosure of training data sources

The judging criteria are:

| Criterion | Weight |
|---|---:|
| Real-world impact | 30% |
| Technical excellence | 25% |
| Completeness | 20% |
| Innovation | 15% |
| Presentation quality | 10% |

## Changes Applied To This PC Repository

| Requirement pressure | Repository change |
|---|---|
| Runnable code repository | V4 code synchronized into this PC repo; legacy launchers route to V4 |
| Offline edge model | Added portable `config.example.json`, bundled llama.cpp runtime, and persistent `llama-server` launcher |
| Completeness | Added rule-only smoke test via `app.py --self-test-rule-only` |
| Presentation quality | Rewrote README with deployment steps, model placement, validation snapshot, and safety boundary |
| Data/model compliance | Kept `.gguf` weights out of Git and documented `models/` placement |
| Demo robustness | Added fallback chain: server -> CLI -> local auditable rule engine |

## Remaining Manual Submission Items

- Record or upload the final 5-minute demo video and put that link in the competition form.
- Keep the main repository as the public entry point:
  <https://github.com/Timmy-zhu12/Track-C-gdc-project-shanghai-Total-Repository>
- Keep this repository focused on the Windows PC reference app:
  <https://github.com/Timmy-zhu12/gdc-shanghai-project>
