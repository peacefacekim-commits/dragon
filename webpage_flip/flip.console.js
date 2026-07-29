/*
 * 웹페이지 뒤집기 (거꾸로 보기)
 *
 * 사용법
 *   1) 뒤집고 싶은 페이지에서 개발자 도구(F12 / Ctrl+Shift+I)를 엽니다.
 *   2) Console 탭에 이 파일 내용 전체를 붙여넣고 Enter.
 *   3) 페이지가 180도 회전합니다. 같은 스크립트를 한 번 더 실행하면 원래대로 돌아옵니다.
 *
 * 외부 리소스(CDN, 이미지, 폰트 등)를 전혀 불러오지 않는 순수 자바스크립트이므로
 * 인터넷이 연결되지 않은 내부망(인트라넷) 페이지에서도 동일하게 동작합니다.
 */
(function () {
  var STYLE_ID = "__webpage_flip_180__";
  var existing = document.getElementById(STYLE_ID);

  if (existing) {
    existing.remove();
    return;
  }

  var style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent =
    "html{" +
    "transform:rotate(180deg) !important;" +
    "transform-origin:50% 50% !important;" +
    "}";

  (document.head || document.documentElement).appendChild(style);
})();
