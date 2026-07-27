"""tkinter 기반 창 인터페이스.

파일을 고르고 → 컬럼 매핑을 눈으로 확인·수정하고 → 보고서를 뽑는 흐름.
tkinter 는 파이썬 공식 설치본에 기본 포함되므로 별도 설치가 필요 없다.
"""

from __future__ import annotations

import os
import sys
import threading
import traceback
import webbrowser

from .analysis import analyze
from .mapping import ColumnMapping, guess_mapping, load_profile, save_profile
from .report import write_report
from .table import Table, format_number, format_percent
from .xlsx_reader import SpreadsheetError, read_table, sheet_names
from .xlsx_writer import write_csv, write_xlsx

__all__ = ["launch"]

_NONE = "(사용 안 함)"
_ROLES = (
    ("category", "분류 기준", "부서·계정과목처럼 묶어서 볼 기준"),
    ("budget", "예산액", "계획된 금액"),
    ("actual", "집행액", "실제 쓴 금액"),
    ("amount", "금액", "예산/집행 구분이 없는 단일 금액"),
    ("date", "일자·기간", "추이 그래프의 가로축"),
)
_FILE_TYPES = [
    ("엑셀 · CSV", "*.xlsx *.xlsm *.csv *.tsv"),
    ("엑셀 파일", "*.xlsx *.xlsm"),
    ("CSV 파일", "*.csv *.tsv"),
    ("모든 파일", "*.*"),
]


