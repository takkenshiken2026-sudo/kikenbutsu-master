# 試験ガイド「編集合格」全件リライト

**正本:** `~/Projects/exam-site-shell/docs/guide-expert-rewrite-program.md`

**本サイトのお手本**

- slug: `exam-schedule`
- batch: `tools/kiken_rewrite_exemplar.py`

**5本 batch の手順:** `docs/guide-hand-rewrite-batch-workflow.md`（`exam-site-shell` から sync）

**運用:** 賃管 149/149 完走後に着手。**expert_pass 130/130 完走**（2026-06-04、exemplar + batch1–25）。アフィリエイト10本は ASP 未設定のため対象外。

```bash
cd ~/Projects/kikenbutsu-master
python3 tools/run_guide_hand_batch.py --batch tools/kiken_rewrite_batchN_expert.py
python3 tools/build_article_pages.py
```
