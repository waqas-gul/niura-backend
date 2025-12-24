#!/bin/bash
# ========================================================================
# Kafka Topics Creation Script (AWS MSK Serverless)
# ========================================================================
# This script creates all required Kafka topics using AWS MSK IAM auth.
# Run this ONCE per environment from the bastion host.
#
# Prerequisites:
#   1. Run bastion-kafka-setup.sh first
#   2. Bastion IAM role has kafka-cluster:CreateTopic permission
#   3. Bastion is in same VPC as MSK Serverless cluster
#
# Usage:
#   1. Copy to bastion: 
#      aws ssm start-session --target <bastion-id>
#   
#   2. Set your bootstrap server:
#      export KAFKA_BOOTSTRAP="boot-xxxxx.c1.kafka-serverless.ap-south-1.amazonaws.com:9098"
#   
#   3. Run this script:
#      bash /home/ec2-user/create-kafka-topics.sh
# ========================================================================

set -e

# Configuration
KAFKA_HOME="/home/ec2-user/kafka_2.12-2.8.1"
KAFKA_BIN="$KAFKA_HOME/bin"
CLIENT_PROPS="$KAFKA_HOME/bin/client.properties"

# Check if KAFKA_BOOTSTRAP is set
if [ -z "$KAFKA_BOOTSTRAP" ]; then
    echo "❌ ERROR: KAFKA_BOOTSTRAP environment variable not set!"
    echo ""
    echo "Usage:"
    echo "  export KAFKA_BOOTSTRAP='boot-xxxxx.c1.kafka-serverless.ap-south-1.amazonaws.com:9098'"
    echo "  bash $0"
    exit 1
fi

echo "🔧 Kafka Bootstrap Server: $KAFKA_BOOTSTRAP"
echo ""

# Create client.properties if it doesn't exist
if [ ! -f "$CLIENT_PROPS" ]; then
    echo "📝 Creating client.properties..."
    cat > "$CLIENT_PROPS" << 'EOF'
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
EOF
    echo "✅ client.properties created"
else
    echo "✅ client.properties already exists"
fi

echo ""

# Define topics to create (matching your application requirements)
declare -A TOPICS=(
    ["eeg.raw.data"]=3
    ["eeg.processed.data"]=3
    ["user.activity"]=3
    ["alerts.events"]=3
    ["analytics.triggers"]=3
)

# Create topics
echo "🪄 Creating Kafka topics..."
echo ""

for topic in "${!TOPICS[@]}"; do
    partitions="${TOPICS[$topic]}"
    
    echo "📌 Creating topic: $topic (partitions: $partitions)"
    
    $KAFKA_BIN/kafka-topics.sh \
        --bootstrap-server "$KAFKA_BOOTSTRAP" \
        --command-config "$CLIENT_PROPS" \
        --create \
        --topic "$topic" \
        --partitions "$partitions" \
        --if-not-exists
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Topic '$topic' created successfully"
    else
        echo "   ⚠️  Failed to create topic '$topic' (may already exist)"
    fi
    echo ""
done

# List all topics to verify
echo ""
echo "📋 Verifying created topics:"
echo ""
$KAFKA_BIN/kafka-topics.sh \
    --bootstrap-server "$KAFKA_BOOTSTRAP" \
    --command-config "$CLIENT_PROPS" \
    --list

echo ""
echo "🎉 Topic creation completed!"
echo ""
echo "✅ Your MSK Serverless cluster is ready for production use."
echo "   All backend services can now publish/consume from these topics."
echo ""
