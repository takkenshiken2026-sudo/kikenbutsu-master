// Supabase Edge Function: post-comment（デプロイ名は swift-responder）
// 役割:
//   action="post"（既定): Turnstile 検証 → 自動モデレーション → 投稿を保存。
//       不適切・ボット・スパム・URL/個人情報を含む投稿は「保存前に拒否」します。
//       投稿者の uid を SHA-256 でハッシュ化した author_id を付与（なりすまし対策）。
//   action="delete": 管理キー(ADMIN_SECRET)を照合し、指定コメントを非表示化（ソフト削除）。
//
// デプロイ: Edge Functions → swift-responder → Code に貼り替えて Deploy（Verify JWT は OFF）
//
// 必要なシークレット（Edge Functions → Secrets）:
//   TURNSTILE_SECRET_KEY = Cloudflare Turnstile の Secret Key
//   ADMIN_SECRET         = 管理者削除に使う任意の長いパスワード
//   （SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY は自動で用意されます）

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const TURNSTILE_SECRET = Deno.env.get("TURNSTILE_SECRET_KEY")!;
const ADMIN_SECRET = Deno.env.get("ADMIN_SECRET") ?? "";

const ALLOWED_ORIGINS = [
  "https://kikenbutsu-master.jp",
  "https://www.kikenbutsu-master.jp",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
];

const CATEGORIES = ["comment", "qa", "taikenki"];

// 連投の上限（同一 author_id が過去60秒に投稿できる件数）
const RATE_WINDOW_SEC = 60;
const RATE_MAX = 4;

// 不適切・スパム語（小文字で照合）。必要に応じて増減してください。
const NG_WORDS = [
  // スパム系
  "副業", "稼げる", "稼ぐ", "儲かる", "儲け", "情報商材", "出会い", "出会系", "援交",
  "カジノ", "オンカジ", "賭博", "ギャンブル", "ビットコイン", "仮想通貨", "暗号資産",
  "必ず儲", "簡単に稼", "高収入", "日給", "即金", "line登録", "lineで", "テレグラム", "telegram", "whatsapp",
  // アダルト系
  "アダルト", "エロ", "av女優", "風俗", "セックス", "出会い系",
  // 攻撃・ハラスメント系
  "死ね", "殺す", "殺害", "きもい", "キモい", "気持ち悪い", "ブス", "デブ",
];

function corsHeaders(origin: string | null): Record<string, string> {
  const allow = origin && ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "authorization, apikey, content-type",
    "Vary": "Origin",
  };
}

function json(body: unknown, status: number, origin: string | null): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders(origin), "Content-Type": "application/json" },
  });
}

