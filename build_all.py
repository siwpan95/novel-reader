#!/usr/bin/env python3
"""
build_all.py
《地狱之下》视觉小说引擎 — 全量构建脚本

将两类原始 txt 解析为引擎所需的 JSON，并更新统一的 meta.json。

─────────────────────────────────────────────
流水线 A：地狱之下正传（build_json.py 逻辑）
  输入：环境变量 HB_SRC_DIR 指向的原文目录（其下按卷分目录）/**/*.txt
  输出：<输出目录，默认本仓 data/>/vol_01.json … vol_13.json（NOVEL_READER_OUT 可覆盖）

  JSON 结构
    {
      "volume": 1,
      "title": "内森·温特斯",
      "protagonist": "内森·温特斯",
      "chapters": [
        {
          "chapter_id": "vol01_ch00",
          "title": "第零集 内森·温特斯",
          "pages": [
            { "text": "...", "choices": [], "chapter_end": true }
          ]
        }
      ]
    }

─────────────────────────────────────────────
流水线 B：作品集（build_works_v2.py 逻辑，取代旧 build_zuopinji.py）
  输入：环境变量 ZP_SRC_DIR 指向的作品集目录/*.txt
  输出：<输出目录>/w1_v01.json … w3_vNX.json（按卷拆分，超大卷自动分册）

  JSON 结构
    {
      "book": "单机作家",
      "volume_index": 1,
      "volume_title": "第一卷 ...",
      "chapter_count": N,
      "total_pages": M,
      "chapters": [
        { "title": "第一章 ...", "pages": ["...", "..."] }
      ]
    }

─────────────────────────────────────────────
最终写入 <输出目录>/meta.json（合并两条流水线的索引）
"""

import re
import json
import os
from pathlib import Path

# ═══════════════════════════════════════════════════════════
#  全局配置
# ═══════════════════════════════════════════════════════════

# 2026-09-23 去本地化：源目录改由环境变量指定（原 C:/Users/.../Desktop 与 D:/allin 均已失效）；
# 输出目录默认落在本仓 data/（可用 NOVEL_READER_OUT 覆盖）。
_HERE = Path(__file__).resolve().parent


def _src_dir(env_name: str, hint: str) -> Path:
    v = os.environ.get(env_name)
    if not v:
        raise SystemExit(
            f"[错误] 未设置 {env_name}（{hint}）。\n"
            f"  例：set {env_name}=D:\\你的目录"
        )
    p = Path(v)
    if not p.is_dir():
        raise SystemExit(f"[错误] {env_name} 指向的目录不存在：{p}")
    return p


HB_SRC_DIR = _src_dir("HB_SRC_DIR", "地狱之下原文目录，其下按卷分目录")
ZP_SRC_DIR = _src_dir("ZP_SRC_DIR", "作品集目录，内含各作品文本")      # 作品集目录
OUT_DIR    = Path(os.environ.get("NOVEL_READER_OUT") or (_HERE / "data"))   # 统一输出目录

PAGE_MAX    = 450   # 地狱之下：每页最大字符数（按段落自然切分）
CHUNK_CHARS = 450   # 作品集：每页约字符数（按句末截断）
SPLIT_LIMIT = 1_200_000  # 作品集：超大卷触发分册阈值（字节）

OUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════
#  流水线 A：地狱之下正传
# ═══════════════════════════════════════════════════════════

# 卷号 → (子目录, 文件名, 主角名)
VOL_MAP = {
    1:  ("1.内森·温特斯",     "综网：地狱之下-第一卷 内森·温特斯.txt",     "内森·温特斯"),
    2:  ("2.布莱恩·辛普森",   "综网：地狱之下-第二卷 布莱恩·辛普森.txt",   "布莱恩·辛普森"),
    3:  ("3.斯托克顿·亚当斯", "综网：地狱之下-第三卷 斯托克顿·亚当斯.txt", "斯托克顿·亚当斯"),
    4:  ("4.艾伦·艾布特",     "综网：地狱之下-第四卷 艾伦·艾布特.txt",     "艾伦·艾布特"),
    5:  ("5.盘尼西林·帕金森", "综网：地狱之下-第五卷 盘尼西林·帕金森.txt", "盘尼西林·帕金森"),
    6:  ("6.安娜·斯克兰顿",   "综网：地狱之下-第六卷 安娜·斯克兰顿.txt",   "安娜·斯克兰顿"),
    7:  ("7.孛儿只斤·察合台", "综网：地狱之下-第七卷 孛儿只斤·察合台.txt", "孛儿只斤·察合台"),
    9:  ("9.刘敬宣",          "综网：地狱之下-第九卷 刘敬宣.txt",           "刘敬宣"),
    10: ("10.远坂凛世",       "综网：地狱之下-第十卷 远坂凛世.txt",         "远坂凛世"),
    11: ("11.墟境",           "综网：地狱之下-第十一卷 墟境.txt",           "墟境·角色"),
    12: ("12.乔治斯·乔尔·拉姆齐-贝潘",
         "综网：地狱之下-第十二卷 乔治斯·乔尔·拉姆齐-贝潘.txt",
         "乔治斯·乔尔·拉姆齐-贝潘"),
    13: ("13.希尔德·斯坦利·杜鲁门",
         "综网：地狱之下-第十三卷 希尔德·斯坦利·杜鲁门.txt",
         "希尔德·斯坦利·杜鲁门"),
}

