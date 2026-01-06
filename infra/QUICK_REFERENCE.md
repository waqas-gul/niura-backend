# Quick Reference: Local vs Cloud Deployment

## Summary

| Component | Local (Docker Compose) | AWS Cloud | 
|-----------|----------------------|-----------|
| **Redis** | `docker-compose up redis` | **ElastiCache** cluster |
| **Celery Worker** | Docker container | **ECS Fargate** task |
| **Gateway** | Docker container | **ECS** with ALB |
| **Networking** | Docker bridge network | **VPC + Security Groups** |
| **Deployment** | `docker-compose up` | **Terraform + ECR push** |
| **Scaling** | Manual | **Auto-scaling policies** |
| **Cost** | $0 (local compute) | ~$92/month (staging) |

---

## What You Need to Do:

### 1. ✅ **Infrastructure (Terraform)**

You need to add 2 new modules to your `infra/` directory:

#### Files Created:
- ✅ `infra/modules/redis/main.tf` - ElastiCache Redis
- ✅ `infra/modules/redis/variables.tf`
- ✅ `infra/modules/redis/outputs.tf`
- ✅ `infra/modules/eeg-worker/main.tf` - Celery worker ECS service
- ✅ `infra/modules/eeg-worker/variables.tf`
- ✅ `infra/modules/eeg-worker/outputs.tf`
- ✅ `infra/CLOUD_DEPLOYMENT_GUIDE.md` - Complete deployment guide

#### Update Required:
- ❌ `infra/main.tf` - Add module calls (see deployment guide section 3)
- ❌ `infra/modules/ecs/main.tf` - Update task definitions with REDIS_URL

---

### 2. ✅ **Docker Images**

You already have the Dockerfiles:
- ✅ `backEnd/eeg-service/Dockerfile` - Already optimized with uvloop
- ✅ `backEnd/eeg-service/Dockerfile.worker` - Celery worker
- ✅ `backEnd/gateway/Dockerfile` - Gateway

What you need to do:
```bash
# Build and push to ECR
docker build -t eeg-service:latest ./eeg-service
docker tag eeg-service:latest <ECR_URL>/niura-staging-eeg-service:latest
docker push <ECR_URL>/niura-staging-eeg-service:latest

docker build -f ./eeg-service/Dockerfile.worker -t eeg-worker:latest ./eeg-service
docker tag eeg-worker:latest <ECR_URL>/niura-staging-eeg-worker:latest
docker push <ECR_URL>/niura-staging-eeg-worker:latest
```

---

### 3. ✅ **Configuration**

No code changes needed! You already have:
- ✅ `backEnd/eeg-service/app/core/celery_app.py` - Celery config
- ✅ `backEnd/eeg-service/app/tasks/eeg_processing.py` - Task definitions
- ✅ `backEnd/eeg-service/app/routes/fft_eeg_controller.py` - Fire-and-forget endpoint
- ✅ `backEnd/docker-compose.override.yml` - Local optimizations

Only environment variables need updating in AWS:
- Add `REDIS_URL=redis://<elasticache-endpoint>:6379/0` to ECS task definitions

---

## Step-by-Step Checklist:

### Phase 1: Infrastructure (30 minutes)
- [ ] Update `infra/main.tf` with Redis and Worker modules
- [ ] Update `infra/modules/ecs/main.tf` with REDIS_URL env var
- [ ] Run `terraform init`
- [ ] Run `terraform plan -var-file=envs/staging.tfvars`
- [ ] Run `terraform apply -var-file=envs/staging.tfvars`
- [ ] Wait for ElastiCache (5-10 minutes)

### Phase 2: Docker Images (20 minutes)
- [ ] Build eeg-service image
- [ ] Build eeg-worker image
- [ ] Build gateway image with 8 workers
- [ ] Tag all images for ECR
- [ ] Push to ECR

