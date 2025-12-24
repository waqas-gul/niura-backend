# 🔧 VPC Endpoints Deployment Guide

## Problem Solved
This fixes the intermittent ECR connection timeouts that cause 9-10 minute deployments:
- ❌ **Before**: ECS tasks fail to pull images with `dial tcp 13.234.X.X:443: i/o timeout`
- ✅ **After**: All ECR traffic routes through AWS private network (no internet dependency)

---

## What Was Added

### 1. **VPC Endpoints Module** (`modules/vpc-endpoints/`)
Creates the following AWS VPC endpoints:

#### **Interface Endpoints** (with security groups):
- `ecr.api` - ECR API calls (GetAuthorizationToken, etc.)
- `ecr.dkr` - Docker registry operations (docker pull)
- `sts` - AWS Security Token Service (IAM role assumptions)
- `logs` - CloudWatch Logs (faster log shipping)

#### **Gateway Endpoint** (no security group needed):
- `s3` - S3 access (ECR stores image layers in S3)

### 2. **Security Group**
- Allows ECS tasks to reach endpoints via HTTPS (port 443)
- Attached to all interface endpoints

### 3. **Network Module Updates**
- Added `route_table_id` output for S3 gateway endpoint

---

## Deployment Steps

### Step 1: Initialize Terraform
```bash
cd backEnd/infra
terraform init
```

### Step 2: Plan the Changes
```bash
terraform plan -var-file=envs/staging.tfvars
```

**Expected output**:
- Will create ~6 new resources (5 endpoints + 1 security group)
- Should show 0 resources to destroy
- Review the plan carefully

### Step 3: Apply the Changes
```bash
terraform apply -var-file=envs/staging.tfvars
```

Type `yes` when prompted.

**This will take 2-3 minutes** as AWS creates the interface endpoint ENIs.

---

## Verification

### 1. Check VPC Endpoints in AWS Console
1. Go to **VPC Console** → **Endpoints**
2. You should see:
   - `niura-staging-ecr-api-endpoint`
   - `niura-staging-ecr-dkr-endpoint`
   - `niura-staging-sts-endpoint`
   - `niura-staging-s3-endpoint`
   - `niura-staging-logs-endpoint`
3. Verify all show **Status: Available**

### 2. Check from Terraform
```bash
terraform output vpc_endpoints_status
```

### 3. Verify Interface Endpoint ENIs
In AWS Console: **VPC** → **Network Interfaces**
- Filter by the endpoint security group
- Should see ENIs in both availability zones (ap-south-1a and ap-south-1b)

---

## Force ECS to Use New Endpoints

After Terraform apply completes, force ECS services to restart:

```bash
# Gateway service
aws ecs update-service \
  --cluster niura-staging-cluster \
  --service niura-staging-gateway-svc \
  --force-new-deployment

# Core service
aws ecs update-service \
  --cluster niura-staging-cluster \
  --service niura-staging-core-service-svc \
  --force-new-deployment

# EEG service
aws ecs update-service \
  --cluster niura-staging-cluster \
  --service niura-staging-eeg-service-svc \
  --force-new-deployment
```

**OR** use your existing deployment scripts:
```bash
cd backEnd
./deploy-all.sh
```

---

## Monitor for Success

### Watch ECS Task Events
```bash
aws ecs describe-services \
  --cluster niura-staging-cluster \
  --services niura-staging-gateway-svc \
  --query "services[0].events[0:5]" \
  --output table
```

### What to Look For:
✅ **SUCCESS**: Tasks start without ECR timeout errors
❌ **OLD ERROR** (should not appear anymore): 
```
ResourceInitializationError: unable to pull registry auth from Amazon ECR: 
There is a connection issue... dial tcp 13.234.X.X:443: i/o timeout
```

### Expected Deployment Time:
- **Before**: 9-10 minutes (with retries)
- **After**: 2-3 minutes (no retries needed)

---

## Testing ECR Connectivity

### From ECS Task (Optional)
If you want to verify the endpoints are working:

1. **Get a task ID**:
```bash
aws ecs list-tasks --cluster niura-staging-cluster --service-name niura-staging-gateway-svc
```

2. **Execute command in task** (if enabled):
```bash
aws ecs execute-command \
  --cluster niura-staging-cluster \
  --task <TASK_ID> \
  --container gateway \
  --interactive \
  --command "/bin/sh"
```

3. **Test ECR connectivity**:
```bash
# Inside the container
nslookup api.ecr.ap-south-1.amazonaws.com
# Should resolve to a private IP (10.0.X.X)

curl -v https://api.ecr.ap-south-1.amazonaws.com
# Should connect successfully
```

---

## Cost Impact

### Interface Endpoints
- **Cost**: ~$0.01 per hour per endpoint per AZ
- **4 endpoints × 2 AZs**: ~$5-6 per month
- **Worth it?** YES - saves time and prevents deployment failures

### Gateway Endpoint (S3)
- **Cost**: FREE (no hourly charges, only data transfer)

---

## Rollback (If Needed)

If something goes wrong, you can destroy just the endpoints:

```bash
terraform destroy -target=module.vpc_endpoints -var-file=envs/staging.tfvars
```

---

## Benefits

1. ✅ **Faster Deployments**: 2-3 minutes instead of 9-10 minutes
2. ✅ **Reliable**: No more intermittent ECR timeout failures
3. ✅ **Secure**: Traffic never leaves AWS private network
4. ✅ **Lower Latency**: Direct connection to ECR within VPC
5. ✅ **Cost Effective**: Eliminates NAT Gateway costs for ECR traffic

---

## Next Steps

After VPC endpoints are working:

1. **Monitor deployment times** over next few deployments
2. **Remove public IPs from ECS tasks** (optional):
   - Move tasks to private subnets
   - Update ECS module: `assign_public_ip = false`
   - Saves costs and improves security
3. **Add VPC Flow Logs** (optional):
   - Monitor VPC traffic patterns
   - Troubleshoot future networking issues

---

## Troubleshooting

### Endpoints show "Available" but tasks still timeout
- Verify security group allows HTTPS from ECS tasks
- Check DNS resolution: `private_dns_enabled = true`
- Ensure endpoints are in same subnets as ECS tasks

### Terraform apply fails
- Check ECS module creates security group first
- Verify `depends_on = [module.ecs]` in vpc_endpoints module

### Tasks can't reach internet after adding endpoints
- Gateway endpoint doesn't affect internet access
- Check route table still has IGW route
- Verify ECS tasks still have public IPs (`assign_public_ip = true`)

---

## Support

If issues persist:
1. Check CloudWatch Logs for ECS tasks
2. Review VPC Flow Logs (if enabled)
3. Verify endpoint ENI status in VPC console
4. Check security group rules for port 443 access
