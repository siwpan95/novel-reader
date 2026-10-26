"""novel-reader 无头自检 —— 不创建 Tk 窗口，也不进入 App 主循环。

game.pyw 是单文件项目（数据层与 GUI 都在里面），但模块级只有类定义，
``App()`` 在 ``if __name__ == "__main__"`` 里，因此以模块方式加载不会开窗口。
这里只 import game.pyw 的数据层（LoreData / GameData / GameState / SaveManager）。

验证点：
1. meta.json 索引与 data/ 实际文件、章节数、页文本三者一致（数据往返）；
2. lore.json 世界观文本可被 LoreData 正常读取；
3. GameState 的 to_dict/from_dict 往返 + SaveManager 存档读写（写到临时目录，
   不污染项目里的 save.json）。

运行：python selfcheck.py
"""

import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data"


def load_game_module():
    """以模块方式加载 game.pyw（只执行类定义，不建窗口）。"""
    path = ROOT / "game.pyw"
    if not path.is_file():
        raise FileNotFoundError("game.pyw 不存在：%s" % path)
    loader = importlib.machinery.SourceFileLoader("novel_reader_selfcheck_game", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def check_meta_and_data(game):
    """功能点 1：meta 索引 <-> data/*.json 文件 <-> 章节/页内容 三者一致。"""
    data = game.GameData()
    if not data.volumes:
        return "meta.json 的 volumes 为空"
    if not data.works:
        return "meta.json 的 works 为空"

    referenced = set()
    for vol in data.volumes:
        referenced.add(str(vol["file"]))
    for work in data.works:
        for vol in work["volumes"]:
            referenced.add(str(vol["file"]))

    on_disk = {p.name for p in DATA_DIR.glob("*.json")} - {"meta.json", "lore.json"}
    missing = sorted(referenced - on_disk)
    if missing:
        return "meta.json 引用了不存在的文件：%r" % (missing[:3],)
    orphan = sorted(on_disk - referenced)
    if orphan:
        return "data/ 中有未被 meta.json 索引的文件：%r" % (orphan[:3],)

    total_pages = 0
    for vol in data.volumes:
        file_key = str(vol["file"])[:-len(".json")]
        chapters = data.chapter_count(file_key)
        if chapters != int(vol["chapter_count"]):
            return "卷 %s 的章节数 %d 与 meta 的 %r 不一致" % (
                file_key, chapters, vol["chapter_count"])
        if chapters <= 0:
            return "卷 %s 没有章节" % file_key
        pages = data.page_count(file_key, 0)
        if pages <= 0:
            return "卷 %s 第一章没有页" % file_key
        text = data.get_page(file_key, 0, 0)
        if not isinstance(text, str) or not text.strip():
            return "卷 %s 第 1 章第 1 页文本为空" % file_key
        vol_total = data.total_pages(file_key)
        if vol_total < chapters:
            return "卷 %s 总页数 %d 少于章节数 %d" % (file_key, vol_total, chapters)
        total_pages += vol_total

    if total_pages < 1000:
        return "全部卷合计只有 %d 页，数据明显不完整" % total_pages

    # 作品集：抽查每个系列的第一卷都能读出章节与页文本
    for work in data.works:
        first = work["volumes"][0]["file"]
        file_key = str(first)[:-len(".json")]
        if data.chapter_count(file_key) <= 0:
            return "作品集文件 %s 没有章节" % file_key
        if not str(data.get_page(file_key, 0, 0)).strip():
            return "作品集文件 %s 首页文本为空" % file_key
        label = data.series_label_for_file_key(file_key)
        if not label or label == file_key:
            return "作品集文件 %s 的系列标签异常：%r" % (file_key, label)
    return ""


def check_lore_data(game):
    """功能点 2：lore.json -> LoreData 的界面文本链路。"""
    lore = game.LoreData()
    if not lore.boot_lines or not all(isinstance(x, str) for x in lore.boot_lines):
        return "boot_lines 为空或含非字符串项"
    fields = {
        "welcome": lore.welcome,
        "boot_title_1": lore.boot_title_1,
        "boot_title_2": lore.boot_title_2,
        "boot_subtitle": lore.boot_subtitle,
        "hell_points_name": lore.hell_points_name,
        "signal_name": lore.signal_name,
        "archive_name": lore.archive_name,
        "game_lib_name": lore.game_lib_name,
        "platform_name": lore.platform_name,
        "platform_slogan": lore.platform_slogan,
    }
    for name, value in fields.items():
        if not value or not str(value).strip():
            return "LoreData.%s 为空" % name
    if lore.hell_points_name != lore._data["ui_text"]["hell_points_name"]:
        return "hell_points_name 未取自 lore.json 的 ui_text"
    return ""


def check_state_and_save(game):
    """功能点 3：GameState 字典往返 + SaveManager 存读档。"""
    data = game.GameData()
    state = game.GameState(data)
    state.file_key, state.ch_idx, state.page_idx = "vol_02", 3, 7
    state.hell_points = 42
    dumped = state.to_dict()
    if dumped != {"file_key": "vol_02", "ch": 3, "page": 7, "hell_points": 42}:
        return "GameState.to_dict 输出结构与预期不符：%r" % (dumped,)

    restored = game.GameState(data)
    restored.from_dict(dumped)
    if (restored.file_key, restored.ch_idx, restored.page_idx,
            restored.hell_points) != ("vol_02", 3, 7, 42):
        return "GameState.from_dict 往返丢字段：%r" % (restored.to_dict(),)
    if restored.is_hell_below is not True:
        return "vol_02 的 is_hell_below 应为 True"
    if restored.series_label != "地狱之下":
        return "vol_02 的 series_label=%r，期望 '地狱之下'" % (restored.series_label,)

    restored.file_key = "w1_v02"
    if restored.is_hell_below is not False:
        return "w1_v02 的 is_hell_below 应为 False"
    if not restored.series_label:
        return "w1_v02 的 series_label 为空"

    # 兼容旧存档字段（vol_key 而非 file_key）
    legacy = game.GameState(data)
    legacy.from_dict({"vol_key": "vol_05", "ch": 1, "page": 2, "hell_points": 9})
    if (legacy.file_key, legacy.ch_idx, legacy.page_idx, legacy.hell_points) != (
            "vol_05", 1, 2, 9):
        return "旧存档字段 vol_key 兼容失败：%r" % (legacy.to_dict(),)

    # SaveManager：写到临时目录，避免在项目里生成 save.json
    tmpdir = tempfile.mkdtemp(prefix="novel_reader_selfcheck_")
    original_save_file = game.SAVE_FILE
    try:
        game.SAVE_FILE = Path(tmpdir) / "save.json"
        saver = game.SaveManager()
        if saver.has_save():
            return "临时存档目录不应已有存档"
        if saver.load() is not None:
            return "无存档时 load() 应返回 None"

        saver.save(restored)
        if not game.SAVE_FILE.is_file():
            return "SaveManager.save 未写出存档文件"
        loaded = saver.load()
        if loaded != restored.to_dict():
            return "存读档往返不一致：%r != %r" % (loaded, restored.to_dict())
        with open(game.SAVE_FILE, encoding="utf-8") as f:
            json.load(f)  # 必须是合法 JSON

        game.SAVE_FILE.write_text("{not json", encoding="utf-8")
        if saver.load() is not None:
            return "损坏的存档应被 load() 吞掉并返回 None"
    finally:
        game.SAVE_FILE = original_save_file
        shutil.rmtree(tmpdir, ignore_errors=True)
    return ""


def main():
    try:
        game = load_game_module()
    except Exception:
        print("FAIL: cannot load game.pyw as a module")
        traceback.print_exc()
        return 1

    checks = [
        ("meta.json <-> data/*.json integrity", lambda: check_meta_and_data(game)),
        ("lore.json -> LoreData text", lambda: check_lore_data(game)),
        ("GameState round-trip + SaveManager", lambda: check_state_and_save(game)),
    ]
    for label, func in checks:
        try:
            err = func()
        except Exception:
            print("FAIL: %s raised" % label)
            traceback.print_exc()
            return 1
        if err:
            print("FAIL: %s: %s" % (label, err))
            return 1

    print("selfcheck ok: validated %d things -- %s" % (
        len(checks), "; ".join(label for label, _ in checks)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
