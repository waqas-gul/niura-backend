# 🚀 Quick Start: Create Kafka Topics (5 Minutes)

## Prerequisites ✅
- AWS CLI configured
- Access to AWS account (654654617590)
- Bastion instance running (i-09b4c09f28b92caf6)

---

## Step 1: Connect to Bastion (30 seconds)

```bash
aws ssm start-session --target i-09b4c09f28b92caf6
```

---

## Step 2: Setup Kafka CLI (2 minutes)

### Copy-paste this entire block into bastion:

```bash
# Install Java 11 (use amazon-corretto8 which is available)
sudo amazon-linux-extras install java-openjdk11 -y

# Verify Java installation
java -version

# Download Kafka CLI to /tmp (SSM user has permissions here)
cd /tmp
wget https://archive.apache.org/dist/kafka/2.8.1/kafka_2.12-2.8.1.tgz
tar -xzf kafka_2.12-2.8.1.tgz
rm kafka_2.12-2.8.1.tgz

# Download AWS MSK IAM Auth JAR
cd kafka_2.12-2.8.1
wget https://github.com/aws/aws-msk-iam-auth/releases/download/v2.3.0/aws-msk-iam-auth-2.3.0-all.jar -P libs/

echo "✅ Kafka CLI setup complete!"
```

---

## Step 3: Create Topics (2 minutes)

### Copy-paste this entire block into bastion:

```bash
# Set bootstrap server
export KAFKA_BOOTSTRAP="boot-mznm5shf.c1.kafka-serverless.ap-south-1.amazonaws.com:9098"

# Create client.properties
cd /tmp/kafka_2.12-2.8.1/bin
cat > client.properties << 'EOF'
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
EOF

# Create topics
for topic in "eeg.raw.data" "eeg.processed.data" "user.activity" "alerts.events" "analytics.triggers"; do
  ./kafka-topics.sh \
    --bootstrap-server $KAFKA_BOOTSTRAP \
    --command-config client.properties \
    --create \
    --topic $topic \
    --partitions 3 \
    --if-not-exists
  echo "✅ Created $topic"
done

# Verify
echo ""
echo "📋 Listing all topics:"
./kafka-topics.sh \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --command-config client.properties \
  --list
```

---

## ✅ Expected Output

```
Created topic eeg.raw.data.
✅ Created eeg.raw.data
Created topic eeg.processed.data.
✅ Created eeg.processed.data
Created topic user.activity.
✅ Created user.activity
Created topic alerts.events.
✅ Created alerts.events
Created topic analytics.triggers.
✅ Created analytics.triggers

alerts.events
analytics.triggers
eeg.processed.data
eeg.raw.data
user.activity
```

---

## 🎯 You're Done!

Your MSK Serverless cluster now has all required topics. Backend services will work immediately.

**To verify services are working:**

```bash
# From your local machine
aws logs tail /ecs/niura-staging --follow --filter-pattern "Kafka"
```

You should NO LONGER see:
- ❌ `_UNKNOWN_TOPIC` errors
- ❌ `Kafka topic bootstrap failed` messages
- ❌ `Transport failure` errors

---

## 📚 Full Documentation

- **Complete Guide:** `backEnd/KAFKA_SETUP.md`
- **Implementation Summary:** `backEnd/IMPLEMENTATION_SUMMARY.md`
- **Troubleshooting:** See KAFKA_SETUP.md section

---

**That's it! Topics are created once and persist forever.** 🚀
