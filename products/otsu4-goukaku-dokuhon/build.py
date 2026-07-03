#!/usr/bin/env python3
# 危険物乙4「合格読本」合本ジェネレータ
# 3冊（数字/ひっかけ/直前）の検証済み本文を取り込み、front matter・部扉・演習編・奥付を付けて1冊に。
# 使い方: python3 products/otsu4-goukaku-dokuhon/build.py
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def rd(slug): return (ROOT/f"products/{slug}/index.html").read_text(encoding="utf-8")
A=rd("otsu4-numbers-cheatsheet"); B=rd("otsu4-hikkake-selection"); C=rd("otsu4-chokuzen-summary")

partA=A[A.index('<!-- ===== CH1'):A.index('<!-- ===== FOOT')]
partA=partA.replace(
 '数字が身についたら、姉妹編「頻出ひっかけ厳選35」「直前3日 総まとめ」で仕上げてください。',
 '数字が身についたら、第2部「見抜く力」で正誤問題のワナに、第3部「直前と当日」で仕上げの段取りに進んでください。')
partA=partA.replace('数値の丸暗記は別冊「数字丸暗記シート」と併用を。','')
partB=B[B.index('<div class="pad">')+len('<div class="pad">'):B.index('<footer class="src">')]
partC=C[C.index('<div class="pad">')+len('<div class="pad">'):C.index('<footer class="src">')]
partC=partC.replace('本書の','本書 第1部・第2部の')

