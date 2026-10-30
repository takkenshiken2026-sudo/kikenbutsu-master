#!/usr/bin/env python3
"""public_site/index.html のローカル参照（データ/設定JS・テーマCSS）に
内容ハッシュ版の ?v= を付けて、ブラウザ/CDN のキャッシュを確実に更新させる。

- 付けるのは public_site（配信物）の index.html だけ。ソースの index.html は変更しない。
- 版は各ファイルの内容ハッシュ。内容が変わったファイルの版だけが変わるので、
  未変更ファイルはキャッシュがそのまま効く（無駄な再ダウンロードを出さない）。
- GitHub Pages はクエリ文字列を無視して実体を返すため、挙動は一切変わらない。
- 乙4 を含む全ファイル共通の仕組みで、特定試験に依存しない。

prepare_public_site.sh（ビルド最終段）から public_site 配置後に呼ばれる。
"""
import hashlib
import pathlib
import re
import sys

# index.html が参照するローカルファイル（更新が反映されるべきもの）。
# ここに無いファイルはそのまま（キャッシュ制御を変えない）。
TARGETS = [
    "site-config.js",
    "exam-site-data-practice.js",
    "exam-site-data-past.js",
    "exam-site-data-ichimondou.js",
    "site-theme.css",
]


def short_hash(path: pathlib.Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:10]


def stamp(html: str, name: str, ver: str):
    """src="name" / href="name"（先頭 ./ 可、既存 ?v= 可）に ?v=ver を付け直す。"""
    # 属性名（src か href）と ./ の有無、既存クエリを許容して置換する。
    pat = re.compile(
        r'(?P<attr>src|href)="(?P<prefix>\./)?' + re.escape(name) + r'(?:\?v=[0-9a-f]+)?"'
    )
    return pat.subn(
        lambda m: f'{m.group("attr")}="{m.group("prefix") or ""}{name}?v={ver}"',
        html,
    )


def main() -> int:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public_site")
    index = out / "index.html"
    if not index.exists():
        print(f"stamp_asset_versions: {index} がありません", file=sys.stderr)
        return 1
    html = index.read_text(encoding="utf-8")
    done = []
    for name in TARGETS:
        f = out / name
        if not f.exists():
            continue
        ver = short_hash(f)
        html, n = stamp(html, name, ver)
        if n:
            done.append(f"{name}?v={ver}(x{n})")
    index.write_text(html, encoding="utf-8")
    print("stamp_asset_versions: " + (" / ".join(done) if done else "対象参照なし"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
