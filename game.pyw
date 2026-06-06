"""
game.py  ──  综网终端 · 地狱之下  ·  视觉小说引擎
────────────────────────────────────────────────
世界观框架
  源海 → 至高存在(林易东) → 以太网络(综网) → 科洛弗事件(谢帕特)
       → 地狱之下平台 → 各游戏世界(11卷)

  因——林易东（至高无上·古神·技能：创造/毁灭）
  果——地狱之下11卷

架构说明
  - game.py     : 全部游戏逻辑 + Tkinter GUI（纯标准库，无第三方依赖）
  - data/*.json : 游戏文本数据（不含任何逻辑）
  - data/lore.json : 世界观数据，供 UI 引用

文件命名
  - vol_01~12.json    地狱之下各卷
  - w1_v01~17.json    单机作家各卷
  - w2_v01~21.json    林东的无限崩坏之旅各卷
  - w3_v01~27.json    玩家之上各卷

UI 叙事框架
  ✦ 主菜单 → 综网终端启动/登录界面
  ✦ 游戏库 → 地狱之下平台的游戏库浏览（按书→按卷展开）
  ✦ 阅读器 → 档案终端（含地狱点数、信号强度、因果链等世界观元素）
  ✦ 存档   → 档案存取

功能
  ✦ 开机动画：逐行显示终端启动文本
  ✦ 游戏库：地狱之下（11卷）& 关联档案（3本书×各卷）分区展示
  ✦ 阅读界面：滚动文字、章节导航、鼠标点击"继续"推进
  ✦ 地狱点数：每翻一页+1，完成一章+5，符合平台世界观
  ✦ 存档/读档：自动保存到 save.json
  ✦ 章节目录：侧边面板可直达任意章节
  ✦ 字体大小调节（A- / A+）
  ✦ 键盘快捷：←→ 翻页，空格 继续，Ctrl+S 存档，Escape 回主菜单
"""

from __future__ import annotations

import json
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════
#  路径常量
# ═══════════════════════════════════════════════════════════════════════

GAME_DIR  = Path(__file__).parent.resolve()
DATA_DIR  = GAME_DIR / "data"
META_FILE = DATA_DIR / "meta.json"
LORE_FILE = DATA_DIR / "lore.json"
SAVE_FILE = GAME_DIR / "save.json"


# ═══════════════════════════════════════════════════════════════════════
#  调色板 —— 综网终端深色主题
# ═══════════════════════════════════════════════════════════════════════

PAL = {
    # 基础
    "bg":          "#0a0a0f",
    "panel":       "#0f0f18",
    "text_area":   "#080810",
    "text":        "#c8c0b0",
    "border":      "#1a1a2a",

    # 强调色 —— 终端风格
    "terminal":    "#00cc66",       # 终端绿
    "terminal_dim":"#007733",
    "accent":      "#8b2222",       # 地狱红
    "accent_glow": "#cc3333",

    # 文字色
    "title":       "#e8a040",       # 琥珀金
    "heading":     "#e0c080",
    "dim":         "#505060",
    "bright":      "#f0d080",

    # 按钮
    "btn_bg":      "#12121e",
    "btn_hover":   "#1e1e30",
    "btn_press":   "#2a1020",
    "btn_text":    "#b0a898",
    "btn_accent":  "#e8a040",

    # 进度条
    "progress":    "#1a1a10",
    "progress_fg":  "#e8a040",

    # 默认分区配色（当 meta.json 中未定义时使用）
    "default_section_accent": "#1a2a3a",
    "default_section_title":  "#a0c0e0",
    "default_section_badge":  "#4a5a6a",
}

FONT_DEFAULT_SIZE = 16


# ═══════════════════════════════════════════════════════════════════════
#  世界观数据
# ═══════════════════════════════════════════════════════════════════════

