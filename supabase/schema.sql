-- 乙4マスター: ユーザー投稿テーブル（コメント / Q&A / 合格体験記）
-- 使い方: Supabase ダッシュボード → SQL Editor にこの全文を貼り付けて Run。
-- 何度実行しても壊れないように書いてあります（IF NOT EXISTS / DROP POLICY IF EXISTS）。

create extension if not exists pgcrypto;

create table if not exists public.comments (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  page_id     text not null,                       -- どのページの投稿か（例: articles/pass-score）
  category    text not null default 'comment'
                check (category in ('comment','qa','taikenki')),  -- コメント / 質問 / 体験記
  author_name text not null default '匿名'
                check (char_length(author_name) between 1 and 40),
  body        text not null
                check (char_length(body) between 1 and 2000),
  is_visible  boolean not null default true        -- false にすると公開画面から消える（＝管理削除）
);

create index if not exists comments_page_idx
  on public.comments (page_id, created_at desc);

-- 行レベルセキュリティ（RLS）を有効化
alter table public.comments enable row level security;

-- 【読み取り】表示中(is_visible=true)の投稿だけ、誰でも(anon)取得できる
drop policy if exists "read visible comments" on public.comments;
create policy "read visible comments"
  on public.comments
  for select
  to anon
  using (is_visible = true);

-- 【書き込み】anon 用の INSERT ポリシーは「あえて作らない」。
--   → anon キーを使った直接 INSERT は拒否される。
--   → 投稿は Edge Function（service_role）経由のみ。
--     service_role は RLS をバイパスするため、Turnstile 検証を通った投稿だけが保存される。
