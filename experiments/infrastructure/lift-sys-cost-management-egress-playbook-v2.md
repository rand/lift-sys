# Lift-sys cost management playbook · v2 (egress-first)

Date: 2025-10-19
Audience: agents and operators
This revision aligns with spec v3: correct W3C trace context, unified HMAC signature, Access-gated ALB by default, and strict RLS boundaries. Focus is on keeping **egress** low without harming UX.

---

## 0) Operating principles

1) Put repetitive bytes on **Cloudflare** (Pages/R2/Images/Stream), not behind the ALB.
2) Keep **OLTP** chatty but **tiny** – shape at the edge, export big results to R2.
3) Treat **egress per request** as a budgeted SLI and alert on regressions.
4) Optimize **cacheability** before micro-optimizing compression.

---

## 1) Quick-start checklist

- [ ] Serve all bulky downloads from **R2** via short-lived signed URLs.
- [ ] **Tiered Cache** on; consider **Cache Reserve** for long-tail assets.
- [ ] Strong `ETag` and `Cache-Control` with `stale-while-revalidate`.
- [ ] **Content-addressed** asset URLs for immutability and reuse.
- [ ] **Projection-first** APIs and server-enforced `LIMIT`. Export to R2 when over thresholds.
- [ ] Worker-level **Brotli** for text, AVIF/WebP for images with edge resizing.
- [ ] **Access** service tokens so only Workers can hit ALB.
- [ ] **Interface VPC endpoints** for ECR/Logs/STS to starve NAT bills.
- [ ] Honeycomb fields: `egress.bytes`, `cache.hit`, `content.encoding`, `origin.service`.

---

## 2) Architecture patterns that cut egress

### A) Edge-origins split
- Public assets, generated artifacts, images, and docs → **R2** behind Workers.
- Private downloads → signed R2 URLs; never proxy big files through ALB.
- For media, use **Cloudflare Images/Stream** to offload transcode + delivery.

### B) Compute-to-data
- Big queries and reports run server-side, then publish **artifacts** to R2.
- The client receives a small JSON index and optionally downloads artifacts from R2.

### C) Fan-out at the edge
- Use **Durable Objects** to multiplex realtime feeds (SSE/WebSocket).
- Fetch compact upstream deltas; DO handles N clients close to users.

### D) Cache-key normalization
- Snap image resize requests to a **small preset matrix**; normalize query params order.
- Avoid cache fragmentation from incidental parameters and auth headers.

---

## 3) Response shaping and formats

- Prefer **paginated, sparse** JSON. Example budget: P50 ≤ 12 KB, P95 ≤ 64 KB.
- For dense lists, consider **MessagePack** or JSON with **stable key order** to improve Brotli gains.
- For streams, use **NDJSON** with Brotli; keep events ≤ 1 KB.
- Return **IDs** on vector search; lazy-load documents separately with conditional requests.

**Worker skeleton**

```ts
function project(u: any) {{
  return {{ id: u.id, t: u.updated_at, title: u.title, tags: (u.tags ?? []).slice(0,8) }}
}}
const res = await fetch(origin, ...)
const data = await res.json()
const shaped = data.items.map(project)
return new Response(JSON.stringify(shaped), {{
  headers: {{
    "content-type": "application/json",
    "cache-control": "public, max-age=300, s-maxage=86400, stale-while-revalidate=604800",
    "etag": `W/"${{await hash(JSON.stringify(shaped))}}"`
  }}
}})
```

---

## 4) Supabase discipline

- Enforce column-level selection: expose `?select=...` and block `select=*`.
- RLS only on the edge path; **service role** is used solely in queue consumers or Fargate.
- Threshold exports: if `count > N`, write CSV/Parquet to **R2**, return link.
- For embeddings, return `{{id, score}}`; fetch docs lazily with ETags.
- Keep Edge Functions tiny and cacheable; heavy work runs elsewhere.

---

## 5) AWS ALB + Fargate guardrails