class LoreData:
    """读取 lore.json，提供世界观术语供 UI 使用。"""

    def __init__(self):
        if LORE_FILE.exists():
            with open(LORE_FILE, encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {"ui_text": {}}

    @property
    def boot_lines(self) -> list[str]:
        return self._data.get("ui_text", {}).get("boot_lines", [
            "正在连接以太网络...",
            "综网信号：已锁定",
            "身份验证：通过",
        ])

    @property
    def welcome(self) -> str:
        return self._data.get("ui_text", {}).get("welcome",
            "您已接入以太网络。当前平台：地狱之下。")

    @property
    def boot_title_1(self) -> str:
        return self._data.get("ui_text", {}).get("boot_title_1", "以 太 网 络")

    @property
    def boot_title_2(self) -> str:
        return self._data.get("ui_text", {}).get("boot_title_2",
            "A E T H E R   N E T W O R K")

    @property
    def boot_subtitle(self) -> str:
        return self._data.get("ui_text", {}).get("boot_subtitle",
            "地 狱 之 下 平 台  ·  终 端 接 入")

    @property
    def hell_points_name(self) -> str:
        return self._data.get("ui_text", {}).get("hell_points_name", "地狱点数")

    @property
    def hell_points_unit(self) -> str:
        return self._data.get("ui_text", {}).get("hell_points_unit", "HP")

    @property
    def signal_name(self) -> str:
        return self._data.get("ui_text", {}).get("signal_name", "综网信号")

    @property
    def archive_name(self) -> str:
        return self._data.get("ui_text", {}).get("archive_name", "档案")

    @property
    def game_lib_name(self) -> str:
        return self._data.get("ui_text", {}).get("game_lib_name", "游戏库")

    @property
    def platform_name(self) -> str:
        return self._data.get("platform", {}).get("name", "地狱之下")

    @property
    def platform_slogan(self) -> str:
        return self._data.get("platform", {}).get("slogan", "酒香不怕巷子深")

    @property
    def causality(self) -> str:
        return self._data.get("universe", {}).get("causality", "")

    @property
    def supreme_name(self) -> str:
        return self._data.get("supreme_being", {}).get("name", "林易东")

    @property
    def supreme_evaluation(self) -> str:
        return self._data.get("supreme_being", {}).get("status_panel", {}).get(
            "evaluation", "至高无上")


# ═══════════════════════════════════════════════════════════════════════
#  数据层
# ═══════════════════════════════════════════════════════════════════════

class GameData:
    """负责读取 JSON 文件，不含任何 UI 逻辑。
    使用 file_key（如 'vol_01', 'w1_v02'）作为统一索引。
    系列配置从 meta.json 的 series_config 动态读取，加新系列无需改代码。
    """

    def __init__(self):
        with open(META_FILE, encoding="utf-8") as f:
            self.meta: dict = json.load(f)
        self._cache: dict[str, dict] = {}

    @property
    def volumes(self) -> list[dict]:
        """地狱之下 11 卷元数据"""
        return self.meta["volumes"]

    @property
    def works(self) -> list[dict]:
        """作品集 3 本书元数据（含各卷列表）"""
        return self.meta.get("works", [])

    @property
    def series_config(self) -> dict:
        """从 meta.json 读取的系列显示配置（label/icon/colors 等）"""
        return self.meta.get("series_config", {})

    def series_for_prefix(self, prefix: str) -> dict:
        """根据 prefix（如 'hell', 'w1', 'w2', 'w3'）获取系列配置。
        未找到时返回默认配色。
        """
        cfg = self.series_config.get(prefix)
        if cfg:
            return cfg
        return {
            "label": prefix,
            "icon": "📄",
            "relation": "",
            "desc": "",
            "colors": {
                "accent": PAL["default_section_accent"],
                "title":  PAL["default_section_title"],
                "badge":  PAL["default_section_badge"],
                "bg":     PAL["panel"],
                "card_bg": PAL["panel"],
            }
        }

    def series_label_for_file_key(self, file_key: str) -> str:
        """根据 file_key 获取系列标签（如 '地狱之下', '单机作家'）"""
        if file_key.startswith("vol_"):
            return self.series_for_prefix("hell")["label"]
        prefix = file_key.split("_")[0]
        return self.series_for_prefix(prefix)["label"]

    def get_book(self, file_key: str) -> dict:
        """按 file_key 读取 JSON（如 'vol_01', 'w1_v02', 'w2_v05'）"""
        fname = f"{file_key}.json"
        if fname not in self._cache:
            fpath = DATA_DIR / fname
            if not fpath.exists():
                raise FileNotFoundError(f"数据文件不存在: {fname}")
            with open(fpath, encoding="utf-8") as f:
                self._cache[fname] = json.load(f)
        return self._cache[fname]

    def chapter_count(self, file_key: str) -> int:
        return len(self.get_book(file_key)["chapters"])

    def get_chapter(self, file_key: str, ch_idx: int) -> dict:
        return self.get_book(file_key)["chapters"][ch_idx]

    def page_count(self, file_key: str, ch_idx: int) -> int:
        return len(self.get_chapter(file_key, ch_idx)["pages"])

    def get_page(self, file_key: str, ch_idx: int, page_idx: int) -> str:
        page = self.get_chapter(file_key, ch_idx)["pages"][page_idx]
        if isinstance(page, dict):
            return page.get("text", "")
        return page

    def total_pages(self, file_key: str) -> int:
        tc = self.chapter_count(file_key)
        return sum(self.page_count(file_key, i) for i in range(tc))

    @property
    def hell_volume_count(self) -> int:
        return len(self.volumes)

    @property
    def works_volume_count(self) -> int:
        return sum(len(w["volumes"]) for w in self.works)

    @property
    def total_json_count(self) -> int:
        return self.hell_volume_count + self.works_volume_count


# ═══════════════════════════════════════════════════════════════════════
#  游戏状态
# ═══════════════════════════════════════════════════════════════════════

class GameState:
    def __init__(self, data_ref: Optional["GameData"] = None):
        self.file_key:   str = "vol_01"   # 当前档案的文件键
        self.ch_idx:     int = 0
        self.page_idx:   int = 0
        self.hell_points: int = 0         # 地狱点数
        self._data_ref = data_ref         # GameData 引用，用于动态读取系列配置

    def to_dict(self) -> dict:
        return {
            "file_key":    self.file_key,
            "ch":          self.ch_idx,
            "page":        self.page_idx,
            "hell_points": self.hell_points,
        }

    def from_dict(self, d: dict):
        self.file_key    = d.get("file_key", d.get("vol_key", "vol_01"))
        self.ch_idx      = d.get("ch",           0)
        self.page_idx    = d.get("page",         0)
        self.hell_points = d.get("hell_points",  0)

    @property
    def is_hell_below(self) -> bool:
        return self.file_key.startswith("vol_")

    @property
    def series_label(self) -> str:
        if self.is_hell_below:
            return "地狱之下"
        prefix = self.file_key.split("_")[0]
        # 动态从 GameData 的 series_config 获取标签
        return self._data_ref.series_label_for_file_key(self.file_key)


class SaveManager:
    def save(self, state: GameState):
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self) -> Optional[dict]:
        if not SAVE_FILE.exists():
            return None
        try:
            with open(SAVE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def has_save(self) -> bool:
        return SAVE_FILE.exists()


# ═══════════════════════════════════════════════════════════════════════
#  可复用 UI 组件
# ═══════════════════════════════════════════════════════════════════════

class HoverButton(tk.Label):
    """带悬停效果的纯文字按钮。"""

    def __init__(self, parent, text, command=None, accent=False, big=False,
                 color_terminal=False, **kw):
        fs = 14 if big else 12
        if color_terminal:
            fg = PAL["terminal"]
        elif accent:
            fg = PAL["btn_accent"]
        else:
            fg = PAL["btn_text"]
        super().__init__(
            parent,
            text=text,
            bg=PAL["btn_bg"],
            fg=fg,
            font=("Microsoft YaHei UI", fs),
            cursor="hand2",
            padx=18,
            pady=8,
            relief="flat",
            **kw
        )
        self._cmd = command
        self.bind("<Enter>",           self._on_enter)
        self.bind("<Leave>",           self._on_leave)
        self.bind("<Button-1>",        self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, _):  self.config(bg=PAL["btn_hover"])
    def _on_leave(self, _):  self.config(bg=PAL["btn_bg"])
    def _on_press(self, _):  self.config(bg=PAL["btn_press"])

    def _on_release(self, _):
        self.config(bg=PAL["btn_hover"])
        if self._cmd:
            self._cmd()


class ProgressBar(tk.Canvas):
    def __init__(self, parent, width=300, height=4, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=PAL["progress"], highlightthickness=0, **kw)
        self._track = self.create_rectangle(0, 0, 0, height,
                                            fill=PAL["progress_fg"], outline="")
        self._bar_w = width
        self._bar_h = height

    def set(self, ratio: float):
        w = max(0, min(self._bar_w, int(self._bar_w * ratio)))
        self.coords(self._track, 0, 0, w, self._bar_h)


class HellPointsDisplay(tk.Frame):
    """地狱点数显示组件。"""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=PAL["panel"], **kw)

        tk.Label(
            self,
            text="🔥",
            font=("Segoe UI Emoji", 12),
            bg=PAL["panel"],
            fg=PAL["accent_glow"],
        ).pack(side="left", padx=(4, 2))

        self._label = tk.Label(
            self,
            text="0 HP",
            font=("Consolas", 11, "bold"),
            fg=PAL["accent_glow"],
            bg=PAL["panel"],
        )
        self._label.pack(side="left", padx=(0, 6))

    def update_points(self, points: int):
        self._label.config(text=f"{points} HP")


