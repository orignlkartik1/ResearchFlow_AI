(() => {
  const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;
  const PDF_SIGNATURE = new TextEncoder().encode("%PDF-");
  const fileInput = document.querySelector("#pdf-file");
  const dropZone = document.querySelector("#drop-zone");
  const uploadForm = document.querySelector("#upload-form");
  const uploadView = document.querySelector("#upload-view");
  const loadingView = document.querySelector("#loading-view");
  const resultView = document.querySelector("#result-view");
  const selectedFileView = document.querySelector("#selected-file");
  const fileName = document.querySelector("#file-name");
  const fileSize = document.querySelector("#file-size");
  const analyzeButton = document.querySelector("#analyze-button");
  const uploadError = document.querySelector("#upload-error");
  const resultMeta = document.querySelector("#result-meta");
  const analysisText = document.querySelector("#analysis-text");
  const limitsNote = document.querySelector("#limits-note");
  let selectedFile = null;

  const errorMessages = {
    FILE_REQUIRED: "Choose a PDF file to get started.",
    INVALID_FILE: "Choose a file with a .pdf extension.",
    EMPTY_FILE: "That PDF is empty. Choose another file.",
    FILE_TOO_LARGE: "This PDF is larger than the 15 MiB upload limit.",
    INVALID_PDF: "That file doesn't appear to be a valid PDF.",
    NO_EXTRACTABLE_TEXT:
      "This PDF doesn't contain extractable text. Scanned or image-only PDFs aren't supported yet.",
    DOCUMENT_TOO_LARGE: "This document is larger than the current analysis limit.",
    PDF_EXTRACTION_FAILED: "We couldn't extract text from this PDF. Try another file.",
    PDF_PROCESSING_FAILED: "This PDF couldn't be processed. Please try again.",
    SESSION_CLEANUP_FAILED: "The analysis couldn't be safely completed. Please try again.",
    RESEARCH_PROCESSING_FAILED:
      "Research analysis couldn't be completed. Please try again.",
  };

  function showError(message) {
    uploadError.textContent = message;
    uploadError.hidden = false;
  }

  function clearError() {
    uploadError.textContent = "";
    uploadError.hidden = true;
  }

  function formatFileSize(bytes) {
    if (bytes < 1024 * 1024) {
      return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function hasPdfSignature(file) {
    return file.slice(0, 1024).arrayBuffer().then((buffer) => {
      const bytes = new Uint8Array(buffer);
      return bytes.some((_, index) =>
        PDF_SIGNATURE.every((byte, offset) => bytes[index + offset] === byte),
      );
    });
  }

  async function selectFile(file) {
    if (!file) return;
    clearError();

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      selectedFile = null;
      updateSelectedFile();
      showError(errorMessages.INVALID_FILE);
      return;
    }

    if (file.size === 0) {
      selectedFile = null;
      updateSelectedFile();
      showError(errorMessages.EMPTY_FILE);
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      selectedFile = null;
      updateSelectedFile();
      showError(errorMessages.FILE_TOO_LARGE);
      return;
    }

    if (!(await hasPdfSignature(file))) {
      selectedFile = null;
      updateSelectedFile();
      showError(errorMessages.INVALID_PDF);
      return;
    }

    selectedFile = file;
    updateSelectedFile();
  }

  function updateSelectedFile() {
    const hasFile = selectedFile !== null;
    selectedFileView.hidden = !hasFile;
    analyzeButton.disabled = !hasFile;
    if (hasFile) {
      fileName.textContent = selectedFile.name;
      fileSize.textContent = formatFileSize(selectedFile.size);
    } else {
      fileName.textContent = "";
      fileSize.textContent = "";
    }
  }

  function setLoading(isLoading) {
    analyzeButton.disabled = isLoading || selectedFile === null;
    analyzeButton.setAttribute("aria-busy", String(isLoading));
    uploadView.hidden = isLoading;
    loadingView.hidden = !isLoading;
  }

  function friendlyApiError(payload, status) {
    const error = payload && typeof payload.error === "object" ? payload.error : {};
    const knownMessage = errorMessages[error.code];
    if (knownMessage) return knownMessage;

    if (typeof error.message === "string" && error.message.length <= 240) {
      return error.message;
    }
    if (status === 413) return errorMessages.DOCUMENT_TOO_LARGE;
    return "Research analysis couldn't be completed. Please try again.";
  }

  function showResult(data) {
    resultMeta.textContent = `${data.filename} · ${data.page_count} ${
      data.page_count === 1 ? "page" : "pages"
    }`;
    analysisText.textContent = data.result.response;
    uploadView.hidden = true;
    loadingView.hidden = true;
    resultView.hidden = false;
    limitsNote.hidden = true;
    document.querySelector("#result-title").focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function analyzePaper(event) {
    event.preventDefault();
    if (!selectedFile) {
      showError(errorMessages.FILE_REQUIRED);
      return;
    }

    clearError();
    setLoading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("/api/analyze-pdf", {
        method: "POST",
        body: formData,
      });
      let payload;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }

      if (!response.ok) {
        throw new Error(friendlyApiError(payload, response.status));
      }

      if (
        !payload ||
        payload.success !== true ||
        typeof payload.filename !== "string" ||
        !Number.isInteger(payload.page_count) ||
        typeof payload.result?.response !== "string"
      ) {
        throw new Error("ResearchFlow-AI returned an unexpected response. Please try again.");
      }

      showResult(payload);
    } catch (error) {
      const message =
        error instanceof TypeError
          ? "We couldn't reach ResearchFlow-AI. Please check your connection and try again."
          : error instanceof Error
            ? error.message
            : "Research analysis couldn't be completed. Please try again.";
      setLoading(false);
      showError(message);
    }
  }

  function startAnotherAnalysis() {
    selectedFile = null;
    fileInput.value = "";
    updateSelectedFile();
    clearError();
    resultMeta.textContent = "";
    analysisText.textContent = "";
    resultView.hidden = true;
    loadingView.hidden = true;
    uploadView.hidden = false;
    limitsNote.hidden = false;
    fileInput.focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  fileInput.addEventListener("change", () => {
    const [file] = fileInput.files;
    void selectFile(file);
    fileInput.value = "";
  });
  uploadForm.addEventListener("submit", analyzePaper);
  document.querySelector("#remove-file").addEventListener("click", () => {
    selectedFile = null;
    updateSelectedFile();
    clearError();
    fileInput.focus();
  });
  document.querySelector("#new-analysis").addEventListener("click", startAnotherAnalysis);
  document
    .querySelector("#new-analysis-bottom")
    .addEventListener("click", startAnotherAnalysis);

  for (const eventName of ["dragenter", "dragover"]) {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("is-dragging");
    });
  }

  for (const eventName of ["dragleave", "drop"]) {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      if (eventName === "drop") void selectFile(event.dataTransfer.files[0]);
      dropZone.classList.remove("is-dragging");
    });
  }
})();