### Phase 3: Deployment (10 minutes)
- [ ] Update ECS services with new task definitions
- [ ] Force new deployment
- [ ] Watch CloudWatch logs for startup
- [ ] Verify worker is processing tasks

### Phase 4: Testing (10 minutes)
- [ ] Run k6 load test against staging ALB
- [ ] Verify p50 < 800ms
- [ ] Check CloudWatch metrics
- [ ] Monitor auto-scaling

---

## Key Differences: Local vs Cloud

### Redis:
```bash
# Local
REDIS_URL=redis://redis:6379/0  # Docker service name

# Cloud
REDIS_URL=redis://niura-staging-redis.abc123.0001.aps1.cache.amazonaws.com:6379/0
```

### Celery Worker:
```yaml
# Local (docker-compose.yml)
eeg-worker:
  build:
    context: ./eeg-service
    dockerfile: Dockerfile.worker
  environment:
    - REDIS_URL=redis://redis:6379/0

# Cloud (ECS Task Definition)
{
  "image": "123456.dkr.ecr.ap-south-1.amazonaws.com/niura-staging-eeg-worker:latest",
  "environment": [
    {
      "name": "REDIS_URL",
      "value": "redis://<elasticache-endpoint>:6379/0"
    }
  ]
}
```

### Gateway:
```yaml
# Local (docker-compose.override.yml)
gateway:
  command: >
    uvicorn app.main:app --workers 8 --loop uvloop --http httptools

# Cloud (ECS Task Definition)
{
  "command": [
    "uvicorn", "app.main:app",
    "--workers", "8",
    "--loop", "uvloop",
    "--http", "httptools"
  ],
  "cpu": 1024,
  "memory": 2048
}
```

---

## Costs Breakdown:

### Staging (~$92/month):
- ElastiCache (t4g.micro): **$12**
- EEG Worker (2 tasks): **$60**
- Additional gateway resources: **$10**
- Data transfer + logs: **$10**

### Production (~$600/month):
- ElastiCache (r7g.large x2): **$320**
- EEG Worker (4-10 tasks): **$240**
- Additional gateway resources: **$30**
- Data transfer + logs: **$10**

---

## Monitoring After Deployment:

```bash
# Check Redis
aws elasticache describe-replication-groups

# Check worker status
aws ecs describe-services --cluster niura-staging-cluster --services niura-staging-eeg-worker

# Watch worker logs
aws logs tail /ecs/niura-staging/eeg-worker --follow

# Check queue length
aws cloudwatch get-metric-statistics \
  --namespace niura/staging \
  --metric-name CeleryQueueLength \
  --statistics Average \
  --start-time 2025-12-25T00:00:00Z \
  --end-time 2025-12-25T23:59:59Z \
  --period 300
```

---

## Rollback Strategy:

If deployment fails:
```bash
# Destroy new resources
terraform destroy -target=module.redis -target=module.eeg_worker -var-file=envs/staging.tfvars

# Revert ECS services
aws ecs update-service \
  --cluster niura-staging-cluster \
  --service niura-staging-eeg-service \
  --task-definition <PREVIOUS_REVISION>
```

---

## FAQ:

**Q: Do I need to change my application code?**  
A: No! All code changes are already done locally. Just deploy to cloud.

**Q: Can I test locally before cloud deployment?**  
A: Yes! Use `docker-compose` with the override file. Everything works the same.

**Q: How much will this cost?**  
A: Staging: ~$92/month. Production: ~$600/month. You can start with staging.

**Q: Can I use my local Redis instead of ElastiCache?**  
A: No. Local Redis won't be accessible from AWS ECS. You need ElastiCache or EC2-hosted Redis.

**Q: What if auto-scaling is too aggressive?**  
A: Tune the scaling policies in `modules/eeg-worker/main.tf` (target values, cooldown periods).

---

**Ready to deploy? Follow the full guide in `CLOUD_DEPLOYMENT_GUIDE.md`!** 🚀