class SignalIndicator(tk.Label):
    """综网信号强度指示器。"""

    def __init__(self, parent, **kw):
        super().__init__(
            parent,
            text="● 在线",
            font=("Consolas", 10),
            fg=PAL["terminal"],
            bg=PAL["panel"],
            **kw
        )

    def set_online(self):
        self.config(text="● 在线", fg=PAL["terminal"])

    def set_offline(self):
        self.config(text="● 离线", fg=PAL["dim"])


def _set_bg(widget, color):
    try:
        widget.config(bg=color)
    except tk.TclError:
        pass
    for c in widget.winfo_children():
        _set_bg(c, color)


# ═══════════════════════════════════════════════════════════════════════
#  主菜单界面 —— 综网终端启动
# ═══════════════════════════════════════════════════════════════════════

class MainMenu(tk.Frame):
    def __init__(self, master: "App"):
        super().__init__(master, bg=PAL["bg"])
        self.app = master
        self._boot_phase = 0
        self._build()

    def _build(self):
        # 顶部红线
        tk.Frame(self, bg=PAL["accent"], height=3).pack(fill="x")

        # 标题区
        title_frame = tk.Frame(self, bg=PAL["bg"])
        title_frame.pack(pady=(50, 6))

        tk.Label(
            title_frame,
            text=self.app.lore.boot_title_1,
            font=("Microsoft YaHei UI", 40, "bold"),
            fg=PAL["heading"],
            bg=PAL["bg"]
        ).pack()

        tk.Label(
            title_frame,
            text=self.app.lore.boot_title_2,
            font=("Consolas", 13),
            fg=PAL["terminal_dim"],
            bg=PAL["bg"]
        ).pack(pady=(4, 8))

        # 副标题 —— 地狱之下平台
        tk.Label(
            title_frame,
            text=self.app.lore.boot_subtitle,
            font=("Microsoft YaHei UI", 16),
            fg=PAL["accent_glow"],
            bg=PAL["bg"]
        ).pack(pady=(2, 0))

        # 因果铭言
        causality = self.app.lore.causality
        if causality:
            tk.Label(
                title_frame,
                text=causality,
                font=("Microsoft YaHei UI", 10, "italic"),
                fg=PAL["dim"],
                bg=PAL["bg"]
            ).pack(pady=(6, 0))

        # 分隔线
        tk.Frame(self, bg=PAL["border"], height=1).pack(fill="x", padx=120, pady=16)

        # 终端启动文本区
        self._terminal_frame = tk.Frame(self, bg=PAL["bg"])
        self._terminal_frame.pack(pady=(0, 8))

        self._terminal_text = tk.Text(
            self._terminal_frame,
            width=56,
            height=9,
            bg=PAL["bg"],
            fg=PAL["terminal"],
            font=("Consolas", 11),
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            state="disabled",
            insertbackground=PAL["terminal"],
            selectbackground=PAL["terminal_dim"],
        )
        self._terminal_text.pack()

        # 状态栏
        status_frame = tk.Frame(self, bg=PAL["bg"])
        status_frame.pack(pady=(0, 16))

        self._status_label = tk.Label(
            status_frame,
            text=f"{self.app.lore.signal_name}：等待连接...",
            font=("Consolas", 10),
            fg=PAL["dim"],
            bg=PAL["bg"],
        )
        self._status_label.pack()

        # 按钮区
        self._btn_frame = tk.Frame(self, bg=PAL["bg"])
        self._btn_frame.pack()

        self._buttons_built = False

        # 平台箴言
        tk.Label(
            self,
            text=f"「{self.app.lore.platform_slogan}」",
            font=("Microsoft YaHei UI", 10, "italic"),
            fg=PAL["dim"],
            bg=PAL["bg"]
        ).pack(side="bottom", pady=(0, 6))

        tk.Label(
            self,
            text=f"综网终端 v3.0  ·  {self.app.lore.platform_name} 平台  ·  "
                 f"因果链校验：{self.app.lore.supreme_evaluation}",
            font=("Microsoft YaHei UI", 9),
            fg=PAL["dim"],
            bg=PAL["bg"]
        ).pack(side="bottom", pady=(0, 12))

        # 启动开机动画
        self._run_boot_sequence()

    # ── 开机动画 ──────────────────────────────────────────────────────

    def _run_boot_sequence(self):
        lines = self.app.lore.boot_lines
        self._boot_phase = 0
        self._show_next_boot_line(lines, 0)

    def _show_next_boot_line(self, lines, idx):
        if idx >= len(lines):
            self._status_label.config(
                text=f"{self.app.lore.signal_name}：● 稳定  |  "
                     f"因果链：因→果  |  至高签名：{self.app.lore.supreme_evaluation}",
                fg=PAL["terminal"],
            )
            self._show_buttons()
            return

        tw = self._terminal_text
        tw.config(state="normal")
        line = lines[idx]
        self._type_line(tw, line, 0, lambda: self._show_next_boot_line(lines, idx + 1))

    def _type_line(self, tw, line, char_idx, callback):
        if char_idx >= len(line):
            tw.config(state="normal")
            tw.insert("end", "\n")
            tw.config(state="disabled")
            tw.see("end")
            self.after(200, callback)
            return

        tw.config(state="normal")
        tw.insert("end", line[char_idx])
        tw.config(state="disabled")
        tw.see("end")
        delay = 25 if char_idx < len(line) - 1 else 50
        self.after(delay, lambda: self._type_line(tw, line, char_idx + 1, callback))

    def _show_buttons(self):
        if self._buttons_built:
            return
        self._buttons_built = True

        buttons = []
        if self.app.save_mgr.has_save():
            buttons.append(("继续接入", self.app.continue_game, True))

        buttons += [
            (f"进入{self.app.lore.game_lib_name}",  self.app.show_bookshelf, False),
            ("断开连接",                            self.app.quit,           False),
        ]

        for label, cmd, accent in buttons:
            btn = HoverButton(
                self._btn_frame, label, command=cmd,
                accent=accent, big=True, color_terminal=accent,
            )
            btn.pack(pady=6, ipadx=30)


