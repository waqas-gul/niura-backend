# Kafka Setup Guide for MSK Serverless

This guide follows **AWS MSK Serverless official best practices** for topic creation and management.

## 📋 Overview

Kafka topics in MSK Serverless are **NOT created by application code**. Instead, they are created **once per environment** using Kafka CLI tools from a client machine inside the VPC (the bastion host).

### Why This Approach?

1. **AWS Recommendation**: Official AWS documentation prescribes manual topic creation via Kafka CLI with IAM authentication
2. **Security**: Topic management requires elevated IAM permissions that applications shouldn't have
3. **Reliability**: Avoids race conditions, timeout issues, and bootstrap failures during service startup
4. **Simplicity**: One-time setup vs. complex retry logic in every service

## 🏗️ Architecture

```
┌──────────────┐
│   Bastion    │ ◄─── YOU SSH HERE (via AWS SSM)
│  (EC2 t3)    │
│              │
│ ✅ Inside VPC │
│ ✅ IAM Role  │ ◄─── Has kafka-cluster:CreateTopic permission
│ ✅ Kafka CLI │
│ ✅ MSK Auth  │
└──────┬───────┘
       │
       │ (SASL_SSL + IAM Auth)
       ▼
┌──────────────────────┐
│  MSK Serverless      │
│  Cluster             │
│                      │
│  Topics:             │
│  • eeg.raw.data      │
│  • eeg.processed.data│
│  • user.activity     │
│  • alerts.events     │
│  • analytics.triggers│
└──────────────────────┘
       ▲
       │ (Producer/Consumer)
       │
┌──────┴────────┐
│ ECS Services  │
│ • Gateway     │
│ • Core        │
│ • EEG         │
└───────────────┘
```

## 🚀 Step-by-Step Setup (One-Time Per Environment)

### Step 1: Apply Terraform Changes

The bastion host already has the required IAM permissions configured in terraform:

```bash
cd backEnd/infra
terraform init
terraform plan
terraform apply
```

This adds `kafka-cluster:CreateTopic`, `kafka-cluster:Connect`, and related permissions to the bastion IAM role.

### Step 2: Connect to Bastion via SSM

Get your bastion instance ID:

```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*bastion*" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text
```

Connect via AWS Systems Manager Session Manager (no SSH keys needed):

```bash
aws ssm start-session --target <bastion-instance-id>
```

Example:
```bash
aws ssm start-session --target i-09b4c09f28b92caf6
```

### Step 3: Install Kafka CLI Tools on Bastion

Copy the setup script to the bastion:

```bash
# From your local machine (Windows PowerShell)
$BASTION_ID = "i-09b4c09f28b92caf6"

# Copy setup script via S3 (easiest method without SSH keys)
aws s3 cp backEnd/bastion-kafka-setup.sh s3://your-bucket/bastion-kafka-setup.sh
```

Or manually copy-paste the script content into a file on the bastion.

Then run it:

```bash
# Inside bastion SSM session
sudo bash /tmp/bastion-kafka-setup.sh
```

This installs:
- Java 11
- Kafka CLI 2.8.1
- AWS MSK IAM Auth JAR v2.3.0

### Step 4: Get MSK Bootstrap Server

From your local machine:

```bash
cd backEnd/infra
terraform output kafka_bootstrap_servers
```

Or from AWS Console:
1. Go to Amazon MSK console
2. Select your cluster: `niura-staging-msk-sls`
3. Copy the **Bootstrap servers** endpoint
4. Should look like: `boot-xxxxx.c1.kafka-serverless.ap-south-1.amazonaws.com:9098`

### Step 5: Create Kafka Topics

Back in the bastion SSM session:

```bash
# Set your bootstrap server
export KAFKA_BOOTSTRAP="boot-mznm5shf.c1.kafka-serverless.ap-south-1.amazonaws.com:9098"

# Run the topic creation script
bash /home/ec2-user/create-kafka-topics.sh
```

**Expected Output:**