CSS = r'''
:root{
  --ink:#211c18; --sub:#6b625b; --paper:#faf8f4; --card:#ffffff; --line:#e7e1d8; --rule:#d8cfc2;
  --accent:#9c2b28; --gold:#a9803f; --hide:#9c2b28; --day:#4a6f43;
  --ng:#9c2b28; --ok:#1f7a48; --law:#9c2b28; --chem:#2f5f86; --fire:#a9803f;
  --serif:"Noto Serif CJK JP","Noto Serif JP",serif;
  --sans:"Noto Sans CJK JP","Noto Sans JP","Hiragino Kaku Gothic ProN",sans-serif;
}
*{box-sizing:border-box} html,body{margin:0;padding:0}
body{font-family:var(--sans);color:var(--ink);background:#eee9e1;line-height:1.95;font-size:15px;letter-spacing:.01em;
  -webkit-print-color-adjust:exact;print-color-adjust:exact}
.book{max-width:720px;margin:0 auto;background:var(--paper);box-shadow:0 6px 40px rgba(0,0,0,.12)}
.pad{padding:0 46px 24px}
@media(max-width:560px){.pad{padding:0 22px 24px}}
.toolbar{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.94);backdrop-filter:blur(6px);
  border-bottom:1px solid var(--line);padding:9px 16px;display:flex;gap:9px;align-items:center;flex-wrap:wrap}
.toolbar .t{font-family:var(--serif);font-weight:700;color:var(--accent);font-size:14px;margin-right:auto}
.btn{appearance:none;border:1px solid var(--accent);background:var(--accent);color:#fff;font-family:var(--sans);
  font-weight:600;font-size:13px;padding:7px 13px;border-radius:6px;cursor:pointer}
.btn.ghost{background:#fff;color:var(--accent)}
.cover{padding:80px 46px 60px;background:radial-gradient(120% 80% at 50% -10%, #fbf7f0 0%, var(--paper) 60%);text-align:center;border-bottom:1px solid var(--line)}
.cover .brand{font-size:12px;letter-spacing:.34em;color:var(--gold);font-weight:600;margin-bottom:26px}
.cover .exam{font-size:13px;color:var(--sub);letter-spacing:.12em;margin-bottom:16px}
.cover h1{font-family:var(--serif);font-weight:900;font-size:46px;line-height:1.25;margin:0}
.cover .sub{font-family:var(--serif);font-size:17px;color:var(--accent);margin:14px 0 0;font-weight:700}
.cover .ornament{width:56px;height:2px;background:var(--gold);margin:30px auto 0}
.cover .parts{margin:26px auto 0;max-width:440px;text-align:left;font-size:13px;color:var(--sub);line-height:2.0}
.cover .parts b{font-family:var(--serif);color:var(--ink)}
.cover .ed{margin-top:26px;font-size:12px;color:var(--sub);letter-spacing:.14em}
.intro-page{padding:44px 46px 8px}
.intro-page h2{font-family:var(--serif);font-size:22px;margin:0 0 14px;letter-spacing:.02em}
.intro-page p{margin:12px 0;font-size:14.5px}
.intro-page .how{background:#f4efe7;border-radius:9px;padding:14px 18px;margin:18px 0;font-size:13.5px}
.intro-page .how b{font-family:var(--serif);color:var(--accent)}
.toc{padding:34px 46px 6px}
.toc h2{font-family:var(--serif);font-size:15px;letter-spacing:.28em;color:var(--sub);font-weight:700;margin:0 0 16px;text-align:center}
.toc .pt{font-family:var(--serif);font-weight:700;color:var(--accent);font-size:13px;letter-spacing:.1em;margin:16px 0 4px;border-bottom:1px solid var(--rule);padding-bottom:5px}
.toc ol{list-style:none;margin:0 0 6px;padding:0}
.toc li{display:flex;align-items:baseline;gap:12px;padding:5px 0;font-size:13.5px}
.toc li .d{color:var(--sub);font-size:12px;margin-left:auto}
.divider{text-align:center;padding:60px 46px 46px;border-top:1px solid var(--line);margin-top:20px}
.divider .pn{font-family:var(--serif);font-size:13px;letter-spacing:.3em;color:var(--gold);font-weight:700}
.divider h2{font-family:var(--serif);font-weight:900;font-size:32px;margin:12px 0 0;letter-spacing:.03em}
.divider p{max-width:460px;margin:16px auto 0;font-size:13.5px;color:var(--sub);text-align:left;line-height:1.95}
.divider .om{width:44px;height:2px;background:var(--gold);margin:18px auto 0}
/* Part I (数字編/A) */
.chapter{padding:44px 46px 22px}
@media(max-width:560px){.chapter,.intro-page,.cover,.toc,.divider{padding-left:22px;padding-right:22px}}
.ch-kick{display:flex;align-items:center;gap:14px;margin-bottom:6px}
.ch-num{font-family:var(--serif);font-weight:900;font-size:15px;color:#fff;background:var(--accent);width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex:none}
.ch-tag{font-size:11px;letter-spacing:.2em;color:var(--gold);font-weight:700}
.chapter h2{font-family:var(--serif);font-weight:900;font-size:25px;line-height:1.4;margin:2px 0 14px}
.lead{font-size:15px;color:#3a332e;line-height:2.0;margin:0 0 4px}
.lead .em{color:var(--accent);font-weight:700}
h3{font-family:var(--serif);font-size:17px;font-weight:700;margin:26px 0 8px;padding-left:12px;border-left:4px solid var(--accent)}
p{margin:12px 0}
.tbl{margin:16px 0;border:1px solid var(--line);border-radius:8px;overflow:hidden}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line)}
thead th{background:#efe7db;color:#5a4d3c;font-weight:700;font-size:12.5px}
tbody tr:last-child td{border-bottom:none}
tbody tr:nth-child(even){background:#fcfaf6}
td.c,th.c{text-align:center;white-space:nowrap}
.grp{font-weight:700;background:#f6f0e7 !important}
.h{color:var(--hide);font-weight:800;font-family:var(--serif)}
body.masked .h{background:var(--hide);color:var(--hide);border-radius:2px}
body.masked .h::selection{background:transparent}
.why,.trap,.ex{border-radius:9px;padding:15px 18px;margin:18px 0;font-size:13.5px;line-height:1.9}
.why{background:#f1f4f6;border:1px solid #dde6ea}
.why .lbl{display:block;font-family:var(--serif);font-weight:700;color:#3a6079;font-size:13px;margin-bottom:4px}
.trap{background:#fbf1ec;border:1px solid #f0d8cd}
.trap .lbl{display:block;font-family:var(--serif);font-weight:700;color:var(--accent);font-size:13px;margin-bottom:4px}
.ex{background:#fbf9f3;border:1px solid #e9e0cb}
.ex .lbl{display:block;font-family:var(--serif);font-weight:700;color:var(--gold);font-size:13px;margin-bottom:6px}
.ex .q{font-weight:600;margin:0 0 8px}
.ex .opt{margin:2px 0 2px 2px;color:#4a423b;font-size:13px}
.ex .ans{margin-top:9px;padding-top:9px;border-top:1px dashed var(--rule)}
.ex .ans b{color:var(--accent)}
.callout{font-family:var(--serif);font-size:16px;line-height:1.9;color:#4a2f2e;background:#f7efe6;border-left:4px solid var(--gold);padding:14px 18px;margin:20px 0;font-weight:600}
/* 図解 */
.fig{background:#fbf9f4;border:1px solid #e9e0cb;border-radius:9px;padding:16px 18px;margin:18px 0}
.fig .cap{font-size:12px;color:var(--sub);text-align:center;margin-top:10px;line-height:1.7}
.fig .ttl{font-family:var(--serif);font-weight:700;color:var(--accent);font-size:14px;margin:0 0 8px}
.ok2{color:#1f7a48;font-weight:800} .no2{color:#9c2b28;font-weight:800}
.flow{display:flex;flex-wrap:wrap;gap:6px;align-items:center;justify-content:center}
.flow .chip{background:#fff;border:1px solid var(--line);border-radius:7px;padding:6px 10px;font-size:12px;text-align:center;line-height:1.5}
.flow .chip b{font-family:var(--serif);color:var(--accent);display:block;font-size:12.5px}
.flow .arw{color:var(--gold);font-weight:700}
.bars{display:flex;flex-direction:column;gap:7px}
.bars .row{display:flex;align-items:center;gap:10px;font-size:12.5px}
.bars .lb{flex:0 0 92px;text-align:right;color:#4a423b}
.bars .track{flex:1;background:#efe7db;border-radius:4px;overflow:hidden;height:15px}
.bars .bar{display:block;height:15px;background:var(--accent);border-radius:4px}
.bars .v{flex:0 0 80px;font-family:var(--serif);color:var(--accent);font-weight:700;font-size:12.5px}
.tank{max-width:380px;margin:4px auto 0;border:2px solid #9bb7c7;border-top:none;border-radius:0 0 10px 10px;background:linear-gradient(#eaf3f8,#d3e6f0);padding:8px 10px 12px}
.tank .wl{border-top:2px dashed #6f9ab2;text-align:right;font-size:10.5px;color:#4f7387;margin:0 -10px 8px;padding:2px 8px 0}
.tank .float{background:#fff;border:1px solid var(--line);border-radius:6px;padding:6px 9px;font-size:11.5px;line-height:1.6}
.tank .sink{background:#f3ddd9;border:1px solid #e2b7af;border-radius:6px;padding:6px 9px;font-size:11.5px;margin-top:20px;line-height:1.6}
.goro{background:#f7efe6;border-left:4px solid var(--gold);border-radius:0 8px 8px 0;padding:12px 16px;margin:16px 0;font-size:13.5px;line-height:1.9}
.goro .lbl{display:block;font-family:var(--serif);font-weight:700;color:#8a5a1f;font-size:12.5px;margin-bottom:3px;letter-spacing:.04em}
.goro .big{font-family:var(--serif);font-size:15px;color:var(--accent);font-weight:700}
/* Part II (見抜く編/B) */
.part2 .subject{margin:40px 0 4px;display:flex;align-items:baseline;gap:12px}
.part2 .subject h2{font-family:var(--serif);font-weight:900;font-size:22px;margin:0;flex:1;border-bottom:2px solid var(--law);padding-bottom:8px}
.part2 .subject .cut{font-size:11.5px;font-weight:700;color:#fff;background:var(--law);border-radius:999px;padding:3px 11px;white-space:nowrap}
.part2 .subject.chem h2{border-color:var(--chem)} .part2 .subject.chem .cut{background:var(--chem)}
.part2 .subject.fire h2{border-color:var(--fire)} .part2 .subject.fire .cut{background:var(--fire)}
.part2 p.lead{font-size:14px;color:#3a332e;line-height:1.95;margin:14px 0 6px}
.part2 .trap{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:15px 18px;margin:13px 0;box-shadow:0 1px 2px rgba(0,0,0,.02)}
.part2 .trap .no{display:inline-block;font-family:var(--serif);font-weight:700;font-size:12px;color:#fff;background:var(--law);border-radius:5px;padding:2px 9px}
.part2 .chem .trap .no{background:var(--chem)} .part2 .fire .trap .no{background:var(--fire)}
.part2 .trap .topic{font-weight:700;font-size:12.5px;color:var(--sub);margin-left:9px}
.part2 .trap p{margin:8px 0 0}
.part2 .ng{color:var(--ng);font-weight:700;font-size:15px;line-height:1.7}
.part2 .ng::before{content:"\2715 ";font-weight:800}
.part2 .ok{font-size:14.5px;line-height:1.85}
.part2 .ok .lead{display:none}
.part2 .ok .body::before{content:"\25cb ";color:var(--ok);font-weight:800}
.part2 .why{font-size:13px;color:#4a423b;background:#f4efe7;border:none;border-radius:7px;padding:9px 12px;margin-top:9px;line-height:1.8}
.part2 .why b{color:var(--accent);font-family:var(--serif)}
body.masked .part2 .ok .body{background:var(--hide);color:var(--hide);border-radius:2px}
body.masked .part2 .ok .body::before{color:var(--hide)}
/* Part III (直前編/C) */
.part3 .chap{margin:40px 0 6px}
.part3 .chap .kick{display:flex;align-items:center;gap:12px}
.part3 .chap .n{font-family:var(--serif);font-weight:900;font-size:14px;color:#fff;background:var(--accent);width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex:none}
.part3 .chap h2{font-family:var(--serif);font-weight:900;font-size:22px;margin:4px 0 0}
.part3 .chap .lead{font-size:14px;color:#3a332e;line-height:1.95;margin:12px 0 4px}
.part3 .plan{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:16px 0}
@media(max-width:560px){.part3 .plan{grid-template-columns:1fr 1fr}.part3 .grid2{grid-template-columns:1fr}}
.part3 .day{border:1px solid var(--line);border-radius:9px;padding:12px;background:#f5f7f3}
.part3 .day h3{font-family:var(--serif);margin:0 0 6px;font-size:14px;color:var(--day);border-bottom:1.5px solid var(--day);padding-bottom:4px;padding-left:0;border-left:none}
.part3 .day ul{margin:0;padding-left:16px;font-size:12.5px;line-height:1.7;color:#3f3a34}
.part3 .band{display:inline-block;font-family:var(--serif);font-weight:700;font-size:13px;color:#fff;background:var(--law);border-radius:5px;padding:3px 12px;margin:18px 0 6px;letter-spacing:.06em}
.part3 .band.chem{background:var(--chem)} .part3 .band.fire{background:var(--fire)} .part3 .band.day{background:var(--day)} .part3 .band.dk{background:#7a3b3a}
.part3 .final{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 14px;margin:7px 0;font-size:14px;line-height:1.85}
.part3 .final b{font-family:var(--serif);color:var(--accent)}
.part3 .grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px 22px}
.part3 ul.check{list-style:none;margin:6px 0 2px;padding:0}
.part3 ul.check li{position:relative;padding:6px 0 6px 30px;font-size:13.5px;border-bottom:1px dotted var(--rule);line-height:1.7}
.part3 ul.check li::before{content:"";position:absolute;left:2px;top:9px;width:15px;height:15px;border:2px solid var(--accent);border-radius:3px}
.part3 ul.check.g li::before{border-color:var(--day)} .part3 ul.check.dk li::before{border-color:#7a3b3a}
.part3 ul.check b{color:var(--accent);font-family:var(--serif)}
.part3 .warn{background:#f7efe6;border-left:4px solid var(--gold);border-radius:0 8px 8px 0;padding:12px 16px;margin:16px 0;font-size:13.5px;line-height:1.85}
.part3 .warn b{font-family:var(--serif);color:#8a5a1f}
.part3 .memo{background:#f1f4f6;border-left:4px solid var(--chem);border-radius:0 8px 8px 0;padding:12px 16px;margin:16px 0;font-size:13.5px;line-height:1.85}
.part3 .memo b{font-family:var(--serif);color:#2f5f86}
/* Part IV (演習編) */
.part4 .sband{font-family:var(--serif);font-weight:900;font-size:19px;color:var(--accent);margin:34px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--accent)}
.part4 .sband.chem{color:var(--chem);border-color:var(--chem)} .part4 .sband.fire{color:var(--fire);border-color:var(--fire)}
.qz{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:15px 18px;margin:12px 0;break-inside:avoid}
.qz .stem{font-weight:700;font-size:14.5px;margin:0 0 8px;line-height:1.8}
.qz .stem .qn{font-family:var(--serif);color:#fff;background:var(--accent);border-radius:5px;padding:1px 8px;font-size:12px;margin-right:8px}
.qz ol.opts{margin:0;padding-left:0;list-style:none;counter-reset:o}
.qz ol.opts li{counter-increment:o;position:relative;padding:3px 0 3px 26px;font-size:13.5px;line-height:1.7}
.qz ol.opts li::before{content:"\ff08"counter(o)"\ff09";position:absolute;left:0;color:var(--sub);font-size:12px}
.qz .sol{margin-top:10px;padding-top:9px;border-top:1px dashed var(--rule);font-size:13px;line-height:1.85;color:#3f3a34}
.qz .sol .a{font-family:var(--serif);font-weight:700;color:var(--accent);margin-right:6px}
body.masked .qz .sol .exp{background:var(--hide);color:var(--hide);border-radius:2px}
.okuzuke{padding:40px 46px 50px;border-top:1px solid var(--line);background:#f6f1ea;margin-top:24px;text-align:center}
.okuzuke .l{font-family:var(--serif);font-size:12px;letter-spacing:.3em;color:var(--gold);margin-bottom:14px}
.okuzuke h2{font-family:var(--serif);font-size:20px;margin:0 0 6px}
.okuzuke p{font-size:12px;color:var(--sub);line-height:1.9;margin:5px 0}
.okuzuke .src{margin-top:18px;text-align:left;font-size:11.5px;color:var(--sub);line-height:1.8}
.okuzuke a{color:#2f5f86}
@media print{
  body{background:#fff;font-size:11.5pt}.toolbar{display:none}
  .book{max-width:100%;box-shadow:none}
  .cover{padding-top:40px}.intro-page,.toc{break-inside:avoid}.toc{break-after:page}
  .divider{break-before:page}
  .chapter,.part2 .subject,.part3 .chap{break-inside:avoid}
  .trap,.ex,.why,.callout,.qz,.tbl,.fig,.part3 .plan,.part3 .final,.part2 .trap{break-inside:avoid}
  h2,h3{break-after:avoid}
  a{color:inherit;text-decoration:none}
  @page{size:A4;margin:16mm 15mm}
}
'''