# ═══════════════════════════════════════════════════════════════════════
#  游戏库界面 —— 地狱之下平台游戏库
# ═══════════════════════════════════════════════════════════════════════

class GameLibrary(tk.Frame):
    """展示所有书卷，按系列分区，以平台游戏库的形式呈现。
    系列配色和标签全部从 meta.json 的 series_config 动态读取。
    """

    def _section_colors(self, section_key: str) -> dict:
        """从 meta.json series_config 获取分区配色"""
        cfg = self.app.data.series_for_prefix(section_key)
        return cfg.get("colors", {
            "accent": PAL["default_section_accent"],
            "title":  PAL["default_section_title"],
            "badge":  PAL["default_section_badge"],
            "bg":     PAL["panel"],
            "card_bg": PAL["panel"],
        })

    def __init__(self, master: "App"):
        super().__init__(master, bg=PAL["bg"])
        self.app = master
        self._build()

    def _build(self):
        tk.Frame(self, bg=PAL["accent"], height=3).pack(fill="x")

        # ── 标题行 ──────────────────────────────────────────────
        hdr = tk.Frame(self, bg=PAL["bg"])
        hdr.pack(fill="x", padx=40, pady=(24, 8))

        tk.Label(
            hdr,
            text=f"🎮  {self.app.lore.game_lib_name}",
            font=("Microsoft YaHei UI", 22, "bold"),
            fg=PAL["heading"],
            bg=PAL["bg"]
        ).pack(side="left")

        HoverButton(hdr, "← 终端", command=self.app.show_main_menu).pack(side="right")

        # ── 状态条 ──────────────────────────────────────────────
        status_row = tk.Frame(self, bg=PAL["bg"])
        status_row.pack(fill="x", padx=40, pady=(0, 12))

        tk.Label(
            status_row,
            text=f"当前平台：{self.app.lore.platform_name}  |  "
                 f"{self.app.lore.signal_name}：● 稳定  |  "
                 f"因果链：{self.app.lore.supreme_name} → {self.app.lore.platform_name}",
            font=("Consolas", 10),
            fg=PAL["terminal_dim"],
            bg=PAL["bg"],
        ).pack(side="left")

        tk.Label(
            status_row,
            text=f"共 {self.app.data.total_json_count} 份档案",
            font=("Consolas", 10),
            fg=PAL["dim"],
            bg=PAL["bg"],
        ).pack(side="right")

        tk.Frame(self, bg=PAL["border"], height=1).pack(fill="x", padx=40)

        # ── 可滚动容器 ──────────────────────────────────────────
        container = tk.Frame(self, bg=PAL["bg"])
        container.pack(fill="both", expand=True, padx=40)

        canvas = tk.Canvas(container, bg=PAL["bg"], highlightthickness=0)
        vsb    = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=PAL["bg"])
        cwin  = canvas.create_window((0, 0), window=inner, anchor="nw")

        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cwin, width=e.width))
        inner.bind("<Configure>",  lambda _: canvas.configure(scrollregion=canvas.bbox("all")))

        def _mw(e): canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _mw)
        inner.bind("<MouseWheel>",  _mw)

        # ── 第一区：地狱之下 · 一切之果 ─────────────────────────
        hell_cfg = self.app.data.series_for_prefix("hell")
        hell_colors = self._section_colors("hell")
        self._section_label(
            inner,
            f"{hell_cfg['icon']} {self.app.lore.platform_name}  ·  {hell_cfg['relation']}",
            hell_colors["accent"], hell_colors["title"],
            f"{hell_cfg['desc']} — {self.app.lore.causality}"
        )

        for v_meta in self.app.data.volumes:
            file_key = f"vol_{v_meta['volume']:02d}"
            self._make_card(
                inner,
                badge    = f"W-{v_meta['volume']:02d}",
                title    = v_meta["title"],
                subtitle = f"主角：{v_meta['protagonist']}  ·  "
                           f"{v_meta['chapter_count']} 章",
                file_key = file_key,
                section  = "hell",
            )

        # ── 作品集各区 ──────────────────────────────────────────
        for w_meta in self.app.data.works:
            prefix = w_meta["prefix"]
            relation = w_meta.get("relation", "")
            cosmic_role = w_meta.get("cosmic_role", "")

            # 从 series_config 获取配置
            s_cfg = self.app.data.series_for_prefix(prefix)
            s_colors = self._section_colors(prefix)
            icon = s_cfg.get("icon", "📄")

            section_desc = f"{relation}"
            if cosmic_role:
                section_desc += f" — {cosmic_role}"

            tk.Frame(inner, bg=PAL["border"], height=1).pack(fill="x", pady=(20, 0))
            self._section_label(
                inner,
                f"{icon} {w_meta['book']}  ·  {relation}",
                s_colors["accent"],
                s_colors["title"],
                section_desc,
            )

            # 各卷卡片
            for v_info in w_meta["volumes"]:
                file_key = v_info["file"].replace(".json", "")
                self._make_card(
                    inner,
                    badge    = f"{prefix.upper()}-{file_key.split('_v')[-1]}",
                    title    = v_info["title"],
                    subtitle = f"档案：{w_meta['book']}",
                    file_key = file_key,
                    section  = prefix,
                )

        # 底部留白
        tk.Frame(inner, bg=PAL["bg"], height=30).pack()

    def _section_label(self, parent, text, bar_color, text_color, desc=""):
        row = tk.Frame(parent, bg=PAL["bg"])
        row.pack(fill="x", pady=(16, 2))
        tk.Frame(row, bg=bar_color, width=4).pack(side="left", fill="y")
        tk.Label(
            row,
            text=f"  {text}",
            font=("Microsoft YaHei UI", 13, "bold"),
            fg=text_color,
            bg=PAL["bg"],
            pady=6,
        ).pack(side="left")
        if desc:
            tk.Label(
                row,
                text=f"  —  {desc}",
                font=("Microsoft YaHei UI", 9),
                fg=PAL["dim"],
                bg=PAL["bg"],
                pady=6,
            ).pack(side="left")

    def _make_card(self, parent, badge, title, subtitle,
                   file_key, section):
        colors = self._section_colors(section)
        card_bg = colors["card_bg"]

        card = tk.Frame(parent, bg=card_bg, pady=10, padx=20)
        card.pack(fill="x", pady=2)

        def _open(_, fk=file_key):
            self.app.start_book(fk)

        card.bind("<Button-1>", _open)

        # 编号徽章
        badge_lbl = tk.Label(
            card,
            text=badge,
            font=("Consolas", 10, "bold"),
            fg=colors["badge"],
            bg=card_bg,
            width=8
        )
        badge_lbl.pack(side="left", padx=(0, 14))
        badge_lbl.bind("<Button-1>", _open)

        # 文字区
        info = tk.Frame(card, bg=card_bg)
        info.pack(side="left", fill="x", expand=True)
        info.bind("<Button-1>", _open)

        title_lbl = tk.Label(
            info,
            text=title,
            font=("Microsoft YaHei UI", 14, "bold"),
            fg=colors["title"],
            bg=card_bg,
            anchor="w"
        )
        title_lbl.pack(fill="x")
        title_lbl.bind("<Button-1>", _open)

        sub_lbl = tk.Label(
            info,
            text=subtitle,
            font=("Consolas", 9),
            fg=PAL["dim"],
            bg=card_bg,
            anchor="w"
        )
        sub_lbl.pack(fill="x")
        sub_lbl.bind("<Button-1>", _open)

        # 悬停
        def _enter(_, c=card):
            c.config(bg=PAL["btn_hover"])
            _set_bg(c, PAL["btn_hover"])

        def _leave(_, c=card, cbg=card_bg):
            c.config(bg=cbg)
            _set_bg(c, cbg)

        card.bind("<Enter>", _enter)
        card.bind("<Leave>", _leave)
        for child in card.winfo_children():
            child.bind("<Enter>", _enter)
            child.bind("<Leave>", _leave)


