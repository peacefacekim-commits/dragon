/*
 * 웹페이지 코드로 보기 (개발자 도구용)
 *
 * 지금 브라우저에 "실제로 그려져 있는" DOM(자바스크립트로 나중에 추가/변경된
 * 내용까지 전부 포함)을 사람이 읽기 좋은 HTML 코드로 정리해서 새 탭에 보여줍니다.
 * 브라우저 기본 기능인 "페이지 소스 보기(Ctrl+U)"는 서버가 처음 내려준 원본
 * HTML만 보여주지만, 이 도구는 지금 화면에 보이는 그대로의 코드를 보여줍니다.
 *
 * 사용법
 *   1) 코드로 보고 싶은 페이지에서 개발자 도구(F12 / Ctrl+Shift+I)를 엽니다.
 *   2) Console 탭에 이 파일 내용 전체를 붙여넣고 Enter.
 *   3) 정리된 HTML 코드가 담긴 새 탭이 열립니다. 복사/다운로드 버튼도 함께 나옵니다.
 *
 * 외부 서버로 아무것도 전송하지 않고, CDN 등 외부 리소스도 전혀 불러오지 않는
 * 순수 자바스크립트입니다. 브라우저 안에서만 동작하므로 인터넷이 없는
 * 내부망(인트라넷) 페이지에서도 동일하게 동작합니다.
 */
(function () {
  "use strict";

  var VOID_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
  ];
  var RAW_TEXT_TAGS = ["script", "style"];

  function indent(n) {
    return "  ".repeat(n);
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // 태그 단위로 잘라 들여쓰기를 붙여 사람이 읽기 좋은 형태로 재구성한다.
  // <script>/<style> 안쪽 내용은 태그로 착각해 잘못 잘리지 않도록 통째로 다룬다.
  function formatHtml(html) {
    var tokens = html.match(/<!--[\s\S]*?-->|<[^>]+>|[^<]+/g) || [];
    var out = [];
    var depth = 0;
    var rawTag = null;
    var rawBuffer = "";

    tokens.forEach(function (token) {
      if (rawTag) {
        var closeRe = new RegExp("^</" + rawTag + "\\s*>$", "i");
        if (closeRe.test(token.trim())) {
          if (rawBuffer.trim()) {
            out.push(indent(depth + 1) + rawBuffer.trim());
          }
          out.push(indent(depth) + token.trim());
          rawTag = null;
          rawBuffer = "";
        } else {
          rawBuffer += token;
        }
        return;
      }

      if (/^<!--/.test(token)) {
        out.push(indent(depth) + token.trim());
        return;
      }

      if (/^<[^>]+>$/.test(token)) {
        var isClosing = /^<\//.test(token);
        var isSelfClosing = /\/>$/.test(token);
        var tagName = (token.match(/^<\/?([a-zA-Z0-9-]+)/) || [])[1];
        var isVoid = tagName && VOID_TAGS.indexOf(tagName.toLowerCase()) !== -1;

        if (isClosing) {
          depth = Math.max(0, depth - 1);
          out.push(indent(depth) + token.trim());
        } else {
          out.push(indent(depth) + token.trim());
          if (
            tagName &&
            RAW_TEXT_TAGS.indexOf(tagName.toLowerCase()) !== -1 &&
            !isSelfClosing
          ) {
            rawTag = tagName.toLowerCase();
          } else if (!isSelfClosing && !isVoid) {
            depth++;
          }
        }
      } else {
        var text = token.trim();
        if (text) out.push(indent(depth) + text);
      }
    });

    return out.join("\n");
  }

  var sourceHtml = document.documentElement.outerHTML;
  var formatted = formatHtml(sourceHtml);
  var escaped = escapeHtml(formatted);
  var pageTitle = document.title || "제목 없음";
  var pageUrl = location.href;
  var capturedAt = new Date().toLocaleString();

  var viewerHtml =
    "<!DOCTYPE html><html><head><meta charset=\"utf-8\">" +
    "<title>코드로 보기 - " + escapeHtml(pageTitle) + "</title>" +
    "<style>" +
    "body{margin:0;background:#1e1e1e;color:#d4d4d4;font-family:Consolas,'D2Coding',monospace;}" +
    "header{position:sticky;top:0;background:#252526;border-bottom:1px solid #3c3c3c;padding:10px 16px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;}" +
    "header .info{flex:1;min-width:200px;font-size:12px;color:#9d9d9d;overflow-wrap:anywhere;}" +
    "header .info b{color:#d4d4d4;}" +
    "button{background:#0e639c;color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;}" +
    "button:hover{background:#1177bb;}" +
    "pre{margin:0;padding:16px;white-space:pre-wrap;word-break:break-all;font-size:13px;line-height:1.5;}" +
    "</style></head><body>" +
    "<header>" +
    "<div class=\"info\"><b>" + escapeHtml(pageTitle) + "</b><br>" +
    escapeHtml(pageUrl) + " · " + escapeHtml(capturedAt) + " 캡처</div>" +
    "<button id=\"__copy_btn\">코드 복사</button>" +
    "<button id=\"__download_btn\">.html로 다운로드</button>" +
    "</header>" +
    "<pre id=\"__source_code\">" + escaped + "</pre>" +
    "<script>" +
    "document.getElementById('__copy_btn').addEventListener('click', function () {" +
    "  var text = document.getElementById('__source_code').textContent;" +
    "  function fallback() {" +
    "    var ta = document.createElement('textarea');" +
    "    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';" +
    "    document.body.appendChild(ta); ta.select();" +
    "    try { document.execCommand('copy'); } catch (e) {}" +
    "    document.body.removeChild(ta);" +
    "  }" +
    "  if (navigator.clipboard && navigator.clipboard.writeText) {" +
    "    navigator.clipboard.writeText(text).catch(fallback);" +
    "  } else { fallback(); }" +
    "  var btn = document.getElementById('__copy_btn');" +
    "  var original = btn.textContent; btn.textContent = '복사됨!';" +
    "  setTimeout(function () { btn.textContent = original; }, 1200);" +
    "});" +
    "document.getElementById('__download_btn').addEventListener('click', function () {" +
    "  var text = document.getElementById('__source_code').textContent;" +
    "  var blob = new Blob([text], { type: 'text/html' });" +
    "  var a = document.createElement('a');" +
    "  a.href = URL.createObjectURL(blob);" +
    "  a.download = 'page-source.html';" +
    "  document.body.appendChild(a); a.click(); document.body.removeChild(a);" +
    "});" +
    "<" + "/script>" +
    "</body></html>";

  var blob = new Blob([viewerHtml], { type: "text/html" });
  var url = URL.createObjectURL(blob);
  window.open(url, "_blank");
})();