async function sha256hex(s: string): Promise<string> {
  const data = new TextEncoder().encode(s);
  const buf = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function restHeaders() {
  return {
    "apikey": SERVICE_ROLE,
    "Authorization": `Bearer ${SERVICE_ROLE}`,
    "Content-Type": "application/json",
    "Prefer": "return=representation",
  };
}

// 全角数字→半角（電話番号検出用）
function toHalfDigits(s: string): string {
  return s.replace(/[０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0));
}

// 自動モデレーション: 問題があれば理由(日本語)を返す。問題なければ null。
function moderate(name: string, body: string): string | null {
  const all = `${name}\n${body}`;
  const low = all.toLowerCase();

  // URL / リンク
  if (
    /https?:\/\//i.test(all) ||
    /www\.[a-z0-9-]+/i.test(low) ||
    /[a-z0-9-]+\.(com|net|org|jp|info|biz|co|me|xyz|shop|online|site|link|ru|cn|tk|work|click)(\/|\b)/i.test(low)
  ) {
    return "URLやリンクを含む投稿はできません。";
  }
  // メールアドレス
  if (/[\w.+-]+@[\w-]+\.[\w.-]+/.test(all)) {
    return "メールアドレスなどの個人情報は投稿できません。";
  }
  // 電話番号（日本の形式）
  const digits = toHalfDigits(all);
  if (/0\d{1,3}[-(\s]?\d{2,4}[-)\s]?\d{3,4}/.test(digits)) {
    return "電話番号などの個人情報は投稿できません。";
  }
  // 長い数字の並び（カード番号等）
  if (/\d{11,}/.test(digits.replace(/[\s-]/g, ""))) {
    return "個人情報と思われる数字の並びは投稿できません。";
  }
  // NGワード（不適切・スパム）
  for (const w of NG_WORDS) {
    if (low.includes(w)) return "不適切な表現やスパムと判断されたため投稿できません。";
  }
  // 同一文字の過剰な繰り返し
  if (/(.)\1{14,}/.test(body)) {
    return "同じ文字の繰り返しが多すぎます。";
  }
  // 記号・空白だけの投稿（文字や数字が1つも無い）
  const letters = (body.match(/[\p{L}\p{N}]/gu) || []).length;
  if (letters < 1) {
    return "文字での内容が含まれていません。";
  }
  return null;
}

// 連投（レート制限）チェック: true なら上限超過
async function isRateLimited(author_id: string | null): Promise<boolean> {
  if (!author_id) return false;
  const since = new Date(Date.now() - RATE_WINDOW_SEC * 1000).toISOString();
  const url = `${SUPABASE_URL}/rest/v1/comments?select=id&author_id=eq.${encodeURIComponent(author_id)}` +
    `&created_at=gte.${encodeURIComponent(since)}`;
  try {
    const res = await fetch(url, { headers: restHeaders() });
    if (!res.ok) return false;
    const rows = await res.json();
    return Array.isArray(rows) && rows.length >= RATE_MAX;
  } catch {
    return false;
  }
}

Deno.serve(async (req: Request) => {
  const origin = req.headers.get("Origin");

  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders(origin) });
  }
  if (req.method !== "POST") {
    return json({ error: "method not allowed" }, 405, origin);
  }

  let payload: Record<string, unknown>;
  try {
    payload = await req.json();
  } catch {
    return json({ error: "invalid json" }, 400, origin);
  }

  const action = String(payload.action ?? "post");

  // ============ 管理者削除（非表示化） ============
  if (action === "delete") {
    const admin = String(payload.admin ?? "");
    const id = String(payload.id ?? "");
    if (!ADMIN_SECRET || admin !== ADMIN_SECRET) {
      return json({ error: "管理キーが違います。" }, 403, origin);
    }
    if (!id) return json({ error: "id required" }, 400, origin);
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/comments?id=eq.${encodeURIComponent(id)}`,
      { method: "PATCH", headers: restHeaders(), body: JSON.stringify({ is_visible: false }) },
    );
    if (!res.ok) {
      return json({ error: "削除に失敗しました。", detail: await res.text() }, 500, origin);
    }
    return json({ ok: true }, 200, origin);
  }

  // ============ 投稿 ============
  const token = String(payload.token ?? "");
  const page_id = String(payload.page_id ?? "").trim().slice(0, 200);
  const category = CATEGORIES.includes(String(payload.category))
    ? String(payload.category)
    : "comment";
  let author_name = String(payload.author_name ?? "").trim().slice(0, 40);
  const body = String(payload.body ?? "").trim().slice(0, 2000);
  const uid = String(payload.uid ?? "").trim().slice(0, 128);

  if (!author_name) author_name = "匿名";
  if (!page_id) return json({ error: "page_id required" }, 400, origin);
  if (!body) return json({ error: "本文が空です。" }, 400, origin);
  if (!token) return json({ error: "認証（Turnstile）が未完了です。" }, 400, origin);

  // 1) Turnstile 検証（ボット対策。通らないと保存しない）
  const ip = req.headers.get("CF-Connecting-IP") ?? "";
  const form = new FormData();
  form.append("secret", TURNSTILE_SECRET);
  form.append("response", token);
  if (ip) form.append("remoteip", ip);

  let verifyOk = false;
  try {
    const verifyRes = await fetch(
      "https://challenges.cloudflare.com/turnstile/v0/siteverify",
      { method: "POST", body: form },
    );
    const verify = await verifyRes.json();
    verifyOk = verify.success === true;
  } catch {
    verifyOk = false;
  }
  if (!verifyOk) {
    return json({ error: "認証に失敗しました。時間をおいて、もう一度お試しください。" }, 403, origin);
  }

  // 2) 自動モデレーション（不適切・スパム・URL・個人情報を保存前に拒否）
  const ngReason = moderate(author_name, body);
  if (ngReason) {
    return json({ error: ngReason }, 422, origin);
  }

  // 3) 投稿者ID（uid を SHA-256 → 先頭16桁）
  const author_id = uid ? (await sha256hex(uid)).slice(0, 16) : null;

  // 4) 連投（スパム）制限
  if (await isRateLimited(author_id)) {
    return json({ error: "短時間に投稿が多すぎます。少し時間をおいてください。" }, 429, origin);
  }

  // 5) 保存（service_role は RLS をバイパス）
  const insertRes = await fetch(`${SUPABASE_URL}/rest/v1/comments`, {
    method: "POST",
    headers: restHeaders(),
    body: JSON.stringify({ page_id, category, author_name, body, author_id }),
  });

  if (!insertRes.ok) {
    return json({ error: "保存に失敗しました。", detail: await insertRes.text() }, 500, origin);
  }
  const rows = await insertRes.json();
  return json({ ok: true, comment: Array.isArray(rows) ? rows[0] : rows }, 200, origin);
});
