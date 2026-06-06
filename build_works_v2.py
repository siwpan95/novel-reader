#!/usr/bin/env python3
"""
build_works_v2.py — 按卷拆分作品集为独立JSON
单机作家: 12卷（卷12拆为5个分册）→ 16个JSON
林东: 20卷 → 20个JSON
玩家之上: 26卷 → 26个JSON
"""
import json
import re
import os
from pathlib import Path

SRC_DIR = Path("C:/Users/13122/Desktop/小说/作品集")
OUT_DIR = Path("C:/Users/13122/Desktop/hell_below_vn/data")
CHUNK_CHARS = 450  # 每页约450字符

# ── 中文数字转整数 ──
CN_DIGITS = "零一二三四五六七八九十百千"
CN_MAP = {c: i for i, c in enumerate("零一二三四五六七八九")}
CN_MAP.update({"十": 10, "百": 100, "千": 1000})

def cn_to_int(s: str) -> int:
    """将中文数字转为整数，如 '十二' → 12"""
    if s.isdigit():
        return int(s)
    result = 0
    current = 0
    for ch in s:
        v = CN_MAP.get(ch, 0)
        if v >= 10:
            if current == 0:
                current = 1
            result += current * v
            current = 0
        else:
            current = current * 10 + v if current else v
    return result + current


def paginate(text: str) -> list[str]:
    """将章节文本按~450字分页"""
    pages = []
    pos = 0
    while pos < len(text):
        end = min(pos + CHUNK_CHARS, len(text))
        # 尝试在句末断页
        if end < len(text):
            for offset in range(min(80, end - pos)):
                idx = end - offset
                if idx > pos and text[idx - 1] in "。！？…」』\n":
                    end = idx
                    break
        pages.append(text[pos:end].strip())
        pos = end
    return [p for p in pages if p]


def split_volumes(content: str) -> list[tuple[str, str]]:
    """按'第X卷'拆分文本，返回 [(卷名, 文本), ...]"""
    pattern = re.compile(r'^(第[零一二三四五六七八九十百千]+卷\s+\S+)', re.MULTILINE)
    matches = list(pattern.finditer(content))
    if not matches:
        return [("全卷", content)]

    volumes = []
    # 卷前正文
    pre = content[:matches[0].start()].strip()
    if pre:
        volumes.append(("序", pre))

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        text = content[start:end].strip()
        volumes.append((title, text))

    return volumes


def split_episodes(content: str) -> list[tuple[str, str]]:
    """按'第X集'拆分，用于单机作家卷5内部"""
    pattern = re.compile(r'^(第[零一二三四五六七八九十百千]+集\s+.+)', re.MULTILINE)
    matches = list(pattern.finditer(content))
    if not matches:
        return [("全卷", content)]

    episodes = []
    pre = content[:matches[0].start()].strip()
    if pre:
        episodes.append(("引", pre))

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        text = content[start:end].strip()
        episodes.append((title, text))

    return episodes


def split_chapters(content: str) -> list[tuple[str, str]]:
    """按'第X章'拆分章节"""
    pattern = re.compile(r'^(第[零一二三四五六七八九十百千]+章\s*.+)', re.MULTILINE)
    matches = list(pattern.finditer(content))
    if not matches:
        # 无章节结构，整卷作为一章
        return [("第一章", content)]

    chapters = []
    pre = content[:matches[0].start()].strip()
    if pre:
        chapters.append(("序章", pre))

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        text = content[start:end].strip()
        chapters.append((title, text))

    return chapters


def text_to_json(title: str, content: str, book_title: str, vol_index: int,
                 sub_label: str = "") -> dict:
    """将一卷文本转为游戏JSON格式"""
    chapters = split_chapters(content)

    ch_list = []
    for ch_title, ch_text in chapters:
        pages = paginate(ch_text)
        if pages:
            ch_list.append({
                "title": ch_title,
                "pages": pages
            })

    label = f" {sub_label}" if sub_label else ""
    return {
        "book": book_title,
        "volume_index": vol_index,
        "volume_title": f"{title}{label}",
        "chapter_count": len(ch_list),
        "total_pages": sum(len(c["pages"]) for c in ch_list),
        "chapters": ch_list
    }