# 章节标题正则（匹配 "第X集/卷 标题"）
_HB_CH_PAT = re.compile(r'^(第[零一二三四五六七八九十百千]+[集卷].+)$', re.MULTILINE)


def _hb_clean(s: str) -> str:
    """去除全角空格缩进，规范化换行"""
    lines = [line.replace('\u3000', '').strip() for line in s.splitlines()]
    return '\n'.join(l for l in lines if l)


def _hb_split_pages(text: str, max_chars: int = PAGE_MAX) -> list[str]:
    """按段落自然边界切分为若干页，每页不超过 max_chars 字符"""
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    pages, current, current_len = [], [], 0

    for para in paras:
        if len(para) > max_chars:
            for sent in re.split(r'(?<=[。！？\n])', para):
                sent = sent.strip()
                if not sent:
                    continue
                if current_len + len(sent) + 1 > max_chars and current:
                    pages.append('\n'.join(current))
                    current, current_len = [], 0
                current.append(sent)
                current_len += len(sent) + 1
        else:
            if current_len + len(para) + 1 > max_chars and current:
                pages.append('\n'.join(current))
                current, current_len = [], 0
            current.append(para)
            current_len += len(para) + 1

    if current:
        pages.append('\n'.join(current))
    return pages


def _hb_parse_volume(vol_num: int) -> dict:
    """解析一卷地狱之下 txt，返回卷 JSON dict"""
    folder, fname, protagonist = VOL_MAP[vol_num]
    fpath = os.path.join(HB_SRC_DIR, folder, fname)
    with open(fpath, encoding='utf-8') as f:
        raw = f.read()

    parts = _HB_CH_PAT.split(raw)
    chapters = []
    chapter_idx = 0
    i = 1

    while i < len(parts) - 1:
        title = parts[i].strip()
        body  = _hb_clean(parts[i + 1] if i + 1 < len(parts) else "")

        # 跳过纯卷标题行（如"第一卷 内森·温特斯"，正文极短）
        if re.match(r'^第[零一二三四五六七八九十百千]+卷\s', title) and len(body) < 20:
            i += 2
            continue

        pages_text = _hb_split_pages(body)
        pages = [{"text": t, "choices": []} for t in pages_text]
        if pages:
            pages[-1]["chapter_end"] = True

        chapters.append({
            "chapter_id": f"vol{vol_num:02d}_ch{chapter_idx:02d}",
            "title": title,
            "pages": pages,
        })
        chapter_idx += 1
        i += 2

    return {
        "volume": vol_num,
        "title": protagonist,
        "protagonist": protagonist,
        "chapters": chapters,
    }


def build_hell_below() -> list[dict]:
    """流水线 A 主函数。返回所有卷的摘要（用于 meta.json）"""
    print("\n" + "=" * 60)
    print("流水线 A：地狱之下正传")
    print("=" * 60)

    vol_summaries = []
    for vol_num in sorted(VOL_MAP.keys()):
        print(f"  处理第 {vol_num:2d} 卷...", end="", flush=True)
        try:
            v = _hb_parse_volume(vol_num)
            out_path = OUT_DIR / f"vol_{vol_num:02d}.json"
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(v, f, ensure_ascii=False, indent=2)
            total_pages = sum(len(ch["pages"]) for ch in v["chapters"])
            print(f" ✓  {len(v['chapters'])}章 / {total_pages}页")
            vol_summaries.append({
                "volume": v["volume"],
                "title": v["title"],
                "protagonist": v["protagonist"],
                "chapter_count": len(v["chapters"]),
                "file": f"vol_{vol_num:02d}.json",
            })
        except Exception as e:
            print(f" ✗  {e}")

    return vol_summaries


