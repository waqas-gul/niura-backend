resource "aws_iam_role" "bastion_role" {
  name = "${var.env_prefix}-bastion-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = { Service = "ec2.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.bastion_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# MSK Serverless IAM permissions for topic creation (AWS recommended approach)
resource "aws_iam_role_policy" "bastion_msk_policy" {
  count = var.kafka_cluster_arn != "" ? 1 : 0
  name  = "${var.env_prefix}-bastion-msk-policy"
  role  = aws_iam_role.bastion_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "kafka-cluster:Connect",
          "kafka-cluster:DescribeCluster"
        ],
        Resource = [var.kafka_cluster_arn]
      },
      {
        Effect = "Allow",
        Action = [
          "kafka-cluster:CreateTopic",
          "kafka-cluster:WriteData",
          "kafka-cluster:DescribeTopic",
          "kafka-cluster:ReadData"
        ],
        Resource = [
          "arn:aws:kafka:${var.aws_region}:*:topic/*/*/*"
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "bastion_profile" {
  name = "${var.env_prefix}-bastion-profile"
  role = aws_iam_role.bastion_role.name
}

resource "aws_security_group" "bastion_sg" {
  name        = "${var.env_prefix}-bastion-sg"
  description = "Security group for bastion host"
  vpc_id      = var.vpc_id

  # No inbound rules! SSM uses HTTPS outbound.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "bastion" {
  ami                    = var.ami_id
  instance_type          = "t3.micro"
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.bastion_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.bastion_profile.name

  tags = {
    Name = "${var.env_prefix}-bastion"
  }
}

output "bastion_instance_id" {
  value = aws_instance.bastion.id
}

output "bastion_sg_id" {
  value = aws_security_group.bastion_sg.id
}
