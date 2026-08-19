resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.project_name}/db-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

resource "aws_secretsmanager_secret" "api_key" {
  name = "${var.project_name}/api-key"
}

resource "aws_secretsmanager_secret_version" "api_key" {
  count = var.api_key != "" ? 1 : 0

  secret_id     = aws_secretsmanager_secret.api_key.id
  secret_string = var.api_key
}
