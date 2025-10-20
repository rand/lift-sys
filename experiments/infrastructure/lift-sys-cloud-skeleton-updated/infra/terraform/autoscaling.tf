resource "aws_appautoscaling_target" "svc" {
  max_capacity       = var.max_count
  min_capacity       = var.desired_count
  resource_id        = "service/${aws_ecs_cluster.this.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
resource "aws_appautoscaling_policy" "cpu_tt" {
  name        = "${var.project}-${var.env}-cpu-tt"
  policy_type = "TargetTrackingScaling"
  resource_id = aws_appautoscaling_target.svc.resource_id
  scalable_dimension = aws_appautoscaling_target.svc.scalable_dimension
  service_namespace  = aws_appautoscaling_target.svc.service_namespace
  target_tracking_scaling_policy_configuration {
    target_value = 60
    predefined_metric_specification { predefined_metric_type = "ECSServiceAverageCPUUtilization" }
  }
}
resource "aws_appautoscaling_policy" "alb_rps_tt" {
  name        = "${var.project}-${var.env}-alb-req-tt"
  policy_type = "TargetTrackingScaling"
  resource_id = aws_appautoscaling_target.svc.resource_id
  scalable_dimension = aws_appautoscaling_target.svc.scalable_dimension
  service_namespace  = aws_appautoscaling_target.svc.service_namespace
  target_tracking_scaling_policy_configuration {
    target_value = 200
    customized_metric_specification {
      metric_name = "RequestCountPerTarget"
      namespace   = "AWS/ApplicationELB"
      statistic   = "Average"
      dimensions = [
        { name = "TargetGroup", value = aws_lb_target_group.api.arn_suffix },
        { name = "LoadBalancer", value = aws_lb.this.arn_suffix }
      ]
      unit = "Count"
    }
  }
}
