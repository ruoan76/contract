# OCR 排版与阅读顺序

## 流水线

1. RapidOCR / EasyOCR 检测识别 → 多 bbox 碎片
2. `AI_OCR_LAYOUT`：
   - `heuristic`（默认）：[`ocr_layout.layout_ocr_blocks_with_meta`](../app/services/ai_review/ocr_layout.py) — X 分栏、行合并、中文拼接、续行合并
   - `ppstructure`：可选 Paddle PP-Structure，未安装或失败时回退 heuristic
3. `build_document_json` 优先使用 `ocr_page_meta.layout_lines`（含 bbox）
4. `AI_OCR_VLM_FALLBACK=true` 时，低置信或 `layout_suspect` 页可走 LLM 页级纠错（`ocr_pdf_pages_async`）

## 配置项

| 变量 | 默认 | 说明 |
|------|------|------|
| `AI_OCR_LAYOUT` | heuristic | heuristic \| ppstructure |
| `AI_OCR_LINE_MERGE_RATIO` | 0.55 | 同行 Y 合并阈值系数 |
| `AI_OCR_PARAGRAPH_GAP_RATIO` | 1.6 | 段落空行阈值系数 |
| `AI_OCR_COLUMN_GAP_RATIO` | 0.12 | 分栏最小水平间隙（相对页宽） |
| `AI_OCR_VLM_FALLBACK` | false | 排版可疑/低置信 LLM 兜底 |

## 页元数据（`ocr_page_meta`）

- `column_count`、`layout_quality_score`、`layout_suspect`
- `layout_lines`: `[{text, bbox}]` 供 DocumentJSON
- `needs_review`: OCR 低置信 **或** `layout_suspect`

## 回归测试

```bash
cd backend
pytest tests/test_ocr_layout.py -m 'not slow'
pytest tests/test_ocr_layout.py -m slow  # 兰州合同样例 PDF 第 2 页句序（需 OCR 环境）
```
