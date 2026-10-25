document.addEventListener("DOMContentLoaded", () => {
  const photoInput = document.getElementById("photoInput");
  const nameInput = document.getElementById("productName");
  const expiryInput = document.getElementById("expiryDate");
  const status = document.getElementById("scanStatus");
  const readBtn = document.getElementById("readLabelBtn");
  const barcodeBtn = document.getElementById("barcodeBtn");
  const video = document.getElementById("barcodeVideo");
  const cameraSelect = document.getElementById("cameraSelect");
let selectedCamera = "environment";
  const stopBtn = document.getElementById("stopScanBtn");
  let stream = null;
  let scanControls = null;

  function setStatus(message) { status.textContent = message; }

  readBtn?.addEventListener("click", async () => {
    const file = photoInput?.files?.[0];
    if (!file) {
      setStatus("Choose or take a clear product-label photo first.");
      photoInput?.focus();
      return;
    }
    if (!window.Tesseract) {
      setStatus("OCR library did not load. Check internet access and try again.");
      return;
    }
    setStatus("Reading label text… please wait.");
    try {
      const result = await Tesseract.recognize(file, "eng");
      const text = result.data.text || "";
      const dateMatch = text.match(/\b(20\d{2})[\/.-](0?[1-9]|1[0-2])[\/.-](0?[1-9]|[12]\d|3[01])\b|\b(0?[1-9]|[12]\d|3[01])[\/.-](0?[1-9]|1[0-2])[\/.-](20\d{2})\b/);
      const lines = text.split(/\r?\n/).map(x => x.trim()).filter(Boolean);
      if (!nameInput.value && lines.length) {
        const likely = lines.find(x => /milk|bread|cheese|yogurt|juice|rice|egg|apple|tomato|butter|curd|biscuit/i.test(x));
        if (likely) nameInput.value = likely.slice(0, 70);
      }
      if (dateMatch) {
        let year, month, day;
        if (dateMatch[1]) { year = dateMatch[1]; month = dateMatch[2]; day = dateMatch[3]; }
        else { day = dateMatch[4]; month = dateMatch[5]; year = dateMatch[6]; }
        const candidate = `${year}-${String(month).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
        const parsed = new Date(`${candidate}T00:00:00`);
        if (!Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0,10) === candidate) expiryInput.value = candidate;
      }
      setStatus("OCR finished. Check every extracted detail against the package before saving. OCR text is not guaranteed accurate.");
      if (!lines.length) setStatus("No readable text found. Try a sharper, well-lit photo.");
    } catch (error) {
      setStatus("Could not read this image. Try a sharper, well-lit photo.");
    }
  });

  
  barcodeBtn?.addEventListener("click", async () => {
    if (!window.ZXing || !window.ZXing.BrowserMultiFormatReader) {
      setStatus("Barcode library did not load. Check internet access and try again.");
      return;
    }

    try {
      video.hidden = false;
      stopBtn.hidden = false;
      setStatus("Requesting camera access...");

      const reader = new ZXing.BrowserMultiFormatReader();

      scanControls = await reader.decodeFromVideoDevice(
        undefined,
        video,
        async (result, err, controls) => {
          if (!result) return;

          const code = result.getText().trim();

          // Stop the camera after reading the barcode.
          controls?.stop();
          stopCamera();

          setStatus(`Barcode ${code} detected. Searching for product...`);

          try {
            
const response = await fetch(
  `https://world.openfoodfacts.org/api/v2/product/${encodeURIComponent(code)}.json`
);

          

            if (!response.ok) {
              throw new Error("Product lookup failed");
            }

            const data = await response.json();

            if (data.status !== 1 || !data.product) {
              setStatus(
                `Barcode ${code} scanned, but no matching product was found. Please enter the name manually.`
              );
              return;
            }

            const product = data.product;
            const productName = (
              product.product_name ||
              product.product_name_en ||
              ""
            ).trim();

            if (!productName) {
              setStatus(
                "Product found, but its name is unavailable. Please enter it manually."
              );
              return;
            }

            // Fill in the product name automatically.
            nameInput.value = productName;

            setStatus(
              `Product identified: ${productName}. Verify the details and enter the expiry date before saving.`
            );
          } catch (error) {
            setStatus(
              "Could not look up the product. Check your internet connection and try again."
            );
          }
        }
      );

      setStatus("Point the camera at the product barcode.");
    } catch (error) {
      setStatus("Camera could not start. Allow camera permission and use localhost or HTTPS.");
      stopCamera();
    }
    
  });


  function stopCamera() {
    try { scanControls?.stop(); } catch (_) {}
    scanControls = null;
    if (stream) stream.getTracks().forEach(track => track.stop());
    stream = null;
    if (video.srcObject) video.srcObject.getTracks().forEach(track => track.stop());
    video.srcObject = null;
    video.hidden = true;
    cameraSelect.hidden = true;
    stopBtn.hidden = true;
  }
  stopBtn?.addEventListener("click", stopCamera);
  window.addEventListener("beforeunload", stopCamera);

  // Native browser notifications are optional and foreground-only in this starter.
  if ("Notification" in window && Notification.permission === "default") {
    // Do not ask permission automatically; user consent should follow an explicit action.
  }
});
