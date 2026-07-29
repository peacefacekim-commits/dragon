// view_source.console.js 를 읽어 index.html 하나로 합치는 빌드 스크립트.
// 외부 패키지(terser 등) 없이 Node.js 표준 라이브러리만 사용한다.
// 사용법: node build_page.js   (view_source.console.js 를 고친 뒤 다시 실행하면 index.html 이 갱신됨)
"use strict";
const fs = require("fs");
const path = require("path");

const srcPath = path.join(__dirname, "view_source.console.js");
const outPath = path.join(__dirname, "index.html");

const src = fs.readFileSync(srcPath, "utf8");

// 줄 앞의 "//" 한 줄 주석과 파일 맨 위의 /* ... */ 블록 주석만 제거해
// 북마클릿용으로 압축한다. (문자열 리터럴 안의 "//"는 줄 시작이 아니므로 보존됨)
function stripComments(code) {
  const withoutBlockComment = code.replace(/\/\*[\s\S]*?\*\//, "");
  return withoutBlockComment
    .split("\n")
    .filter((line) => !/^\s*\/\//.test(line))
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join(" ");
}

// javascript: URL은 브라우저가 별도로 디코딩하지 않고 그대로 실행하므로
// encodeURIComponent 등으로 인코딩하면 안 된다. HTML 속성(href/value) 안에
// 넣기 위한 최소한의 이스케이프만 한다.
function escapeAttr(str) {
  return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}

// <textarea> 는 RCDATA라 &, <, > 를 문자 참조로 넣어야 원래 문자로 복원된다.
function escapeRcdata(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

const minified = stripComments(src);
const bookmarkletUrl = "javascript:" + minified;
const bookmarkletHrefAttr = escapeAttr(bookmarkletUrl);
const bookmarkletValueAttr = escapeAttr(bookmarkletUrl);
const consoleScriptRcdata = escapeRcdata(src);

const html = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>웹페이지 코드로 보기</title>
<style>
  :root { color-scheme: light dark; }
  body {
    margin: 0; padding: 32px 16px 64px; background: #f5f5f5; color: #1a1a1a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Malgun Gothic", sans-serif;
    line-height: 1.6;
  }
  @media (prefers-color-scheme: dark) {
    body { background: #1e1e1e; color: #e0e0e0; }
    .card { background: #2a2a2a !important; border-color: #3c3c3c !important; }
    textarea, input[readonly] { background: #1e1e1e !important; color: #d4d4d4 !important; border-color: #444 !important; }
  }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  .lead { color: #666; margin-top: 0; }
  .card {
    background: #fff; border: 1px solid #ddd; border-radius: 10px;
    padding: 20px 24px; margin: 20px 0;
  }
  .card h2 { font-size: 16px; margin-top: 0; }
  .step { font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: .05em; }
  .bookmarklet-btn {
    display: inline-block; padding: 10px 18px; margin: 12px 0;
    background: #0e639c; color: #fff !important; text-decoration: none;
    border-radius: 6px; font-weight: 600; cursor: grab;
  }
  .bookmarklet-btn:hover { background: #1177bb; }
  .row { display: flex; gap: 8px; align-items: center; margin: 10px 0; }
  input[readonly], textarea {
    width: 100%; box-sizing: border-box; font-family: Consolas, "D2Coding", monospace;
    font-size: 12px; padding: 8px 10px; border: 1px solid #ccc; border-radius: 6px;
    background: #fafafa; color: #333;
  }
  textarea { height: 160px; resize: vertical; white-space: pre; }
  button.copy {
    flex-shrink: 0; padding: 8px 14px; border: none; border-radius: 6px;
    background: #444; color: #fff; cursor: pointer; font-size: 13px;
  }
  button.copy:hover { background: #555; }
  .note { font-size: 13px; color: #777; }
  code { background: rgba(127,127,127,.15); padding: 1px 5px; border-radius: 4px; }
</style>
</head>
<body>
<main>
  <h1>웹페이지 코드로 보기</h1>
  <p class="lead">
    지금 화면에 실제로 그려져 있는 페이지(자바스크립트로 나중에 추가된 내용까지 포함)를
    사람이 읽기 좋은 HTML 코드로 정리해 새 탭에 보여줍니다. 외부 서버로 아무것도 보내지 않고
    브라우저 안에서만 동작하므로, 인터넷이 없는 내부망(인트라넷) 페이지에서도 그대로 동작합니다.
  </p>

  <div class="card">
    <div class="step">방법 A · 즐겨찾기 한 번 클릭 (추천)</div>
    <h2>아래 버튼을 즐겨찾기 표시줄로 드래그하세요</h2>
    <a class="bookmarklet-btn" href="${bookmarkletHrefAttr}" onclick="return false;">📄 코드로 보기</a>
    <p class="note">
      즐겨찾기 표시줄이 안 보이면 <code>Ctrl+Shift+B</code>(Mac은 <code>Cmd+Shift+B</code>)로 켤 수 있습니다.
      드래그가 안 되는 환경이라면 아래 링크를 복사해 새 즐겨찾기의 주소(URL) 칸에 직접 붙여넣으세요.
    </p>
    <div class="row">
      <input id="bookmarklet-url" type="text" readonly value="${bookmarkletValueAttr}">
      <button class="copy" data-copy-target="bookmarklet-url">복사</button>
    </div>
    <p class="note">등록해 두면, 코드로 보고 싶은 아무 페이지에서나 클릭 한 번으로 실행됩니다.</p>
  </div>

  <div class="card">
    <div class="step">방법 B · 개발자 도구 콘솔에 붙여넣기</div>
    <h2>아래 코드를 복사해 콘솔(F12 → Console)에 붙여넣고 Enter</h2>
    <div class="row">
      <textarea id="console-script" readonly>${consoleScriptRcdata}</textarea>
    </div>
    <button class="copy" data-copy-target="console-script">코드 복사</button>
    <p class="note">
      콘솔에 처음 붙여넣으면 브라우저가 "코드를 붙여넣으면 안 됩니다" 같은 경고를 보여줄 수 있습니다.
      직접 입력한 것이 맞다면 안내대로 <code>allow pasting</code> 등을 입력해 진행하면 됩니다.
    </p>
  </div>

  <p class="note">
    실행하면 정리된 HTML 코드가 담긴 새 탭이 열립니다(팝업 차단 알림이 뜨면 허용해 주세요).
    그 탭에서 코드를 다시 복사하거나 <code>.html</code> 파일로 내려받을 수 있습니다.
  </p>
</main>
<script>
  document.querySelectorAll("button.copy").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = document.getElementById(btn.getAttribute("data-copy-target"));
      var text = target.value;
      function fallback() {
        target.removeAttribute("readonly");
        target.focus();
        target.select();
        try { document.execCommand("copy"); } catch (e) {}
        target.setAttribute("readonly", "readonly");
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).catch(fallback);
      } else {
        fallback();
      }
      var original = btn.textContent;
      btn.textContent = "복사됨!";
      setTimeout(function () { btn.textContent = original; }, 1200);
    });
  });
</script>
</body>
</html>
`;

fs.writeFileSync(outPath, html);
console.log("wrote " + outPath + " (" + html.length + " bytes)");
