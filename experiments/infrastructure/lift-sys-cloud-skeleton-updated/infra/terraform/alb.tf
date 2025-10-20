resource "aws_security_group" "alb" {
  name   = "${var.project}-${var.env}-alb"
  vpc_id = aws_vpc.this.id
  ingress { from_port = 443 to_port = 443 protocol = "tcp" cidr_blocks = var.alb_allowed_cidrs }
  egress  { from_port = 0   to_port = 0   protocol = "-1"  cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_lb" "this" {
  name               = "${var.project}-${var.env}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [for s in aws_subnet.public : s.id]
  idle_timeout       = var.alb_idle_timeout
}

resource "aws_lb_target_group" "api" {
  name        = "${var.project}-${var.env}-api"
  port        = var.container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.this.id

  health_check {
    enabled             = true
    path                = "/healthz"
    matcher             = "200-399"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.alb_certificate_arn

  default_action { type = "forward"; target_group_arn = aws_lb_target_group.api.arn }
}
