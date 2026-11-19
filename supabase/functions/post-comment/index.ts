// Supabase Edge Function: post-comment
// 役割: Cloudflare Turnstile を検証 → OK なら comments テーブルに1件保存する「門番」。
//
// デプロイ（どちらか）:
//   A) ダッシュボード: Edge Functions → Deploy a new function → 名前 "post-comment"
//      → このコードを貼り付け → "Verify JWT" を OFF にして Deploy
//   B) CLI: supabase functions deploy post-comment --no-verify-jwt
//
// 必要なシークレット（ダッシュボード → Edge Functions → Secrets で設定）:
//   TURNSTILE_SECRET_KEY = Cloudflare Turnstile の Secret Key
//   （SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY は Supabase が自動で用意します）

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const TURNSTILE_SECRET = Deno.env.get("TURNSTILE_SECRET_KEY")!;

// 本番ドメインとローカルテスト用。ここに無い Origin からは受け付けない。
const ALLOWED_ORIGINS = [
  "https://kikenbutsu-master.jp",
  "https://www.kikenbutsu-master.jp",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
];

const CATEGORIES = ["comment", "qa", "taikenki"];

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

  const token = String(payload.token ?? "");
  const page_id = String(payload.page_id ?? "").trim().slice(0, 200);
  const category = CATEGORIES.includes(String(payload.category))
    ? String(payload.category)
    : "comment";
  let author_name = String(payload.author_name ?? "").trim().slice(0, 40);
  const body = String(payload.body ?? "").trim().slice(0, 2000);

  if (!author_name) author_name = "匿名";
  if (!page_id) return json({ error: "page_id required" }, 400, origin);
  if (!body) return json({ error: "本文が空です。" }, 400, origin);
  if (!token) return json({ error: "認証（Turnstile）が未完了です。" }, 400, origin);

  // 1) Turnstile 検証（これに通らないと保存しない）
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

  // 2) 保存（service_role は RLS をバイパスして INSERT できる）
  const insertRes = await fetch(`${SUPABASE_URL}/rest/v1/comments`, {
    method: "POST",
    headers: {
      "apikey": SERVICE_ROLE,
      "Authorization": `Bearer ${SERVICE_ROLE}`,
      "Content-Type": "application/json",
      "Prefer": "return=representation",
    },
    body: JSON.stringify({ page_id, category, author_name, body }),
  });

  if (!insertRes.ok) {
    const detail = await insertRes.text();
    return json({ error: "保存に失敗しました。", detail }, 500, origin);
  }
  const rows = await insertRes.json();
  return json({ ok: true, comment: Array.isArray(rows) ? rows[0] : rows }, 200, origin);
});
