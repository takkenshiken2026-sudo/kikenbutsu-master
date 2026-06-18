#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""リライト検証ヘルパー: 誤情報・意図せぬ<ul>・FAQ/section字数を一括チェック。
使い方: python3 tools/_check_rewrites.py slug1 slug2 ...
"""
from __future__ import annotations
import re, csv, sys
sys.path.insert(0, '.')
from tools.guide_article_rules import reader_facing_text

BADTOK = ['執筆待ち', 'greenfield', '旧稿', '50問', '四肢択一', '35/50', '60分·', '72秒',
          '三領域', '物性・火災', '物性·火災', '18歳', '17問', '12/17', '10/17']

rows = {r['slug']: r for r in csv.DictReader(open('data/guide_articles.csv', encoding='utf-8-sig'))}
st = {s: r['title'] for s, r in rows.items()}
ok = True
for slug in sys.argv[1:]:
    h = open(f'articles/{slug}/index.html', encoding='utf-8').read()
    t = re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', h))
    bad = [x for x in BADTOK if x in t]
    uls = [m for m in re.findall(r'<ul([^>]*)>', h)
           if 'quality-source-list' not in m and 'affiliate' not in m]
    r = rows[slug]
    faqs = [len(reader_facing_text(r, f'faq_{n}_answer', r[f'faq_{n}_answer'], slug_titles=st))
            for n in (1, 2, 3, 4) if r.get(f'faq_{n}_answer')]
    secs = [len(reader_facing_text(r, f'section_{i}_body', r[f'section_{i}_body'], slug_titles=st))
            for i in range(1, 8) if r.get(f'section_{i}_body')]
    faqmin, secmin = (min(faqs) if faqs else 0), (min(secs) if secs else 0)
    flag = '' if (not bad and not uls and faqmin >= 100 and secmin >= 180) else '  <<< FIX'
    if flag:
        ok = False
    print(f"{slug:30} bad:{bad} ul:{len(uls)} faqmin:{faqmin} secmin:{secmin}{flag}")
print('ALL CLEAN' if ok else 'NEEDS FIX')
sys.exit(0 if ok else 1)
