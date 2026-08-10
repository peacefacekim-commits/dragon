"""tkinter 기반 창 인터페이스.

세 단계로 나뉜다.
  1. 데이터 — 엑셀을 열고 시트·머리글을 확인한다
  2. 분석 양식 — 무엇을 어떻게 집계할지 직접 정의한다 (JSON 을 손으로 쓸 필요 없음)
  3. 실행 — 양식대로 분석해 보고서를 만든다

tkinter 는 파이썬 공식 설치본에 기본 포함되므로 별도 설치가 필요 없다.
"""

from __future__ import annotations

import datetime as _dt
import os
import sys
import threading
import traceback
import webbrowser

from . import expression
from .engine import run
from .forecast import ForecastError, ForecastSettings, build_forecast, end_of_quarter, write_forecast
from .mapping import guess_mapping
from .report import write_report
from .table import Table, format_number, format_percent, to_date, to_number
from .template import (
    AGGREGATIONS,
    FORMATS,
    Block,
    Computed,
    Measure,
    Rule,
    Summary,
    Template,
    TemplateError,
    builtin_templates,
    load_template,
    save_template,
    template_from_mapping,
)
from .xlsx_reader import SpreadsheetError, read_table, sheet_names
from .xlsx_writer import write_csv, write_xlsx

__all__ = ["launch"]

_FILE_TYPES = [
    ("엑셀 · CSV", "*.xlsx *.xlsm *.csv *.tsv"),
    ("엑셀 파일", "*.xlsx *.xlsm"),
    ("CSV 파일", "*.csv *.tsv"),
    ("모든 파일", "*.*"),
]
_JSON_TYPES = [("분석 양식 (JSON)", "*.json"), ("모든 파일", "*.*")]

BLOCK_KINDS = ("집계", "추이", "목록")
CHART_KINDS = ("자동", "막대", "선", "없음")
GRAINS = ("월", "분기", "연도")


def launch(initial_file: str | None = None) -> int:
    """GUI 를 띄운다. tkinter 가 없으면 안내 후 1 을 반환한다."""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print(
            "이 파이썬에는 tkinter 가 없어 GUI 를 열 수 없습니다.\n"
            "  · Windows/macOS 공식 설치본에는 기본 포함되어 있습니다.\n"
            "  · 리눅스라면 python3-tk 패키지가 필요합니다.\n"
            "  · 지금은 명령줄로 사용하세요:  python -m budget_analyzer 파일.xlsx",
            file=sys.stderr,
        )
        return 1

    _App(initial_file).run()
    return 0


# ── 작은 도우미 위젯 ───────────────────────────────────────────────


class _RecordDialog:
    """dataclass 한 건을 편집하는 모달 창.

    ``spec`` 은 (필드명, 라벨, 종류, 선택지) 목록. 종류는 text/combo/int/check.
    """

    def __init__(self, parent, title: str, spec, record, columns) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.spec = spec
        self.record = record
        self.columns = columns
        self.result = None

        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.resizable(True, False)

        frame = ttk.Frame(self.window, padding=12)
        frame.pack(fill="both", expand=True)

        self.vars: dict[str, object] = {}
        for row, (name, label, kind, options) in enumerate(spec):
            ttk.Label(frame, text=label, width=10).grid(row=row, column=0, sticky="w", pady=3)
            current = getattr(record, name, "")

            if kind == "check":
                variable = tk.BooleanVar(value=bool(current))
                ttk.Checkbutton(frame, variable=variable).grid(row=row, column=1, sticky="w")
            elif kind == "combo":
                variable = tk.StringVar(value=str(current))
                choices = list(options) if options else list(columns)
                ttk.Combobox(
                    frame, textvariable=variable, values=choices, state="readonly", width=34
                ).grid(row=row, column=1, sticky="we")
            elif kind == "column":
                variable = tk.StringVar(value=str(current))
                ttk.Combobox(frame, textvariable=variable, values=list(columns), width=34).grid(
                    row=row, column=1, sticky="we"
                )
            else:
                variable = tk.StringVar(value="" if current is None else str(current))
                ttk.Entry(frame, textvariable=variable, width=36).grid(row=row, column=1, sticky="we")

            self.vars[name] = variable
            if kind == "formula":
                ttk.Button(
                    frame, text="함수 도움말", command=lambda: _show_function_help(self.window)
                ).grid(row=row, column=2, padx=4)

        frame.columnconfigure(1, weight=1)

        self.message = ttk.Label(frame, text="", foreground="#b00")
        self.message.grid(row=len(spec), column=0, columnspan=3, sticky="w", pady=(6, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(spec) + 1, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="취소", command=self.window.destroy).pack(side="right", padx=3)
        ttk.Button(buttons, text="확인", command=self._accept).pack(side="right", padx=3)

        self.window.bind("<Return>", lambda _event: self._accept())
        self.window.bind("<Escape>", lambda _event: self.window.destroy())

    def _accept(self) -> None:
        values = {}
        for name, label, kind, _options in self.spec:
            raw = self.vars[name].get()
            if kind == "int":
                try:
                    values[name] = int(raw or 0)
                except ValueError:
                    self.message.configure(text=f"'{label}' 은 숫자여야 합니다.")
                    return
            elif kind == "check":
                values[name] = bool(raw)
            else:
                values[name] = str(raw).strip()

            # 수식은 저장 전에 문법을 확인해 준다.
            if kind == "formula" and values[name]:
                problem = expression.check(values[name], self.columns)
                if problem:
                    self.message.configure(text=problem)
                    return

        for name, value in values.items():
            setattr(self.record, name, value)
        self.result = self.record
        self.window.destroy()

    def show(self):
        self.window.wait_window()
        return self.result


class _ListEditor:
    """dataclass 목록을 추가/수정/삭제하는 작은 편집기."""

    def __init__(self, parent, title: str, spec, factory, describe, columns_getter) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.spec = spec
        self.factory = factory
        self.describe = describe
        self.columns_getter = columns_getter
        self.items: list = []

        self.frame = ttk.LabelFrame(parent, text=f" {title} ", padding=8)
        body = ttk.Frame(self.frame)
        body.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(body, height=4, activestyle="none", exportselection=False)
        scroll = ttk.Scrollbar(body, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda _event: self.edit())

        buttons = ttk.Frame(self.frame)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="추가", command=self.add, width=8).pack(side="left")
        ttk.Button(buttons, text="수정", command=self.edit, width=8).pack(side="left", padx=3)
        ttk.Button(buttons, text="삭제", command=self.remove, width=8).pack(side="left")
        ttk.Button(buttons, text="▲", command=lambda: self.move(-1), width=3).pack(side="right")
        ttk.Button(buttons, text="▼", command=lambda: self.move(1), width=3).pack(side="right", padx=3)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
        return self

    def set_items(self, items) -> None:
        self.items = list(items)
        self.refresh()

    def refresh(self) -> None:
        selected = self.listbox.curselection()
        self.listbox.delete(0, "end")
        for item in self.items:
            self.listbox.insert("end", self.describe(item))
        if selected and selected[0] < len(self.items):
            self.listbox.selection_set(selected[0])

    def _selected(self) -> int | None:
        selection = self.listbox.curselection()
        return selection[0] if selection else None

    def add(self) -> None:
        record = _RecordDialog(
            self.frame, "추가", self.spec, self.factory(), self.columns_getter()
        ).show()
        if record is not None:
            self.items.append(record)
            self.refresh()

    def edit(self) -> None:
        index = self._selected()
        if index is None:
            return
        record = _RecordDialog(
            self.frame, "수정", self.spec, self.items[index], self.columns_getter()
        ).show()
        if record is not None:
            self.items[index] = record
        self.refresh()

    def remove(self) -> None:
        index = self._selected()
        if index is None:
            return
        del self.items[index]
        self.refresh()

    def move(self, delta: int) -> None:
        index = self._selected()
        if index is None:
            return
        target = index + delta
        if not 0 <= target < len(self.items):
            return
        self.items[index], self.items[target] = self.items[target], self.items[index]
        self.refresh()
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(target)