def launch(initial_file: str | None = None) -> int:
    """GUI 를 띄운다. tkinter 가 없으면 안내 후 1 을 반환한다."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError:
        print(
            "이 파이썬에는 tkinter 가 없어 GUI 를 열 수 없습니다.\n"
            "  · Windows/macOS 공식 설치본에는 기본 포함되어 있습니다.\n"
            "  · 리눅스라면 python3-tk 패키지가 필요합니다.\n"
            "  · 지금은 명령줄로 사용하세요:  python -m budget_analyzer 파일.xlsx",
            file=sys.stderr,
        )
        return 1

    app = _App(tk, ttk, filedialog, messagebox, initial_file)
    app.run()
    return 0


class _App:
    """창 하나짜리 앱. 상태는 전부 여기 모아둔다."""

    def __init__(self, tk, ttk, filedialog, messagebox, initial_file: str | None) -> None:
        self.tk, self.ttk = tk, ttk
        self.filedialog, self.messagebox = filedialog, messagebox

        self.table: Table | None = None
        self.result = None
        self.path: str | None = None

        self.root = tk.Tk()
        self.root.title("예산 분석기 — 오프라인")
        self.root.geometry("880x720")
        self.root.minsize(760, 600)

        self.file_var = tk.StringVar(value="파일을 선택하세요")
        self.sheet_var = tk.StringVar()
        self.header_var = tk.StringVar(value="자동")
        self.grain_var = tk.StringVar(value="month")
        self.status_var = tk.StringVar(value="준비됨")
        self.role_vars = {key: tk.StringVar(value=_NONE) for key, _, _ in _ROLES}

        self._build()
        if initial_file and os.path.exists(initial_file):
            self._load_file(initial_file)

    # ── 화면 구성 ───────────────────────────────────────────────────

    def _build(self) -> None:
        tk, ttk = self.tk, self.ttk
        try:
            ttk.Style().theme_use("clam")
        except tk.TclError:
            pass

        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        # 1단계: 파일
        step1 = ttk.LabelFrame(outer, text=" 1. 엑셀 파일 ", padding=10)
        step1.pack(fill="x")
        row = ttk.Frame(step1)
        row.pack(fill="x")
        ttk.Button(row, text="파일 열기…", command=self._choose_file, width=14).pack(side="left")
        ttk.Label(row, textvariable=self.file_var, foreground="#444").pack(
            side="left", padx=10, fill="x", expand=True
        )

        row2 = ttk.Frame(step1)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="시트").pack(side="left")
        self.sheet_box = ttk.Combobox(row2, textvariable=self.sheet_var, state="readonly", width=26)
        self.sheet_box.pack(side="left", padx=(6, 16))
        self.sheet_box.bind("<<ComboboxSelected>>", lambda _event: self._reload())

        ttk.Label(row2, text="머리글 행").pack(side="left")
        header_box = ttk.Combobox(
            row2,
            textvariable=self.header_var,
            state="readonly",
            width=8,
            values=["자동"] + [str(i) for i in range(1, 21)],
        )
        header_box.pack(side="left", padx=6)
        header_box.bind("<<ComboboxSelected>>", lambda _event: self._reload())

        # 2단계: 컬럼 매핑
        step2 = ttk.LabelFrame(outer, text=" 2. 컬럼 지정 (자동 인식된 값을 확인하세요) ", padding=10)
        step2.pack(fill="x", pady=10)
        self.role_boxes = {}
        for index, (key, label, hint) in enumerate(_ROLES):
            line = ttk.Frame(step2)
            line.pack(fill="x", pady=2)
            ttk.Label(line, text=label, width=10).pack(side="left")
            box = ttk.Combobox(line, textvariable=self.role_vars[key], state="readonly", width=28)
            box.pack(side="left", padx=6)
            ttk.Label(line, text=hint, foreground="#777").pack(side="left", padx=6)
            self.role_boxes[key] = box

        line = ttk.Frame(step2)
        line.pack(fill="x", pady=(8, 0))
        ttk.Label(line, text="추이 단위", width=10).pack(side="left")
        for value, text in (("month", "월별"), ("quarter", "분기별"), ("year", "연도별")):
            ttk.Radiobutton(line, text=text, value=value, variable=self.grain_var).pack(side="left", padx=4)
        ttk.Button(line, text="매핑 저장…", command=self._save_profile).pack(side="right", padx=3)
        ttk.Button(line, text="매핑 불러오기…", command=self._load_profile).pack(side="right", padx=3)

        # 3단계: 실행
        step3 = ttk.Frame(outer)
        step3.pack(fill="x")
        self.run_button = ttk.Button(step3, text="분석 실행", command=self._run, width=16)
        self.run_button.pack(side="left")
        ttk.Button(step3, text="보고서 열기", command=self._open_report).pack(side="left", padx=5)
        ttk.Button(step3, text="엑셀로 저장…", command=self._save_xlsx).pack(side="left", padx=5)
        ttk.Button(step3, text="CSV로 저장…", command=self._save_csv).pack(side="left", padx=5)

        # 결과 요약
        result_frame = ttk.LabelFrame(outer, text=" 결과 요약 ", padding=8)
        result_frame.pack(fill="both", expand=True, pady=10)
        self.output = self.tk.Text(
            result_frame, wrap="word", height=18, relief="flat", background="#fbfbfa"
        )
        scroll = ttk.Scrollbar(result_frame, command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set, state="disabled")
        scroll.pack(side="right", fill="y")
        self.output.pack(side="left", fill="both", expand=True)

        ttk.Label(outer, textvariable=self.status_var, foreground="#555").pack(fill="x")

    # ── 동작 ────────────────────────────────────────────────────────

    def _write(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def _choose_file(self) -> None:
        path = self.filedialog.askopenfilename(title="예산 엑셀 파일 선택", filetypes=_FILE_TYPES)
        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        self.path = path
        self.file_var.set(os.path.basename(path))
        try:
            names = sheet_names(path)
        except (SpreadsheetError, OSError) as error:
            self.messagebox.showerror("파일 열기 실패", str(error))
            return
        self.sheet_box["values"] = names
        if names:
            self.sheet_var.set(names[0] if len(names) == 1 else "")
        self._reload()

    def _reload(self) -> None:
        """선택된 시트를 다시 읽고 컬럼 매핑을 자동 인식한다."""
        if not self.path:
            return
        sheet = self.sheet_var.get() or None
        if sheet == "(csv)":
            sheet = None

        header = None
        if self.header_var.get() != "자동":
            header = int(self.header_var.get()) - 1

        try:
            self.table = read_table(self.path, sheet=sheet, header_row=header)
        except (SpreadsheetError, OSError, ValueError) as error:
            self.messagebox.showerror("읽기 실패", str(error))
            return

        if not self.sheet_var.get():
            self.sheet_var.set(self.table.name)

        options = [_NONE] + self.table.columns
        for box in self.role_boxes.values():
            box["values"] = options

        mapping = guess_mapping(self.table)
        self._apply_mapping(mapping)

        preview = [
            f"파일: {self.path}",
            f"시트: {self.table.name}   행 수: {len(self.table):,}",
            f"컬럼 ({len(self.table.columns)}개): {', '.join(self.table.columns)}",
            "",
            "자동 인식 결과: " + mapping.describe(),
            "",
            "─ 미리보기 (상위 5행) " + "─" * 30,
        ]
        head = self.table.head(5)
        preview.append(" | ".join(str(c)[:14] for c in head.columns))
        for row in head.rows:
            preview.append(" | ".join("" if c is None else str(c)[:14] for c in row))
        preview.append("")
        preview.append("컬럼 지정을 확인한 뒤 [분석 실행] 을 누르세요.")
        self._write("\n".join(preview))
        self.status_var.set(f"{len(self.table):,}행을 읽었습니다.")

    def _apply_mapping(self, mapping: ColumnMapping) -> None:
        for key, _, _ in _ROLES:
            value = getattr(mapping, key)
            self.role_vars[key].set(value if value in (self.table.columns if self.table else []) else _NONE)

    def _current_mapping(self) -> ColumnMapping:
        mapping = ColumnMapping()
        for key, _, _ in _ROLES:
            value = self.role_vars[key].get()
            setattr(mapping, key, None if value == _NONE else value)
        return mapping

    def _run(self) -> None:
        if self.table is None:
            self.messagebox.showinfo("파일 필요", "먼저 엑셀 파일을 선택하세요.")
            return

        mapping = self._current_mapping()
        if mapping.value_column is None:
            self.messagebox.showwarning(
                "컬럼 확인",
                "예산액·집행액·금액 중 최소 하나는 지정해야 분석할 수 있습니다.",
            )
            return

        self.run_button.state(["disabled"])
        self.status_var.set("분석 중…")

        def work() -> None:
            try:
                result = analyze(
                    self.table,
                    mapping,
                    source=self.path or "",
                    grain=self.grain_var.get(),
                )
                report_path = os.path.join(
                    os.path.dirname(os.path.abspath(self.path or ".")),
                    os.path.splitext(os.path.basename(self.path or "분석"))[0] + "_분석.html",
                )
                write_report(
                    report_path,
                    result,
                    title=f"예산 분석 보고서 — {os.path.basename(self.path or '')}",
                )
            except Exception:  # 사용자에게 스택을 그대로 보여주는 편이 낫다.
                message = traceback.format_exc()
                self.root.after(0, lambda: self._failed(message))
                return
            self.root.after(0, lambda: self._succeeded(result, report_path))

        threading.Thread(target=work, daemon=True).start()

    def _failed(self, message: str) -> None:
        self.run_button.state(["!disabled"])
        self.status_var.set("분석 실패")
        self._write("분석 중 오류가 발생했습니다.\n\n" + message)

    def _succeeded(self, result, report_path: str) -> None:
        self.result = result
        self.report_path = report_path
        self.run_button.state(["!disabled"])
        self.status_var.set(f"완료 — 보고서: {report_path}")
        self._write(self._summary(result, report_path))
        self._open_report()

    def _summary(self, result, report_path: str) -> str:
        lines = [
            f"분석 완료 — {result.sheet} ({result.row_count:,}행)",
            f"인식된 컬럼: {result.mapping.describe()}",
            "",
        ]
        for label, value in result.totals.items():
            lines.append(f"  총 {label}: {format_number(value)} 원")
        rate = result.execution_rate
        if rate is not None:
            remaining = result.totals.get("예산액", 0.0) - result.totals.get("집행액", 0.0)
            lines.append(f"  전체 집행률: {format_percent(rate)}  (잔액 {format_number(remaining)} 원)")

        if result.breakdown is not None and len(result.breakdown):
            value_column = result.mapping.value_column
            index = result.breakdown.index_of(value_column)
            share_index = result.breakdown.index_of("구성비")
            lines += ["", f"  [상위 항목] {result.mapping.category}별 {value_column}"]
            for row in result.breakdown.rows[:8]:
                share = row[share_index]
                lines.append(
                    f"    {str(row[0])[:26]:<26} {format_number(row[index]):>16}"
                    f"   {format_percent(share) if share is not None else '-'}"
                )

        if result.warnings:
            lines += ["", "  [확인 필요]"] + [f"    · {w}" for w in result.warnings]
        lines += ["", f"보고서를 브라우저로 열었습니다:\n  {report_path}"]
        return "\n".join(lines)

    def _open_report(self) -> None:
        path = getattr(self, "report_path", None)
        if not path or not os.path.exists(path):
            self.messagebox.showinfo("보고서 없음", "먼저 [분석 실행] 을 눌러 보고서를 만드세요.")
            return
        webbrowser.open(f"file:///{os.path.abspath(path).replace(os.sep, '/')}")

    def _save_xlsx(self) -> None:
        if self.result is None or not self.result.tables():
            self.messagebox.showinfo("결과 없음", "먼저 분석을 실행하세요.")
            return
        path = self.filedialog.asksaveasfilename(
            title="분석 결과 저장", defaultextension=".xlsx", filetypes=[("엑셀 파일", "*.xlsx")]
        )
        if not path:
            return
        write_xlsx(path, self.result.tables())
        self.status_var.set(f"엑셀 저장 완료: {path}")

    def _save_csv(self) -> None:
        if self.result is None or not self.result.tables():
            self.messagebox.showinfo("결과 없음", "먼저 분석을 실행하세요.")
            return
        folder = self.filedialog.askdirectory(title="CSV 를 저장할 폴더 선택")
        if not folder:
            return
        for table in self.result.tables():
            write_csv(os.path.join(folder, f"{table.name or 'sheet'}.csv"), table)
        self.status_var.set(f"CSV 저장 완료: {folder}")

    def _save_profile(self) -> None:
        path = self.filedialog.asksaveasfilename(
            title="컬럼 매핑 저장", defaultextension=".json", filetypes=[("JSON", "*.json")]
        )
        if path:
            save_profile(path, self._current_mapping())
            self.status_var.set(f"매핑 저장 완료: {path}")

    def _load_profile(self) -> None:
        if self.table is None:
            self.messagebox.showinfo("파일 필요", "먼저 엑셀 파일을 선택하세요.")
            return
        path = self.filedialog.askopenfilename(
            title="컬럼 매핑 불러오기", filetypes=[("JSON", "*.json"), ("모든 파일", "*.*")]
        )
        if not path:
            return
        try:
            self._apply_mapping(load_profile(path))
        except (OSError, ValueError, TypeError) as error:
            self.messagebox.showerror("불러오기 실패", str(error))
            return
        self.status_var.set(f"매핑 불러옴: {path}")

    def run(self) -> None:
        self.root.mainloop()
