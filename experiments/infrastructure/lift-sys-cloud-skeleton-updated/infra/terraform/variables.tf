variable "project" { type = string }
variable "env"     { type = string }
variable "aws_region" { type = string  default = "us-east-2" }

variable "vpc_cidr" { type = string  default = "10.20.0.0/16" }

variable "public_subnets" {
  type        = list(string)
  default     = ["10.20.0.0/20", "10.20.16.0/20"]
}
variable "private_subnets" {
  type        = list(string)
  default     = ["10.20.32.0/20", "10.20.48.0/20"]
}

variable "alb_certificate_arn" { type = string }
variable "alb_allowed_cidrs" { type = list(string) default = ["0.0.0.0/0"] }
variable "alb_idle_timeout" { type = number default = 120 }

variable "ecs_cpu"    { type = number default = 1024 }
variable "ecs_memory" { type = number default = 2048 }
variable "desired_count" { type = number default = 2 }
variable "max_count"     { type = number default = 10 }

variable "container_image" { type = string }
variable "container_port"  { type = number default = 8080 }
variable "tags" { type = map(string) default = {} }