def q(qn,stem,opts,ans,exp):
    lis="".join(f"<li>{o}</li>" for o in opts)
    return (f'<div class="qz"><p class="stem"><span class="qn">{qn}</span>{stem}</p>'
            f'<ol class="opts">{lis}</ol>'
            f'<div class="sol"><span class="a">正解 {ans}</span><span class="exp">{exp}</span></div></div>')

LAW=[
 q("法01","灯油の指定数量として正しいものはどれか。",["50L","200L","400L","1,000L","2,000L"],"（4）","灯油は第二石油類（非水溶性）で1,000L。200Lは第一石油類のガソリンの値で、混同が頻出。"),
 q("法02","ガソリン200Lと軽油3,000Lを同一の場所で貯蔵するとき、指定数量の倍数はいくつか。",["2.0倍","3.0倍","4.0倍","5.0倍","16倍"],"（3）","ガソリン200/200＝1.0倍、軽油3,000/1,000＝3.0倍。複数品目は各倍数を合計して1.0＋3.0＝4.0倍。"),
 q("法03","製造所と学校（多数の人を収容する施設）との間に必要な保安距離はどれか。",["10m以上","20m以上","30m以上","50m以上","70m以上"],"（3）","学校・病院・劇場等は30m以上。住居10m・高圧ガス施設20m・重要文化財50mと区別して覚える。"),
 q("法04","次のうち、保安距離を必要としない製造所等はどれか。",["製造所","屋内貯蔵所","屋外タンク貯蔵所","一般取扱所","給油取扱所"],"（5）","保安距離が必要なのは製造所・屋内貯蔵所・屋外貯蔵所・屋外タンク貯蔵所・一般取扱所の5施設。給油取扱所は独自基準で不要。"),
 q("法05","予防規程について、正しいものはどれか。",["作成すれば届出も認可も不要","市町村長等の認可を受ける","消防長への報告のみでよい","甲種取扱者が承認する","国が一律に定める"],"（2）","予防規程は市町村長等の認可が必要。変更のときも認可を受ける。届出では足りない。"),
 q("法06","免状の記載事項（氏名・本籍など）に変更が生じたときの手続きはどれか。",["再交付","書換え","返納","更新","届出不要"],"（2）","記載事項の変更は書換え。再交付は亡失・滅失・汚損・破損のとき。両者は別手続き。"),
 q("法07","危険物保安監督者に関する記述として正しいものはどれか。",["乙4に合格すれば直ちに選任できる","6か月以上の実務経験が必要","丙種でも全類の監督ができる","無資格者でも選任できる","選任に届出は不要"],"（2）","保安監督者は甲種または当該類の乙種で、かつ6か月以上の実務経験が必要。選任・解任は市町村長等へ届出。"),
 q("法08","丙種危険物取扱者が取り扱うことができないものはどれか。",["ガソリン","灯油","軽油","重油","アルコール類"],"（5）","丙種はガソリン・灯油・軽油・第三石油類（重油等）・第四石油類・動植物油類に限られる。アルコール類・特殊引火物・ベンゼン等は不可。"),
 q("法09","定期点検の記録の保存期間として正しいものはどれか。",["6か月","1年","3年","5年","10年"],"（3）","定期点検は1年に1回以上実施し、記録は3年間保存する。実施周期（1年）と保存期間（3年）を混同しない。"),
 q("法10","移動タンク貯蔵所（タンクローリー）のタンク容量の上限はどれか。",["4,000L以下","10,000L以下","20,000L以下","30,000L以下","制限なし"],"（4）","容量は30,000L以下。内部は4,000L以下ごとに間仕切り、2,000L以上の室には防波板を設ける。"),
]
CHEM=[
 q("物01","引火点の説明として正しいものはどれか。",["火源がなくても発火する最低温度","外部の火源で燃え出す最低温度","液体が沸騰する温度","蒸気が発生し始める温度","燃焼が終わる温度"],"（2）","引火点は外部の火源を近づけたとき燃え出す最低温度。火源なしで発火する最低温度は発火点で、別概念。"),
 q("物02","第4類危険物のうち、発火点が最も低いものはどれか。",["ガソリン","灯油","二硫化炭素","エタノール","重油"],"（3）","二硫化炭素の発火点は約90℃で第4類最低。水より重い（比重1.3）点も併せて頻出。"),
 q("物03","ガソリンと灯油の発火点の関係として正しいものはどれか。",["ガソリンの方が低い","ほぼ同じ","ガソリンの方が高い","灯油には発火点がない","比較できない"],"（3）","発火点はガソリン約300℃＞灯油・軽油約220℃。引火点はガソリンが低いが、発火点は逆に高い。"),
 q("物04","次のうち、水より重い（液比重が1より大きい）第4類危険物はどれか。",["ガソリン","灯油","エタノール","二硫化炭素","アセトン"],"（4）","二硫化炭素は比重約1.3で水より重い。第4類の大半は水より軽い（比重1未満）ため例外として覚える。"),
 q("物05","第4類危険物の蒸気の性質として正しいものはどれか。",["空気より軽く上方に拡散する","空気より重く低所に滞留する","空気と同じ重さ","水に溶けて消える","無臭で無害"],"（2）","第4類の蒸気は空気より重く（蒸気比重1超）、ピットや床面付近の低所に滞留する。換気は低所を意識する。"),
 q("物06","燃焼範囲（爆発範囲）についての記述として正しいものはどれか。",["範囲が狭いほど危険","上限値が高いほど安全","下限値が低いほど危険","範囲は温度で決まらない","下限値以下でよく燃える"],"（3）","下限値が低いほど、また範囲が広いほど危険。わずかな蒸気濃度でも燃えるため。下限未満・上限超では燃焼しない。"),
 q("物07","静電気による災害を防ぐ方法として適切なものはどれか。",["注液の流速を速くする","容器を絶縁して浮かせる","接地（アース）して除去する","湿度を下げる","乾いた布で強くこする"],"（3）","帯電を防ぐには接地して電荷を逃がし、流速を遅くする。ガソリン等は電気を通しにくく帯電しやすい。"),
 q("物08","ガソリンの品名の区分として正しいものはどれか。",["特殊引火物","第一石油類","第二石油類","アルコール類","動植物油類"],"（2）","ガソリンは第一石油類（引火点21℃未満）。引火点が低いからと特殊引火物に分類するのは誤り。"),
 q("物09","第一石油類の引火点の範囲として正しいものはどれか。",["21℃未満","21℃以上70℃未満","70℃以上200℃未満","200℃以上250℃未満","250℃以上"],"（1）","第一石油類は引火点21℃未満。以降、第二21〜70未満、第三70〜200未満、第四200〜250未満と続く。"),
]
FIRE=[
 q("性01","第4類危険物の火災に対して、一般に不適とされる消火方法はどれか。",["泡消火","二酸化炭素消火","粉末消火","棒状注水","霧状水"],"（4）","多くは水より軽く水に浮くため、棒状注水は火面を広げて不適。泡・粉末・二酸化炭素等で窒息消火する。"),
 q("性02","アルコールなど水溶性液体の火災に有効な消火剤はどれか。",["普通の泡消火剤","耐アルコール泡（水溶性液体用泡）","棒状注水","乾燥砂のみ","効果的な薬剤はない"],"（2）","水溶性液体は普通泡を溶かして消してしまうため、耐アルコール泡を用いる。"),
 q("性03","電気設備の火災に対して不適な消火方法はどれか。",["二酸化炭素消火","粉末消火","棒状注水","霧状水","不活性ガス消火"],"（3）","棒状注水は感電の恐れがあり不適。二酸化炭素・粉末・霧状水などを用いる。"),
 q("性04","マグネシウム等の金属火災の消火方法として適切なものはどれか。",["大量の注水","泡消火","乾燥砂・金属火災用粉末","二酸化炭素","霧状水"],"（3）","注水すると水と反応し可燃性ガス（水素等）を発生して危険。乾燥砂や金属火災用粉末を用いる。"),
 q("性05","消火の三要素に当てはまらないものはどれか。",["除去","窒息","冷却","加圧","（すべて三要素である）"],"（4）","消火の三要素は除去・窒息・冷却。加圧は含まれない。第4類では窒息が中心となる。"),
 q("性06","消火設備の区分について、消火器（小型）は第何種に区分されるか。",["第1種","第2種","第3種","第4種","第5種"],"（5）","小型消火器・乾燥砂等は第5種、大型消火器は第4種。第1種は屋内・屋外消火栓。"),
 q("性07","二酸化炭素消火剤の主な消火作用はどれか。",["冷却","除去","窒息","分解","加圧"],"（3）","二酸化炭素は酸素濃度を下げる窒息（希釈）作用が主体。泡は窒息＋冷却で作用が異なる。"),
 q("性08","危険物が漏えいしたときの初動として不適切なものはどれか。",["着火源を除去する","流出の拡大を防ぐ","低所の窓を閉め切って密閉する","安全に換気する","土のう等で流出を止める"],"（3）","蒸気は低所に滞留するため密閉は危険。着火源の除去・拡大防止・安全な換気が先。"),
]
def block(t,cls,items): return f'<div class="sband {cls}">{t}</div>\n'+"\n".join(items)

