"""
build_zuopinji.py
将《作品集》3本小说解析为 Tkinter 视觉小说引擎所需的 JSON 格式。

输出文件（独立，不覆盖地狱之下数据）：
  data/zuopinji_01.json  ← 单机作家 (206章)
  data/zuopinji_02.json  ← 林东的无限崩坏之旅 (534章)
  data/zuopinji_03.json  ← 玩家之上 (666章)

并追加更新 meta.json 中的 works 段落。
"""

import re
import json
import os

# ── 配置 ──────────────────────────────────────────────────────────────
SRC_DIR = "C:/Users/13122/Desktop/小说/作品集"
OUT_DIR = "C:/Users/13122/Desktop/hell_below_vn/data"
META_PATH = os.path.join(OUT_DIR, "meta.json")

BOOK_MAP = {
    1: ("单机作家.txt",            "单机作家",            "未知·写手"),
    2: ("林东的无限崩坏之旅.txt",  "林东的无限崩坏之旅",  "林东"),
    3: ("玩家之上.txt",            "玩家之上",            "未知·玩家"),
}

# 章节标题：第X章 标题  或  第X章：标题
CH_PAT = re.compile(
    r'^(第[零一二三四五六七八九十百千]+章[：: ].+|第[零一二三四五六七八九十百千]+章\s*.*)$',
    re.MULTILINE
)

PAGE_MAX = 450

os.makedirs(OUT_DIR, exist_ok=True)


# ── 工具函数 ──────────────────────────────────────────────────────────

def clean_text(s: str) -> str:
    lines = []
    for line in s.splitlines():
        l = line.replace('\u3000', '').strip()
        if l:
            lines.append(l)
    return '\n'.join(lines)


def split_into_pages(text: str, max_chars: int = PAGE_MAX) -> list:
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    pages = []
    current = []
    current_len = 0

    for para in paras:
        if len(para) > max_chars:
            sents = re.split(r'(?<=[。！？\n])', para)
            for sent in sents:
                sent = sent.strip()
                if not sent:
                    continue
                if current_len + len(sent) + 1 > max_chars and current:
                    pages.append('\n'.join(current))
                    current = []
                    current_len = 0
                current.append(sent)
                current_len += len(sent) + 1
        else:
            if current_len + len(para) + 1 > max_chars and current:
                pages.append('\n'.join(current))
                current = []
                current_len = 0
            current.append(para)
            current_len += len(para) + 1

    if current:
        pages.append('\n'.join(current))

    return pages


def parse_book(book_id: int) -> dict:
    fname, title, protagonist = BOOK_MAP[book_id]
    fpath = os.path.join(SRC_DIR, fname)
    with open(fpath, encoding='utf-8', errors='replace') as f:
        raw = f.read()

    # 找到"第一章"的位置，跳过前言
    first_ch = CH_PAT.search(raw)
    if first_ch:
        raw = raw[first_ch.start():]

    parts = CH_PAT.split(raw)
    # parts = [前置, 标题1, 正文1, 标题2, 正文2, ...]

    chapters = []
    chapter_idx = 0
    i = 1
    while i < len(parts) - 1:
        ch_title = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        body = clean_text(body)

        # 过滤空章节（标题行无正文）
        if len(body) < 10:
            i += 2
            continue

        ch_id = f"zuopinji{book_id:02d}_ch{chapter_idx:03d}"
        pages_text = split_into_pages(body)
        pages = [{"text": t, "choices": []} for t in pages_text]

        if pages:
            pages[-1]["chapter_end"] = True

        chapters.append({
            "chapter_id": ch_id,
            "title": ch_title,
            "pages": pages
        })
        chapter_idx += 1
        i += 2

    return {
        "series": "zuopinji",
        "book_id": book_id,
        "title": title,
        "protagonist": protagonist,
        "chapters": chapters
    }


def main():
    book_summaries = []
    for book_id in sorted(BOOK_MAP.keys()):
        title = BOOK_MAP[book_id][1]
        print(f"正在处理《{title}》...", end="", flush=True)
        try:
            data = parse_book(book_id)
            ch_count = len(data["chapters"])
            pg_count = sum(len(ch["pages"]) for ch in data["chapters"])

            out_path = os.path.join(OUT_DIR, f"zuopinji_{book_id:02d}.json")
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            size_kb = os.path.getsize(out_path) // 1024
            print(f" ✓  {ch_count}章 / {pg_count}页 / {size_kb}KB")

            book_summaries.append({
                "book_id": book_id,
                "series": "zuopinji",
                "title": data["title"],
                "protagonist": data["protagonist"],
                "chapter_count": ch_count,
                "page_count": pg_count,
                "file": f"zuopinji_{book_id:02d}.json"
            })
        except Exception as e:
            print(f" ✗  {e}")

    # 更新 meta.json：追加 works 字段
    with open(META_PATH, encoding='utf-8') as f:
        meta = json.load(f)

    meta["works"] = book_summaries
    meta["version"] = "2.0"  # 标记版本升级

    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n✓ meta.json 已更新（新增 works 字段）")
    print("全部完成。")


if __name__ == "__main__":
    main()
