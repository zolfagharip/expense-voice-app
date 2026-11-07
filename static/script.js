// ========== تنظیمات ==========
const recordBtn = document.getElementById("recordBtn");
const statusEl = document.getElementById("status");
const resultBox = document.getElementById("resultBox");
const resAmount = document.getElementById("resAmount");
const resCategory = document.getElementById("resCategory");
const resDescription = document.getElementById("resDescription");
const resRawTranscript = document.getElementById("resRawTranscript");
const cancelResult = document.getElementById("cancelResult");

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let stream = null;

// ========== ضبط صدا ==========

async function startRecording() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];

    // انتخاب فرمت مناسب
    let mimeType = "";
    if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
      mimeType = "audio/webm;codecs=opus";
    } else if (MediaRecorder.isTypeSupported("audio/webm")) {
      mimeType = "audio/webm";
    } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
      mimeType = "audio/mp4";
    }

    const options = mimeType ? { mimeType } : {};
    mediaRecorder = new MediaRecorder(stream, options);

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      // آزاد کردن میکروفون
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
      }

      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      if (blob.size < 1000) {
        setStatus("ضبط خیلی کوتاه بود. دوباره امتحان کن.", "error");
        resetButton();
        return;
      }

      setStatus("⏳ در حال ارسال و پردازش...");
      await sendAudioToServer(blob);
      resetButton();
    };

    mediaRecorder.start();
    isRecording = true;
    recordBtn.classList.add("recording");
    recordBtn.querySelector(".record-label").textContent = "⏹ توقف و ارسال";
    setStatus("🔴 در حال ضبط... دوباره بزن تا ارسال بشه.");
  } catch (err) {
    console.error(err);
    let msg = "دسترسی به میکروفون ممکن نشد.";
    if (err.name === "NotAllowedError") msg = "اجازه دسترسی به میکروفون داده نشد.";
    if (err.name === "NotFoundError") msg = "میکروفونی پیدا نشد.";
    setStatus(msg, "error");
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    isRecording = false;
  }
}

function resetButton() {
  recordBtn.classList.remove("recording");
  recordBtn.querySelector(".record-label").textContent = "شروع ضبط";
}

async function sendAudioToServer(blob) {
  const formData = new FormData();
  const ext = blob.type.includes("mp4") ? "mp4" : "webm";
  formData.append("audio", blob, `voice.${ext}`);

  try {
    const res = await fetch("/api/voice", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok || data.error) {
      setStatus("خطا: " + (data.error || "پردازش ناموفق"), "error");
      return;
    }

    if (!data.amount || data.amount <= 0) {
      setStatus("مبلغ شناسایی نشد. واضح‌تر بگو یا دستی وارد کن.", "error");
      showResult(data);
      return;
    }

    setStatus("✅ تشخیص انجام شد. بررسی و ذخیره کن.", "success");
    showResult(data);
  } catch (err) {
    console.error(err);
    setStatus("خطا در ارتباط با سرور.", "error");
  }
}

function showResult(data) {
  resAmount.value = data.amount || 0;
  resDescription.value = data.description || "";
  resRawTranscript.value = data.raw_transcript || "";

  if (data.category) {
    // انتخاب دسته در select
    const opt = Array.from(resCategory.options).find((o) => o.value === data.category);
    if (opt) resCategory.value = data.category;
  }

  resultBox.style.display = "block";
  resultBox.scrollIntoView({ behavior: "smooth", block: "center" });
}

function setStatus(text, type) {
  statusEl.textContent = text;
  statusEl.className = "status" + (type ? " " + type : "");
}

// ========== رویدادها ==========

recordBtn.addEventListener("click", () => {
  if (!isRecording) startRecording();
  else stopRecording();
});

cancelResult.addEventListener("click", () => {
  resultBox.style.display = "none";
  setStatus("");
});

// ========== Shake detection (اختیاری، برای موبایل) ==========
let lastShake = 0;
window.addEventListener("devicemotion", (e) => {
  const acc = e.accelerationIncludingGravity;
  if (!acc) return;
  const magnitude = Math.sqrt(acc.x * acc.x + acc.y * acc.y + acc.z * acc.z);
  if (magnitude > 25 && Date.now() - lastShake > 1500) {
    lastShake = Date.now();
    // فقط اگه در حال ضبط نبود، شروع کن
    if (!isRecording && resultBox.style.display === "none") {
      startRecording();
      // ۳ ثانیه بعد خودکار متوقف کن
      setTimeout(() => {
        if (isRecording) stopRecording();
      }, 4000);
    }
  }
});

// ثبت Service Worker برای PWA
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((err) => {
      console.log("SW registration failed:", err);
    });
  });
}