FRONT=f'''<body>
<div class="toolbar">
  <span class="t">危険物乙4 合格読本</span>
  <button class="btn" id="mask">🟥 数字・答えを隠す</button>
  <button class="btn ghost" onclick="window.print()">🖨 PDFで保存</button>
</div>
<div class="book">
<div class="cover">
  <div class="brand">乙 4 マ ス タ ー</div>
  <div class="exam">危険物取扱者試験（乙種第4類）</div>
  <h1>合格読本</h1>
  <div class="sub">読んで・覚えて・解く ― 一冊で仕上げる</div>
  <div class="ornament"></div>
  <div class="parts">
    <b>第1部</b>　数字編 ― 指定数量・性状・法令数値を理解して覚える<br>
    <b>第2部</b>　見抜く編 ― 合否を分けるひっかけ35<br>
    <b>第3部</b>　直前・当日編 ― 3日プランと本番戦術<br>
    <b>第4部</b>　演習編 ― 解説付き問題27問
  </div>
  <div class="ed">2026年度版 ／ 全内容 公式・一次情報で確認</div>
</div>
<div class="intro-page">
  <h2>はじめに</h2>
  <p>危険物乙4は、受験資格が不要で誰でも挑戦できる一方、<strong>3科目それぞれで60%以上</strong>という足切りがあり、「合計点は足りるのに1科目で落ちる」ことが珍しくありません。裏を返せば、<strong>出るところを外さず、取り違えのワナに引っかからず、当日を落ち着いて迎える</strong>――この3つを押さえれば十分に届く試験です。</p>
  <p>本書はその3つを、<strong>読む（第1部）・見抜く（第2部）・仕上げる（第3部）・解く（第4部）</strong>の順で一冊にまとめました。数字は丸暗記の一歩手前にある「なぜその数字か」を図解と語呂で補い、正誤問題は「誤文のどこが罠か」を言語化し、最後は解説付きの演習で仕上げます。</p>
  <div class="how"><b>この本の使い方</b><br>① まず通読して全体像をつかむ　② 上部の「数字・答えを隠す」ボタン（印刷時は赤シート）で赤い数字・正答を消し、言えるか確認　③ 第4部の演習で到達度を測る　④ 直前期は第3部と各部の要点だけを繰り返す。</div>
</div>
<nav class="toc">
  <h2>目 次</h2>
  <div class="pt">第1部　数字編</div>
  <ol>
    <li>指定数量 ― まず、ここで点を取る<span class="d">最重要</span></li>
    <li>品名の区分と引火点<span class="d">21・70・200・250</span></li>
    <li>主要品目の性状<span class="d">引火点と比重</span></li>
    <li>発火点という落とし穴<span class="d">逆転に注意</span></li>
    <li>法令に出てくる数値<span class="d">距離・周期・容量</span></li>
    <li>試験そのものの数字<span class="d">合格ライン</span></li>
  </ol>
  <div class="pt">第2部　見抜く編（ひっかけ35）</div>
  <ol><li>法令・制度<span class="d">ワナ15</span></li><li>物理・化学<span class="d">ワナ10</span></li><li>性質・火災予防・消火<span class="d">ワナ10</span></li></ol>
  <div class="pt">第3部　直前・当日編</div>
  <ol><li>直前3日の過ごし方／最終確認／チェックリスト／当日／本番の解き方<span class="d">仕上げ</span></li></ol>
  <div class="pt">第4部　演習編（解説付き27問）</div>
  <ol><li>法令10問／物化9問／性消8問<span class="d">到達度チェック</span></li></ol>
</nav>
<div class="divider"><div class="pn">第 1 部</div><h2>数字編</h2><div class="om"></div>
  <p>指定数量・引火点・比重・法令の数値を「理解して」覚える。丸暗記の一歩手前にある理屈を図解と語呂で補い、忘れにくく取り違えにくい形で定着させます。</p></div>
'''
PART2='''
<div class="divider"><div class="pn">第 2 部</div><h2>見抜く編</h2><div class="om"></div>
  <p>乙4の正誤問題は「もっともらしい誤文」を見抜けるかで差がつきます。頻出のワナ35を、誤文→正しくは→見抜き方の3段で。</p></div>
<div class="part2"><div class="pad">
'''+partB+'</div></div>'
PART3='''
<div class="divider"><div class="pn">第 3 部</div><h2>直前・当日編</h2><div class="om"></div>
  <p>直前期の段取り、絶対に落とせない最終確認、当日の持ち物と本番の解き方。仕上げの一部です。</p></div>
<div class="part3"><div class="pad">
'''+partC+'</div></div>'
PART4=('''
<div class="divider"><div class="pn">第 4 部</div><h2>演習編</h2><div class="om"></div>
  <p>解説付きの27問で到達度を測ります。各科目60%（法令9/15・物化6/10・性消6/10）が合格ライン。まず解いてから解説を読み、間違えた論点は第1〜3部へ戻って確認しましょう。「数字・答えを隠す」で解説を伏せれば、繰り返し演習できます。</p></div>
<div class="part4"><div class="pad">
'''+block("法令・制度（10問）","",LAW)+"\n"+block("物理・化学（9問）","chem",CHEM)+"\n"+block("性質・火災予防・消火（8問）","fire",FIRE)+"\n</div></div>")
OKU='''
<div class="okuzuke">
  <div class="l">奥 付</div>
  <h2>危険物乙4 合格読本</h2>
  <p>2026年度版　／　発行：乙4マスター（kikenbutsu-master.jp）</p>
  <p>読む・見抜く・仕上げる・解くの4部構成／全内容を公式・一次情報で確認</p>
  <div class="src">
    <p><b>出典・正確性について</b>：本書の数値・制度・当日ルールは、一般財団法人 消防試験研究センターの公表情報、消防法・危険物の規制に関する政令／規則を起点に、消防庁および自治体・危険物安全協会の公表資料で裏取りしています。主な参照：<a href="https://www.shoubo-shiken.or.jp/kikenbutsu/">消防試験研究センター 危険物取扱者</a>、<a href="https://www.shoubo-shiken.or.jp/kikenbutsu/annai/preparation.html">同 注意事項</a>、<a href="https://www.fdma.go.jp/">消防庁</a>。</p>
    <p>※ 試験制度・法令・手数料・当日ルールは改定されることがあります。受験・実務の判断は必ず公式の最新情報でご確認ください。引火点・発火点・比重は物質・出典により幅があり、試験で問われる代表値を掲載しています。本書は学習補助資料であり、試験主催者・国の機関とは関係ありません。無断転載・再配布を禁じます。</p>
    <p>© 2026 乙4マスター</p>
  </div>
</div>
'''
SCRIPT='''
</div>
<script>
  var btn=document.getElementById('mask');
  btn.addEventListener('click',function(){
    var on=document.body.classList.toggle('masked');
    btn.textContent=on?'👁 表示に戻す':'🟥 数字・答えを隠す';
  });
</script>
</body></html>
'''
HEAD='<!DOCTYPE html>\n<html lang="ja">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>危険物乙4 合格読本｜乙4マスター</title>\n<style>'+CSS+'</style>\n</head>\n'
out=HEAD+FRONT+partA+PART2+PART3+PART4+OKU+SCRIPT
(ROOT/"products/otsu4-goukaku-dokuhon/index.html").write_text(out,encoding="utf-8")
assert out.count('class="qz"')==27
assert out.count('class="fig"')>=13   # Part1:5 + Part2:6 + Part3:2
print("built:",len(out),"bytes / qz27 / fig",out.count('class=\"fig\"'))