```
🔧 Kafka Bootstrap Server: boot-mznm5shf.c1.kafka-serverless.ap-south-1.amazonaws.com:9098

📝 Creating client.properties...
✅ client.properties created

🪄 Creating Kafka topics...

📌 Creating topic: eeg.raw.data (partitions: 3)
   ✅ Topic 'eeg.raw.data' created successfully

📌 Creating topic: eeg.processed.data (partitions: 3)
   ✅ Topic 'eeg.processed.data' created successfully

📌 Creating topic: user.activity (partitions: 3)
   ✅ Topic 'user.activity' created successfully

📌 Creating topic: alerts.events (partitions: 3)
   ✅ Topic 'alerts.events' created successfully

📌 Creating topic: analytics.triggers (partitions: 3)
   ✅ Topic 'analytics.triggers' created successfully

📋 Verifying created topics:

alerts.events
analytics.triggers
eeg.processed.data
eeg.raw.data
user.activity

🎉 Topic creation completed!
```

### Step 6: Verify Topics (Optional)

List all topics:

```bash
cd /home/ec2-user/kafka_2.12-2.8.1/bin

./kafka-topics.sh \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --command-config client.properties \
  --list
```

Describe a specific topic:

```bash
./kafka-topics.sh \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --command-config client.properties \
  --describe \
  --topic eeg.raw.data
```

## ✅ Topics Created

| Topic Name              | Partitions | Use Case                                  |
|------------------------|------------|-------------------------------------------|
| `eeg.raw.data`         | 3          | Raw EEG sensor data from mobile app      |
| `eeg.processed.data`   | 3          | Processed/analyzed EEG data              |
| `user.activity`        | 3          | User session tracking, app usage events  |
| `alerts.events`        | 3          | Medical alerts, notifications            |
| `analytics.triggers`   | 3          | Analytics events, ML triggers            |

## 🔄 Do You Need to Do This Again?

**NO!** Topics are persistent in MSK Serverless. They survive:
- ECS service restarts
- Deployments
- Code changes

You only need to repeat this process if:
- You create a **new environment** (e.g., production)
- You want to add **new topics** in the future

## 🧹 What Was Removed From Application Code

Previously, each service tried to create topics during startup using Python's `confluent_kafka.admin.AdminClient`. This caused:
- ❌ Transport timeout errors (10-second startup window too short)
- ❌ Race conditions (3 services competing to create same topics)
- ❌ Silent failures (bootstrap failed but services continued)
- ❌ IAM permission complexity (every service needed CreateTopic permission)

**Files Removed:**
- `backEnd/gateway/app/events/kafka_topic_bootstrap.py`
- `backEnd/core-service/app/events/kafka_topic_bootstrap.py`
- `backEnd/eeg-service/app/events/kafka_topic_bootstrap.py`

**Code Changes:**
- Removed `ensure_kafka_topics()` calls from all `main.py` lifespan handlers
- Services now assume topics exist (fail fast if they don't)

## 🐛 Troubleshooting

### "Connection timed out" when creating topics

**Cause**: Bastion can't reach MSK cluster on port 9098

**Fix**:
1. Check bastion security group allows outbound HTTPS (443) and Kafka (9098)
2. Verify bastion is in same VPC as MSK cluster
3. Check MSK cluster security group allows inbound from bastion SG

```bash
# From local machine
aws ec2 describe-security-groups --group-ids <msk-sg-id>
```

### "Unauthorized" errors

**Cause**: Bastion IAM role lacks MSK permissions

**Fix**:
1. Verify terraform applied successfully: `terraform show | grep bastion_msk_policy`
2. Check IAM role attached to bastion instance
3. Wait 5 minutes for IAM policy propagation

### "Topic already exists" warnings

**Not an error!** The script uses `--if-not-exists` flag, so this is safe.

### Topic creation succeeds but services can't produce

**Cause**: ECS services lack `kafka-cluster:WriteData` permission

**Fix**: Verify ECS task role has MSK IAM policy (already configured in `backEnd/infra/modules/ecs/main.tf`)

## 📚 References

- [AWS MSK Serverless Documentation](https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html)
- [MSK IAM Access Control](https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control.html)
- [Kafka CLI Tools Reference](https://kafka.apache.org/documentation/#quickstart)

## 🎯 Summary

✅ **One-time setup** via bastion host  
✅ **AWS recommended approach**  
✅ **No code complexity** in services  
✅ **Reliable & production-grade**  
✅ **Topics persist** across deployments  

Your Kafka cluster is now ready for production! 🚀
