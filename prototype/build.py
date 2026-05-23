#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将模块化源码合并为可双击打开的 index.html"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PAGES = ROOT / "pages"
PARTIALS = ROOT / "partials"
CSS = ROOT / "css" / "main.css"

JS_FILES = [
    "js/00-core.js",
    "js/01-data.js",
    "js/01b-ai-seeds.js",
    "js/02-app.js",
    "js/99-init.js",
]


def build() -> None:
    shell_path = SRC / "shell.html"
    if not shell_path.exists():
        raise SystemExit("缺少 src/shell.html，请先运行 extract 或从备份恢复")

    shell = shell_path.read_text(encoding="utf-8")
    order_file = PAGES / "_order.txt"
    page_ids = [
        ln.strip()
        for ln in order_file.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]

    pages_html = []
    for pid in page_ids:
        p = PAGES / f"{pid}.html"
        if not p.exists():
            raise SystemExit(f"缺少页面文件: {p}")
        pages_html.append(p.read_text(encoding="utf-8").rstrip())

    modals = ""
    modals_path = PARTIALS / "modals.html"
    if modals_path.exists():
        modals = modals_path.read_text(encoding="utf-8").rstrip()

    pages_block = "\n\n".join(pages_html)
    out = shell.replace("<!-- PAGES -->", pages_block)
    if modals and "<!-- MODALS -->" in out:
        out = out.replace("<!-- MODALS -->", modals)
    elif modals:
        out = out.replace(pages_block, pages_block + "\n\n" + modals)

    scripts = []
    for rel in JS_FILES:
        fp = ROOT / rel
        if not fp.exists() and rel == "js/02-app.js":
            fp = ROOT / "js" / "app.js"
        if fp.exists():
            scripts.append(f'<script src="{rel if fp.name != "app.js" else "js/app.js"}"></script>')

    out = out.replace("<!-- SCRIPTS -->", "\n".join(scripts))
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    print(f"built index.html — {len(page_ids)} pages, {len(scripts)} scripts")


if __name__ == "__main__":
    build()
