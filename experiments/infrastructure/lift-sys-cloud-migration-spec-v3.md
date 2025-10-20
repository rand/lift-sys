# Lift‑sys cloud migration specification · v3

Date: 2025‑10‑19
Audience: Claude Code or equivalent agent plus human operator
Intent: Canonical, executable spec for the Workers‑first stack with Supabase, Fargate, and Modal. This version fixes trace context, signature contract, Durable Objects routing, and strengthens Zero Trust and RLS boundaries.

## 0) Final architecture

- **Frontend** – Cloudflare Pages
- **Edge/API** – Cloudflare Workers with bindings: R2, KV, Queues, Durable Objects, Hyperdrive
- **Database** – Supabase Postgres with pgvector and RLS
- **Heavy/long‑lived services** – AWS ECS Fargate behind an ALB
- **Inference** – Modal.com services (per‑request signed)
- **Storage** – R2 for public artifacts and large downloads; Supabase Storage for auth‑bound user files
- **Async** – Cloudflare Queues; DOs for coordination
- **Access control** – Cloudflare Access in front of any ALB path (or Cloudflare Tunnel publishing a private hostname); Workers present service tokens
- **Observability** – OpenTelemetry traces to Honeycomb; LLM spans/evals to Arize Phoenix; W3C `traceparent` propagated end‑to‑end

## 1) Security and correctness deltas (mandatory)

1. **Trace context is W3C‑compliant**
   - Trace ID is **16 bytes = 32 hex**, Span ID is **8 bytes = 16 hex**.

   ```ts
   // Worker helper
   function hex(n: number) {
     const a = new Uint8Array(n)
     crypto.getRandomValues(a)
     return [...a].map(b => b.toString(16).padStart(2,"0")).join("")
   }
   export function generateTraceparent() {
     const version = "00"
     const traceId = hex(16)   // 32 hex
     const spanId  = hex(8)    // 16 hex
     const flags   = "01"
     return `${version}-${traceId}-${spanId}-${flags}`
   }
   ```

2. **Signature contract is normalized**
   - Worker sends `X‑Signature: base64(hmac_sha256(secret, rawBody))`.
   - Backend or Modal verifies against the **exact raw body bytes** received.

   ```python
   # Modal/Backend verification (Python)
   import base64, hmac, hashlib
   raw = request.body  # bytes
   sent = request.headers.get("X-Signature","")
   calc = base64.b64encode(hmac.new(KEY, raw, hashlib.sha256).digest()).decode()
   if not hmac.compare_digest(sent, calc):
       return Response(status=403)
   ```

3. **Durable Object route aligns with caller**
   - DO updates at POST `/update`; Worker calls `/update` explicitly.

4. **Service‑role keys are never used on the public edge path**
   - Worker uses **anon key** + RLS for OLTP reads/writes.
   - Any use of Supabase **service role** happens only in **Queue consumer** or Fargate, never in request‑response from the edge.

5. **Zero Trust by default for origin**
   - ALB is protected with **Cloudflare Access** service tokens. Workers attach `Cf‑Access‑Client‑Id` and `Cf‑Access‑Client‑Secret`. Optionally replace public ALB with **Cloudflare Tunnel** to a private hostname.

## 2) Data plane and egress discipline

- Large or repeatable downloads are staged to **R2**, and clients fetch via short‑lived signed URLs. ALB never serves bulk files.
- Workers shape and compress responses. Cache immutable assets with content‑addressed keys and strong TTLs.
- Supabase OLTP APIs are **field‑selective**; enforce server‑side LIMITs; provide “export to R2” when queries exceed thresholds.
- Use **Hyperdrive** between Workers and Supabase for pooled, accelerated global access.

## 3) Reference configs and snippets

### 3.1 `wrangler.toml` (delta view)

