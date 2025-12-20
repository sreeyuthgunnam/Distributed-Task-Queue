# Quick Testing Checklist - Deployed Application

Use this checklist to quickly verify all features are working on your deployed site.

## 📋 Pre-Flight Checks

### 1. Basic Access
```
□ Can access https://your-app.vercel.app
□ Dashboard loads without errors
□ Navigation menu works (Dashboard, Tasks, Queues, Workers)
```

### 2. System Health
**Visit: `https://your-app.vercel.app/api/health`**

```json
Expected Response:
{
  "status": "healthy",          ← Should be "healthy"
  "redis_connected": true,      ← MUST be true
  "version": "1.0.0"
}
```

```
□ API returns 200 OK
□ status is "healthy"
□ redis_connected is true
```

⚠️ **If redis_connected is false:**
- Go to Vercel Dashboard → Settings → Environment Variables
- Add/verify: `REDIS_URL=redis://your-redis-host:6379`
- Redeploy

### 3. Workers Running
**Go to: Workers page**

```
□ At least one worker is shown
□ Worker status is Active (🟢) or Idle (🟡)
□ Last heartbeat is recent (< 30 seconds)
```

⚠️ **If no workers:**
```bash
# Start worker locally
python -m src.worker.main --worker-id worker-1 --queues default
```

---

## 🧪 Feature Tests

### Test 1: Submit Task via Web Interface

**Steps:**
1. Go to "Tasks" page
2. Click "+ New Task"
3. Fill in:
   - Name: `send_email`
   - Priority: `7`
   - Queue: `default`
   - Payload:
     ```json
     {
       "to": "test@example.com",
       "subject": "Test",
       "body": "Testing task submission"
     }
     ```
4. Click "Submit Task"

**Expected Result:**
```
□ Success message appears
□ Task appears in task list
□ Task status is "Pending" (then changes to "Processing")
□ Task completes within 5 seconds
□ Status changes to "Completed" (green badge)
```

---

### Test 2: Submit Task via API

**PowerShell Command:**
```powershell
$body = @{
    name = "send_email"
    payload = @{
        to = "api-test@example.com"
        subject = "API Test"
        body = "Testing API submission"
    }
    priority = 5
    queue = "default"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

Write-Host "✓ Task ID: $($result.id)"
Write-Host "✓ Status: $($result.status)"
```

**Expected Result:**
```
□ Command succeeds (no errors)
□ Returns task ID (UUID format)
□ Status is "pending"
□ Task appears in dashboard
```

---

### Test 3: Priority Scheduling

**Submit 3 tasks with different priorities:**

```powershell
# High priority (10)
$high = @{ name = "send_email"; payload = @{ to = "high@example.com" }; priority = 10 } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $high

# Medium priority (5)
$med = @{ name = "send_email"; payload = @{ to = "med@example.com" }; priority = 5 } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $med

# Low priority (1)
$low = @{ name = "send_email"; payload = @{ to = "low@example.com" }; priority = 1 } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $low
```

**Expected Result:**
```
□ High priority (10) completes first
□ Medium priority (5) completes second
□ Low priority (1) completes last
```

---

### Test 4: Real-time Updates

**Steps:**
1. Open Dashboard in browser
2. Keep browser visible
3. Run this in PowerShell:
   ```powershell
   1..5 | ForEach-Object {
       $body = @{ name = "send_email"; payload = @{}; priority = 5 } | ConvertTo-Json
       Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $body
       Start-Sleep -Seconds 1
   }
   ```
4. Watch the dashboard

**Expected Result:**
```
□ Dashboard updates automatically (no page refresh)
□ Task count increases in real-time
□ Chart updates with new data
□ Tasks appear in the list automatically
```

---

### Test 5: Task Details

**Steps:**
1. Go to "Tasks" page
2. Click on any Task ID

**Expected Result:**
```
□ Detail panel opens
□ Shows all task information:
  - ID, Name, Status
  - Priority, Queue
  - Timestamps (Created, Started, Completed)
  - Payload (JSON)
  - Result (JSON)
□ Actions available (Cancel/Retry if applicable)
```

---

### Test 6: Multiple Task Types

**Test all three handlers:**

```powershell
# 1. Email Task
$email = @{ name = "send_email"; payload = @{ to = "user@example.com"; subject = "Test" } } | ConvertTo-Json
$r1 = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $email
Write-Host "Email Task: $($r1.id)"

# 2. Data Task
$data = @{ name = "process_data"; payload = @{ data = @(1,2,3,4,5) } } | ConvertTo-Json
$r2 = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $data
Write-Host "Data Task: $($r2.id)"

# 3. Image Task
$image = @{ name = "process_image"; payload = @{ url = "https://example.com/image.jpg" } } | ConvertTo-Json
$r3 = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $image
Write-Host "Image Task: $($r3.id)"
```

**Expected Result:**
```
□ All three tasks submit successfully
□ All three tasks complete
□ Each task type shows different results
```

---

### Test 7: Queue Management

**Steps:**
1. Go to "Queues" page
2. Find "default" queue
3. Click "Pause"
4. Submit a task
5. Verify task stays pending
6. Click "Resume"
7. Task should process

**Expected Result:**
```
□ Can view all queues
□ Queues show statistics (pending, processing, completed)
□ Can pause queue
□ Can resume queue
□ Tasks respect queue pause state
```

---

### Test 8: Worker Monitoring

**Steps:**
1. Go to "Workers" page
2. Observe worker information

**Expected Result:**
```
□ Shows worker ID
□ Shows worker status (Active/Idle)
□ Shows queues worker is listening to
□ Shows task count processed
□ Shows current task (if processing)
□ Heartbeat timestamp updates
```

