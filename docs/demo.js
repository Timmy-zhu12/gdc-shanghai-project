(() => {
  const SIZE = 256;
  const MAX_DYNAMIC_FRAMES = 24;
  const DICOM_SCAN_VALUE_LIMIT = 4096;
  const VIDEO_EXTENSIONS = new Set(["mp4", "m4v", "mov", "avi", "mkv", "webm", "wmv", "mpg", "mpeg", "3gp", "cine"]);
  const DICOM_EXTENSIONS = new Set(["dcm", "dicom", "dcom"]);

  const LOW_EF = {
    means: [
      0.3439935179, 0.1202890558, 0.0257984379, 0.0245626505,
      0.0402119582, 0.0737082141, 0.7069971181, 0.4954215066,
      0.1480851636, 0.0763964283, 0.0746771633, 1.3412349234,
      0.0336320823, 0.7312120198
    ],
    scales: [
      0.0320823992, 0.0130243928, 0.0025158036, 0.0021835693,
      0.0035243618, 0.0154935366, 0.0205262283, 0.0097401574,
      0.0088450145, 0.0618941601, 0.0176097238, 0.1334816438,
      0.0174574480, 0.0417555305
    ],
    coeffs: [
      0.6227405327, -0.0138485092, 0.2119849661, -0.2368895083,
      0.1975460847, 0.0613060324, 0.7014784635, 1.4841314955,
      0.2065621561, 0.2448794316, 0.7444971896, 0.4895215522,
      -0.5426316802, 1.0054161135
    ],
    intercept: 0.3068175790,
    threshold: 0.270
  };

  const state = {
    frames: [],
    analysis: null
  };

  const els = {
    fileInput: document.getElementById("fileInput"),
    dropZone: document.getElementById("dropZone"),
    sampleButton: document.getElementById("sampleButton"),
    analyzeButton: document.getElementById("analyzeButton"),
    resetButton: document.getElementById("resetButton"),
    fileList: document.getElementById("fileList"),
    filmstrip: document.getElementById("filmstrip"),
    previewCanvas: document.getElementById("previewCanvas"),
    diagnosisTitle: document.getElementById("diagnosisTitle"),
    confidenceText: document.getElementById("confidenceText"),
    reportText: document.getElementById("reportText"),
    featureText: document.getElementById("featureText"),
    modelStatus: document.getElementById("modelStatus"),
    metricFiles: document.getElementById("metricFiles"),
    metricViews: document.getElementById("metricViews"),
    metricDiastole: document.getElementById("metricDiastole"),
    metricSystole: document.getElementById("metricSystole")
  };

  els.fileInput.addEventListener("change", async (event) => {
    const files = [...event.target.files];
    await loadFiles(files);
  });

  els.dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    els.dropZone.classList.add("dragging");
  });

  els.dropZone.addEventListener("dragleave", () => {
    els.dropZone.classList.remove("dragging");
  });

  els.dropZone.addEventListener("drop", async (event) => {
    event.preventDefault();
    els.dropZone.classList.remove("dragging");
    await loadFiles([...event.dataTransfer.files]);
  });

  els.sampleButton.addEventListener("click", () => {
    state.frames = makeSampleFrames();
    state.analysis = null;
    renderFrames();
    analyzeAndRender();
  });

  els.analyzeButton.addEventListener("click", () => {
    if (state.frames.length === 0) {
      state.frames = makeSampleFrames();
      renderFrames();
    }
    analyzeAndRender();
  });

  els.resetButton.addEventListener("click", () => {
    state.frames = [];
    state.analysis = null;
    els.fileInput.value = "";
    renderFrames();
    renderEmpty();
  });

  renderEmpty();

  async function loadFiles(files) {
    if (files.length === 0) return;
    setBusy(true, "Loading files");
    const frames = [];
    const errors = [];
    for (const file of files) {
      try {
        frames.push(...await decodeFile(file));
      } catch (error) {
        errors.push(`${file.name}: ${error.message || error}`);
      }
    }
    state.frames = frames;
    state.analysis = null;
    renderFrames(errors);
    if (state.frames.length > 0) {
      analyzeAndRender();
    } else {
      renderEmpty(errors.join("\n") || "No supported frames were loaded.");
    }
    setBusy(false, "Browser edge demo");
  }

  async function decodeFile(file) {
    const extension = file.name.split(".").pop().toLowerCase();
    if (DICOM_EXTENSIONS.has(extension)) {
      return decodeDicomFile(file);
    }
    if (VIDEO_EXTENSIONS.has(extension) || file.type.startsWith("video/")) {
      return extractVideoFrames(file);
    }
    return decodeImageFrames(file);
  }

  async function decodeImageFrames(file) {
    const bitmap = await createImageBitmap(file);
    return [frameFromDrawable(bitmap, file.name, 0, "image")];
  }

  async function extractVideoFrames(file) {
    const url = URL.createObjectURL(file);
    const video = document.createElement("video");
    video.muted = true;
    video.playsInline = true;
    video.preload = "metadata";
    video.src = url;
    try {
      await once(video, "loadedmetadata");
      const duration = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 0;
      const count = duration > 0 ? Math.min(Math.max(Math.floor(duration / 0.5) + 1, 2), MAX_DYNAMIC_FRAMES) : 1;
      const frames = [];
      for (let index = 0; index < count; index += 1) {
        const time = count <= 1 || duration <= 0 ? 0 : duration * index / (count - 1);
        await seek(video, time);
        frames.push(frameFromDrawable(video, file.name, index, "video"));
      }
      return frames;
    } finally {
      URL.revokeObjectURL(url);
      video.removeAttribute("src");
    }
  }

  async function decodeDicomFile(file) {
    const meta = await parseDicomFile(file);
    const bytesPerSample = Math.max(Math.floor(meta.bitsAllocated / 8), 1);
    const samples = Math.max(meta.samplesPerPixel, 1);
    const frameBytes = meta.rows * meta.columns * samples * bytesPerSample;
    if (frameBytes <= 0 || meta.pixelOffset < 0 || meta.pixelLength <= 0) {
      throw new Error("missing readable DICOM/DCOM pixel data");
    }
    const available = Math.max(Math.floor(meta.pixelLength / frameBytes), 1);
    const frameCount = Math.min(Math.max(meta.numberOfFrames, 1), available);
    const selected = representativeIndices(frameCount, MAX_DYNAMIC_FRAMES);
    const frames = [];
    for (const frameIndex of selected) {
      const start = meta.pixelOffset + frameIndex * frameBytes;
      const frameBytesView = await readFileSlice(file, start, Math.min(start + frameBytes, file.size));
      if (frameBytesView.length < Math.min(frameBytes, file.size - start)) {
        continue;
      }
      const rgba = meta.samplesPerPixel >= 3 && meta.bitsAllocated === 8
        ? dicomRgb(frameBytesView, 0, meta)
        : dicomMono(frameBytesView, 0, meta);
      frames.push(resizeRgbaFrame(rgba, meta.columns, meta.rows, file.name, frameIndex, "dicom-stream", meta.metadata));
    }
    if (frames.length === 0) {
      throw new Error("no readable DICOM/DCOM frames after streaming decode");
    }
    return frames;
  }

  async function parseDicomFile(file) {
    const head = await readFileSlice(file, 0, Math.min(file.size, 160));
    let offset = head.length > 132 && ascii(head, 128, 4) === "DICM" ? 132 : 0;
    let transferSyntax = "";
    const meta = {
      rows: 0,
      columns: 0,
      samplesPerPixel: 1,
      bitsAllocated: 8,
      numberOfFrames: 1,
      photometric: "MONOCHROME2",
      windowCenter: null,
      windowWidth: null,
      pixelOffset: -1,
      pixelLength: -1,
      metadata: {}
    };

    if (offset === 132) {
      while (offset + 8 <= file.size) {
        const tag = await readDicomTagFromFile(file, offset, true);
        if (!tag || tag.group !== 0x0002) {
          break;
        }
        if (tagKey(tag.group, tag.element) === "0002,0010") {
          transferSyntax = await textValueFromFile(file, tag);
        }
        offset = nextOffsetForTag(tag, file.size);
      }
    }

    if (transferSyntax &&
      transferSyntax !== "1.2.840.10008.1.2" &&
      transferSyntax !== "1.2.840.10008.1.2.1") {
      throw new Error(`transfer syntax ${transferSyntax} requires a compressed/big-endian DICOM decoder not bundled in this browser demo`);
    }

    const explicit = transferSyntax === "1.2.840.10008.1.2" ? false : true;
    while (offset + 8 <= file.size) {
      const tag = await readDicomTagFromFile(file, offset, explicit);
      if (!tag) break;
      const key = tagKey(tag.group, tag.element);
      if (key === "7FE0,0010") {
        meta.pixelOffset = tag.offset;
        if (tag.length === 0xffffffff) {
          const firstBytes = await readFileSlice(file, tag.offset, Math.min(tag.offset + 8, file.size));
          if (firstBytes.length >= 4 && firstBytes[0] === 0xfe && firstBytes[1] === 0xff && firstBytes[2] === 0x00 && firstBytes[3] === 0xe0) {
            throw new Error("encapsulated/compressed DICOM pixel data is not supported in the browser demo");
          }
          meta.pixelLength = file.size - tag.offset;
        } else {
          meta.pixelLength = tag.length;
        }
        break;
      }

      if (tag.length === 0xffffffff) {
        offset = await findUndefinedLengthEnd(file, tag.offset);
        continue;
      }

      if (key === "0028,0010") meta.rows = await u16ValueFromFile(file, tag);
      else if (key === "0028,0011") meta.columns = await u16ValueFromFile(file, tag);
      else if (key === "0028,0002") meta.samplesPerPixel = Math.max(await u16ValueFromFile(file, tag), 1);
      else if (key === "0028,0100") meta.bitsAllocated = Math.max(await u16ValueFromFile(file, tag), 8);
      else if (key === "0028,0008") meta.numberOfFrames = Math.max(parseInt(await textValueFromFile(file, tag), 10) || 1, 1);
      else if (key === "0028,0004") meta.photometric = (await textValueFromFile(file, tag)).toUpperCase();
      else if (key === "0028,1050") meta.windowCenter = firstNumber(await textValueFromFile(file, tag));
      else if (key === "0028,1051") meta.windowWidth = firstNumber(await textValueFromFile(file, tag));
      else if (key === "0010,0020") meta.metadata.PatientID = await textValueFromFile(file, tag);
      else if (key === "0008,0020") meta.metadata.StudyDate = await textValueFromFile(file, tag);
      else if (key === "0008,1030") meta.metadata.StudyDescription = await textValueFromFile(file, tag);
      else if (key === "0008,103E") meta.metadata.SeriesDescription = await textValueFromFile(file, tag);

      offset = nextOffsetForTag(tag, file.size);
    }

    if (meta.rows <= 0 || meta.columns <= 0) {
      throw new Error("DICOM/DCOM rows or columns are missing");
    }
    return meta;
  }

  async function readDicomTagFromFile(file, offset, explicit) {
    const header = await readFileSlice(file, offset, Math.min(offset + 16, file.size));
    if (header.length < 8) return null;
    return readDicomTag(header, new DataView(header.buffer, header.byteOffset, header.byteLength), 0, explicit, offset);
  }

  async function textValueFromFile(file, tag) {
    if (tag.length <= 0 || tag.length === 0xffffffff) return "";
    const bytes = await readFileSlice(file, tag.offset, Math.min(tag.offset + tag.length, tag.offset + DICOM_SCAN_VALUE_LIMIT, file.size));
    return textValue(bytes, 0, bytes.length);
  }

  async function u16ValueFromFile(file, tag) {
    const bytes = await readFileSlice(file, tag.offset, Math.min(tag.offset + 2, file.size));
    return bytes.length >= 2 ? readU16(bytes, 0) : 0;
  }

  async function findUndefinedLengthEnd(file, startOffset) {
    const marker = [0xfe, 0xff, 0xdd, 0xe0, 0x00, 0x00, 0x00, 0x00];
    const chunkSize = 1024 * 1024;
    let offset = startOffset;
    let overlap = new Uint8Array(0);
    while (offset < file.size) {
      const chunk = await readFileSlice(file, offset, Math.min(offset + chunkSize, file.size));
      const merged = new Uint8Array(overlap.length + chunk.length);
      merged.set(overlap, 0);
      merged.set(chunk, overlap.length);
      for (let index = 0; index <= merged.length - marker.length; index += 1) {
        let match = true;
        for (let j = 0; j < marker.length; j += 1) {
          if (merged[index + j] !== marker[j]) {
            match = false;
            break;
          }
        }
        if (match) {
          return offset - overlap.length + index + marker.length;
        }
      }
      overlap = merged.slice(Math.max(0, merged.length - marker.length + 1));
      offset += chunk.length;
      if (chunk.length === 0) break;
    }
    return file.size;
  }

  function representativeIndices(frameCount, limit) {
    if (frameCount <= limit) {
      return Array.from({ length: frameCount }, (_, index) => index);
    }
    const out = [];
    for (let index = 0; index < limit; index += 1) {
      out.push(Math.round(index * (frameCount - 1) / (limit - 1)));
    }
    return [...new Set(out)];
  }

  async function readFileSlice(file, start, end) {
    const buffer = await file.slice(start, end).arrayBuffer();
    return new Uint8Array(buffer);
  }

  function nextOffsetForTag(tag, fileSize) {
    if (tag.length === 0xffffffff) {
      return Math.min(tag.offset, fileSize);
    }
    return Math.min(tag.offset + Math.max(tag.length, 0), fileSize);
  }

  function decodeDicom(bytes, fileName) {
    const meta = parseDicom(bytes);
    const bytesPerSample = Math.max(Math.floor(meta.bitsAllocated / 8), 1);
    const samples = Math.max(meta.samplesPerPixel, 1);
    const frameBytes = meta.rows * meta.columns * samples * bytesPerSample;
    if (frameBytes <= 0 || meta.pixelOffset < 0 || meta.pixelLength <= 0) {
      throw new Error("missing readable DICOM pixel data");
    }
    const available = Math.max(Math.floor(meta.pixelLength / frameBytes), 1);
    const count = Math.min(Math.max(meta.numberOfFrames, 1), available, MAX_DYNAMIC_FRAMES);
    const frames = [];
    for (let frameIndex = 0; frameIndex < count; frameIndex += 1) {
      const start = meta.pixelOffset + frameIndex * frameBytes;
      const rgba = meta.samplesPerPixel >= 3 && meta.bitsAllocated === 8
        ? dicomRgb(bytes, start, meta)
        : dicomMono(bytes, start, meta);
      frames.push(resizeRgbaFrame(rgba, meta.columns, meta.rows, fileName, frameIndex, "dicom", meta.metadata));
    }
    return frames;
  }

  function parseDicom(bytes) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    let offset = bytes.length > 132 && ascii(bytes, 128, 4) === "DICM" ? 132 : 0;
    const meta = {
      rows: 0,
      columns: 0,
      samplesPerPixel: 1,
      bitsAllocated: 8,
      numberOfFrames: 1,
      photometric: "MONOCHROME2",
      windowCenter: null,
      windowWidth: null,
      pixelOffset: -1,
      pixelLength: -1,
      metadata: {}
    };

    while (offset + 8 <= bytes.length) {
      const tag = readDicomTag(bytes, view, offset);
      if (!tag || tag.length === 0xffffffff) {
        throw new Error("encapsulated/compressed DICOM is not supported in the browser demo");
      }
      if (tag.offset + tag.length > bytes.length) break;
      const key = tagKey(tag.group, tag.element);
      const text = textValue(bytes, tag.offset, tag.length);
      if (key === "0028,0010") meta.rows = readU16(bytes, tag.offset);
      else if (key === "0028,0011") meta.columns = readU16(bytes, tag.offset);
      else if (key === "0028,0002") meta.samplesPerPixel = Math.max(readU16(bytes, tag.offset), 1);
      else if (key === "0028,0100") meta.bitsAllocated = Math.max(readU16(bytes, tag.offset), 8);
      else if (key === "0028,0008") meta.numberOfFrames = Math.max(parseInt(text, 10) || 1, 1);
      else if (key === "0028,0004") meta.photometric = text.toUpperCase();
      else if (key === "0028,1050") meta.windowCenter = firstNumber(text);
      else if (key === "0028,1051") meta.windowWidth = firstNumber(text);
      else if (key === "0010,0020") meta.metadata.PatientID = text;
      else if (key === "0008,0020") meta.metadata.StudyDate = text;
      else if (key === "0008,1030") meta.metadata.StudyDescription = text;
      else if (key === "0008,103E") meta.metadata.SeriesDescription = text;
      else if (key === "7FE0,0010") {
        meta.pixelOffset = tag.offset;
        meta.pixelLength = tag.length;
        break;
      }
      offset = tag.offset + tag.length;
    }

    if (meta.rows <= 0 || meta.columns <= 0) {
      throw new Error("DICOM rows/columns are missing");
    }
    return meta;
  }

  function readDicomTag(bytes, view, offset, explicitOverride = null, baseOffset = 0) {
    const group = view.getUint16(offset, true);
    const element = view.getUint16(offset + 2, true);
    let vr = ascii(bytes, offset + 4, 2);
    let length = 0;
    let valueOffset = offset + 8;
    const explicit = explicitOverride === null ? /^[A-Z]{2}$/.test(vr) : explicitOverride;
    if (explicit) {
      if (["OB", "OD", "OF", "OL", "OV", "OW", "SQ", "UC", "UR", "UT", "UN"].includes(vr)) {
        length = view.getUint32(offset + 8, true);
        valueOffset = offset + 12;
      } else {
        length = view.getUint16(offset + 6, true);
      }
    } else {
      vr = "UN";
      length = view.getUint32(offset + 4, true);
      valueOffset = offset + 8;
    }
    return { group, element, vr, length, offset: baseOffset + valueOffset };
  }

  function dicomMono(bytes, offset, meta) {
    const count = meta.rows * meta.columns;
    const values = new Array(count);
    let min = Infinity;
    let max = -Infinity;
    const step = Math.max(Math.floor(meta.bitsAllocated / 8), 1);
    for (let index = 0; index < count; index += 1) {
      const value = meta.bitsAllocated <= 8 ? bytes[offset + index] : readU16(bytes, offset + index * step);
      values[index] = value;
      min = Math.min(min, value);
      max = Math.max(max, value);
    }
    const low = meta.windowCenter !== null && meta.windowWidth > 1 ? meta.windowCenter - meta.windowWidth / 2 : min;
    const high = meta.windowCenter !== null && meta.windowWidth > 1 ? meta.windowCenter + meta.windowWidth / 2 : Math.max(max, low + 1);
    const rgba = new Uint8ClampedArray(count * 4);
    for (let index = 0; index < count; index += 1) {
      let gray = clamp(Math.round(((values[index] - low) / Math.max(high - low, 1)) * 255), 0, 255);
      if (meta.photometric === "MONOCHROME1") gray = 255 - gray;
      rgba[index * 4] = gray;
      rgba[index * 4 + 1] = gray;
      rgba[index * 4 + 2] = gray;
      rgba[index * 4 + 3] = 255;
    }
    return rgba;
  }

  function dicomRgb(bytes, offset, meta) {
    const count = meta.rows * meta.columns;
    const rgba = new Uint8ClampedArray(count * 4);
    for (let index = 0; index < count; index += 1) {
      const source = offset + index * meta.samplesPerPixel;
      rgba[index * 4] = bytes[source];
      rgba[index * 4 + 1] = bytes[source + 1];
      rgba[index * 4 + 2] = bytes[source + 2];
      rgba[index * 4 + 3] = 255;
    }
    return rgba;
  }

  function frameFromDrawable(drawable, name, frameIndex, sourceType) {
    const canvas = document.createElement("canvas");
    canvas.width = SIZE;
    canvas.height = SIZE;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, SIZE, SIZE);
    ctx.drawImage(drawable, 0, 0, SIZE, SIZE);
    const imageData = ctx.getImageData(0, 0, SIZE, SIZE);
    return {
      name,
      frameIndex,
      sourceType,
      width: SIZE,
      height: SIZE,
      rgba: new Uint8ClampedArray(imageData.data),
      metadata: {}
    };
  }

  function resizeRgbaFrame(rgba, width, height, name, frameIndex, sourceType, metadata = {}) {
    const sourceCanvas = document.createElement("canvas");
    sourceCanvas.width = width;
    sourceCanvas.height = height;
    const sourceCtx = sourceCanvas.getContext("2d");
    sourceCtx.putImageData(new ImageData(rgba, width, height), 0, 0);
    const frame = frameFromDrawable(sourceCanvas, name, frameIndex, sourceType);
    frame.metadata = metadata;
    return frame;
  }

  function analyzeAndRender() {
    if (state.frames.length === 0) {
      renderEmpty("No frames available.");
      return;
    }
    state.analysis = analyzeStudy(state.frames);
    renderReport(state.analysis);
    renderFrames();
  }

  function analyzeStudy(frames) {
    const provisional = frames.map((frame) => {
      const gray = grayMatrix(frame.rgba, frame.width, frame.height);
      const bmode = bModeFeatures(gray, frame.width, frame.height);
      const flow = flowFeatures(frame.rgba, frame.width, frame.height);
      return {
        loaded: frame,
        view: detectView(frame.name),
        phase: phaseFromName(frame.name),
        chamberAreaProxy: bmode[9],
        hasColorDoppler: flow[4] > 0.015,
        bmodeFeatures: bmode,
        flowFeatures: flow
      };
    });
    const analyzedFrames = assignPhases(provisional);
    const views = new Set(analyzedFrames.map((frame) => frame.view));
    const systoleCount = analyzedFrames.filter((frame) => frame.phase === "systole").length;
    const diastoleCount = analyzedFrames.filter((frame) => frame.phase === "diastole").length;
    const meanBmode = meanVector(analyzedFrames.map((frame) => frame.bmodeFeatures), 14);
    const meanFlow = meanVector(analyzedFrames.map((frame) => frame.flowFeatures), 14);
    const contractilityProxy = computeContractility(analyzedFrames);
    const contractilityFractionProxy = computeContractilityFraction(analyzedFrames);
    const lowEf = estimateLowEf(meanBmode);
    const coverageWarning = views.size < 2
      ? "体位覆盖较少，输出只能作为低置信度教学参考。"
      : "";
    const diagnosis = classifyTeachingCondition({
      frames: analyzedFrames,
      viewCount: views.size,
      inputCount: frames.length,
      systoleCount,
      diastoleCount,
      meanBmode,
      meanFlow,
      contractilityProxy,
      contractilityFractionProxy,
      lowEf
    });
    return {
      frames: analyzedFrames,
      viewCount: views.size,
      inputCount: frames.length,
      systoleCount,
      diastoleCount,
      meanBmode,
      meanFlow,
      contractilityProxy,
      contractilityFractionProxy,
      lowEf,
      diagnosis,
      coverageWarning
    };
  }

  function bModeFeatures(gray, width, height) {
    const normalized = robustNormalize(gray);
    const blurSmall = boxBlur(normalized, width, height, 1);
    const blurLarge = boxBlur(normalized, width, height, 3);
    const dog = robustNormalize(blurSmall.map((value, index) => value - blurLarge[index]));
    const mean = average(normalized);
    let variance = 0;
    let dxSum = 0;
    let dySum = 0;
    let gradSum = 0;
    let edgeCount = 0;
    let gradCount = 0;
    const hist = new Array(32).fill(0);
    for (let y = 0; y < height - 1; y += 1) {
      for (let x = 0; x < width - 1; x += 1) {
        const index = y * width + x;
        const value = normalized[index];
        const dx = normalized[index + 1] - value;
        const dy = normalized[index + width] - value;
        const grad = Math.sqrt(dx * dx + dy * dy);
        variance += (value - mean) * (value - mean);
        dxSum += Math.abs(dx);
        dySum += Math.abs(dy);
        gradSum += grad;
        if (grad > 0.12) edgeCount += 1;
        hist[clamp(Math.round(value * 31), 0, 31)] += 1;
        gradCount += 1;
      }
    }
    const denom = Math.max(gradCount, 1);
    const varianceFeature = clamp01(variance / denom);
    const dxFeature = clamp01(dxSum / denom);
    const dyFeature = clamp01(dySum / denom);
    const dogMean = clamp01(average(dog));
    let speckleResidual = 0;
    let dogVariance = 0;
    let leftSum = 0;
    let rightSum = 0;
    let leftCount = 0;
    let rightCount = 0;
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const index = y * width + x;
        speckleResidual += Math.abs(normalized[index] - dog[index]);
        const diff = dog[index] - dogMean;
        dogVariance += diff * diff;
        if (x < width / 2) {
          leftSum += normalized[index];
          leftCount += 1;
        } else {
          rightSum += normalized[index];
          rightCount += 1;
        }
      }
    }
    speckleResidual = clamp01(speckleResidual / Math.max(normalized.length, 1));
    dogVariance /= Math.max(dog.length, 1);
    const contrastGain = clamp(dogVariance / Math.max(varianceFeature, 0.000001), 0, 3);
    const directionalAnisotropy = clamp01(Math.abs(dxFeature - dyFeature) / Math.max(dxFeature + dyFeature, 0.001));
    const symmetryProxy = clamp01(1 - Math.abs(leftSum / Math.max(leftCount, 1) - rightSum / Math.max(rightCount, 1)));
    return [
      clamp01(mean),
      varianceFeature,
      dxFeature,
      dyFeature,
      clamp01(gradSum / denom),
      clamp01(edgeCount / denom),
      normalizedEntropy(hist),
      dogMean,
      clamp01(dog.filter((value) => value > 0.65).length / Math.max(dog.length, 1)),
      chamberAreaProxy(normalized, width, height),
      speckleResidual,
      contrastGain,
      directionalAnisotropy,
      symmetryProxy
    ];
  }

  function flowFeatures(rgba, width, height) {
    const count = width * height;
    const vx = new Float32Array(count);
    const vy = new Float32Array(count);
    const speed = new Float32Array(count);
    let active = 0;
    let towards = 0;
    let away = 0;
    let speedSum = 0;
    let signedSum = 0;
    for (let index = 0; index < count; index += 1) {
      const base = index * 4;
      const hsv = rgbToHsv(rgba[base] / 255, rgba[base + 1] / 255, rgba[base + 2] / 255);
      const currentSpeed = hsv.s * hsv.v;
      if (currentSpeed > 0.12 && hsv.s > 0.18) {
        const theta = hueToTheta(hsv.h);
        const x = currentSpeed * Math.cos(theta);
        const y = currentSpeed * Math.sin(theta);
        vx[index] = x;
        vy[index] = y;
        speed[index] = currentSpeed;
        active += 1;
        speedSum += currentSpeed;
        signedSum += x;
        if (x >= 0) towards += 1;
        else away += 1;
      }
    }
    const activeDenom = Math.max(active, 1);
    const meanSpeed = speedSum / activeDenom;
    let turbulence = 0;
    for (let index = 0; index < count; index += 1) {
      if (speed[index] > 0) {
        turbulence += (speed[index] - meanSpeed) ** 2;
      }
    }
    turbulence /= activeDenom;
    let gradientEnergy = 0;
    let divergence = 0;
    let vorticity = 0;
    let vectorCount = 0;
    for (let y = 1; y < height - 1; y += 1) {
      for (let x = 1; x < width - 1; x += 1) {
        const index = y * width + x;
        const dvxDx = (vx[index + 1] - vx[index - 1]) * 0.5;
        const dvyDy = (vy[index + width] - vy[index - width]) * 0.5;
        const dvyDx = (vy[index + 1] - vy[index - 1]) * 0.5;
        const dvxDy = (vx[index + width] - vx[index - width]) * 0.5;
        gradientEnergy += Math.sqrt(dvxDx * dvxDx + dvyDy * dvyDy + dvyDx * dvyDx + dvxDy * dvxDy);
        divergence += Math.abs(dvxDx + dvyDy);
        vorticity += Math.abs(dvyDx - dvxDy);
        vectorCount += 1;
      }
    }
    const activeRatio = active / Math.max(count, 1);
    const connected = largestActiveComponent(speed, width, height);
    const widthProxy = jetWidthProxy(speed, width, height);
    const directionConsistency = active > 0 ? Math.abs(towards - away) / active : 0;
    return [
      clamp01(towards / activeDenom),
      clamp01(away / activeDenom),
      clamp01(meanSpeed),
      clamp01((signedSum / activeDenom + 1) * 0.5),
      clamp01(activeRatio),
      clamp01(turbulence),
      clamp01(gradientEnergy / Math.max(vectorCount, 1)),
      clamp01(divergence / Math.max(vectorCount, 1)),
      clamp01(vorticity / Math.max(vectorCount, 1)),
      clamp01(meanSpeed),
      connected,
      widthProxy,
      directionConsistency,
      clamp01(activeRatio * directionConsistency)
    ];
  }

  function chamberAreaProxy(gray, width, height) {
    const x0 = Math.floor(width * 0.12);
    const x1 = Math.floor(width * 0.88);
    const y0 = Math.floor(height * 0.18);
    const y1 = Math.floor(height * 0.86);
    const crop = [];
    for (let y = y0; y < y1; y += 1) {
      for (let x = x0; x < x1; x += 1) {
        crop.push(gray[y * width + x]);
      }
    }
    const threshold = otsu(crop);
    const cropWidth = Math.max(x1 - x0, 1);
    const cropHeight = Math.max(y1 - y0, 1);
    const cx = (cropWidth - 1) / 2;
    const cy = (cropHeight - 1) / 2;
    let darkWeighted = 0;
    let weightSum = 0;
    for (let y = 0; y < cropHeight; y += 1) {
      for (let x = 0; x < cropWidth; x += 1) {
        const radius = Math.sqrt(((y - cy) / cropHeight) ** 2 + ((x - cx) / cropWidth) ** 2);
        const weight = clamp(1 - radius * 2.2, 0.15, 1);
        if (crop[y * cropWidth + x] < threshold) darkWeighted += weight;
        weightSum += weight;
      }
    }
    return clamp01(darkWeighted / Math.max(weightSum, 0.001));
  }

  function classifyTeachingCondition(study) {
    const b = study.meanBmode;
    const f = study.meanFlow;
    const views = new Set(study.frames.map((frame) => frame.view));
    const hasA4C = views.has("A4C");
    const hasA5C = views.has("A5C");
    const hasA2C = views.has("A2C");
    const hasA3C = views.has("A3C");
    const hasPLAX = views.has("PLAX");
    const hasPSAXAV = views.has("PSAX-AV");
    const dopplerActive = f[4] || 0;
    const turbulence = f[5] || 0;
    const vorticity = f[8] || 0;
    const connected = f[10] || 0;
    const jetWidth = f[11] || 0;
    const signed = f[3] || 0.5;
    const away = f[1] || 0;
    const towards = f[0] || 0;
    const edgeDensity = b[5] || 0;
    const entropy = b[6] || 0;
    const chamberProxy = b[9] || 0;
    const enoughPhase = study.systoleCount >= 1 && study.diastoleCount >= 1;
    const apicalLvView = hasA4C || hasA2C || hasA3C;
    const calibratedLowEf = enoughPhase && apicalLvView && study.lowEf.positive;
    const motionLowEf = enoughPhase && study.contractilityFractionProxy < 0.30 && chamberProxy > 0.025;
    let label = "未见明确心脏超声异常";
    let rationale = "B-mode 结构代理、收缩舒张差异和 Doppler 代理未达到异常阈值。";

    if (dopplerActive > 0.14 && (turbulence > 0.055 || vorticity > 0.045 || jetWidth > 0.18) && (hasPLAX || hasA3C)) {
      label = "中度二尖瓣反流";
      rationale = "二尖瓣相关切面中 Doppler 活跃区、喷流宽度或湍流代理升高。";
    } else if ((dopplerActive > 0.13 || connected > 0.22) && hasA4C && (turbulence > 0.045 || vorticity > 0.04 || jetWidth > 0.16)) {
      label = "中度三尖瓣反流";
      rationale = "A4C 相关输入中右心房室区彩色信号较集中，并伴湍流或喷流宽度代理升高。";
    } else if (dopplerActive > 0.07 && (hasPLAX || hasA3C || hasA2C) && signed < 0.54) {
      label = "轻度二尖瓣反流";
      rationale = "二尖瓣相关切面中出现一定 Doppler 活跃区，但未达到中度阈值。";
    } else if (dopplerActive > 0.07 && hasA4C && signed >= 0.54) {
      label = "轻度三尖瓣反流";
      rationale = "A4C 输入中出现轻度反流教学模式，活跃区未达到中重度阈值。";
    } else if (dopplerActive > 0.09 && (hasA5C || hasPSAXAV) && (turbulence > 0.035 || vorticity > 0.035)) {
      label = "主动脉瓣轻度狭窄倾向";
      rationale = "主动脉瓣相关切面中高速紊流代理升高。";
    } else if (dopplerActive > 0.08 && hasA5C && away > towards) {
      label = "轻度主动脉瓣反流";
      rationale = "A5C 相关输入中 Doppler 方向代理偏离正常射流方向。";
    } else if (dopplerActive > 0.11 && hasPSAXAV && (turbulence > 0.035 || vorticity > 0.035)) {
      label = "肺动脉瓣轻度反流";
      rationale = "短轴层面附近流场活跃和涡量代理升高。";
    } else if (calibratedLowEf || motionLowEf || (enoughPhase && study.contractilityProxy < 0.035 && chamberProxy > 0.035)) {
      label = "左心室收缩功能减低";
      rationale = `CAMUS low-EF B-mode calibration p=${study.lowEf.probability.toFixed(3)}, relative contractility=${study.contractilityFractionProxy.toFixed(3)}.`;
    } else if (edgeDensity > 0.30 || entropy > 0.74) {
      label = "节段性室壁运动异常";
      rationale = "B-mode 差分矩阵边缘密度或纹理熵偏高，且未达到明确瓣膜反流阈值。";
    } else if (dopplerActive > 0.045) {
      label = defaultMildValveLabel(views, signed, towards, away);
      rationale = "Doppler 活跃区存在但湍流代理不高，因此输出对应切面的轻度瓣膜反流教学标签。";
    } else if (!enoughPhase) {
      label = "图像证据不足，倾向未见明确异常";
      rationale = "缺少可靠的收缩/舒张配对，当前只能给出低置信度教学参考判断。";
    }
    const confidence = study.viewCount >= 6 && enoughPhase ? "中等" : enoughPhase ? "中低" : "低";
    return { label, confidence, rationale };
  }

  function renderReport(study) {
    const b = study.meanBmode;
    const f = study.meanFlow;
    const diagnosis = study.diagnosis;
    els.metricFiles.textContent = study.inputCount;
    els.metricViews.textContent = study.viewCount;
    els.metricDiastole.textContent = study.diastoleCount;
    els.metricSystole.textContent = study.systoleCount;
    els.diagnosisTitle.textContent = diagnosis.label;
    els.confidenceText.textContent = `教学参考置信度：${diagnosis.confidence} · ${study.inputCount} frames · ${study.viewCount} views`;
    els.reportText.textContent = [
      `教学参考病症判断：${diagnosis.label}。`,
      `本次输入包含 ${study.inputCount} 个文件/帧，覆盖约 ${study.viewCount} 个体位，系统自动识别出 ${study.diastoleCount} 个舒张态、${study.systoleCount} 个收缩态。`,
      `判断依据为：${diagnosis.rationale} B-mode 边缘密度 ${b[5].toFixed(3)}、纹理熵 ${b[6].toFixed(3)}、散斑残差 ${b[10].toFixed(3)}、收缩舒张腔室面积代理差值 ${study.contractilityProxy.toFixed(3)}、相对收缩幅度代理 ${study.contractilityFractionProxy.toFixed(3)}；Color Doppler 活跃区比例 ${f[4].toFixed(3)}、最大连通域 ${f[10].toFixed(3)}、喷流宽度代理 ${f[11].toFixed(3)}、湍流代理 ${f[5].toFixed(3)}、涡量代理 ${f[8].toFixed(3)}。`,
      `本在线演示为浏览器边缘计算与规则后备展示；完整离线 Gemma4 4B GGUF 推理请运行提交仓库中的 Windows PC V5 版本。该结论仅用于医学教学和算法演示，不作为临床最终诊断、治疗建议或医嘱。${study.coverageWarning ? " " + study.coverageWarning : ""}`
    ].join("");
    els.featureText.textContent = compactFeatureText(study);
    els.modelStatus.textContent = "Feature + rule fallback";
  }

  function renderFrames(errors = []) {
    els.metricFiles.textContent = state.frames.length;
    els.metricViews.textContent = state.analysis ? state.analysis.viewCount : 0;
    els.metricDiastole.textContent = state.analysis ? state.analysis.diastoleCount : 0;
    els.metricSystole.textContent = state.analysis ? state.analysis.systoleCount : 0;
    els.fileList.innerHTML = "";
    if (errors.length > 0) {
      for (const error of errors) {
        const row = document.createElement("div");
        row.className = "file-row warning";
        row.textContent = error;
        els.fileList.appendChild(row);
      }
    }
    for (const frame of state.frames.slice(0, 18)) {
      const row = document.createElement("div");
      row.className = "file-row";
      row.innerHTML = `<strong>${escapeHtml(displayLabel(frame))}</strong><small>${frame.sourceType}</small>`;
      els.fileList.appendChild(row);
    }
    drawPreview(state.frames[0] || null);
    renderFilmstrip();
  }

  function renderFilmstrip() {
    els.filmstrip.innerHTML = "";
    for (const frame of state.frames.slice(0, 24)) {
      const wrap = document.createElement("button");
      wrap.className = "thumb";
      wrap.type = "button";
      wrap.title = displayLabel(frame);
      const canvas = document.createElement("canvas");
      canvas.width = 160;
      canvas.height = 120;
      const ctx = canvas.getContext("2d");
      const source = document.createElement("canvas");
      source.width = frame.width;
      source.height = frame.height;
      source.getContext("2d").putImageData(new ImageData(frame.rgba, frame.width, frame.height), 0, 0);
      ctx.drawImage(source, 0, 0, canvas.width, canvas.height);
      const label = document.createElement("span");
      label.textContent = `#${frame.frameIndex}`;
      wrap.append(canvas, label);
      wrap.addEventListener("click", () => drawPreview(frame));
      els.filmstrip.appendChild(wrap);
    }
  }

  function drawPreview(frame) {
    const ctx = els.previewCanvas.getContext("2d");
    ctx.fillStyle = "#10171b";
    ctx.fillRect(0, 0, els.previewCanvas.width, els.previewCanvas.height);
    if (!frame) {
      ctx.fillStyle = "#8ea1aa";
      ctx.font = "18px system-ui, sans-serif";
      ctx.fillText("Upload study files or run sample", 30, 46);
      return;
    }
    const source = document.createElement("canvas");
    source.width = frame.width;
    source.height = frame.height;
    source.getContext("2d").putImageData(new ImageData(frame.rgba, frame.width, frame.height), 0, 0);
    ctx.drawImage(source, 64, 0, 384, 384);
    ctx.fillStyle = "rgba(0,0,0,0.68)";
    ctx.fillRect(14, 318, 484, 50);
    ctx.fillStyle = "#fff";
    ctx.font = "14px system-ui, sans-serif";
    ctx.fillText(displayLabel(frame), 24, 341);
    ctx.fillStyle = "#b7d8d2";
    ctx.fillText(frame.sourceType, 24, 360);
  }

  function renderEmpty(message = "") {
    els.metricFiles.textContent = "0";
    els.metricViews.textContent = "0";
    els.metricDiastole.textContent = "0";
    els.metricSystole.textContent = "0";
    els.fileList.innerHTML = "";
    els.filmstrip.innerHTML = "";
    els.diagnosisTitle.textContent = "Awaiting input";
    els.confidenceText.textContent = "Load files or run the sample study.";
    els.reportText.textContent = message || "The online demo runs browser-side feature extraction and the PC rule fallback. Full offline Gemma4 4B inference runs through local GGUF files in the Windows PC V5 application.";
    els.featureText.textContent = "No features yet.";
    els.modelStatus.textContent = "Browser edge demo";
    drawPreview(null);
  }

  function compactFeatureText(study) {
    return [
      `views=${study.viewCount}, files_or_frames=${study.inputCount}, systole=${study.systoleCount}, diastole=${study.diastoleCount}`,
      `contractility_proxy=${study.contractilityProxy.toFixed(4)}, contractility_fraction_proxy=${study.contractilityFractionProxy.toFixed(4)}`,
      `low_ef_calibration_probability=${study.lowEf.probability.toFixed(4)}, threshold=${LOW_EF.threshold.toFixed(4)}`,
      `B-mode mean features=[${study.meanBmode.map((value) => value.toFixed(4)).join(", ")}]`,
      `Doppler mean features=[${study.meanFlow.map((value) => value.toFixed(4)).join(", ")}]`
    ].join("\n");
  }

  function makeSampleFrames() {
    return [
      syntheticEchoFrame("sample_A4C_ED_color.png", 0, 0.62, true),
      syntheticEchoFrame("sample_A4C_ES_color.png", 1, 0.50, true),
      syntheticEchoFrame("sample_A4C_mid_color.png", 2, 0.56, true)
    ];
  }

  function syntheticEchoFrame(name, frameIndex, chamberScale, withDoppler) {
    const canvas = document.createElement("canvas");
    canvas.width = SIZE;
    canvas.height = SIZE;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#05080a";
    ctx.fillRect(0, 0, SIZE, SIZE);
    const gradient = ctx.createRadialGradient(128, 126, 16, 128, 128, 138);
    gradient.addColorStop(0, "#151a1d");
    gradient.addColorStop(0.55, "#334049");
    gradient.addColorStop(1, "#0a0d10");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.moveTo(128, 24);
    ctx.quadraticCurveTo(32, 132, 82, 232);
    ctx.quadraticCurveTo(128, 206, 174, 232);
    ctx.quadraticCurveTo(224, 132, 128, 24);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "rgba(220,230,228,0.36)";
    ctx.lineWidth = 5;
    ctx.stroke();

    ctx.fillStyle = "#030506";
    ctx.beginPath();
    ctx.ellipse(108, 150, 34 * chamberScale, 72 * chamberScale, -0.25, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(158, 150, 29 * chamberScale, 63 * chamberScale, 0.22, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = "rgba(210,220,218,0.32)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(128, 70);
    ctx.lineTo(128, 216);
    ctx.stroke();

    if (withDoppler) {
      ctx.globalAlpha = 0.84;
      const jet = ctx.createLinearGradient(142, 112, 184, 184);
      jet.addColorStop(0, "#f51919");
      jet.addColorStop(0.46, "#f6d546");
      jet.addColorStop(1, "#225cf2");
      ctx.fillStyle = jet;
      ctx.beginPath();
      ctx.moveTo(138, 112);
      ctx.quadraticCurveTo(196, 142, 184, 206);
      ctx.quadraticCurveTo(166, 178, 122, 136);
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = 1;
    }

    const imageData = ctx.getImageData(0, 0, SIZE, SIZE);
    return {
      name,
      frameIndex,
      sourceType: "sample",
      width: SIZE,
      height: SIZE,
      rgba: new Uint8ClampedArray(imageData.data),
      metadata: {}
    };
  }

  function grayMatrix(rgba, width, height) {
    const gray = new Float32Array(width * height);
    for (let index = 0; index < gray.length; index += 1) {
      const base = index * 4;
      gray[index] = (0.299 * rgba[base] + 0.587 * rgba[base + 1] + 0.114 * rgba[base + 2]) / 255;
    }
    return [...gray];
  }

  function robustNormalize(values) {
    const sorted = [...values].sort((a, b) => a - b);
    const low = sorted[Math.max(0, Math.min(sorted.length - 1, Math.round((sorted.length - 1) * 0.02)))] || 0;
    const high = sorted[Math.max(0, Math.min(sorted.length - 1, Math.round((sorted.length - 1) * 0.98)))] || 1;
    const denom = Math.max(high - low, 0.001);
    return values.map((value) => clamp01((value - low) / denom));
  }

  function boxBlur(values, width, height, radius) {
    const out = new Array(values.length).fill(0);
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        let sum = 0;
        let count = 0;
        for (let yy = Math.max(0, y - radius); yy <= Math.min(height - 1, y + radius); yy += 1) {
          for (let xx = Math.max(0, x - radius); xx <= Math.min(width - 1, x + radius); xx += 1) {
            sum += values[yy * width + xx];
            count += 1;
          }
        }
        out[y * width + x] = sum / Math.max(count, 1);
      }
    }
    return out;
  }

  function otsu(values) {
    const hist = new Array(96).fill(0);
    for (const value of values) {
      hist[clamp(Math.floor(clamp01(value) * 95), 0, 95)] += 1;
    }
    const total = Math.max(values.length, 1);
    let sumTotal = 0;
    for (let index = 0; index < hist.length; index += 1) {
      sumTotal += hist[index] * (index / 95);
    }
    let weightBg = 0;
    let sumBg = 0;
    let bestVariance = -1;
    let best = 0.25;
    for (let index = 0; index < hist.length; index += 1) {
      const count = hist[index];
      weightBg += count;
      if (weightBg <= 0) continue;
      const weightFg = total - weightBg;
      if (weightFg <= 0) break;
      const center = index / 95;
      sumBg += count * center;
      const meanBg = sumBg / weightBg;
      const meanFg = (sumTotal - sumBg) / weightFg;
      const between = weightBg * weightFg * (meanBg - meanFg) ** 2;
      if (between > bestVariance) {
        bestVariance = between;
        best = center;
      }
    }
    return clamp(best, 0.08, 0.55);
  }

  function normalizedEntropy(hist) {
    const total = Math.max(hist.reduce((sum, value) => sum + value, 0), 1);
    let entropy = 0;
    for (const count of hist) {
      if (count > 0) {
        const p = count / total;
        entropy -= p * Math.log2(p);
      }
    }
    return clamp01(entropy / 5);
  }

  function largestActiveComponent(speed, width, height) {
    const visited = new Uint8Array(speed.length);
    let best = 0;
    const stack = [];
    for (let index = 0; index < speed.length; index += 1) {
      if (visited[index] || speed[index] <= 0.12) continue;
      let size = 0;
      visited[index] = 1;
      stack.push(index);
      while (stack.length > 0) {
        const current = stack.pop();
        size += 1;
        const x = current % width;
        const neighbors = [current - 1, current + 1, current - width, current + width];
        for (const next of neighbors) {
          if (next < 0 || next >= speed.length) continue;
          if ((next === current - 1 && x === 0) || (next === current + 1 && x === width - 1)) continue;
          if (!visited[next] && speed[next] > 0.12) {
            visited[next] = 1;
            stack.push(next);
          }
        }
      }
      best = Math.max(best, size);
    }
    return clamp01(best / Math.max(speed.length, 1));
  }

  function jetWidthProxy(speed, width, height) {
    let maxWidth = 0;
    for (let y = 0; y < height; y += 1) {
      let current = 0;
      for (let x = 0; x < width; x += 1) {
        if (speed[y * width + x] > 0.12) {
          current += 1;
          maxWidth = Math.max(maxWidth, current);
        } else {
          current = 0;
        }
      }
    }
    return clamp01(maxWidth / Math.max(width, 1));
  }

  function assignPhases(frames) {
    const out = frames.map((frame) => ({ ...frame }));
    const groups = new Map();
    for (let index = 0; index < out.length; index += 1) {
      if (!groups.has(out[index].view)) groups.set(out[index].view, []);
      groups.get(out[index].view).push(index);
    }
    for (const indices of groups.values()) {
      const unknown = indices.filter((index) => out[index].phase === "unknown");
      if (indices.length >= 2 && unknown.length > 0) {
        const ordered = [...indices].sort((a, b) => out[a].chamberAreaProxy - out[b].chamberAreaProxy);
        out[ordered[0]].phase = "systole";
        out[ordered[ordered.length - 1]].phase = "diastole";
        for (const index of ordered.slice(1, -1)) {
          if (out[index].phase === "unknown") out[index].phase = "intermediate";
        }
      } else if (indices.length === 1 && out[indices[0]].phase === "unknown") {
        out[indices[0]].phase = "unknown_single_frame";
      }
    }
    return out;
  }

  function computeContractility(frames) {
    const values = pairedByView(frames).map(({ ed, es }) => Math.max(ed - es, 0));
    return values.length ? clamp01(average(values)) : 0;
  }

  function computeContractilityFraction(frames) {
    const values = pairedByView(frames)
      .filter(({ ed }) => ed > 0.001)
      .map(({ ed, es }) => clamp01(Math.max(ed - es, 0) / ed));
    return values.length ? clamp01(average(values)) : 0;
  }

  function pairedByView(frames) {
    const groups = new Map();
    for (const frame of frames) {
      if (!groups.has(frame.view)) groups.set(frame.view, []);
      groups.get(frame.view).push(frame);
    }
    const pairs = [];
    for (const group of groups.values()) {
      const systolic = group.filter((frame) => frame.phase === "systole").map((frame) => frame.chamberAreaProxy);
      const diastolic = group.filter((frame) => frame.phase === "diastole").map((frame) => frame.chamberAreaProxy);
      if (systolic.length > 0 && diastolic.length > 0) {
        pairs.push({ es: Math.min(...systolic), ed: Math.max(...diastolic) });
      }
    }
    return pairs;
  }

  function estimateLowEf(bmode) {
    let score = LOW_EF.intercept;
    for (let index = 0; index < LOW_EF.coeffs.length; index += 1) {
      const value = Number.isFinite(bmode[index]) ? bmode[index] : LOW_EF.means[index];
      score += ((value - LOW_EF.means[index]) / Math.max(LOW_EF.scales[index], 0.000001)) * LOW_EF.coeffs[index];
    }
    const probability = clamp01(sigmoid(score));
    return {
      probability,
      positive: probability >= LOW_EF.threshold
    };
  }

  function meanVector(vectors, length) {
    const out = new Array(length).fill(0);
    if (vectors.length === 0) return out;
    for (const vector of vectors) {
      for (let index = 0; index < length; index += 1) {
        out[index] += vector[index] || 0;
      }
    }
    return out.map((value) => value / vectors.length);
  }

  function detectView(name) {
    const lower = stem(name).toLowerCase();
    const views = [
      ["PLAX", ["plax", "parasternal_long", "long_axis", "长轴"]],
      ["PSAX-AV", ["psax_av", "aortic_valve", "short_axis_av"]],
      ["PSAX-MV", ["psax_mv", "mitral"]],
      ["PSAX-PM", ["psax_pm", "papillary"]],
      ["PSAX-APEX", ["psax_apex", "apex_short"]],
      ["A4C", ["a4c", "apical_4", "four_chamber", "4ch", "4_chamber", "四腔"]],
      ["A5C", ["a5c", "apical_5", "five_chamber", "5ch"]],
      ["A2C", ["a2c", "apical_2", "two_chamber", "2ch", "2_chamber", "二腔"]],
      ["A3C", ["a3c", "apical_3", "three_chamber", "3ch"]],
      ["SUBCOSTAL-4C", ["subcostal", "subxiphoid"]],
      ["IVC", ["ivc"]],
      ["SUPRASTERNAL", ["suprasternal", "arch"]]
    ];
    for (const [view, keys] of views) {
      if (keys.some((key) => lower.includes(key))) return view;
    }
    return "UNKNOWN";
  }

  function phaseFromName(name) {
    const lower = stem(name).toLowerCase();
    if (["systole", "systolic", "_es", "-es", "endsystole", "end_systole", "收缩"].some((key) => lower.includes(key))) {
      return "systole";
    }
    if (["diastole", "diastolic", "_ed", "-ed", "enddiastole", "end_diastole", "舒张"].some((key) => lower.includes(key))) {
      return "diastole";
    }
    return "unknown";
  }

  function defaultMildValveLabel(views, signed, towards, away) {
    if (views.has("A4C") && signed >= 0.52) return "轻度三尖瓣反流";
    if (views.has("PLAX") || views.has("A3C") || views.has("A2C")) return "轻度二尖瓣反流";
    if (views.has("A5C")) return away > towards ? "轻度主动脉瓣反流" : "主动脉瓣轻度狭窄倾向";
    if (views.has("PSAX-AV")) return "肺动脉瓣轻度反流";
    return "轻度二尖瓣反流";
  }

  function rgbToHsv(r, g, b) {
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const delta = max - min;
    let h = 0;
    if (delta > 0.000001) {
      if (max === r) h = 60 * (((g - b) / delta) % 6);
      else if (max === g) h = 60 * ((b - r) / delta + 2);
      else h = 60 * ((r - g) / delta + 4);
      if (h < 0) h += 360;
    }
    const s = max <= 0.000001 ? 0 : delta / max;
    return { h, s, v: max };
  }

  function hueToTheta(hue) {
    if (hue <= 240) return (hue / 240) * Math.PI;
    if (hue < 330) return Math.PI + ((hue - 240) / 90) * Math.PI;
    return 0;
  }

  function once(target, eventName) {
    return new Promise((resolve, reject) => {
      const onError = () => {
        cleanup();
        reject(new Error("media decode failed"));
      };
      const onDone = () => {
        cleanup();
        resolve();
      };
      const cleanup = () => {
        target.removeEventListener(eventName, onDone);
        target.removeEventListener("error", onError);
      };
      target.addEventListener(eventName, onDone, { once: true });
      target.addEventListener("error", onError, { once: true });
    });
  }

  function seek(video, time) {
    return new Promise((resolve, reject) => {
      const targetTime = Math.min(Math.max(time, 0), video.duration || 0);
      if (Math.abs(video.currentTime - targetTime) < 0.01 && video.readyState >= 2) {
        requestAnimationFrame(resolve);
        return;
      }
      const onSeeked = () => {
        cleanup();
        resolve();
      };
      const onError = () => {
        cleanup();
        reject(new Error("video seek failed"));
      };
      const cleanup = () => {
        video.removeEventListener("seeked", onSeeked);
        video.removeEventListener("error", onError);
      };
      video.addEventListener("seeked", onSeeked, { once: true });
      video.addEventListener("error", onError, { once: true });
      video.currentTime = targetTime;
    });
  }

  function readU16(bytes, offset) {
    return bytes[offset] | (bytes[offset + 1] << 8);
  }

  function ascii(bytes, offset, length) {
    let out = "";
    for (let index = 0; index < length && offset + index < bytes.length; index += 1) {
      out += String.fromCharCode(bytes[offset + index]);
    }
    return out;
  }

  function textValue(bytes, offset, length) {
    let out = "";
    const end = Math.min(offset + length, bytes.length);
    for (let index = offset; index < end; index += 1) {
      if (bytes[index] !== 0) out += String.fromCharCode(bytes[index]);
    }
    return out.trim().replace("\\", ",");
  }

  function tagKey(group, element) {
    return `${group.toString(16).padStart(4, "0")},${element.toString(16).padStart(4, "0")}`.toUpperCase();
  }

  function firstNumber(text) {
    const value = Number.parseFloat(String(text).split(",")[0]);
    return Number.isFinite(value) ? value : null;
  }

  function stem(name) {
    const base = String(name).split(/[\\/]/).pop();
    const dot = base.lastIndexOf(".");
    return dot >= 0 ? base.slice(0, dot) : base;
  }

  function displayLabel(frame) {
    return `${frame.name}${frame.frameIndex > 0 ? `#${frame.frameIndex}` : ""}`;
  }

  function setBusy(isBusy, text) {
    els.analyzeButton.disabled = isBusy;
    els.sampleButton.disabled = isBusy;
    els.modelStatus.textContent = text;
  }

  function average(values) {
    return values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;
  }

  function sigmoid(value) {
    if (value >= 0) return 1 / (1 + Math.exp(-value));
    const z = Math.exp(value);
    return z / (1 + z);
  }

  function clamp01(value) {
    return clamp(value, 0, 1);
  }

  function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
})();
