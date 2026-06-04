# Dataset Sources and Use Boundaries

CardioConsult is submitted as a source-code and prototype repository. Raw public datasets, restricted research datasets, private teaching cases, and model weights are not redistributed in this repository.

All examples included in the repository are synthetic or generated demonstration assets unless a file explicitly says otherwise. Real patient data must be de-identified and used only under the user's institutional authorization.

## Dataset Inventory

| Dataset | Source | What It Provides | CardioConsult Use | Redistribution Status |
|---|---|---|---|---|
| CAMUS | [CREATIS CAMUS database](https://www.creatis.insa-lyon.fr/Challenge/camus/databases.html) | 500 anonymized cardiac ultrasound exams with A2C/A4C views, ED/ES frames, segmentation labels, EF and volume metadata | B-mode validation, ED/ES phase logic, low-EF calibration, LV function label design | Not redistributed |
| EchoNet-Dynamic | [Stanford EchoNet-Dynamic](https://echonet.github.io/dynamic/) and [AIMI dataset page](https://aimi.stanford.edu/datasets/echonet-dynamic-cardiac-ultrasound) | 10,030 A4C echocardiography videos with EF, EDV, ESV, and LV tracings | Cine/video compatibility planning, EF/volume evaluation design, dynamic-frame workflow | Not redistributed; Stanford research-use terms apply |
| EchoNet-LVH | [Stanford EchoNet-LVH](https://echonet.github.io/lvh/) | 12,000 PLAX echocardiography videos with wall-thickness measurements | LVH label hierarchy and PLAX measurement roadmap | Not redistributed; Stanford research-use terms apply |
| TMED-2 | [Tufts Medical Echocardiogram Dataset](https://tmed.cs.tufts.edu/tmed_v2.html) | PLAX/PSAX/A2C/A4C/other view labels and aortic stenosis severity labels | View-label hierarchy, AS severity labels, repository documentation | Not redistributed |
| HMC-QU | [HMC-QU dataset paper](https://arxiv.org/abs/2010.02281) and [dataset summary](https://hyper.ai/en/datasets/38456/) | A4C/A2C myocardial infarction echo records and LV-wall segmentation masks | MI / regional wall-motion abnormality validation plan | Not redistributed |
| EchoXFlow | [arXiv:2605.05447](https://arxiv.org/abs/2605.05447) | Beamspace echocardiography with modality-specific 1D/2D/3D data, Doppler streams, ECG and annotations | Color Doppler and vector-flow roadmap; not used as bundled training data | Not redistributed |
| Mitral regurgitation color Doppler images | [Segmentation and evaluation of mitral regurgitation study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11591529/) | 367 A4C color Doppler images categorized as mild, moderate and severe MR in the publication | Label-system reference for MR severity; not used as a downloaded dataset in this repo | Not redistributed |
| MIMIC-IV-ECHO | [PhysioNet MIMIC-IV-ECHO](https://physionet.org/content/mimic-iv-echo/) | Structured echocardiographic measurements and DICOM files linked to MIMIC-IV clinical records | Future validation roadmap for broad disease hierarchy, Doppler-derived measurements, and report-to-image consistency | Not redistributed; credentialed PhysioNet access and terms apply |
| ECHOVIEW | [PhysioNet ECHOVIEW](https://www.physionet.org/content/echoview/) | Granular view classifications for MIMIC-IV-ECHO videos | View-label expansion and FoCUS completeness roadmap | Not redistributed; credentialed PhysioNet access and terms apply |
| CACTUS | [Academic Torrents CACTUS dataset](https://academictorrents.com/details/329c0ee4a0037a2628e2f2dba826066f764f193c) and [paper](https://arxiv.org/abs/2503.05604) | Cardiac ultrasound phantom images with view and quality grading | Beginner image-quality and view-guidance roadmap | Not redistributed |
| Local teaching set | User-provided, de-identified teaching images under project authorization | PNG/DICOM examples such as mild mitral regurgitation and mild tricuspid regurgitation cases | Local smoke tests and rule tuning only | Not committed or redistributed |

## How These Sources Affect the Product

The project does not claim clinically validated diagnosis. Public datasets are used to shape and test the teaching prototype:

- CAMUS and EchoNet-Dynamic inform the B-mode branch, ED/ES handling, EF-related teaching labels, and cine support.
- TMED-2 and EchoNet-LVH inform view and disease hierarchy expansion for PLAX/PSAX/A2C/A4C workflows.
- EchoXFlow and color Doppler literature inform the Doppler-vector roadmap and the current HSV/vector-flow proxy features.
- MIMIC-IV-ECHO, ECHOVIEW, and CACTUS are listed for future validation and label expansion, especially view classification, image quality, and broad report-linked disease categories.
- Local de-identified examples are used only for smoke testing and do not leave the local machine.

## Data and Compliance Rules

- Do not commit raw DICOM, raw dataset downloads, local patient images, generated diagnosis reports, or model weights.
- Do not share Stanford EchoNet download links or files; every user must register and comply with the dataset terms.
- Do not redistribute PhysioNet credentialed datasets such as MIMIC-IV-ECHO or ECHOVIEW.
- Do not attempt re-identification.
- Keep all clinical use claims framed as medical education, algorithm demonstration, and primary-care reference support only.
- Any use beyond teaching/prototype evaluation requires IRB/ethics review, medical-device compliance review, and clinician validation.

## APA-Style Source List

Leclerc, S., Smistad, E., Pedrosa, J., Ostvik, A., Cervenansky, F., Espinosa, F., Espeland, T., Berg, E. A. R., Jodoin, P.-M., Grenier, T., Lartizien, C., D'Hooge, J., Lovstakken, L., & Bernard, O. (2019). Deep learning for segmentation using an open large-scale dataset in 2D echocardiography. *IEEE Transactions on Medical Imaging*. https://www.creatis.insa-lyon.fr/Challenge/camus/databases.html

Ouyang, D., He, B., Ghorbani, A., Yuan, N., Ebinger, J., Langlotz, C. P., Heidenreich, P. A., Harrington, R. A., Liang, D. H., Ashley, E. A., & Zou, J. Y. (2020). Video-based AI for beat-to-beat assessment of cardiac function. *Nature*. https://echonet.github.io/dynamic/

Duffy, G., Cheng, P. P., Yuan, N., He, B., Kwan, A. C., Shun-Shin, M. J., ... & Ouyang, D. (2022). High-throughput precision phenotyping of left ventricular hypertrophy with cardiovascular deep learning. *JAMA Cardiology*. https://echonet.github.io/lvh/

Huang, Z., Long, W., Li, B., et al. (2022). TMED-2: A dataset for semi-supervised classification of echocardiograms. https://tmed.cs.tufts.edu/tmed_v2.html

Stenhede, E., Sulkowska, J., Orstad, E. B., Schirmer, H., & Ranjbar, A. (2026). EchoXFlow: A beamspace echocardiography dataset for cardiac motion, flow, and function. *arXiv*. https://arxiv.org/abs/2605.05447

Gow, B., Pollard, T., Greenbaum, N., Moody, B., Han, A., Waks, J. W., Johnson, A., Herbst, E., Eslami, P., Chaudhari, A., Carbonati, T., Berkowitz, S., Mark, R., & Horng, S. (2026). *MIMIC-IV-ECHO: Echocardiogram matched subset* (Version 1.0). PhysioNet. https://doi.org/10.13026/nrjh-5r77

Rapuri, S., Dias, S. S., Carvalho, M. S., Lizzappi, M., Harris, C., & Stevens, R. (2026). *Structured viewing classification annotations from the MIMIC-IV-ECHO dataset (ECHOVIEW)* (Version 0.1). PhysioNet. https://doi.org/10.13026/ywz0-5b62

Elmekki, H., Alagha, A., Sami, H., Spilkin, A., Zanuttini, A. M., Zakeri, E., Bentahar, J., Kadem, J., Xie, W. F., Pibarot, P., Mizouni, R., Otrok, H., Singh, S., & Mourad, A. (2025). CACTUS: An open dataset and framework for automated cardiac assessment and classification of ultrasound images using deep transfer learning. *Computers in Biology and Medicine, 190*, 110003. https://doi.org/10.1016/j.compbiomed.2025.110003