def split_large_volume(title: str, content: str, book_title: str,
                       vol_index: int, max_chars: int = 1_200_000) -> list[tuple[str, dict]]:
    """将超大卷拆分为多个分册JSON"""
    if len(content) <= max_chars:
        return [(title, text_to_json(title, content, book_title, vol_index))]

    parts = []
    total = len(content)
    n_parts = max(2, (total + max_chars - 1) // max_chars)
    part_size = total // n_parts
    part_labels = "上中下前中后续终余声".translate(str.maketrans("", ""))  # unused
    labels = []
    if n_parts == 2:
        labels = ["上", "下"]
    elif n_parts == 3:
        labels = ["上", "中", "下"]
    elif n_parts == 4:
        labels = ["上", "中上", "中下", "下"]
    elif n_parts == 5:
        labels = ["壹", "贰", "叁", "肆", "伍"]
    else:
        labels = [f"Part{i+1}" for i in range(n_parts)]

    for i in range(n_parts):
        start = i * part_size
        end = (i + 1) * part_size if i < n_parts - 1 else total
        part_text = content[start:end].strip()
        label = labels[i] if i < len(labels) else f"P{i+1}"
        json_data = text_to_json(title, part_text, book_title, vol_index,
                                 sub_label=f"（{label}）")
        parts.append((f"{title}（{label}）", json_data))

    return parts


def process_book(src_path: Path, book_title: str, book_prefix: str) -> list[tuple[str, dict, str]]:
    """
    处理一本书，按卷拆分，返回 [(文件名, JSON数据, 卷名), ...]
    book_prefix: w1/w2/w3
    """
    with open(src_path, encoding="utf-8", errors="replace") as f:
        content = f.read()

    volumes = split_volumes(content)
    print(f"\n  {book_title}: {len(volumes)} 卷")

    results = []
    for i, (vol_title, vol_text) in enumerate(volumes):
        vol_num = i + 1
        size_kb = len(vol_text) // 1024

        # 检查单机作家卷5的特殊处理（内含"集"）
        if book_prefix == "w1" and "选择你自己的冒险" in vol_title:
            # 先不单独处理，将整卷（含集）作为一卷
            pass

        file_name = f"{book_prefix}_v{vol_num:02d}.json"

        # 超大卷需要拆分
        if len(vol_text) > 1_200_000:  # > ~1.2MB
            parts = split_large_volume(vol_title, vol_text, book_title, vol_num)
            for j, (part_title, part_data) in enumerate(parts):
                part_suffix = chr(ord('a') + j)  # a, b, c...
                part_fname = f"{book_prefix}_v{vol_num:02d}{part_suffix}.json"
                part_data["volume_title"] = part_title
                results.append((part_fname, part_data, part_title))
                print(f"    {part_fname:25s}  {part_data['total_pages']:5d}页  "
                      f"{part_data['chapter_count']:3d}章  "
                      f"{len(vol_text)//(1024*len(parts)):5d}KB×{len(parts)}  {part_title}")
        else:
            json_data = text_to_json(vol_title, vol_text, book_title, vol_num)
            results.append((file_name, json_data, vol_title))
            print(f"    {file_name:25s}  {json_data['total_pages']:5d}页  "
                  f"{json_data['chapter_count']:3d}章  {size_kb:5d}KB  {vol_title}")

    return results


def main():
    print("=" * 60)
    print("作品集按卷拆分构建 v2")
    print("=" * 60)

    # 删除旧的3个大JSON
    old_files = list(OUT_DIR.glob("zuopinji_*.json"))
    for f in old_files:
        f.unlink()
        print(f"  删除旧文件: {f.name}")

    all_results = []

    # ── 单机作家 ──
    results = process_book(
        SRC_DIR / "单机作家.txt",
        "单机作家", "w1"
    )
    all_results.extend(results)

    # ── 林东的无限崩坏之旅 ──
    results = process_book(
        SRC_DIR / "林东的无限崩坏之旅.txt",
        "林东的无限崩坏之旅", "w2"
    )
    all_results.extend(results)

    # ── 玩家之上 ──
    results = process_book(
        SRC_DIR / "玩家之上.txt",
        "玩家之上", "w3"
    )
    all_results.extend(results)

    # 写入所有JSON
    print(f"\n{'=' * 60}")
    print("写入JSON文件...")
    for fname, data, vol_title in all_results:
        out_path = OUT_DIR / fname
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        file_size = out_path.stat().st_size // 1024
        print(f"  ✓ {fname:25s}  {file_size:5d}KB  {vol_title}")

    # ── 更新 meta.json ──
    print(f"\n{'=' * 60}")
    print("更新 meta.json...")
    meta_path = OUT_DIR / "meta.json"
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {"version": "2.0", "volumes": [], "works": []}

    # 构建作品集条目
    works_meta = []
    # 单机作家
    w1_vols = [(fname, title) for fname, _, title in all_results if fname.startswith("w1_")]
    works_meta.append({
        "book": "单机作家",
        "prefix": "w1",
        "relation": "设定圣典",
        "cosmic_role": "宇宙理论架构解析",
        "volumes": [
            {"file": fname, "title": title}
            for fname, title in w1_vols
        ]
    })
    # 林东
    w2_vols = [(fname, title) for fname, _, title in all_results if fname.startswith("w2_")]
    works_meta.append({
        "book": "林东的无限崩坏之旅",
        "prefix": "w2",
        "relation": "因果之源",
        "cosmic_role": "林易东——至高无上的古神，一切之因",
        "volumes": [
            {"file": fname, "title": title}
            for fname, title in w2_vols
        ]
    })
    # 玩家之上
    w3_vols = [(fname, title) for fname, _, title in all_results if fname.startswith("w3_")]
    works_meta.append({
        "book": "玩家之上",
        "prefix": "w3",
        "relation": "平台创始人视角",
        "cosmic_role": "地狱之下平台创始记录",
        "volumes": [
            {"file": fname, "title": title}
            for fname, title in w3_vols
        ]
    })

    meta["works"] = works_meta
    meta["version"] = "3.0"

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"  ✓ meta.json 已更新 (v{meta['version']})")

    # ── 统计 ──
    total_ch = sum(d["chapter_count"] for _, d, _ in all_results)
    total_pg = sum(d["total_pages"] for _, d, _ in all_results)
    total_files = len(all_results)
    print(f"\n{'=' * 60}")
    print(f"作品集统计: {total_files} 个JSON / {total_ch} 章 / {total_pg} 页")
    print(f"加上地狱之下11卷 → 总计 {total_files + 11} 个JSON")
    print("=" * 60)


if __name__ == "__main__":
    main()
