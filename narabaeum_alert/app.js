(() => {
  "use strict";

  const STORAGE_KEY = "narabaeum_timers_v1";

  const el = {
    permBanner: document.getElementById("perm-banner"),
    btnRequestPerm: document.getElementById("btn-request-perm"),
    courseLabel: document.getElementById("course-label"),
    btnCamera: document.getElementById("btn-camera"),
    cameraInput: document.getElementById("camera-input"),
    btnManualToggle: document.getElementById("btn-manual-toggle"),
    manualInputs: document.getElementById("manual-inputs"),
    manualHours: document.getElementById("manual-hours"),
    manualMinutes: document.getElementById("manual-minutes"),
    ocrPreview: document.getElementById("ocr-preview"),
    ocrStatus: document.getElementById("ocr-status"),
    ocrCandidates: document.getElementById("ocr-candidates"),
    btnStart: document.getElementById("btn-start"),
    timerList: document.getElementById("timer-list"),
    timerEmpty: document.getElementById("timer-empty"),
  };

  let selectedMinutes = null;

  // ---------- 시간 문자열 인식 ----------

  function normalizeDigits(text) {
    // OCR이 자주 헷갈리는 문자를 숫자로 보정
    return text
      .replace(/[oO]/g, "0")
      .replace(/[lI]/g, "1")
      .replace(/[Ss]/g, "5");
  }

  function parseDurationCandidates(rawText) {
    const text = normalizeDigits(rawText);
    const found = new Map(); // key: 분(정수) -> 표시용 라벨

    // "1시간 30분", "1시간30분", "2 시간"
    for (const m of text.matchAll(/(\d{1,2})\s*시간\s*(\d{1,2})?\s*분?/g)) {
      const h = parseInt(m[1], 10);
      const mm = m[2] ? parseInt(m[2], 10) : 0;
      if (h > 23 || mm > 59) continue;
      const total = h * 60 + mm;
      if (total > 0 && total < 24 * 60) {
        found.set(total, `${h}시간 ${mm}분`);
      }
    }

    // "45분" (위에서 이미 "시간"과 묶인 숫자는 별도로 다시 안 잡히게 최소 처리)
    for (const m of text.matchAll(/(?<![:\d])(\d{1,3})\s*분(?!의)/g)) {
        const mm = parseInt(m[1], 10);
        if (mm > 0 && mm < 24 * 60) {
          found.set(mm, `${mm}분`);
        }
    }

    // "01:30:00" (시:분:초)
    for (const m of text.matchAll(/(\d{1,2}):(\d{2}):(\d{2})/g)) {
      const h = parseInt(m[1], 10);
      const mm = parseInt(m[2], 10);
      if (h > 23 || mm > 59) continue;
      const total = h * 60 + mm;
      if (total > 0) {
        found.set(total, `${h}시간 ${mm}분 (${m[0]})`);
      }
    }

    // "01:30" (시:분으로 추정)
    for (const m of text.matchAll(/(?<!\d)(\d{1,2}):(\d{2})(?!:\d)/g)) {
      const h = parseInt(m[1], 10);
      const mm = parseInt(m[2], 10);
      if (h > 23 || mm > 59) continue;
      const total = h * 60 + mm;
      if (total > 0) {
        found.set(total, `${h}시간 ${mm}분 (${m[0]})`);
      }
    }

    return [...found.entries()]
      .sort((a, b) => b[0] - a[0])
      .slice(0, 6)
      .map(([minutes, label]) => ({ minutes, label }));
  }

  function renderCandidates(candidates) {
    el.ocrCandidates.innerHTML = "";
    if (candidates.length === 0) {
      el.ocrStatus.textContent =
        "시간을 자동으로 찾지 못했어요. '직접 입력'으로 넣어주세요.";
      return;
    }
    el.ocrStatus.textContent = "인식된 시간 후보예요. 맞는 걸 골라주세요.";
    candidates.forEach(({ minutes, label }) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = label;
      btn.addEventListener("click", () => {
        selectedMinutes = minutes;
        [...el.ocrCandidates.children].forEach((c) => c.classList.remove("selected"));
        btn.classList.add("selected");
        el.manualHours.value = Math.floor(minutes / 60);
        el.manualMinutes.value = minutes % 60;
        el.btnStart.disabled = false;
      });
      el.ocrCandidates.appendChild(btn);
    });
  }

  // ---------- OCR ----------

  el.btnCamera.addEventListener("click", () => el.cameraInput.click());

  el.cameraInput.addEventListener("change", async () => {
    const file = el.cameraInput.files && el.cameraInput.files[0];
    if (!file) return;

    const url = URL.createObjectURL(file);
    el.ocrPreview.src = url;
    el.ocrPreview.style.display = "block";
    el.ocrCandidates.innerHTML = "";
    el.btnStart.disabled = true;
    selectedMinutes = null;
    el.ocrStatus.textContent = "사진에서 글자를 읽는 중... (처음엔 조금 걸려요)";

    try {
      const { data } = await Tesseract.recognize(file, "kor", {
        logger: (m) => {
          if (m.status && typeof m.progress === "number") {
            el.ocrStatus.textContent = `${translateStatus(m.status)} ${Math.round(
              m.progress * 100
            )}%`;
          }
        },
      });
      const candidates = parseDurationCandidates(data.text || "");
      renderCandidates(candidates);
      if (candidates.length > 0) {
        // 가장 큰 후보를 기본 선택
        el.ocrCandidates.firstChild.click();
      }
    } catch (err) {
      console.error(err);
      el.ocrStatus.textContent =
        "인식에 실패했어요. 다시 찍거나 '직접 입력'을 사용해주세요.";
    }
  });

  function translateStatus(status) {
    const map = {
      "loading tesseract core": "엔진 불러오는 중",
      "initializing tesseract": "준비 중",
      "loading language traineddata": "한글 데이터 불러오는 중",
      "initializing api": "준비 중",
      "recognizing text": "글자 인식 중",
    };
    return map[status] || status;
  }

  // ---------- 수동 입력 ----------

  el.btnManualToggle.addEventListener("click", () => {
    const showing = el.manualInputs.style.display !== "none";
    el.manualInputs.style.display = showing ? "none" : "block";
  });

  function readManualMinutes() {
    const h = parseInt(el.manualHours.value, 10) || 0;
    const m = parseInt(el.manualMinutes.value, 10) || 0;
    return h * 60 + m;
  }

  [el.manualHours, el.manualMinutes].forEach((input) => {
    input.addEventListener("input", () => {
      const total = readManualMinutes();
      selectedMinutes = total > 0 ? total : null;
      el.btnStart.disabled = !(total > 0);
    });
  });

  // ---------- 타이머 ----------

  function loadTimers() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch {
      return [];
    }
  }

  function saveTimers(timers) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(timers));
  }

  let timers = loadTimers();

  el.btnStart.addEventListener("click", () => {
    const minutes = selectedMinutes || readManualMinutes();
    if (!minutes || minutes <= 0) return;

    const label = el.courseLabel.value.trim() || `교육 ${timers.length + 1}`;
    const now = Date.now();
    timers.push({
      id: `${now}-${Math.random().toString(36).slice(2, 8)}`,
      label,
      startTime: now,
      durationMinutes: minutes,
      endTime: now + minutes * 60 * 1000,
      notified: false,
    });
    saveTimers(timers);
    resetForm();
    renderTimers();
  });

  function resetForm() {
    el.courseLabel.value = "";
    el.ocrPreview.style.display = "none";
    el.ocrStatus.textContent = "";
    el.ocrCandidates.innerHTML = "";
    el.manualHours.value = 0;
    el.manualMinutes.value = 0;
    el.manualInputs.style.display = "none";
    el.btnStart.disabled = true;
    el.cameraInput.value = "";
    selectedMinutes = null;
  }

  function removeTimer(id) {
    timers = timers.filter((t) => t.id !== id);
    saveTimers(timers);
    renderTimers();
  }

  function formatRemaining(ms) {
    if (ms <= 0) return "완료!";
    const totalSec = Math.floor(ms / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    const pad = (n) => String(n).padStart(2, "0");
    return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
  }

  function renderTimers() {
    el.timerList.innerHTML = "";
    el.timerEmpty.style.display = timers.length === 0 ? "block" : "none";

    timers
      .slice()
      .sort((a, b) => a.endTime - b.endTime)
      .forEach((t) => {
        const remaining = t.endTime - Date.now();
        const done = remaining <= 0;
        const totalMs = t.durationMinutes * 60 * 1000;
        const progress = Math.min(1, Math.max(0, 1 - remaining / totalMs));

        const item = document.createElement("div");
        item.className = "timer-item" + (done ? " done" : "");
        item.innerHTML = `
          <div class="label">
            <span>${escapeHtml(t.label)}</span>
            <span>${done ? "✅" : "⏳"}</span>
          </div>
          <div class="remaining">${done ? "완료!" : formatRemaining(remaining)}</div>
          <div class="progress-bar"><div style="width:${progress * 100}%"></div></div>
          <div class="timer-actions">
            <button class="secondary" data-remove="${t.id}">삭제</button>
          </div>
        `;
        el.timerList.appendChild(item);
      });

    el.timerList.querySelectorAll("[data-remove]").forEach((btn) => {
      btn.addEventListener("click", () => removeTimer(btn.getAttribute("data-remove")));
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------- 완료 알림 ----------

  function beep() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      osc.start();
      osc.stop(ctx.currentTime + 0.4);
      osc.onended = () => ctx.close();
    } catch {
      // 무음 환경 등에서는 조용히 무시
    }
  }

  function notifyDone(timer) {
    const title = "🎉 교육 수강완료!";
    const body = `${timer.label} 학습 시간이 끝났어요.`;

    if ("serviceWorker" in navigator && Notification.permission === "granted") {
      navigator.serviceWorker.ready.then((reg) => {
        reg.showNotification(title, {
          body,
          icon: "icons/icon.svg",
          badge: "icons/icon.svg",
          tag: timer.id,
          vibrate: [200, 100, 200],
        });
      });
    } else if (Notification.permission === "granted") {
      new Notification(title, { body, icon: "icons/icon.svg" });
    }

    if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
    beep();
    document.title = "🎉 완료! - 나라배움터 알림";
  }

  function checkExpired() {
    let changed = false;
    const now = Date.now();
    timers.forEach((t) => {
      if (!t.notified && t.endTime <= now) {
        t.notified = true;
        changed = true;
        notifyDone(t);
      }
    });
    if (changed) saveTimers(timers);
  }

  function tick() {
    checkExpired();
    renderTimers();
  }

  setInterval(tick, 1000);
  tick();

  // ---------- 알림 권한 ----------

  function refreshPermBanner() {
    if (!("Notification" in window)) {
      el.permBanner.style.display = "none";
      return;
    }
    el.permBanner.style.display = Notification.permission === "granted" ? "none" : "block";
  }

  el.btnRequestPerm.addEventListener("click", async () => {
    if (!("Notification" in window)) return;
    await Notification.requestPermission();
    refreshPermBanner();
  });

  refreshPermBanner();

  // ---------- 서비스워커 등록 ----------

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("service-worker.js").catch((err) => {
        console.warn("서비스워커 등록 실패", err);
      });
    });
  }

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      document.title = "나라배움터 수강완료 알림";
      tick();
    }
  });
})();
