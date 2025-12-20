# 🚀 QUICK START - 5 Minutes to Success!

**Follow these 5 simple steps to verify your deployed app is working:**

---

## Step 1️⃣: Check System Health (30 seconds)

**Open this URL in your browser:**
```
https://your-app.vercel.app/api/health
```

**✅ You should see:**
```json
{
  "status": "healthy",
  "redis_connected": true,
  "version": "1.0.0"
}
```

**❌ If redis_connected is false:**
1. Go to https://vercel.com/dashboard
2. Select your project → Settings → Environment Variables
3. Add: `REDIS_URL` = your Redis URL
4. Redeploy

---

## Step 2️⃣: Open the Dashboard (30 seconds)

**Visit:**
```
https://your-app.vercel.app/
```

**✅ You should see:**
- System statistics (Pending, Processing, Completed, Failed)
- Real-time chart
- Recent tasks table
- Clean, professional interface with no errors

---

## Step 3️⃣: Check Workers (1 minute)

**Click "Workers" in the navigation menu**

**✅ You should see:**
- At least one worker listed
- Status: 🟢 Active or 🟡 Idle
- Last heartbeat < 30 seconds ago

**❌ If you see "No workers available":**

**Start a worker on your machine:**
```bash
python -m src.worker.main --worker-id worker-1 --queues default
```

Leave this running! Workers MUST run separately from Vercel.

---

## Step 4️⃣: Submit Your First Task (1 minute)

**Two ways to do this:**

### Option A: Web Interface
1. Click "Tasks" → "+ New Task"
2. Fill in:
   - Task Name: `send_email`
   - Priority: `7`
   - Payload:
     ```json
     {
       "to": "test@example.com",
       "subject": "My First Task!",
       "body": "Testing the task queue"
     }
     ```
3. Click "Submit Task"

### Option B: PowerShell Command
```powershell
$body = @{
    name = "send_email"
    payload = @{
        to = "test@example.com"
        subject = "My First Task!"
        body = "Testing via API"
    }
    priority = 7
    queue = "default"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**✅ Success looks like:**
```
✓ Task submitted successfully!
Task ID: 550e8400-e29b-41d4-a716-446655440000
```

---

## Step 5️⃣: Watch It Complete (1 minute)

**Stay on the Dashboard or Tasks page**

**✅ You should see:**
1. Task appears with status "Pending" (yellow)
2. Status changes to "Processing" (blue) - within 1-2 seconds
3. Status changes to "Completed" (green) - within 1-5 seconds
4. ✨ **No page refresh needed!** Updates happen automatically

**Click the Task ID to see full details:**
- Timestamps (created, started, completed)
- Payload (your data)
- Result (success message)

---

## 🎉 You're Done!

**If all 5 steps worked, your system is fully functional!**

### What You've Verified:
- ✅ API is healthy
- ✅ Redis is connected
- ✅ Workers are running
- ✅ Tasks can be submitted
- ✅ Tasks are processed
- ✅ Real-time updates work

---

## 🧪 Try These Next:

### Test Priority Scheduling:
```powershell
# Submit 3 tasks with different priorities
$high = @{ name = "send_email"; payload = @{}; priority = 10 } | ConvertTo-Json
$med = @{ name = "send_email"; payload = @{}; priority = 5 } | ConvertTo-Json
$low = @{ name = "send_email"; payload = @{}; priority = 1 } | ConvertTo-Json

Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $high
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $med
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $low

# High priority (10) should complete first!
```

### Test Different Task Types:
```powershell
# Data processing task
$data = @{
    name = "process_data"
    payload = @{ data = @(1,2,3,4,5); operation = "sum" }
    priority = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $data

# Image processing task
$image = @{
    name = "process_image"
    payload = @{ url = "https://example.com/image.jpg"; operation = "resize" }
    priority = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $image
```

### Explore the API:
```
Visit: https://your-app.vercel.app/api/docs

Try out all the endpoints in the interactive Swagger UI!
```

---

## 📚 Learn More:

- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete guide with all features explained
- **[TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)** - Comprehensive testing checklist
- **[VISUAL_GUIDE.md](VISUAL_GUIDE.md)** - See what everything should look like
- **[VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)** - Deployment instructions

---

## 🆘 Quick Troubleshooting:

| Problem | Quick Fix |
|---------|-----------|
| redis_connected: false | Set REDIS_URL in Vercel env vars |
| No workers | Run: `python -m src.worker.main --worker-id worker-1 --queues default` |
| Tasks stay pending | Start a worker (see above) |
| Page shows errors | Check browser console (F12) |

---

## 🎯 Complete Test Script:

**Run this entire test in one go:**

```powershell
Write-Host "🚀 Running Complete System Test..." -ForegroundColor Cyan

# Test 1: Health
Write-Host "`n[1/5] Health Check..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/health"
if ($health.redis_connected) {
    Write-Host "✓ PASSED" -ForegroundColor Green
} else {
    Write-Host "✗ FAILED - Redis not connected" -ForegroundColor Red
}

# Test 2: Submit Task
Write-Host "`n[2/5] Submit Task..." -ForegroundColor Yellow
$body = @{
    name = "send_email"
    payload = @{ to = "test@example.com"; subject = "Test" }
    priority = 7
} | ConvertTo-Json

$task = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" `
    -Method POST -ContentType "application/json" -Body $body
Write-Host "✓ PASSED - Task ID: $($task.id)" -ForegroundColor Green

# Test 3: Wait and Check
Write-Host "`n[3/5] Waiting for processing..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

$result = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks/$($task.id)"
Write-Host "✓ Task Status: $($result.status)" -ForegroundColor Green

# Test 4: List Tasks
Write-Host "`n[4/5] List Tasks..." -ForegroundColor Yellow
$tasks = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks?limit=5"
Write-Host "✓ PASSED - Found $($tasks.tasks.Count) tasks" -ForegroundColor Green

# Test 5: Check Workers
Write-Host "`n[5/5] Check Workers..." -ForegroundColor Yellow
$workers = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/workers"
if ($workers.workers.Count -gt 0) {
    Write-Host "✓ PASSED - $($workers.workers.Count) worker(s) active" -ForegroundColor Green
} else {
    Write-Host "⚠ WARNING - No workers running!" -ForegroundColor Yellow
}

Write-Host "`n🎉 Test Complete!" -ForegroundColor Cyan
Write-Host "Visit: https://your-app.vercel.app" -ForegroundColor Cyan
```

**Save as `quick-test.ps1` and run!**

---

**🎊 Congratulations! Your distributed task queue is live and working!**

**Need more help? Check the full [USER_GUIDE.md](USER_GUIDE.md)**