---

### Test 9: Error Handling

**Test invalid task:**
```powershell
# Invalid task name
$invalid = @{ name = "nonexistent_task"; payload = @{} } | ConvertTo-Json
try {
    Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $invalid
} catch {
    Write-Host "Error caught (expected):"
    Write-Host $_.Exception.Message
}
```

**Expected Result:**
```
□ Returns clear error message (not "Unknown error")
□ Error message explains what's wrong
□ HTTP status code is appropriate (400, 404, 503)
```

---

### Test 10: API Documentation

**Visit: `https://your-app.vercel.app/api/docs`**

**Expected Result:**
```
□ Swagger UI loads
□ Shows all endpoints:
  - POST /api/tasks
  - GET /api/tasks
  - GET /api/tasks/{id}
  - GET /api/queues
  - GET /api/workers
□ Can test endpoints from Swagger UI
```

---

## 📊 Performance Tests

### Bulk Task Submission

**Submit 10 tasks at once:**
```powershell
Write-Host "Submitting 10 tasks..."
$start = Get-Date

1..10 | ForEach-Object {
    $body = @{ name = "send_email"; payload = @{ to = "bulk-$_@example.com" }; priority = 5 } | ConvertTo-Json
    Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $body | Out-Null
}

$elapsed = (Get-Date) - $start
Write-Host "✓ Completed in $($elapsed.TotalSeconds) seconds"
Write-Host "✓ Average: $($elapsed.TotalSeconds / 10) seconds per task"
```

**Expected Result:**
```
□ All tasks submit successfully
□ Submission takes < 5 seconds total
□ Tasks process in order of priority
□ All tasks complete successfully
```

---

## 🎯 Final Verification

### System Overview

**Go to Dashboard and verify:**
```
□ Stats show correct totals
□ Recent tasks list populated
□ Chart shows activity
□ No errors in browser console (F12)
```

### All Pages Working
```
□ Dashboard page loads
□ Tasks page loads
□ Queues page loads
□ Workers page loads
```

### Core Functionality
```
□ Can submit tasks
□ Tasks are processed
□ Can view task details
□ Real-time updates work
□ All task types work
□ Queues are manageable
□ Workers are visible
□ Errors are descriptive
```

---

## 🐛 If Something Fails

### Check These First:

1. **API Health**
   ```
   Visit: https://your-app.vercel.app/api/health
   Verify: redis_connected = true
   ```

2. **Worker Status**
   ```
   Workers page should show at least one worker
   Status should be Active or Idle (not offline)
   ```

3. **Browser Console**
   ```
   Press F12 → Console tab
   Look for errors (red messages)
   ```

4. **Vercel Logs**
   ```
   Vercel Dashboard → Your Project → Deployments
   Click latest deployment → View Function Logs
   ```

### Common Issues:

| Problem | Solution |
|---------|----------|
| redis_connected: false | Set REDIS_URL in Vercel env vars |
| No workers | Start worker separately |
| Tasks stay pending | No worker running |
| Unknown error | Check browser console for details |
| 404 errors | Check URL is correct |

---

## ✅ Success Criteria

**Your deployment is fully functional if:**

- ✅ Health check passes
- ✅ At least one worker connected
- ✅ Can submit tasks via web & API
- ✅ Tasks are processed (status changes to completed)
- ✅ Real-time updates work
- ✅ All three task types work
- ✅ Priority scheduling works
- ✅ Error messages are clear
- ✅ All pages load without errors

---

## 📝 Quick Test Script

**Run this complete test:**

```powershell
Write-Host "🚀 Starting Complete System Test..." -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "`n[1/5] Testing API health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/health"
    if ($health.redis_connected) {
        Write-Host "✓ Health check PASSED" -ForegroundColor Green
    } else {
        Write-Host "✗ Redis not connected!" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Health check FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Task Submission
Write-Host "`n[2/5] Submitting test task..." -ForegroundColor Yellow
try {
    $body = @{
        name = "send_email"
        payload = @{ to = "test@example.com"; subject = "System Test" }
        priority = 7
    } | ConvertTo-Json
    
    $task = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    
    Write-Host "✓ Task submitted: $($task.id)" -ForegroundColor Green
    $taskId = $task.id
} catch {
    Write-Host "✗ Task submission FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Task Retrieval
Write-Host "`n[3/5] Retrieving task..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
try {
    $retrieved = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks/$taskId"
    Write-Host "✓ Task retrieved: Status = $($retrieved.status)" -ForegroundColor Green
} catch {
    Write-Host "✗ Task retrieval FAILED" -ForegroundColor Red
}

# Test 4: List Tasks
Write-Host "`n[4/5] Listing all tasks..." -ForegroundColor Yellow
try {
    $tasks = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks?limit=5"
    Write-Host "✓ Found $($tasks.tasks.Count) tasks" -ForegroundColor Green
} catch {
    Write-Host "✗ Task listing FAILED" -ForegroundColor Red
}

# Test 5: Workers Check
Write-Host "`n[5/5] Checking workers..." -ForegroundColor Yellow
try {
    $workers = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/workers"
    if ($workers.workers.Count -gt 0) {
        Write-Host "✓ Found $($workers.workers.Count) worker(s)" -ForegroundColor Green
    } else {
        Write-Host "⚠ No workers running!" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Workers check FAILED" -ForegroundColor Red
}

Write-Host "`n🎉 Test Complete!" -ForegroundColor Cyan
```

**Save this as `test-deployment.ps1` and run: `.\test-deployment.ps1`**

---

**Need help? See [USER_GUIDE.md](USER_GUIDE.md) for detailed instructions!**
