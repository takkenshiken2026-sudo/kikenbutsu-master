-- 乙4マスター: ユーザー投稿テーブル（コメント / Q&A / 合格体験記）
-- 使い方: Supabase ダッシュボード → SQL Editor にこの全文を貼り付けて Run。
-- 何度実行しても壊れないように書いてあります（IF NOT EXISTS / DROP POLICY IF EXISTS）。
-- 既存テーブルに対して再実行すると、不足している列(author_id)が追加されます。

create extension if not exists pgcrypto;

create table if not exists public.comments (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  page_id     text not null,                       -- どのページの投稿か（例: articles/pass-score）
  category    text not null default 'comment'
                check (category in ('comment','qa','taikenki')),  -- コメント / 質問 / 体験記
  author_name text not null default '匿名'
                check (char_length(author_name) between 1 and 40),
  author_id   text,                                 -- 投稿者の識別ID（uidのSHA-256先頭16桁。なりすまし対策）
  body        text not null
                check (char_length(body) between 1 and 2000),
  is_visible  boolean not null default true        -- false にすると公開画面から消える（＝管理削除）
);

-- 既存テーブル向けのマイグレーション（新しい列を後から追加）
alter table public.comments add column if not exists author_id text;

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

-- 【書き込み・更新】anon 用のポリシーは「あえて作らない」。
--   → anon キーを使った直接 INSERT / UPDATE は拒否される。
--   → 投稿・削除(非表示化)は Edge Function（service_role）経由のみ。
--     投稿は Turnstile 検証を、削除は管理キー照合を通ったものだけが反映される。
