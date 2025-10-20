import { generateTraceparent } from "./trace"

export default {
  async fetch(req: Request, env: Env) {
    const url = new URL(req.url)
    const traceparent = generateTraceparent()

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

    if (url.pathname === "/api/jobs" && req.method === "POST") {
      const buf = await req.arrayBuffer()
      const sig = await sign(buf, env.MODAL_SIGNING_KEY)
      const res = await fetch(env.MODAL_URL, {
        method: "POST",
        headers: { "content-type": "application/json", "x-signature": sig, "traceparent": traceparent },
        body: buf
      })

      const id = env.SESSION_DO.idFromName("job-status")
      const stub = env.SESSION_DO.get(id)
      await stub.fetch("https://do/update", { method: "POST", body: await res.text() })
      return new Response(JSON.stringify({ ok: true }), { headers: { "content-type": "application/json" } })
    }

    return new Response("ok")
  }
}

async function sign(buf: ArrayBuffer, keyB64: string) {
  const raw = Uint8Array.from(atob(keyB64), c => c.charCodeAt(0))
  const key = await crypto.subtle.importKey("raw", raw, { name: "HMAC", hash: "SHA-256" }, false, ["sign"])
  const mac = await crypto.subtle.sign("HMAC", key, buf)
  const b = new Uint8Array(mac)
  let s = ""; for (const x of b) s += String.fromCharCode(x)
  return btoa(s)
}

export interface Env {
  ACCESS_CLIENT_ID: string
  ACCESS_CLIENT_SECRET: string
  MODAL_SIGNING_KEY: string
  FARGATE_HOST: string
  MODAL_URL: string
  PG: any
  R2_PUBLIC: R2Bucket
  JOB_QUEUE: Queue
  SESSION_DO: DurableObjectNamespace
}
