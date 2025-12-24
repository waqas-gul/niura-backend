#!/bin/bash
# ========================================================================
# Bastion Kafka CLI Setup Script
# ========================================================================
# This script installs Kafka CLI tools and AWS MSK IAM auth JAR on the 
# bastion host, following AWS MSK Serverless official documentation.
#
# Run this ONCE on your bastion host via SSM:
#   aws ssm start-session --target <bastion-instance-id>
#   
# Then run:
#   sudo bash /tmp/bastion-kafka-setup.sh
# ========================================================================

set -e

echo "🚀 Starting Kafka CLI setup on bastion host..."

# Install Java 11
echo "📦 Installing Java 11..."
sudo yum install -y java-11-openjdk wget tar

# Verify Java installation
java -version

# Download Kafka CLI 2.8.1 (AWS recommended version)
echo "📥 Downloading Kafka CLI 2.8.1..."
cd /home/ec2-user
wget https://archive.apache.org/dist/kafka/2.8.1/kafka_2.12-2.8.1.tgz
tar -xzf kafka_2.12-2.8.1.tgz
rm kafka_2.12-2.8.1.tgz

# Download AWS MSK IAM Auth JAR
echo "🔐 Downloading AWS MSK IAM Auth JAR..."
cd /home/ec2-user/kafka_2.12-2.8.1
wget https://github.com/aws/aws-msk-iam-auth/releases/download/v2.3.0/aws-msk-iam-auth-2.3.0-all.jar -P libs/

# Fix permissions
sudo chown -R ec2-user:ec2-user /home/ec2-user/kafka_2.12-2.8.1

echo "✅ Kafka CLI setup completed!"
echo ""
echo "📝 Next steps:"
echo "   1. Create client.properties file (see create-kafka-topics.sh)"
echo "   2. Run create-kafka-topics.sh to create Kafka topics"
echo ""
