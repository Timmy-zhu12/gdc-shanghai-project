# Competitive Edge

CardioConsult is designed as an offline Gemma 4 edge-AI application with a realistic clinical-education workflow. The project is not only a model wrapper; it combines ultrasound-specific edge features, deterministic safety fallback, and Gemma 4 report generation into one reproducible Windows PC workflow.

## Why It Is Different

1. Offline-first healthcare scenario.

   The target setting is medical education and primary-care ultrasound reference where network access, specialist availability, and privacy tolerance may all be limited. The app can run locally and does not require raw patient data to leave the device.

2. Ultrasound-aware math before the LLM.

   B-mode frames are processed with robust normalization, speckle suppression, local contrast enhancement, texture/edge proxies, and chamber-area phase estimation. Color Doppler frames are processed separately with HSV vectorization, connected-component filtering, jet-width proxy, direction consistency, turbulence proxy, and vorticity proxy. Gemma 4 receives structured evidence rather than only an image caption.

3. Stable input and output contract.

   The PC V5 app and browser demo preserve the same user promise: import one or more de-identified PNG/JPG/DICOM/DCOM/cine files and receive one Chinese teaching-reference diagnosis paragraph with a specific smallest disease label, evidence chain, confidence, and safety boundary.

4. Hierarchical disease labels.

   The report starts from a broad disease direction, then narrows to middle category, smallest specific finding, severity, and evidence sufficiency. If evidence is incomplete, the system still emits a clear broad direction while explicitly stating what cannot be localized.

5. Demo resilience without hiding limitations.

   When a Gemma 4 model file is absent, unsupported, or too large for the current device, deterministic edge rules keep the demo runnable. The UI and report disclose whether the output came from Gemma 4 inference or rule fallback.

6. Device strategy.

   The current Windows PC V5 reference implementation is published in `Timmy-zhu12/gdc-shanghai-project` and uses local Gemma4 4B GGUF through `llama-cli` or persistent `llama-server` reuse. V5 adds EchoNet-Dynamic dynamic B-mode calibration for EF / left-ventricular systolic dysfunction while preserving the auditable valve-regurgitation rules. Mobile and desktop ports can reuse the same shared diagnostic contract later, but they are not required for evaluating this submission.

7. Evidence package included.

   The repository includes APA-style technical reporting, dataset-source disclosure, validation reports, validation DOCX files, online demo source, deployment notes, safety policy, Apache 2.0 license, and Windows PC README instructions.

## Judge Demo Focus

- Open with the online demo so reviewers see the product immediately.
- Show the PC V5 reference app from `https://github.com/Timmy-zhu12/gdc-shanghai-project` for the fullest offline workflow, using `run_cardio_pc_v5.bat`; use `run_cardio_pc_v4_fast_server.bat` first when repeated local GGUF calls should reuse a warm llama.cpp server.
- Show `DATASETS.md` and the validation bundle to establish credibility.
- End with the strict safety boundary: medical teaching reference only, not a clinical diagnosis or medical device output.