# ═══════════════════════════════════════════════════════════
#  流水线 B：作品集（v2 逻辑，原 build_works_v2.py）
# ═══════════════════════════════════════════════════════════

# 三本书配置：(文件名, 书名, 前缀, 关系说明, 宇宙角色)
BOOK_CFG = [
    ("单机作家.txt",           "单机作家",           "w1",
     "设定圣典",       "宇宙理论架构解析"),
    ("林东的无限崩坏之旅.txt", "林东的无限崩坏之旅", "w2",
     "因果之源",       "林易东——至高无上的古神，一切之因"),
    ("玩家之上.txt",           "玩家之上",           "w3",
     "平台创始人视角", "地狱之下平台创始记录"),
]

_CN_MAP = {c: i for i, c in enumerate("零一二三四五六七八九")}
_CN_MAP.update({"十": 10, "百": 100, "千": 1000})


def _zp_paginate(text: str) -> list[str]:
    """将章节文本按 ~450 字、句末断行分页"""
    pages, pos = [], 0
    while pos < len(text):
        end = min(pos + CHUNK_CHARS, len(text))
        if end < len(text):
            for offset in range(min(80, end - pos)):
                idx = end - offset
                if idx > pos and text[idx - 1] in "。！？…」』\n":
                    end = idx
                    break
        pages.append(text[pos:end].strip())
        pos = end
    return [p for p in pages if p]


def _zp_split_volumes(content: str) -> list[tuple[str, str]]:
    """按'第X卷'拆分全文，返回 [(卷名, 文本), ...]"""
    pat = re.compile(r'^(第[零一二三四五六七八九十百千]+卷\s+\S+)', re.MULTILINE)
    matches = list(pat.finditer(content))
    if not matches:
        return [("全卷", content)]

    volumes = []
    pre = content[:matches[0].start()].strip()
    if pre:
        volumes.append(("序", pre))

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        volumes.append((title, content[start:end].strip()))

    return volumes


def _zp_split_chapters(content: str) -> list[tuple[str, str]]:
    """按'第X章'拆分，返回 [(章名, 文本), ...]"""
    pat = re.compile(r'^(第[零一二三四五六七八九十百千]+章\s*.+)', re.MULTILINE)
    matches = list(pat.finditer(content))
    if not matches:
        return [("第一章", content)]

    chapters = []
    pre = content[:matches[0].start()].strip()
    if pre:
        chapters.append(("序章", pre))

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        chapters.append((title, content[start:end].strip()))

    return chapters


def _zp_vol_to_json(vol_title: str, content: str, book_title: str,
                     vol_index: int, sub_label: str = "") -> dict:
    """将一卷文本转为游戏 JSON dict"""
    ch_list = []
    for ch_title, ch_text in _zp_split_chapters(content):
        pages = _zp_paginate(ch_text)
        if pages:
            ch_list.append({"title": ch_title, "pages": pages})

    label = f" {sub_label}" if sub_label else ""
    return {
        "book": book_title,
        "volume_index": vol_index,
        "volume_title": f"{vol_title}{label}",
        "chapter_count": len(ch_list),
        "total_pages": sum(len(c["pages"]) for c in ch_list),
        "chapters": ch_list,
    }