def _show_function_help(parent) -> None:
    import tkinter as tk
    from tkinter import ttk

    window = tk.Toplevel(parent)
    window.title("수식에서 쓸 수 있는 함수")
    window.geometry("620x520")

    text = tk.Text(window, wrap="word", padx=12, pady=10)
    scroll = ttk.Scrollbar(window, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    text.pack(side="left", fill="both", expand=True)

    lines = [
        "컬럼은 대괄호로 감쌉니다.   예)  [집행액] / [예산액]",
        "문자열은 큰따옴표로 감쌉니다.   예)  [구분] == \"정기\"",
        "연산자: + - * / % **   ==  !=  <  <=  >  >=   and  or  not  &  |",
        "",
    ]
    groups = {"행": "행마다 계산", "전체": "열 전체를 값 하나로", "누적": "열 전체를 열 전체로"}
    for group, title in groups.items():
        lines.append(f"[{title}]")
        for name, kind, example in expression.FUNCTION_HELP:
            if kind == group:
                lines.append(f"  {name}")
                lines.append(f"      예)  {example}")
        lines.append("")

    lines += [
        "자주 쓰는 조합",
        '  구성비        비율([집행액])',
        '  누적 구성비    누적비율([집행액])',
        '  집행률        [집행액] / [예산액]',
        '  전기 대비      증감률([집행액])',
        '  3단계 판정     조건([집행률] > 1, "초과", 조건([집행률] < 0.7, "부진", "정상"))',
    ]
    text.insert("1.0", "\n".join(lines))
    text.configure(state="disabled")


# ── 본 화면 ────────────────────────────────────────────────────────


class _App:
    def __init__(self, initial_file: str | None) -> None:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk

        self.tk, self.ttk = tk, ttk
        self.filedialog, self.messagebox = filedialog, messagebox

        self.table: Table | None = None
        self.result = None
        self.report_path: str | None = None
        self.path: str | None = None
        self.blocks: list[Block] = []
        self.editing_index: int | None = None
        self._syncing = False  # 목록을 다시 그리는 동안 선택 이벤트를 무시하기 위한 잠금

        self.root = tk.Tk()
        self.root.title("예산 분석기 — 오프라인")
        self.root.geometry("960x780")
        self.root.minsize(840, 680)

        self.file_var = tk.StringVar(value="파일을 선택하세요")
        self.sheet_var = tk.StringVar()
        self.header_var = tk.StringVar(value="자동")
        self.status_var = tk.StringVar(value="준비됨")

        self.template_name_var = tk.StringVar(value="새 양식")
        self.template_desc_var = tk.StringVar()
        self.global_filter_var = tk.StringVar()

        self.forecast_current_path: str | None = None
        self.forecast_history_path: str | None = None
        self.forecast_current_var = tk.StringVar(value="올해 집행 현황 파일을 선택하세요")
        self.forecast_history_var = tk.StringVar(value="작년 원인행위상세 파일을 선택하세요")
        self.forecast_base_date_var = tk.StringVar(value=_dt.date.today().isoformat())
        self.forecast_target_date_var = tk.StringVar(value="")
        self.forecast_weight_var = tk.StringVar(value="100")
        self.forecast_result = None
        self.forecast_output_path: str | None = None

        self.block_vars = {
            "이름": tk.StringVar(),
            "유형": tk.StringVar(value="집계"),
            "설명": tk.StringVar(),
            "필터": tk.StringVar(),
            "단위": tk.StringVar(value="월"),
            "정렬": tk.StringVar(),
            "상위": tk.StringVar(value="0"),
            "차트": tk.StringVar(value="자동"),
            "차트값": tk.StringVar(),
            "내림차순": tk.BooleanVar(value=True),
            "기타로묶기": tk.BooleanVar(value=True),
        }

        self._build()
        if initial_file and os.path.exists(initial_file):
            self._load_file(initial_file)

    # ── 화면 구성 ───────────────────────────────────────────────

    def _columns(self) -> list[str]:
        return list(self.table.columns) if self.table else []

    def _build(self) -> None:
        tk, ttk = self.tk, self.ttk
        try:
            ttk.Style().theme_use("clam")
        except tk.TclError:
            pass

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self._build_data_tab()
        self._build_template_tab()
        self._build_result_tab()
        self._build_forecast_tab()

        ttk.Label(outer, textvariable=self.status_var, foreground="#555").pack(fill="x", pady=(6, 0))

    def _build_data_tab(self) -> None:
        ttk = self.ttk
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text=" 1. 데이터 ")

        row = ttk.Frame(tab)
        row.pack(fill="x")
        ttk.Button(row, text="엑셀 파일 열기…", command=self._choose_file, width=16).pack(side="left")
        ttk.Label(row, textvariable=self.file_var, foreground="#444").pack(
            side="left", padx=10, fill="x", expand=True
        )

        row2 = ttk.Frame(tab)
        row2.pack(fill="x", pady=(10, 0))
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

        preview = ttk.LabelFrame(tab, text=" 미리보기 ", padding=8)
        preview.pack(fill="both", expand=True, pady=12)
        self.preview = self.tk.Text(preview, wrap="none", height=18, relief="flat", background="#fbfbfa")
        scroll = ttk.Scrollbar(preview, command=self.preview.yview)
        self.preview.configure(yscrollcommand=scroll.set, state="disabled")
        scroll.pack(side="right", fill="y")
        self.preview.pack(side="left", fill="both", expand=True)

    def _build_template_tab(self) -> None:
        ttk = self.ttk
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text=" 2. 분석 양식 ")

        top = ttk.Frame(tab)
        top.pack(fill="x")
        ttk.Label(top, text="양식 이름", width=9).grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.template_name_var, width=28).grid(row=0, column=1, sticky="w")
        ttk.Label(top, text="설명", width=5).grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(top, textvariable=self.template_desc_var).grid(row=0, column=3, sticky="we")
        ttk.Label(top, text="전체 필터", width=9).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(top, textvariable=self.global_filter_var).grid(
            row=1, column=1, columnspan=3, sticky="we", pady=(6, 0)
        )
        top.columnconfigure(3, weight=1)

        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="자동 생성", command=self._autofill_template).pack(side="left")
        ttk.Button(actions, text="예시 양식…", command=self._choose_preset).pack(side="left", padx=4)
        ttk.Button(actions, text="양식 불러오기…", command=self._load_template).pack(side="left")
        ttk.Button(actions, text="양식 저장…", command=self._save_template).pack(side="left", padx=4)
        ttk.Button(actions, text="양식 검사", command=self._validate_template).pack(side="left")
        ttk.Button(actions, text="함수 도움말", command=lambda: _show_function_help(self.root)).pack(
            side="right"
        )

        self.summary_editor = _ListEditor(
            tab,
            "요약 타일 (보고서 맨 위의 큰 숫자)",
            [
                ("이름", "이름", "text", None),
                ("식", "수식", "formula", None),
                ("서식", "서식", "combo", FORMATS),
                ("설명", "단위/설명", "text", None),
            ],
            lambda: Summary(이름="", 식=""),
            lambda s: f"{s.이름}   =  {s.식}",
            self._columns,
        ).pack(fill="x", pady=(0, 8))

        panes = ttk.Frame(tab)
        panes.pack(fill="both", expand=True)

        left = ttk.LabelFrame(panes, text=" 블록 (보고서 섹션) ", padding=8)
        left.pack(side="left", fill="both", expand=False, padx=(0, 8))
        self.block_list = self.tk.Listbox(left, width=26, height=14, activestyle="none", exportselection=False)
        self.block_list.pack(fill="both", expand=True)
        self.block_list.bind("<<ListboxSelect>>", lambda _event: self._select_block())

        block_buttons = ttk.Frame(left)
        block_buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(block_buttons, text="추가", command=self._add_block, width=6).pack(side="left")
        ttk.Button(block_buttons, text="삭제", command=self._delete_block, width=6).pack(side="left", padx=3)
        ttk.Button(block_buttons, text="▲", command=lambda: self._move_block(-1), width=3).pack(side="right")
        ttk.Button(block_buttons, text="▼", command=lambda: self._move_block(1), width=3).pack(side="right", padx=2)

        self.block_panel = ttk.LabelFrame(panes, text=" 선택한 블록 ", padding=8)
        self.block_panel.pack(side="left", fill="both", expand=True)
        self._build_block_panel(self.block_panel)

    def _build_block_panel(self, parent) -> None:
        ttk = self.ttk
        grid = ttk.Frame(parent)
        grid.pack(fill="x")

        def label(text: str, row: int) -> None:
            ttk.Label(grid, text=text, width=8).grid(row=row, column=0, sticky="w", pady=2)

        label("이름", 0)
        ttk.Entry(grid, textvariable=self.block_vars["이름"]).grid(row=0, column=1, columnspan=3, sticky="we")

        label("유형", 1)
        kind_box = ttk.Combobox(
            grid, textvariable=self.block_vars["유형"], values=BLOCK_KINDS, state="readonly", width=10
        )
        kind_box.grid(row=1, column=1, sticky="w")
        kind_box.bind("<<ComboboxSelected>>", lambda _event: self._sync_block_panel())

        ttk.Label(grid, text="단위").grid(row=1, column=2, sticky="e")
        self.grain_box = ttk.Combobox(
            grid, textvariable=self.block_vars["단위"], values=GRAINS, state="readonly", width=8
        )
        self.grain_box.grid(row=1, column=3, sticky="w")

        label("설명", 2)
        ttk.Entry(grid, textvariable=self.block_vars["설명"]).grid(row=2, column=1, columnspan=3, sticky="we")

        label("필터", 3)
        ttk.Entry(grid, textvariable=self.block_vars["필터"]).grid(row=3, column=1, columnspan=3, sticky="we")

        label("정렬", 4)
        self.sort_box = ttk.Combobox(grid, textvariable=self.block_vars["정렬"], width=18)
        self.sort_box.grid(row=4, column=1, sticky="w")
        ttk.Checkbutton(grid, text="내림차순", variable=self.block_vars["내림차순"]).grid(
            row=4, column=2, columnspan=2, sticky="w"
        )

        label("상위 N", 5)
        ttk.Entry(grid, textvariable=self.block_vars["상위"], width=8).grid(row=5, column=1, sticky="w")
        ttk.Checkbutton(grid, text="나머지는 '기타'로", variable=self.block_vars["기타로묶기"]).grid(
            row=5, column=2, columnspan=2, sticky="w"
        )

        label("차트", 6)
        ttk.Combobox(
            grid, textvariable=self.block_vars["차트"], values=CHART_KINDS, state="readonly", width=8
        ).grid(row=6, column=1, sticky="w")
        ttk.Label(grid, text="그릴 값").grid(row=6, column=2, sticky="e")
        self.chart_value_box = ttk.Combobox(grid, textvariable=self.block_vars["차트값"], width=14)
        self.chart_value_box.grid(row=6, column=3, sticky="w")
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)

        keys = ttk.LabelFrame(parent, text=" 묶는 기준 (여러 개 선택 가능) ", padding=6)
        keys.pack(fill="x", pady=8)
        self.key_list = self.tk.Listbox(keys, selectmode="extended", height=4, exportselection=False)
        self.key_list.pack(fill="x")

        self.measure_editor = _ListEditor(
            parent,
            "측정값 (집계할 숫자)",
            [
                ("컬럼", "컬럼", "column", None),
                ("함수", "함수", "combo", AGGREGATIONS),
                ("이름", "표시 이름", "text", None),
                ("서식", "서식", "combo", FORMATS),
            ],
            lambda: Measure(컬럼=""),
            lambda m: f"{m.함수}({m.컬럼})  →  {m.결과이름}",
            self._columns,
        ).pack(fill="x", pady=(0, 6))

        self.computed_editor = _ListEditor(
            parent,
            "계산 컬럼 (집계 결과 위에서 수식으로)",
            [
                ("이름", "이름", "text", None),
                ("식", "수식", "formula", None),
                ("서식", "서식", "combo", FORMATS),
            ],
            lambda: Computed(이름="", 식=""),
            lambda c: f"{c.이름}  =  {c.식}",
            self._block_result_columns,
        ).pack(fill="x", pady=(0, 6))

        self.rule_editor = _ListEditor(
            parent,
            "경고 규칙 (조건에 걸리면 문구를 띄움)",
            [
                ("조건", "조건", "formula", None),
                ("메시지", "메시지", "text", None),
            ],
            lambda: Rule(조건="", 메시지=""),
            lambda r: f"{r.조건}  →  {r.메시지}",
            self._block_result_columns,
        ).pack(fill="x")

    def _build_result_tab(self) -> None:
        ttk = self.ttk
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text=" 3. 실행 ")

        buttons = ttk.Frame(tab)
        buttons.pack(fill="x")
        self.run_button = ttk.Button(buttons, text="분석 실행", command=self._run, width=16)
        self.run_button.pack(side="left")
        ttk.Button(buttons, text="보고서 열기", command=self._open_report).pack(side="left", padx=5)
        ttk.Button(buttons, text="엑셀로 저장…", command=self._save_xlsx).pack(side="left", padx=5)
        ttk.Button(buttons, text="CSV로 저장…", command=self._save_csv).pack(side="left")

        frame = ttk.LabelFrame(tab, text=" 결과 요약 ", padding=8)
        frame.pack(fill="both", expand=True, pady=10)
        self.output = self.tk.Text(frame, wrap="word", relief="flat", background="#fbfbfa")
        scroll = ttk.Scrollbar(frame, command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set, state="disabled")
        scroll.pack(side="right", fill="y")
        self.output.pack(side="left", fill="both", expand=True)

    def _build_forecast_tab(self) -> None:
        ttk = self.ttk
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text=" 4. 집행 전망 ")

        intro = ttk.Label(
            tab,
            foreground="#555",
            wraplength=880,
            justify="left",
            text=(
                "작년 같은 기간에 얼마나 더 지출됐는지를 목/세목 단위로 구해, 올해 목표일까지의 "
                "집행 전망을 추정합니다. 아래 두 파일을 고르고 [집행 전망 계산]을 누르면 결과 엑셀이 "
                "만들어집니다 — 그 엑셀의 '설정' 시트에서 가중치(%)를 바꾸면 전망이 다시 계산됩니다."
            ),
        )
        intro.pack(fill="x", pady=(0, 12))

        files = ttk.Frame(tab)
        files.pack(fill="x")
        ttk.Button(files, text="올해 집행 현황 파일…", command=self._choose_forecast_current, width=20).grid(
            row=0, column=0, sticky="w", pady=3
        )
        ttk.Label(files, textvariable=self.forecast_current_var, foreground="#444").grid(
            row=0, column=1, sticky="w", padx=10
        )
        ttk.Button(files, text="작년 원인행위상세 파일…", command=self._choose_forecast_history, width=20).grid(
            row=1, column=0, sticky="w", pady=3
        )
        ttk.Label(files, textvariable=self.forecast_history_var, foreground="#444").grid(
            row=1, column=1, sticky="w", padx=10
        )

        settings = ttk.Frame(tab)
        settings.pack(fill="x", pady=(10, 0))
        ttk.Label(settings, text="기준일").pack(side="left")
        ttk.Entry(settings, textvariable=self.forecast_base_date_var, width=12).pack(side="left", padx=(4, 16))
        ttk.Label(settings, text="목표일 (비우면 분기 말)").pack(side="left")
        ttk.Entry(settings, textvariable=self.forecast_target_date_var, width=12).pack(side="left", padx=(4, 16))
        ttk.Label(settings, text="가중치(%)").pack(side="left")
        ttk.Entry(settings, textvariable=self.forecast_weight_var, width=6).pack(side="left", padx=4)

        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        self.forecast_run_button = ttk.Button(
            actions, text="집행 전망 계산…", command=self._run_forecast, width=16
        )
        self.forecast_run_button.pack(side="left")
        ttk.Button(actions, text="결과 엑셀 열기", command=self._open_forecast_output).pack(side="left", padx=5)

        frame = ttk.LabelFrame(tab, text=" 결과 ", padding=8)
        frame.pack(fill="both", expand=True)
        self.forecast_output = self.tk.Text(frame, wrap="word", relief="flat", background="#fbfbfa")
        scroll = ttk.Scrollbar(frame, command=self.forecast_output.yview)
        self.forecast_output.configure(yscrollcommand=scroll.set, state="disabled")
        scroll.pack(side="right", fill="y")
        self.forecast_output.pack(side="left", fill="both", expand=True)

    # ── 데이터 ──────────────────────────────────────────────────

    def _write(self, widget, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

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
        self.sheet_var.set(names[0] if len(names) == 1 else "")
        self._reload()

    def _reload(self) -> None:
        if not self.path:
            return
        sheet = self.sheet_var.get() or None
        if sheet == "(csv)":
            sheet = None
        header = None if self.header_var.get() == "자동" else int(self.header_var.get()) - 1

        try:
            self.table = read_table(self.path, sheet=sheet, header_row=header)
        except (SpreadsheetError, OSError, ValueError) as error:
            self.messagebox.showerror("읽기 실패", str(error))
            return

        if not self.sheet_var.get():
            self.sheet_var.set(self.table.name)

        columns = self._columns()
        self.key_list.delete(0, "end")
        for column in columns:
            self.key_list.insert("end", column)
        self.sort_box["values"] = columns
        self.chart_value_box["values"] = columns

        lines = [
            f"파일: {self.path}",
            f"시트: {self.table.name}   행 수: {len(self.table):,}",
            f"컬럼 ({len(columns)}개): {', '.join(columns)}",
            "",
            "자동 인식: " + guess_mapping(self.table).describe(),
            "",
            "─ 상위 8행 " + "─" * 40,
            " | ".join(str(c)[:14] for c in columns),
        ]
        for row in self.table.head(8).rows:
            lines.append(" | ".join("" if c is None else str(c)[:14] for c in row))
        lines += ["", "[2. 분석 양식] 탭에서 분석 내용을 정의하세요.",
                  "처음이라면 '자동 생성' 을 누른 뒤 필요한 부분만 고치는 편이 빠릅니다."]
        self._write(self.preview, "\n".join(lines))

        if not self.blocks:
            self._autofill_template()
        self.status_var.set(f"{len(self.table):,}행을 읽었습니다.")

    # ── 양식 편집 ───────────────────────────────────────────────

    def _block_result_columns(self) -> list[str]:
        """계산·규칙 수식이 쓸 수 있는 컬럼 (집계 이후 기준)."""
        block = self._collect_block(validate=False)
        if block is None:
            return self._columns()
        names = list(block.기준) + [m.결과이름 for m in block.측정값] + ["건수"]
        names += [c.이름 for c in self.computed_editor.items if c.이름]
        return names

    def _autofill_template(self) -> None:
        if self.table is None:
            self.messagebox.showinfo("파일 필요", "먼저 엑셀 파일을 선택하세요.")
            return
        self._apply_template(template_from_mapping(guess_mapping(self.table)))
        self.status_var.set("자동 생성된 양식을 불러왔습니다. 필요한 부분을 고쳐 쓰세요.")

    def _choose_preset(self) -> None:
        if self.table is None:
            self.messagebox.showinfo("파일 필요", "먼저 엑셀 파일을 선택하세요.")
            return
        presets = builtin_templates(guess_mapping(self.table))
        self._show_preset_chooser(presets)

    def _show_preset_chooser(self, presets) -> None:
        tk, ttk = self.tk, self.ttk
        window = tk.Toplevel(self.root)
        window.title("예시 양식 고르기")
        window.transient(self.root)
        window.grab_set()

        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)
        listbox = tk.Listbox(frame, width=54, height=8, activestyle="none")
        listbox.pack(fill="both", expand=True)
        for preset in presets:
            listbox.insert("end", f"{preset.이름} — {preset.설명}")
        listbox.selection_set(0)

        def accept() -> None:
            selection = listbox.curselection()
            if selection:
                self._apply_template(presets[selection[0]])
                self.status_var.set(f"'{presets[selection[0]].이름}' 양식을 불러왔습니다.")
            window.destroy()

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="취소", command=window.destroy).pack(side="right", padx=3)
        ttk.Button(buttons, text="사용", command=accept).pack(side="right")

    def _apply_template(self, template: Template) -> None:
        self.template_name_var.set(template.이름)
        self.template_desc_var.set(template.설명)
        self.global_filter_var.set(template.전체필터)
        self.summary_editor.set_items(template.요약)
        self.blocks = list(template.블록)
        self.editing_index = None
        self._refresh_block_list(select=0 if self.blocks else None)
        if self.blocks:
            self._select_block()

    def _refresh_block_list(self, select: int | None = None) -> None:
        """목록을 다시 그린다. 다시 그리면 선택이 풀리므로 복원까지 책임진다."""
        if select is None:
            selection = self.block_list.curselection()
            select = selection[0] if selection else None

        self._syncing = True
        try:
            self.block_list.delete(0, "end")
            for block in self.blocks:
                self.block_list.insert("end", f"{block.이름}  ({block.유형})")
            if select is not None and 0 <= select < len(self.blocks):
                self.block_list.selection_set(select)
        finally:
            self._syncing = False

    def _sync_block_panel(self) -> None:
        """유형에 따라 의미 없는 입력칸을 비활성화한다."""
        kind = self.block_vars["유형"].get()
        self.grain_box.configure(state="readonly" if kind == "추이" else "disabled")

    def _select_block(self) -> None:
        # 목록을 다시 그리는 동안에도 선택 이벤트가 날아오므로 재진입을 막는다.
        if self._syncing:
            return
        selection = self.block_list.curselection()
        if not selection:
            return

        index = selection[0]
        if self.editing_index is not None and self.editing_index != index:
            self._store_block(self.editing_index)

        self.editing_index = index
        if not 0 <= index < len(self.blocks):
            return
        block = self.blocks[index]

        for name, variable in self.block_vars.items():
            variable.set(getattr(block, name))
        self.block_vars["상위"].set(str(block.상위))

        self.key_list.selection_clear(0, "end")
        for position, column in enumerate(self._columns()):
            if column in block.기준:
                self.key_list.selection_set(position)
        # 파일에 없는 기준(파생컬럼 등)은 목록에 추가해 보여준다.
        for column in block.기준:
            if column not in self._columns():
                self.key_list.insert("end", column)
                self.key_list.selection_set("end")

        self.measure_editor.set_items(block.측정값)
        self.computed_editor.set_items(block.계산)
        self.rule_editor.set_items(block.규칙)
        self._sync_block_panel()

    def _collect_block(self, validate: bool = True) -> Block | None:
        if self.editing_index is None:
            return None
        keys = [self.key_list.get(i) for i in self.key_list.curselection()]
        try:
            top = int(self.block_vars["상위"].get() or 0)
        except ValueError:
            top = 0
            if validate:
                self.messagebox.showwarning("입력 확인", "'상위 N' 은 숫자여야 합니다. 0으로 둡니다.")

        return Block(
            이름=self.block_vars["이름"].get().strip() or "이름 없는 블록",
            유형=self.block_vars["유형"].get(),
            설명=self.block_vars["설명"].get().strip(),
            필터=self.block_vars["필터"].get().strip(),
            기준=keys,
            단위=self.block_vars["단위"].get(),
            측정값=list(self.measure_editor.items),
            계산=list(self.computed_editor.items),
            정렬=self.block_vars["정렬"].get().strip(),
            내림차순=bool(self.block_vars["내림차순"].get()),
            상위=top,
            기타로묶기=bool(self.block_vars["기타로묶기"].get()),
            차트=self.block_vars["차트"].get(),
            차트값=self.block_vars["차트값"].get().strip(),
            규칙=list(self.rule_editor.items),
        )

    def _store_block(self, index: int | None = None) -> None:
        index = self.editing_index if index is None else index
        if index is None or not 0 <= index < len(self.blocks):
            return
        block = self._collect_block()
        if block is None:
            return
        changed = (block.이름, block.유형) != (self.blocks[index].이름, self.blocks[index].유형)
        self.blocks[index] = block
        if changed:
            self._refresh_block_list(select=self.editing_index)

    def _add_block(self) -> None:
        self._store_block()
        self.blocks.append(Block(이름=f"새 블록 {len(self.blocks) + 1}"))
        self.editing_index = None
        self._refresh_block_list(select=len(self.blocks) - 1)
        self._select_block()

    def _delete_block(self) -> None:
        selection = self.block_list.curselection()
        if not selection:
            return
        del self.blocks[selection[0]]
        self.editing_index = None
        self._refresh_block_list(select=0 if self.blocks else None)
        if self.blocks:
            self._select_block()

    def _move_block(self, delta: int) -> None:
        selection = self.block_list.curselection()
        if not selection:
            return
        self._store_block()
        index = selection[0]
        target = index + delta
        if not 0 <= target < len(self.blocks):
            return
        self.blocks[index], self.blocks[target] = self.blocks[target], self.blocks[index]
        self.editing_index = target
        self._refresh_block_list(select=target)

    def _current_template(self) -> Template:
        self._store_block()
        return Template(
            이름=self.template_name_var.get().strip() or "새 양식",
            설명=self.template_desc_var.get().strip(),
            전체필터=self.global_filter_var.get().strip(),
            요약=list(self.summary_editor.items),
            블록=list(self.blocks),
        )

    def _validate_template(self) -> None:
        template = self._current_template()
        problems = template.validate(self._columns() if self.table else None)
        if problems:
            self.messagebox.showwarning(
                "양식 검사", f"{len(problems)}건의 문제를 찾았습니다:\n\n" + "\n".join(f"· {p}" for p in problems)
            )
        else:
            self.messagebox.showinfo("양식 검사", "문제가 없습니다. 바로 실행할 수 있습니다.")

    def _save_template(self) -> None:
        path = self.filedialog.asksaveasfilename(
            title="분석 양식 저장", defaultextension=".json", filetypes=_JSON_TYPES
        )
        if not path:
            return
        save_template(path, self._current_template())
        self.status_var.set(f"양식 저장 완료: {path}")

    def _load_template(self) -> None:
        path = self.filedialog.askopenfilename(title="분석 양식 불러오기", filetypes=_JSON_TYPES)
        if not path:
            return
        try:
            template = load_template(path)
        except (TemplateError, OSError) as error:
            self.messagebox.showerror("불러오기 실패", str(error))
            return
        self._apply_template(template)
        self.status_var.set(f"양식 불러옴: {path}")

    # ── 실행 ────────────────────────────────────────────────────

    def _run(self) -> None:
        if self.table is None:
            self.messagebox.showinfo("파일 필요", "먼저 [1. 데이터] 탭에서 엑셀 파일을 선택하세요.")
            return

        template = self._current_template()
        problems = template.validate(self._columns())
        if problems:
            proceed = self.messagebox.askyesno(
                "양식 확인",
                f"{len(problems)}건의 문제가 있습니다:\n\n"
                + "\n".join(f"· {p}" for p in problems[:8])
                + "\n\n문제가 있는 부분은 건너뛰고 진행할까요?",
            )
            if not proceed:
                return

        self.run_button.state(["disabled"])
        self.status_var.set("분석 중…")

        def work() -> None:
            try:
                result = run(self.table, template, source=self.path or "")
                report_path = os.path.join(
                    os.path.dirname(os.path.abspath(self.path or ".")),
                    os.path.splitext(os.path.basename(self.path or "분석"))[0] + "_분석.html",
                )
                write_report(
                    report_path, result, title=f"{template.이름} — {os.path.basename(self.path or '')}"
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
        self.notebook.select(2)
        self._write(self.output, "분석 중 오류가 발생했습니다.\n\n" + message)

    def _succeeded(self, result, report_path: str) -> None:
        self.result = result
        self.report_path = report_path
        self.run_button.state(["!disabled"])
        self.status_var.set(f"완료 — 보고서: {report_path}")
        self.notebook.select(2)
        self._write(self.output, self._summary(result, report_path))
        self._open_report()

    def _summary(self, result, report_path: str) -> str:
        lines = [f"{result.template.이름} — {result.sheet} ({result.row_count:,}행)", ""]
        for tile in result.tiles:
            number = to_number(tile.값)
            if number is None:
                text = "-" if tile.값 is None else str(tile.값)
            elif tile.서식 == "비율":
                text = format_percent(number)
            else:
                text = format_number(number)
            lines.append(f"  {tile.이름}: {text}")

        for block in result.blocks:
            if not len(block.표):
                continue
            lines += ["", f"  [{block.이름}]"]
            key_count = max(1, len(block.기준이름))
            value_column = block.차트값 or (block.측정값이름[0] if block.측정값이름 else "")
            for row in block.표.rows[:8]:
                label = " · ".join(str(c) for c in row[:key_count] if str(c).strip())
                if value_column in block.표.columns:
                    number = to_number(row[block.표.index_of(value_column)])
                    shown = (
                        format_percent(number)
                        if block.서식.get(value_column) == "비율"
                        else format_number(number)
                    )
                    lines.append(f"    {label[:30]:<30} {shown:>16}")
                else:
                    lines.append(f"    {label}")
            for warning in block.경고:
                lines.append(f"    ! {warning}")

        if result.warnings:
            lines += ["", "  [확인 필요]"] + [f"    · {w}" for w in result.warnings]
        lines += ["", f"보고서를 브라우저로 열었습니다:\n  {report_path}"]
        return "\n".join(lines)

    def _open_report(self) -> None:
        if not self.report_path or not os.path.exists(self.report_path):
            self.messagebox.showinfo("보고서 없음", "먼저 [분석 실행] 을 눌러 보고서를 만드세요.")
            return
        webbrowser.open(f"file:///{os.path.abspath(self.report_path).replace(os.sep, '/')}")

    def _save_xlsx(self) -> None:
        if self.result is None or not self.result.tables():
            self.messagebox.showinfo("결과 없음", "먼저 분석을 실행하세요.")
            return
        path = self.filedialog.asksaveasfilename(
            title="분석 결과 저장", defaultextension=".xlsx", filetypes=[("엑셀 파일", "*.xlsx")]
        )
        if path:
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

    # ── 집행 전망 ───────────────────────────────────────────────

    def _choose_forecast_current(self) -> None:
        path = self.filedialog.askopenfilename(title="올해 집행 현황 파일 선택", filetypes=_FILE_TYPES)
        if path:
            self.forecast_current_path = path
            self.forecast_current_var.set(os.path.basename(path))

    def _choose_forecast_history(self) -> None:
        path = self.filedialog.askopenfilename(title="작년 원인행위상세 파일 선택", filetypes=_FILE_TYPES)
        if path:
            self.forecast_history_path = path
            self.forecast_history_var.set(os.path.basename(path))

    def _run_forecast(self) -> None:
        if not self.forecast_current_path or not self.forecast_history_path:
            self.messagebox.showinfo("파일 필요", "올해 집행 현황 파일과 작년 원인행위상세 파일을 모두 선택하세요.")
            return

        base_date = to_date(self.forecast_base_date_var.get().strip())
        if base_date is None:
            self.messagebox.showwarning("입력 확인", "기준일을 이해하지 못했습니다 (예: 2026-08-10).")
            return

        target_text = self.forecast_target_date_var.get().strip()
        target_date = to_date(target_text) if target_text else end_of_quarter(base_date)
        if target_date is None:
            self.messagebox.showwarning("입력 확인", "목표일을 이해하지 못했습니다 (예: 2026-09-30).")
            return

        try:
            weight = float(self.forecast_weight_var.get().strip() or "100")
        except ValueError:
            self.messagebox.showwarning("입력 확인", "가중치(%)는 숫자여야 합니다.")
            return

        out_path = self.filedialog.asksaveasfilename(
            title="집행 전망 엑셀 저장",
            defaultextension=".xlsx",
            filetypes=[("엑셀 파일", "*.xlsx")],
            initialfile=os.path.splitext(os.path.basename(self.forecast_current_path))[0] + "_집행전망.xlsx",
        )
        if not out_path:
            return

        self.forecast_run_button.state(["disabled"])
        self.status_var.set("집행 전망 계산 중…")

        def work() -> None:
            try:
                current = read_table(self.forecast_current_path)
                history = read_table(self.forecast_history_path)
                settings = ForecastSettings(base_date=base_date, target_date=target_date, weight_percent=weight)
                result = build_forecast(history, current, settings)
                write_forecast(out_path, result)
            except (SpreadsheetError, ForecastError) as error:
                self.root.after(0, lambda: self._forecast_failed(str(error)))
                return
            except Exception:  # 사용자에게 스택을 그대로 보여주는 편이 낫다.
                message = traceback.format_exc()
                self.root.after(0, lambda: self._forecast_failed(message))
                return
            self.root.after(0, lambda: self._forecast_succeeded(result, out_path))

        threading.Thread(target=work, daemon=True).start()

    def _forecast_failed(self, message: str) -> None:
        self.forecast_run_button.state(["!disabled"])
        self.status_var.set("집행 전망 계산 실패")
        self._write(self.forecast_output, "계산 중 오류가 발생했습니다.\n\n" + message)

    def _forecast_succeeded(self, result, out_path: str) -> None:
        self.forecast_result = result
        self.forecast_output_path = out_path
        self.forecast_run_button.state(["!disabled"])
        self.status_var.set(f"완료 — 집행 전망 엑셀: {out_path}")

        settings = result.settings
        lines = [
            f"기준일 {settings.base_date} → 목표일 {settings.target_date}",
            f"(작년 {settings.history_base_date + _dt.timedelta(days=1)} ~ {settings.history_target_date} 패턴 사용, 가중치 {settings.weight_percent:.0f}%)",
            "",
            f"목/세목 매칭: {result.matched_rows}행 매칭, {result.unmatched_rows}행은 전체 평균으로 대체",
        ]
        for warning in result.warnings:
            lines.append(f"  · {warning}")
        lines += ["", f"저장 위치: {out_path}", "", "엑셀을 열어 '설정' 시트의 가중치(%) 값을 바꾸면 전망이 다시 계산됩니다."]
        self._write(self.forecast_output, "\n".join(lines))
        self._open_forecast_output()

    def _open_forecast_output(self) -> None:
        if not self.forecast_output_path or not os.path.exists(self.forecast_output_path):
            self.messagebox.showinfo("결과 없음", "먼저 [집행 전망 계산]을 실행하세요.")
            return
        try:
            os.startfile(self.forecast_output_path)  # type: ignore[attr-defined]
        except AttributeError:
            webbrowser.open(f"file:///{os.path.abspath(self.forecast_output_path).replace(os.sep, '/')}")
        except OSError as error:
            self.messagebox.showwarning("열기 실패", f"{error}\n\n파일 위치: {self.forecast_output_path}")

    def run(self) -> None:
        self.root.mainloop()
