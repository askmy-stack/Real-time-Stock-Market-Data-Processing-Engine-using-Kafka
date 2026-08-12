resource "aws_security_group" "msk" {
  count       = var.enable_msk ? 1 : 0
  name        = "${var.project_name}-msk-sg"
  description = "MarketPulse MSK"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 9092
    to_port         = 9098
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_msk_cluster" "main" {
  count = var.enable_msk ? 1 : 0

  cluster_name           = "${var.project_name}-msk"
  kafka_version          = "3.6.0"
  number_of_broker_nodes = 2

  broker_node_group_info {
    instance_type   = "kafka.t3.small"
    client_subnets  = module.vpc.private_subnets
    security_groups = [aws_security_group.msk[0].id]
  }

  encryption_info {
    encryption_at_rest_kms_key_arn = null
  }
}
