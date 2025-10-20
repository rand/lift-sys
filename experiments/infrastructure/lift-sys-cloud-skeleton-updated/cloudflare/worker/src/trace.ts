export function hex(n: number) {
  const a = new Uint8Array(n)
  crypto.getRandomValues(a)
  return [...a].map(b => b.toString(16).padStart(2, "0")).join("")
}
export function generateTraceparent() {
  const version = "00"
  const traceId = hex(16)
  const spanId  = hex(8)
  const flags   = "01"
  return `${version}-${traceId}-${spanId}-${flags}`
}
