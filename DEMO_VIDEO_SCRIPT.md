# Five-Minute Demo Video Script

Target length: 4 minutes 30 seconds to 4 minutes 50 seconds.

## 0:00-0:30 Opening

Show the project title and the PC repository online demo.

Voice-over:

CardioConsult PC V5 is an offline Gemma 4 edge-AI prototype for medical education and primary-care ultrasound reference. The target users are ultrasound beginners and primary-care sites without immediate access to echocardiography specialists. The app runs locally and outputs a clear teaching-reference disease label, such as mild mitral regurgitation or suspected reduced left-ventricular systolic function, while keeping a strict medical safety boundary.

## 0:30-1:20 Input Workflow

Show importing multiple files in the browser demo or the PC V5 app.

Demonstrate:

- PNG/JPG input.
- DICOM/DCOM input.
- Cine/video input if available.
- Multiple files in one study.

Voice-over:

The input contract is the same across versions: the user can provide one or more de-identified cardiac ultrasound files. The ideal maximum is the standard 12-view echocardiography set. The minimum is any one view with systolic and diastolic frames; if phase labels are missing, the system estimates phase from image proxies.

## 1:20-2:20 Edge Feature Pipeline

Show the feature summary and flow overlay.

Voice-over:

The edge pipeline separates B-mode and Color Doppler logic. B-mode frames use robust normalization, speckle suppression, local contrast enhancement, edge and texture features, and chamber-area proxies. Color Doppler frames use HSV-based blood-flow vectorization, connected-component filtering, jet-width proxy, direction consistency, turbulence proxy, and vorticity proxy. These features are fused into a structured study summary before Gemma 4 report generation.

## 2:20-3:10 Offline Gemma 4

Show the PC V5 repository, model placement in `models/`, and the fast server launcher.

Voice-over:

The design is offline-first. The Windows PC V5 repository uses local Gemma4 4B GGUF with `llama-cli`, and also supports a persistent `llama-server` mode through `run_cardio_pc_v4_fast_server.bat` so repeated diagnoses do not reload the model every time. If the model file is absent during a live demo, the deterministic edge-rule fallback still produces the same output contract, so the workflow remains runnable.

## 3:10-4:05 Output And Safety

Show the final diagnosis text.

Voice-over:

The output starts with a hierarchical teaching label: large disease direction, middle category, smallest specific disease, severity, and evidence sufficiency. The system also shows a logic chain and beginner guidance, such as which FoCUS views are missing and what to rescan. This is a teaching-reference output only. It is not a medical device, not a clinical final diagnosis, and must be reviewed by a qualified clinician.

## 4:05-4:40 Validation And Submission Package

Show `SUBMISSION.md`, the PC V5 README, `DATASETS.md`, and the technical report.

Voice-over:

The submission includes a technical report in APA format, validation reports, dataset-source disclosure, Apache 2.0 license, static online demo source, and Windows PC deployment instructions. The PC V5 validation snapshot reports strong teaching-reference F1 for mitral and tricuspid regurgitation proxies on the authorized local DICOM set, and CAMUS / EchoNet-Dynamic validation improved low-EF sensitivity and overall coarse accuracy. Raw datasets, patient images, and model weights are not redistributed.

## 4:40-4:50 Closing

Voice-over:

CardioConsult demonstrates privacy-preserving edge AI for ultrasound education and primary-care support, using Gemma 4 as the local reasoning and reporting layer.

## Recording Checklist

- Keep video under 5 minutes.
- Show the online demo URL in the browser address bar.
- Show at least one successful diagnosis output.
- Show `run_cardio_pc_v5.bat` or `run_cardio_pc_v4_fast_server.bat`.
- Show `DATASETS.md` for data-source disclosure.
- Do not show any identifiable patient data.
