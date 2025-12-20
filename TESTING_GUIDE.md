# Quick Testing Guide

## Before Testing: Start Redis

Choose one option:

### Option 1: Docker (Recommended for Local Testing)
```bash
# Make sure Docker Desktop is running first!
docker-compose up redis -d

# Verify Redis is running
docker ps | grep redis
```

### Option 2: Redis Manually (Windows)
Download from: https://github.com/microsoftarchive/redis/releases
Or use Chocolatey:
```bash
choco install redis-64
redis-server
```

### Option 3: Use Cloud Redis (Skip to Vercel Deployment)
Sign up for Upstash: https://upstash.com/

## Local Testing (If you have Redis running)

### 1. Start the API Server
```bash
cd "c:\Users\sreey\Documents\Projects\Distributed Task Queue"

# Option A: Direct Python
python -m uvicorn src.api.main:app --reload

# Option B: Docker
docker-compose up api
```

### 2. Test Health Endpoint
Open browser or use curl:
```bash
# Browser: http://localhost:8000/api/health

# PowerShell:
Invoke-RestMethod -Uri "http://localhost:8000/api/health"
```

Expected output:
```json
{
  "status": "healthy",
  "redis_connected": true,
  "version": "1.0.0"
}
```

### 3. Start a Worker
Open a new terminal:
```bash
cd "c:\Users\sreey\Documents\Projects\Distributed Task Queue"
python -m src.worker.main --worker-id worker-1 --queues default
```

You should see:
```
Starting worker: worker-1
Listening to queues: ['default']
Worker started successfully
```

### 4. Submit a Test Task

#### Using PowerShell:
```powershell
$body = @{
    name = "send_email"
    payload = @{
        to = "test@example.com"
        subject = "Test Email"
        body = "This is a test"
    }
    priority = 5
    queue = "default"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/tasks" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

#### Using curl:
```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "send_email",
    "payload": {
      "to": "test@example.com",
      "subject": "Test Email",
      "body": "This is a test"
    },
    "priority": 5,
    "queue": "default"
  }'
```

Expected response:
```json
{
  "id": "some-uuid-here",
  "status": "pending",
  "queue": "default",
  "message": "Task submitted successfully"
}
```

### 5. Check Worker Logs
In the worker terminal, you should see:
```
Processing task: some-uuid-here
Task send_email completed successfully
```

## Testing on Vercel (Production)

### 1. Deploy to Vercel
```bash
# Option A: Vercel CLI
vercel --prod

# Option B: GitHub push (if connected)
git add .
git commit -m "Fix production issues"
git push
```

### 2. Set Environment Variables in Vercel Dashboard
1. Go to https://vercel.com/dashboard
2. Select your project
3. Go to Settings → Environment Variables
4. Add: `REDIS_URL` = your Redis connection string

### 3. Test Health Endpoint
```bash
# Replace with your actual Vercel URL
curl https://your-app.vercel.app/api/health
```

### 4. Run Worker Locally with Cloud Redis
```bash
# Set environment variable to point to cloud Redis
$env:REDIS_URL="redis://your-cloud-redis-url:6379"

# Start worker
python -m src.worker.main --worker-id worker-1 --queues default
```

### 5. Submit Task to Production
```powershell
$body = @{
    name = "send_email"
    payload = @{
        to = "test@example.com"
        subject = "Test"
    }
    priority = 5
    queue = "default"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

## Common Issues and Solutions

### ❌ "Redis broker not initialized"
**Cause**: Redis is not running or REDIS_URL is incorrect

**Solution**:
1. Check Redis is running: `docker ps` or `redis-cli ping`
2. Verify REDIS_URL in .env or environment variables
3. Check API logs for connection errors

### ❌ "Unknown error" when submitting tasks
**Cause**: Fixed by our changes! If you still see this:

**Solution**:
1. Make sure you've deployed the latest code
2. Check `/api/health` - should show specific error now
3. Look at Vercel function logs for details

### ❌ Tasks stay "pending" forever
**Cause**: No worker is running

**Solution**:
1. Start at least one worker
2. Worker must connect to same Redis as API
3. Check worker logs for connection errors

### ❌ "ConnectionRefusedError" in worker
**Cause**: Can't connect to Redis

**Solution**:
```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connection
python -c "import redis; r=redis.Redis(host='localhost', port=6379); print(r.ping())"

# If using Docker, make sure Redis container is up
docker-compose up redis -d
```

## Quick Verification Checklist

- [ ] Redis is running (local or cloud)
- [ ] API server starts without errors
- [ ] `/api/health` returns "healthy" with `redis_connected: true`
- [ ] Worker starts and connects successfully
- [ ] Task submission returns task ID
- [ ] Worker logs show task processing
- [ ] Task completes successfully

## Need Help?

1. Check logs:
   - API: Console where you ran uvicorn
   - Worker: Console where you ran worker
   - Vercel: Dashboard → Deployments → Function Logs

2. Test Redis directly:
   ```bash
   docker exec -it taskqueue-redis redis-cli
   > PING
   PONG
   > KEYS *
   ```

3. Review error messages:
   - Now much more descriptive!
   - Will tell you exactly what's wrong
   - Connection, validation, or server issues clearly identified