def _zp_split_large_vol(vol_title: str, content: str, book_title: str,
                         vol_index: int) -> list[tuple[str, dict]]:
    """超大卷（>SPLIT_LIMIT）自动按字数切为分册"""
    total = len(content)
    n = max(2, (total + SPLIT_LIMIT - 1) // SPLIT_LIMIT)
    label_sets = {2: ["上", "下"], 3: ["上", "中", "下"],
                  4: ["上", "中上", "中下", "下"], 5: ["壹", "贰", "叁", "肆", "伍"]}
    labels = label_sets.get(n, [f"Part{i+1}" for i in range(n)])

    parts = []
    part_size = total // n
    for i in range(n):
        s = i * part_size
        e = (i + 1) * part_size if i < n - 1 else total
        lab = labels[i] if i < len(labels) else f"P{i+1}"
        data = _zp_vol_to_json(vol_title, content[s:e].strip(), book_title,
                                vol_index, sub_label=f"（{lab}）")
        parts.append((f"{vol_title}（{lab}）", data))
    return parts


def _zp_process_book(fname: str, book_title: str, prefix: str) -> list[tuple[str, dict, str]]:
    """处理一本作品集，返回 [(文件名, JSON数据, 卷名), ...]"""
    src_path = ZP_SRC_DIR / fname
    with open(src_path, encoding="utf-8", errors="replace") as f:
        content = f.read()

    volumes = _zp_split_volumes(content)
    print(f"\n  {book_title}: {len(volumes)} 卷")

    results = []
    for i, (vol_title, vol_text) in enumerate(volumes):
        vol_num  = i + 1
        size_kb  = len(vol_text) // 1024
        file_name = f"{prefix}_v{vol_num:02d}.json"

        if len(vol_text) > SPLIT_LIMIT:
            for j, (part_title, part_data) in enumerate(
                    _zp_split_large_vol(vol_title, vol_text, book_title, vol_num)):
                part_fname = f"{prefix}_v{vol_num:02d}{chr(ord('a') + j)}.json"
                part_data["volume_title"] = part_title
                results.append((part_fname, part_data, part_title))
                print(f"    {part_fname:28s}  {part_data['total_pages']:5d}页  "
                      f"{part_data['chapter_count']:3d}章  分册  {part_title}")
        else:
            data = _zp_vol_to_json(vol_title, vol_text, book_title, vol_num)
            results.append((file_name, data, vol_title))
            print(f"    {file_name:28s}  {data['total_pages']:5d}页  "
                  f"{data['chapter_count']:3d}章  {size_kb:5d}KB  {vol_title}")

    return results


def build_works() -> list[dict]:
    """
    流水线 B 主函数。
    清理旧 zuopinji_*.json，生成新的按卷 JSON，返回作品集元数据列表。
    """
    print("\n" + "=" * 60)
    print("流水线 B：作品集（按卷拆分）")
    print("=" * 60)

    # 清理旧格式大文件
    old_files = list(OUT_DIR.glob("zuopinji_*.json"))
    for fp in old_files:
        fp.unlink()
        print(f"  删除旧文件: {fp.name}")

    all_results = []
    for fname, book_title, prefix, *_ in BOOK_CFG:
        results = _zp_process_book(fname, book_title, prefix)
        all_results.extend(results)

    print(f"\n写入 JSON 文件...")
    for out_fname, data, vol_title in all_results:
        out_path = OUT_DIR / out_fname
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ✓ {out_fname:28s}  {out_path.stat().st_size // 1024}KB  {vol_title}")

    # 构建 works_meta（供 meta.json）
    works_meta = []
    for fname, book_title, prefix, relation, cosmic_role in BOOK_CFG:
        vols = [(fn, t) for fn, _, t in all_results if fn.startswith(f"{prefix}_")]
        works_meta.append({
            "book": book_title,
            "prefix": prefix,
            "relation": relation,
            "cosmic_role": cosmic_role,
            "volumes": [{"file": fn, "title": t} for fn, t in vols],
        })

    # 统计
    total_ch = sum(d["chapter_count"] for _, d, _ in all_results)
    total_pg = sum(d["total_pages"]   for _, d, _ in all_results)
    print(f"\n  作品集统计: {len(all_results)} 个JSON / {total_ch} 章 / {total_pg} 页")

    return works_meta


# ═══════════════════════════════════════════════════════════
#  meta.json 合并写入
# ═══════════════════════════════════════════════════════════

def write_meta(vol_summaries: list[dict], works_meta: list[dict]) -> None:
    """将两条流水线的索引合并写入 meta.json"""
    meta_path = OUT_DIR / "meta.json"

    # 读取已有 meta（如果存在）
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {}

    meta["game_title"] = "地狱之下"
    meta["subtitle"]   = "Hell Below"
    meta["version"]    = "3.0"
    meta["volumes"]    = vol_summaries   # 地狱之下正传索引
    meta["works"]      = works_meta      # 作品集索引

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n  ✓ meta.json 已写入（v{meta['version']}）：{meta_path}")


# ═══════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("地狱之下 VN 全量构建")
    print("=" * 60)

    vol_summaries = build_hell_below()
    works_meta    = build_works()
    write_meta(vol_summaries, works_meta)

    # 最终汇总
    hb_files  = len(vol_summaries)
    zp_files  = sum(len(w["volumes"]) for w in works_meta)
    print(f"\n{'=' * 60}")
    print(f"全部完成。地狱之下正传: {hb_files} 个 JSON  |  "
          f"作品集: {zp_files} 个 JSON  |  "
          f"总计: {hb_files + zp_files + 1} 个文件（含 meta.json）")
    print("=" * 60)


if __name__ == "__main__":
    main()
