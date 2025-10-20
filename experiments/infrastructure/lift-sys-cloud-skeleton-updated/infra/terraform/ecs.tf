resource "aws_ecs_cluster" "this" {
  name = "${var.project}-${var.env}"
  setting { name = "containerInsights" value = "enabled" }
}

resource "aws_cloudwatch_log_group" "api" { name = "/ecs/${var.project}-${var.env}-api"; retention_in_days = 30 }

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project}-${var.env}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.ecs_cpu)
  memory                   = tostring(var.ecs_memory)
  execution_role_arn       = aws_iam_role.exec.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform { operating_system_family = "LINUX"; cpu_architecture = "X86_64" }

  container_definitions = jsonencode([{
    name      = "api",
    image     = var.container_image,
    essential = true,
    portMappings = [{ containerPort = var.container_port, protocol = "tcp" }],
    environment = [
      { "name": "OTEL_EXPORTER_OTLP_ENDPOINT", "value": "https://api.honeycomb.io" },
      { "name": "OTEL_RESOURCE_ATTRIBUTES", "value": "service.name=${var.project}-api,env=${var.env}" }
    ],
    logConfiguration = {
      logDriver = "awslogs",
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name,
        awslogs-region        = var.aws_region,
        awslogs-stream-prefix = "ecs"
      }
    }
  }])
}

resource "aws_security_group" "svc" {
  name   = "${var.project}-${var.env}-svc"
  vpc_id = aws_vpc.this.id
  ingress { from_port = var.container_port to_port = var.container_port protocol = "tcp" security_groups = [aws_security_group.alb.id] }
  egress  { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_ecs_service" "api" {
  name            = "${var.project}-${var.env}-api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  enable_execute_command = true
  deployment_circuit_breaker { enable = true rollback = true }

  network_configuration {
    subnets         = [for s in aws_subnet.private : s.id]
    security_groups = [aws_security_group.svc.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = var.container_port
  }

  lifecycle { ignore_changes = [desired_count] }
}
