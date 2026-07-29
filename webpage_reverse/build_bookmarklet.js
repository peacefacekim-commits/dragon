// view_source.console.js 를 읽어 javascript: 북마클릿 한 줄로 압축하는 빌드 스크립트.
// 외부 패키지(terser 등) 없이 표준 라이브러리만 사용한다.
// 사용법: node build_bookmarklet.js > flip.bookmarklet.txt (또는 npm run build 대신 수동 실행)
"use strict";
const fs = require("fs");
const path = require("path");

const srcPath = path.join(__dirname, "view_source.console.js");
const outPath = path.join(__dirname, "view_source.bookmarklet.txt");

let src = fs.readFileSync(srcPath, "utf8");

// 줄 앞의 "//" 한 줄 주석만 제거한다. (문자열 안의 "//"는 건드리지 않도록
// 각 줄이 공백을 제외하고 "//"로 "시작"할 때만 지운다.)
const lines = src.split("\n").filter((line) => !/^\s*\/\//.test(line));

// 여러 줄에 걸친 /* ... */ 블록 주석(파일 맨 위 설명)만 별도로 제거한다.
let body = lines.join("\n").replace(/\/\*[\s\S]*?\*\//, "");

// 줄 단위로 앞뒤 공백만 잘라내 크기를 줄인다. (문자열 리터럴 내부 공백은 보존됨)
body = body
  .split("\n")
  .map((line) => line.trim())
  .filter((line) => line.length > 0)
  .join("\n");

// 한 줄로 합친다. javascript: URL은 브라우저가 별도로 디코딩하지 않고
// 그대로 실행하므로 encodeURIComponent 등으로 인코딩하면 안 된다.
const oneLine = body.split("\n").join(" ");

const bookmarklet = "javascript:" + oneLine;

fs.writeFileSync(outPath, bookmarklet + "\n");
console.log("wrote " + outPath + " (" + bookmarklet.length + " chars)");
