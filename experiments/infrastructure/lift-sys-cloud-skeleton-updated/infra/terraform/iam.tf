data "aws_iam_policy_document" "exec_assume" {
  statement { actions = ["sts:AssumeRole"]; principals { type = "Service"; identifiers = ["ecs-tasks.amazonaws.com"] } }
}
resource "aws_iam_role" "exec" { name = "${var.project}-${var.env}-ecs-exec"; assume_role_policy = data.aws_iam_policy_document.exec_assume.json }
resource "aws_iam_role_policy_attachment" "exec_logs" {
  role       = aws_iam_role.exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
data "aws_iam_policy_document" "task_assume" {
  statement { actions = ["sts:AssumeRole"]; principals { type = "Service"; identifiers = ["ecs-tasks.amazonaws.com"] } }
}
resource "aws_iam_role" "task" { name = "${var.project}-${var.env}-ecs-task"; assume_role_policy = data.aws_iam_policy_document.task_assume.json }
resource "aws_iam_role_policy" "task_secrets" {
  name = "${var.project}-${var.env}-ecs-task-secrets"
  role = aws_iam_role.task.id
  policy = jsonencode({ Version="2012-10-17", Statement=[{Effect="Allow",Action=["secretsmanager:GetSecretValue"],Resource="*"}] })
}