```toml
name = "lift-api"
main = "src/index.ts"
compatibility_date = "2025-10-19"
workers_dev = false

[vars]
ENV = "staging"
FARGATE_HOST = "CHANGE_ME_ALB_HOSTNAME"
MODAL_URL = "https://CHANGE_ME.modal.run/solve"

[[hyperdrive]]
binding = "PG"
id = "CHANGE_ME_HYPERDRIVE_ID"

[[queues.producers]]
binding = "JOB_QUEUE"
queue = "lift-jobs"

[[r2_buckets]]
binding = "R2_PUBLIC"
bucket_name = "lift-public"

[durable_objects]
bindings = [{ name = "SESSION_DO", class_name = "SessionDO" }]
```

### 3.2 Worker proxy and Modal call

```ts
import { generateTraceparent } from "./trace"

export default {
  async fetch(req: Request, env: Env) {
    const url = new URL(req.url)
    const traceparent = generateTraceparent()

    // Proxy to Fargate behind ALB with Access token
    if (url.pathname.startsWith("/backend/")) {
      const headers = new Headers(req.headers)
      headers.set("Cf-Access-Client-Id", env.ACCESS_CLIENT_ID)
      headers.set("Cf-Access-Client-Secret", env.ACCESS_CLIENT_SECRET)
      headers.set("traceparent", traceparent)

      url.hostname = env.FARGATE_HOST
      url.protocol = "https:"
      return fetch(url.toString(), {
        method: req.method,
        headers,
        body: req.method === "GET" || req.method === "HEAD" ? undefined : req.body
      })
    }

    // Queue a job, use anon key + RLS only (service role not allowed here)
    if (url.pathname === "/api/jobs" && req.method === "POST") {
      const body = await req.arrayBuffer()
      const sig  = await sign(body, env.MODAL_SIGNING_KEY) // base64(HMAC)
      const res = await fetch(env.MODAL_URL, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-signature": sig,
          "traceparent": traceparent
        },
        body: body
      })
      // Update DO status at explicit path
      const id = env.SESSION_DO.idFromName("job-status")
      const stub = env.SESSION_DO.get(id)
      await stub.fetch("https://do/update", { method: "POST", body: await res.text() })
      return new Response(JSON.stringify({ ok: true }), { headers: { "content-type": "application/json" } })
    }

    return new Response("ok")
  }
}

async function sign(buf: ArrayBuffer, keyB64: string) {
  const key = await crypto.subtle.importKey(
    "raw",
    Uint8Array.from(atob(keyB64), c=>c.charCodeAt(0)),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  )
  const mac = await crypto.subtle.sign("HMAC", key, buf)
  const b = new Uint8Array(mac)
  let s = ""; for (const x of b) s += String.fromCharCode(x)
  return btoa(s)
}
```

### 3.3 ECS/Fargate cleanups

- CPU/Memory are task‑level only; no container `resourceRequirements`.
- SOCI lazy loading is optional in CI; do not hard‑require the plugin.
- ALB idle timeout set via Terraform var (default 120s) for WebSockets/SSE.

## 4) Terraform deltas (summarized)

- Add `alb_idle_timeout` variable and apply to ALB.
- Keep `alb_allowed_cidrs` to restrict ingress to Cloudflare egress if desired.
- ECS service enables Exec for debugging; autoscaling by CPU plus ALB RequestCount per target.
- VPC endpoints for ECR API/DKR, CloudWatch Logs, STS to shrink NAT use.

> See updated files in `infra/terraform/*` in this package.

## 5) CI/CD deltas

- ECS deploy workflow builds and pushes to ECR, then forces a new deployment. SOCI index creation is best‑effort and non‑blocking.
- Workers deploy via wrangler action. Supabase migrations separate workflow. Infra plan/apply via workflow_dispatch.
- Region is provided via secret `AWS_REGION` with a default fallback in the workflow expression.

## 6) Runbooks (selected)

- **Trace break** – check `traceparent` format at the Worker and that ALB → app preserves headers.
- **403 from Modal** – confirm X‑Signature constructed from raw body bytes; compare with backend recompute.
- **RLS bypass risk** – grep for service role usage in Worker code; move to Queue consumer or Fargate if found.
- **ALB egress spike** – confirm bulk downloads are served from R2 and Access blocks non‑Worker traffic.

## 7) Non‑goals

- No k8s. No long‑lived state in Workers beyond DO patterns. No direct client → ALB without Access.
