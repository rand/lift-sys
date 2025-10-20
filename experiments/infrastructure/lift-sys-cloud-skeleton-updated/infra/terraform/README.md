# infra/terraform (updated)

- `alb_idle_timeout` controls websocket/SSE friendliness (default 120s).
- Restrict `alb_allowed_cidrs` to Cloudflare egress ranges or front with Cloudflare Tunnel + Access.
- VPC interface endpoints reduce NAT costs during pulls and logging.
