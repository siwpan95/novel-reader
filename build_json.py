"""
build_json.py
将《地狱之下》各卷 txt 解析为 Tkinter 视觉小说引擎所需的 JSON 格式。

JSON 结构说明
─────────────
meta.json          : 卷索引 + 全局配置
data/vol_01.json   : 第一卷所有节点
  {
    "volume": 1,
    "title": "内森·温特斯",
    "protagonist": "内森·温特斯",
    "chapters": [
      {
        "chapter_id": "vol1_ch00",
        "title": "第零集 内森·温特斯",
        "pages": [
          { "text": "...段落文字...", "choices": [] }   <- 普通翻页节点
        ]
      },
      ...
    ]
  }

每页 text 约 300~600 字（根据段落自然切分）。
choices 默认空列表 = 显示"继续"按钮；
特殊章节结尾可有多个 choice（此脚本暂统一为"继续"）。
"""

import re
import json
import os
import textwrap

# ── 配置 ──────────────────────────────────────────────────────────────
BASE_DIR = "C:/Users/13122/Desktop/小说/地狱之下/已完成"
OUT_DIR  = "C:/Users/13122/Desktop/hell_below_vn/data"

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

# 章节标题正则（匹配 "第X集 标题"）
CH_PAT = re.compile(r'^(第[零一二三四五六七八九十百千]+[集卷].+)$', re.MULTILINE)

# 每页最大字符数（约 450 字）
PAGE_MAX = 450

os.makedirs(OUT_DIR, exist_ok=True)

# ── 工具函数 ──────────────────────────────────────────────────────────

def clean_text(s: str) -> str:
    """去除全角空格缩进，规范化换行"""
    lines = []
    for line in s.splitlines():
        l = line.replace('\u3000', '').strip()
        if l:
            lines.append(l)
    return '\n'.join(lines)


def split_into_pages(text: str, max_chars: int = PAGE_MAX) -> list[str]:
    """
    将连续正文按段落切成若干"页"。
    优先按段落边界切分，每页不超过 max_chars 字符。
    """
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    pages = []
    current = []
    current_len = 0

    for para in paras:
        # 单段超长时先内部切分
        if len(para) > max_chars:
            # 按句号切
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


def parse_volume(vol_num: int) -> dict:
    folder, fname, protagonist = VOL_MAP[vol_num]
    fpath = os.path.join(BASE_DIR, folder, fname)
    with open(fpath, encoding='utf-8') as f:
        raw = f.read()

    # 按章节标题切分
    parts = CH_PAT.split(raw)
    # parts = [前置文字, 标题1, 正文1, 标题2, 正文2, ...]

    chapters = []
    chapter_idx = 0
    i = 1  # 跳过 parts[0]（通常为空或前言）
    while i < len(parts) - 1:
        title = parts[i].strip()
        body  = parts[i + 1] if i + 1 < len(parts) else ""
        body  = clean_text(body)

        # 跳过纯卷标题行（如"第一卷 内森·温特斯"），它不含正文
        is_volume_header = re.match(r'^第[零一二三四五六七八九十百千]+卷\s', title)
        if is_volume_header and len(body) < 20:
            i += 2
            continue

        ch_id = f"vol{vol_num:02d}_ch{chapter_idx:02d}"
        pages_text = split_into_pages(body)
        pages = [{"text": t, "choices": []} for t in pages_text]

        # 章节最后一页加上章末标记
        if pages:
            pages[-1]["chapter_end"] = True

        chapters.append({
            "chapter_id": ch_id,
            "title": title,
            "pages": pages
        })
        chapter_idx += 1
        i += 2

    vol_data = {
        "volume": vol_num,
        "title": protagonist,
        "protagonist": protagonist,
        "chapters": chapters
    }
    return vol_data


def build_meta(all_vols: list[dict]) -> dict:
    meta = {
        "game_title": "地狱之下",
        "subtitle": "Hell Below",
        "version": "1.0",
        "volumes": []
    }
    for v in all_vols:
        meta["volumes"].append({
            "volume": v["volume"],
            "title": v["title"],
            "protagonist": v["protagonist"],
            "chapter_count": len(v["chapters"]),
            "file": f"vol_{v['volume']:02d}.json"
        })
    return meta


# ── 主流程 ────────────────────────────────────────────────────────────

def main():
    all_vols = []
    for vol_num in sorted(VOL_MAP.keys()):
        print(f"正在处理第 {vol_num} 卷...", end="", flush=True)
        try:
            v = parse_volume(vol_num)
            all_vols.append(v)
            out_path = os.path.join(OUT_DIR, f"vol_{vol_num:02d}.json")
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(v, f, ensure_ascii=False, indent=2)
            total_pages = sum(len(ch["pages"]) for ch in v["chapters"])
            print(f" ✓  {len(v['chapters'])} 章 / {total_pages} 页")
        except Exception as e:
            print(f" ✗  {e}")

    meta = build_meta(all_vols)
    meta_path = os.path.join(OUT_DIR, "meta.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"\nmeta.json 已写入：{meta_path}")
    print("全部完成。")


if __name__ == "__main__":
    main()
