(() => {
  const DURATION = 60;
  let remaining = DURATION;

  const statusEl = document.getElementById("status");
  const timerEl = document.getElementById("timer");
  const fillEl = document.getElementById("fill");
  const nextBtn = document.getElementById("next-btn");
  const hintEl = document.getElementById("hint");

  function fmt(sec) {
    const m = String(Math.floor(sec / 60)).padStart(2, "0");
    const s = String(sec % 60).padStart(2, "0");
    return `${m}:${s} 남음`;
  }

  function tick() {
    const pct = Math.round(((DURATION - remaining) / DURATION) * 100);
    fillEl.style.width = pct + "%";
    timerEl.textContent = fmt(remaining);

    if (remaining <= 0) {
      clearInterval(intervalId);
      statusEl.textContent = "수강완료";
      statusEl.classList.remove("learning");
      statusEl.classList.add("done");
      fillEl.classList.add("done");
      timerEl.textContent = "완료";
      nextBtn.classList.add("show");
      hintEl.classList.add("show");
      return;
    }
    remaining -= 1;
  }

  tick();
  const intervalId = setInterval(tick, 1000);
})();
