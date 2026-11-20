// Supabase Edge Function: post-comment（デプロイ名は swift-responder）
// 役割:
//   action="post"（既定): Turnstile を検証し、投稿を保存する「門番」。
//       投稿者の uid を SHA-256 でハッシュ化した author_id を付与（なりすまし対策）。
//   action="delete": 管理キー(ADMIN_SECRET)を照合し、指定コメントを非表示化（ソフト削除）。
//
// デプロイ（どちらか）:
//   A) ダッシュボード: Edge Functions → 対象関数 → Code にこのコードを貼り付け → Deploy
//      （Verify JWT は OFF のまま）
//   B) CLI: supabase functions deploy swift-responder --no-verify-jwt
//
// 必要なシークレット（ダッシュボード → Edge Functions → Secrets）:
//   TURNSTILE_SECRET_KEY = Cloudflare Turnstile の Secret Key
//   ADMIN_SECRET         = 管理者削除に使う任意の長いパスワード（あなただけが知る値）
//   （SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY は Supabase が自動で用意します）

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

  // 2) 投稿者ID（uid を SHA-256  → 先頭16桁）。uid 無しは匿名識別なし。
  const author_id = uid ? (await sha256hex(uid)).slice(0, 16) : null;

  // 3) 保存（service_role は RLS をバイパスして INSERT できる）
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
