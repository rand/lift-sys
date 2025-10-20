project = "lift-sys"
env     = "staging"
aws_region = "us-east-2"

alb_certificate_arn = "arn:aws:acm:us-east-2:111111111111:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

vpc_cidr        = "10.20.0.0/16"
public_subnets  = ["10.20.0.0/20", "10.20.16.0/20"]
private_subnets = ["10.20.32.0/20", "10.20.48.0/20"]

container_image = "111111111111.dkr.ecr.us-east-2.amazonaws.com/lift-api:CHANGE_ME"
container_port  = 8080
alb_idle_timeout = 120