- Do not serve files through ECS; publish to R2.
- Set **ALB idle timeout** ≥ 120 s if using SSE/WebSockets to reduce reconnects.
- Reuse connections Worker → ALB; honor `keep-alive`.
- Compress text responses; prefer `br` then `gzip`.
- Watch **LCU** drivers: new connections, active conns, rules, bytes. Trim rules and reuse conns.

---

## 6) Creative tactics

1) **Delta-first APIs** – clients request `?since=cursor`; server returns only changed IDs plus a tiny patch.
2) **KV prewarm** – push hot object summaries into KV on write. Serve from KV with SWR validation.
3) **Anti-hotlink + Access** – require Access token for ALB; deny direct origin pulls.
4) **Bundle sprites** – combine small assets into stable bundles to increase cache hit and compression.
5) **Client hints** – detect `Save-Data` and downshift images and list sizes opportunistically.
6) **Deterministic paging** – make pages stable across users to amplify cache reuse.
7) **Signed-URL hop** – when Supabase Storage is used, proxy app issues signed URLs rather than streaming bytes.

---

## 7) Measurement and budgets

Emit per request:
- `egress.bytes`, `payload.bytes.body`, `payload.bytes.headers`
- `cache.hit` (bool), `cache.key` (hash), `cache.ttl`
- `origin.service` (supabase|fargate|r2), `content.encoding`, `image.format`
- `traceparent` to link to Honeycomb

Initial budgets:
- API GET P50 ≤ 12 KB, P95 ≤ 64 KB
- ALB egress 0 GB for downloads – all big files must be from R2
- Supabase bandwidth ≤ 200 GB/month (under Pro cap)

Alerts:
- Warn on 7d P95 `egress.bytes/request` +20% WoW
- Page if ALB egress projects +30% over monthly target at mid-cycle

---

## 8) Cost sensitivity cheat sheet

Let `E = responses/month`, `S = avg KB/resp`, `P = $/GB egress` (AWS ≈ 0.09):

```
egress_GB = E * S / 1024 / 1024
egress_cost = egress_GB * P
```

Example: 3M responses × 100 KB ≈ 286 GB → ≈ $25.8 at $0.09/GB.
10M × 1 MB ≈ 9537 GB → ≈ $858. If payloads double, cost doubles.

Levers that hit egress the hardest:
- Move downloads to R2; increase cache hit ratio; cut response size (projection + compression); reduce reconnects; limit origin exposure with Access.

---

## 9) Runbooks

**ALB egress spike**
1) Identify top routes by bytes.
2) Check if responses are cacheable; add cache headers, hash URLs.
3) If large payloads are expected, publish artifacts to R2 and return signed URLs.
4) Verify Access tokens enforced; block non-Worker callers.

**Supabase bandwidth spike**
1) Audit queries for `select=*`.
2) Enforce server-side `LIMIT`.
3) Offer export-to-R2 and return a link.
4) Enable Hyperdrive and verify pooling reduces chatter.

**Worker miss storms**
1) Normalize cache keys and query param ordering.
2) Turn on Tiered Cache; consider Cache Reserve for long-tail.
3) Add request coalescing – one origin fetch, many waiters.

---

## 10) Snippets

**Signed R2 redirect**

```ts
const url = await env.R2_PUBLIC.createPresignedUrl({{ key, method: "GET", expiration: 60 }})
return Response.redirect(url, 302)
```

**Content-addressed key**

```ts
const hash = await crypto.subtle.digest("SHA-256", data)
const hex = [...new Uint8Array(hash)].map(b=>b.toString(16).padStart(2,"0")).join("")
const key = `artifacts/{{hex}}.bin`
```

**Server-Timing for visibility**

```ts
const t0 = Date.now()
// .. work
const t1 = Date.now()
return new Response(body, {{ headers: {{ "server-timing": `edge;dur=${{t1-t0}}` }} }})
```

---

## 11) To do next

- Wire per-route budgets and dashboards; add alerts.
- Migrate all downloads to R2 and backfill Cache Reserve.
- Add image preset snapping; audit resize callers.
- Formalize export thresholds and R2 lifecycle policies.