# ═══════════════════════════════════════════════════════════════════════
#  阅读器界面 —— 档案终端
# ═══════════════════════════════════════════════════════════════════════

class ReaderView(tk.Frame):
    """档案终端阅读视图，兼容所有系列数据。"""

    def __init__(self, master: "App"):
        super().__init__(master, bg=PAL["bg"])
        self.app   = master
        self.state = master.state
        self.data  = master.data
        self._font_size = FONT_DEFAULT_SIZE
        self._toc_open  = False

        self._build()
        self.refresh()

        master.bind("<Right>",     lambda _: self.next_page())
        master.bind("<Left>",      lambda _: self.prev_page())
        master.bind("<space>",     lambda _: self.next_page())
        master.bind("<Control-s>", lambda _: self.app.save_game())
        master.bind("<Escape>",    lambda _: self._ask_back())

    def _build(self):
        # ── 顶部工具栏 ─────────────────────────────────────────────
        toolbar = tk.Frame(self, bg=PAL["panel"], pady=4)
        toolbar.pack(fill="x")

        HoverButton(toolbar, "☰ 目录",    command=self._toggle_toc).pack(side="left", padx=(8, 4))
        HoverButton(toolbar, "← 游戏库",  command=self._ask_back).pack(side="left",  padx=4)

        self._signal = SignalIndicator(toolbar)
        self._signal.pack(side="left", padx=(16, 8))

        self._vol_label = tk.Label(
            toolbar,
            text="",
            font=("Consolas", 10),
            fg=PAL["dim"],
            bg=PAL["panel"]
        )
        self._vol_label.pack(side="left", padx=4)

        self._hp_display = HellPointsDisplay(toolbar)
        self._hp_display.pack(side="right", padx=(4, 4))

        HoverButton(toolbar, "💾 存取", command=self.app.save_game).pack(side="right", padx=4)
        HoverButton(toolbar, "A+",      command=self._font_up).pack(side="right", padx=2)
        HoverButton(toolbar, "A-",      command=self._font_dn).pack(side="right", padx=2)

        self._progress = ProgressBar(self, height=3)
        self._progress.pack(fill="x")

        # ── 主体区 ────────────────────────────────────────────────
        self._body = tk.Frame(self, bg=PAL["bg"])
        self._body.pack(fill="both", expand=True)

        self._toc_frame = tk.Frame(self._body, bg=PAL["panel"], width=260)
        self._build_toc_panel()

        self._reader_frame = tk.Frame(self._body, bg=PAL["bg"])
        self._reader_frame.pack(fill="both", expand=True)
        self._build_reader_panel()

        # ── 底部导航 ─────────────────────────────────────────────
        nav = tk.Frame(self, bg=PAL["panel"], pady=8)
        nav.pack(fill="x")

        self._prev_btn = HoverButton(nav, "◀  上一页", command=self.prev_page)
        self._prev_btn.pack(side="left", padx=20)

        self._page_label = tk.Label(
            nav,
            text="",
            font=("Consolas", 10),
            fg=PAL["dim"],
            bg=PAL["panel"]
        )
        self._page_label.pack(side="left", expand=True)

        self._next_btn = HoverButton(
            nav, "继续  ▶", command=self.next_page, accent=True
        )
        self._next_btn.pack(side="right", padx=20)

    # ── 目录面板 ─────────────────────────────────────────────────────

    def _build_toc_panel(self):
        toc_header = tk.Frame(self._toc_frame, bg=PAL["panel"])
        toc_header.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(
            toc_header,
            text=f"📋 {self.app.lore.archive_name}目录",
            font=("Microsoft YaHei UI", 13, "bold"),
            fg=PAL["heading"],
            bg=PAL["panel"]
        ).pack(side="left")
        HoverButton(toc_header, "✕", command=self._toggle_toc).pack(side="right")

        toc_canvas = tk.Canvas(self._toc_frame, bg=PAL["panel"], highlightthickness=0)
        toc_vsb    = tk.Scrollbar(self._toc_frame, orient="vertical", command=toc_canvas.yview)
        toc_canvas.configure(yscrollcommand=toc_vsb.set)
        toc_vsb.pack(side="right", fill="y")
        toc_canvas.pack(side="left", fill="both", expand=True)

        self._toc_inner = tk.Frame(toc_canvas, bg=PAL["panel"])
        toc_win = toc_canvas.create_window((0, 0), window=self._toc_inner, anchor="nw")

        toc_canvas.bind("<Configure>", lambda e: toc_canvas.itemconfig(toc_win, width=e.width))
        toc_canvas.bind("<MouseWheel>", lambda e: toc_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self._toc_inner.bind(
            "<Configure>",
            lambda _: toc_canvas.configure(scrollregion=toc_canvas.bbox("all"))
        )

    def _populate_toc(self):
        for w in self._toc_inner.winfo_children():
            w.destroy()

        s = self.state
        book = self.data.get_book(s.file_key)

        for i, ch in enumerate(book["chapters"]):
            is_cur = (i == s.ch_idx)
            bg = PAL["accent"] if is_cur else PAL["panel"]
            fg = PAL["heading"] if is_cur else PAL["btn_text"]

            lbl = tk.Label(
                self._toc_inner,
                text=ch["title"],
                font=("Microsoft YaHei UI", 10),
                fg=fg, bg=bg,
                anchor="w", padx=10, pady=5,
                wraplength=230, justify="left",
                cursor="hand2"
            )
            lbl.pack(fill="x")
            lbl.bind("<Button-1>", lambda _, idx=i: self._jump_chapter(idx))

            def _enter(_, w=lbl, idx=i):
                if idx != self.state.ch_idx:
                    w.config(bg=PAL["btn_hover"])
            def _leave(_, w=lbl, idx=i):
                w.config(bg=PAL["accent"] if idx == self.state.ch_idx else PAL["panel"])
            lbl.bind("<Enter>", _enter)
            lbl.bind("<Leave>", _leave)

    def _toggle_toc(self):
        self._toc_open = not self._toc_open
        if self._toc_open:
            self._populate_toc()
            self._toc_frame.pack(side="left", fill="y", before=self._reader_frame)
        else:
            self._toc_frame.pack_forget()

    def _jump_chapter(self, ch_idx: int):
        self.state.ch_idx   = ch_idx
        self.state.page_idx = 0
        if self._toc_open:
            self._toggle_toc()
        self.refresh()

    # ── 阅读区 ───────────────────────────────────────────────────────

    def _build_reader_panel(self):
        pad_frame = tk.Frame(self._reader_frame, bg=PAL["bg"])
        pad_frame.pack(fill="both", expand=True)

        self._ch_title_label = tk.Label(
            pad_frame,
            text="",
            font=("Microsoft YaHei UI", 14, "bold"),
            fg=PAL["title"],
            bg=PAL["bg"],
            anchor="w",
            wraplength=1000
        )
        self._ch_title_label.pack(fill="x", padx=80, pady=(20, 6))

        tk.Frame(pad_frame, bg=PAL["border"], height=1).pack(fill="x", padx=80, pady=(0, 16))

        txt_frame = tk.Frame(pad_frame, bg=PAL["text_area"])
        txt_frame.pack(fill="both", expand=True, padx=60, pady=(0, 10))

        vsb = tk.Scrollbar(txt_frame, orient="vertical")
        vsb.pack(side="right", fill="y")

        self._text_widget = tk.Text(
            txt_frame,
            wrap="word",
            bg=PAL["text_area"],
            fg=PAL["text"],
            font=("Microsoft YaHei UI", self._font_size),
            relief="flat",
            bd=0,
            padx=30, pady=20,
            spacing1=6, spacing3=6,
            cursor="arrow",
            state="disabled",
            yscrollcommand=vsb.set,
            selectbackground=PAL["accent"],
        )
        self._text_widget.pack(fill="both", expand=True)
        vsb.config(command=self._text_widget.yview)

    def _set_text(self, content: str):
        tw = self._text_widget
        tw.config(state="normal")
        tw.delete("1.0", "end")
        for i, p in enumerate(content.split('\n')):
            tw.insert("end", p)
            if i < len(content.split('\n')) - 1:
                tw.insert("end", "\n")
        tw.config(state="disabled")
        tw.yview_moveto(0)

    # ── 刷新 ─────────────────────────────────────────────────────────

    def refresh(self):
        s    = self.state

        book = self.data.get_book(s.file_key)
        ch   = self.data.get_chapter(s.file_key, s.ch_idx)
        page = self.data.get_page(s.file_key, s.ch_idx, s.page_idx)

        # 工具栏标题 —— 根据系列显示不同格式
        if s.is_hell_below:
            label_text = (f"{self.app.lore.platform_name}  ·  "
                         f"世界 {s.file_key[-2:]}  ·  {book.get('title', '')}")
        else:
            vol_title = book.get('title', book.get('volume_title', ''))
            label_text = f"{s.series_label}  ·  {vol_title}"
        self._vol_label.config(text=label_text)

        # 章节标题
        if s.page_idx == 0:
            self._ch_title_label.config(text=ch["title"])
        else:
            self._ch_title_label.config(text="")

        # 正文
        self._set_text(page)

        # 地狱点数
        self._hp_display.update_points(s.hell_points)

        # 进度
        total_pages = self.data.total_pages(s.file_key)
        passed = sum(self.data.page_count(s.file_key, i) for i in range(s.ch_idx)) + s.page_idx + 1
        self._progress.set(passed / max(total_pages, 1))

        # 页码
        total_ch = self.data.chapter_count(s.file_key)
        ch_pages = self.data.page_count(s.file_key, s.ch_idx)
        pct = int(passed / max(total_pages, 1) * 100)
        self._page_label.config(
            text=f"CH.{s.ch_idx + 1:03d}/{total_ch:03d}  |  "
                 f"PG.{s.page_idx + 1:03d}/{ch_pages:03d}  |  "
                 f"PROG {pct}%"
        )

        # 按钮状态
        is_first = (s.ch_idx == 0 and s.page_idx == 0)
        is_last  = (s.ch_idx == total_ch - 1
                    and s.page_idx == self.data.page_count(s.file_key, s.ch_idx) - 1)
        self._prev_btn.config(fg=PAL["dim"] if is_first else PAL["btn_text"])

        if is_last:
            self._next_btn.config(text="【档案结束】")
        else:
            self._next_btn.config(text="继续  ▶")

        self._text_widget.config(font=("Microsoft YaHei UI", self._font_size))

    # ── 翻页 ─────────────────────────────────────────────────────────

    def next_page(self):
        s = self.state
        ch_pages = self.data.page_count(s.file_key, s.ch_idx)
        total_ch = self.data.chapter_count(s.file_key)

        if s.page_idx < ch_pages - 1:
            s.page_idx += 1
            s.hell_points += 1
        elif s.ch_idx < total_ch - 1:
            s.ch_idx  += 1
            s.page_idx = 0
            s.hell_points += 5
        else:
            self._book_end_dialog()
            return
        self.refresh()

    def prev_page(self):
        s = self.state
        if s.page_idx > 0:
            s.page_idx -= 1
            s.hell_points = max(0, s.hell_points - 1)
        elif s.ch_idx > 0:
            s.ch_idx  -= 1
            s.page_idx = self.data.page_count(s.file_key, s.ch_idx) - 1
        self.refresh()

    # ── 字号 ─────────────────────────────────────────────────────────

    def _font_up(self):
        if self._font_size < 28:
            self._font_size += 2
            self.refresh()

    def _font_dn(self):
        if self._font_size > 10:
            self._font_size -= 2
            self.refresh()

    # ── 对话框 ───────────────────────────────────────────────────────

    def _ask_back(self):
        if messagebox.askyesno(
            "返回游戏库",
            f"要保存当前{self.app.lore.archive_name}进度并返回游戏库吗？",
            parent=self.app
        ):
            self.app.save_game()
            self.app.show_bookshelf()

    def _book_end_dialog(self):
        msg = (f"您已阅读完本{self.app.lore.archive_name}全部内容！\n"
               f"累计{self.app.lore.hell_points_name}：{self.state.hell_points} "
               f"{self.app.lore.hell_points_unit}\n\n"
               f"是否返回游戏库？")
        if messagebox.askyesno("档案结束", msg, parent=self.app):
            self.app.save_game()
            self.app.show_bookshelf()


# ═══════════════════════════════════════════════════════════════════════
#  主应用
# ═══════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.lore     = LoreData()
        self.data     = GameData()
        self.state    = GameState(data_ref=self.data)
        self.save_mgr = SaveManager()

        self.title(f"综网终端  ·  {self.lore.platform_name}")
        self.geometry("1100x700")
        self.minsize(800, 560)
        self.configure(bg=PAL["bg"])

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"1100x700+{(sw - 1100) // 2}+{(sh - 700) // 2}")

        self._current_view: Optional[tk.Frame] = None
        self.show_main_menu()

    # ── 视图切换 ─────────────────────────────────────────────────────

    def _switch_view(self, view: tk.Frame):
        if self._current_view:
            self._current_view.destroy()
        self._current_view = view
        view.pack(fill="both", expand=True)

    def _unbind_reader_keys(self):
        for seq in ("<Right>", "<Left>", "<space>", "<Control-s>", "<Escape>"):
            try:
                self.unbind(seq)
            except Exception:
                pass

    def show_main_menu(self):
        self._unbind_reader_keys()
        self._switch_view(MainMenu(self))

    def show_bookshelf(self):
        self._unbind_reader_keys()
        self._switch_view(GameLibrary(self))

    def show_reader(self):
        self._switch_view(ReaderView(self))

    # ── 游戏操作 ─────────────────────────────────────────────────────

    def start_book(self, file_key: str, ch_idx: int = 0, page_idx: int = 0):
        self.state.file_key = file_key
        self.state.ch_idx   = ch_idx
        self.state.page_idx = page_idx
        self.show_reader()

    def continue_game(self):
        d = self.save_mgr.load()
        if d:
            self.state.from_dict(d)
            self.show_reader()
        else:
            messagebox.showinfo("提示", "没有找到存档。", parent=self)

    def save_game(self):
        self.save_mgr.save(self.state)
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=PAL["panel"])
        tk.Label(
            popup,
            text=f"  ✓ {self.lore.archive_name}已存取  ",
            font=("Consolas", 12),
            fg=PAL["terminal"],
            bg=PAL["panel"]
        ).pack(padx=16, pady=8)
        self.update_idletasks()
        rx = self.winfo_rootx() + self.winfo_width() - 160
        ry = self.winfo_rooty() + 50
        popup.geometry(f"+{rx}+{ry}")
        self.after(1200, popup.destroy)


# ═══════════════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()
