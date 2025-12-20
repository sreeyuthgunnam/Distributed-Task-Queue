# User Guide - How to Use Your Deployed Task Queue

This guide walks you through using your deployed task queue application step-by-step, from first visit to testing all features.

## Table of Contents
1. [Quick Start - First Time User](#quick-start---first-time-user)
2. [Understanding the Dashboard](#understanding-the-dashboard)
3. [Submitting Your First Task](#submitting-your-first-task)
4. [Monitoring Tasks](#monitoring-tasks)
5. [Managing Queues](#managing-queues)
6. [Viewing Workers](#viewing-workers)
7. [Testing All Features](#testing-all-features)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start - First Time User

### Step 1: Access Your Application

1. **Open your browser** and go to your Vercel URL:
   ```
   https://your-app-name.vercel.app
   ```
   
2. **You should see the Dashboard** with four main sections:
   - Dashboard (Home)
   - Tasks
   - Queues
   - Workers

### Step 2: Verify System is Working

Before submitting tasks, check if everything is healthy:

1. **Check API Health** - Open a new tab and visit:
   ```
   https://your-app-name.vercel.app/api/health
   ```

2. **Expected Response:**
   ```json
   {
     "status": "healthy",
     "redis_connected": true,
     "version": "1.0.0"
   }
   ```

3. **What each field means:**
   - ✅ `status: "healthy"` - API is working
   - ✅ `redis_connected: true` - Database is connected
   - ❌ `redis_connected: false` - **PROBLEM**: Redis not configured (see [Troubleshooting](#troubleshooting))

### Step 3: Check if Workers are Running

**IMPORTANT**: For tasks to be processed, you need workers running!

1. Click **"Workers"** in the navigation menu
2. You should see a list of active workers

**If you see "No workers available":**
- Workers must be running separately (they can't run on Vercel)
- See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) section "Running Workers"
- Quick fix for testing:
  ```bash
  # On your local machine or server
  python -m src.worker.main --worker-id worker-1 --queues default
  ```

---

## Understanding the Dashboard

### Dashboard Overview (Home Page)

When you first load the app, you'll see:

#### 1. **System Stats (Top Cards)**
```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   Pending   │ Processing  │  Completed  │   Failed    │
│     12      │      3      │     245     │      2      │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

- **Pending**: Tasks waiting to be processed
- **Processing**: Tasks currently being worked on
- **Completed**: Successfully finished tasks
- **Failed**: Tasks that encountered errors

#### 2. **Recent Tasks Table**
Shows the most recent tasks with:
- **ID**: Unique identifier (click to see details)
- **Name**: Task type (e.g., "send_email", "process_image")
- **Status**: Current state (badge with color)
- **Priority**: 1-10 (higher = more important)
- **Created**: When the task was submitted
- **Queue**: Which queue it belongs to

#### 3. **Real-time Chart**
- Live graph showing task completion rate
- Updates automatically as tasks are processed
- Green line = Completed, Red line = Failed

---

## Submitting Your First Task

### Method 1: Using the Web Interface

1. **Click "Tasks"** in the navigation menu

2. **Click the "+ New Task" button** (top right)

3. **Fill in the Task Form:**

   **Task Name:** Choose from available handlers
   ```
   ┌─────────────────────────────┐
   │ Task Name                   │
   │ ┌─────────────────────────┐ │
   │ │ send_email           ▼  │ │
   │ └─────────────────────────┘ │
   └─────────────────────────────┘
   ```
   Options:
   - `send_email` - Simulate sending an email
   - `process_data` - Data transformation tasks
   - `process_image` - Image processing tasks

   **Priority:** (1-10, higher = processed first)
   ```
   ┌─────────────────────────────┐
   │ Priority: 5                 │
   │ [━━━━━●━━━━━━]  1────────10 │
   └─────────────────────────────┘
   ```

   **Queue:** Where to send the task
   ```
   ┌─────────────────────────────┐
   │ Queue                       │
   │ ┌─────────────────────────┐ │
   │ │ default              ▼  │ │
   │ └─────────────────────────┘ │
   └─────────────────────────────┘
   ```

   **Payload:** Task-specific data (JSON format)
   ```json
   {
     "to": "user@example.com",
     "subject": "Test Email",
     "body": "This is a test message"
   }
   ```

4. **Click "Submit Task"**

5. **You'll see a success message** with the task ID:
   ```
   ✅ Task submitted successfully!
   Task ID: 550e8400-e29b-41d4-a716-446655440000
   ```

### Method 2: Using the API (Advanced)

#### Using PowerShell:
```powershell
$body = @{
    name = "send_email"
    payload = @{
        to = "test@example.com"
        subject = "Hello from Task Queue"
        body = "This is a test email"
    }
    priority = 7
    queue = "default"
    max_retries = 3
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

Write-Host "Task ID: $($response.id)"
Write-Host "Status: $($response.status)"
```

#### Using curl (Git Bash/WSL):
```bash
curl -X POST https://your-app.vercel.app/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "send_email",
    "payload": {
      "to": "test@example.com",
      "subject": "Hello",
      "body": "Test message"
    },
    "priority": 7,
    "queue": "default"
  }'
```

#### Using JavaScript (Browser Console):
```javascript
fetch('https://your-app.vercel.app/api/tasks', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'send_email',
    payload: {
      to: 'test@example.com',
      subject: 'Hello',
      body: 'Test message'
    },
    priority: 7,
    queue: 'default'
  })
})
.then(r => r.json())
.then(data => console.log('Task ID:', data.id));
```

---

## Monitoring Tasks

### View All Tasks

1. **Click "Tasks"** in the navigation

2. **You'll see a table** with all tasks:
   ```
   ┌─────────────┬──────────────┬──────────┬──────────┬────────────┐
   │     ID      │     Name     │  Status  │ Priority │   Queue    │
   ├─────────────┼──────────────┼──────────┼──────────┼────────────┤
   │ 550e8400... │ send_email   │ [Done]   │    7     │  default   │
   │ 661f9511... │ process_data │ [Active] │    5     │  default   │
   │ 772fa622... │ send_email   │ [Pending]│    3     │  emails    │
   └─────────────┴──────────────┴──────────┴──────────┴────────────┘
   ```

3. **Filter Tasks** using the dropdown filters:
   - **Status**: All, Pending, Processing, Completed, Failed
   - **Queue**: All, default, emails, images, data

### View Task Details

1. **Click on any Task ID** or row

2. **Task Detail Panel opens** showing:
   ```
   ╔══════════════════════════════════════════╗
   ║ Task Details                            ║
   ╠══════════════════════════════════════════╣
   ║ ID: 550e8400-e29b-41d4-a716-446655440000 ║
   ║ Name: send_email                         ║
   ║ Status: ✅ Completed                     ║
   ║ Priority: 7                              ║
   ║ Queue: default                           ║
   ║                                          ║
   ║ Timestamps:                              ║
   ║ • Created: Dec 19, 2025 10:30:00 AM     ║
   ║ • Started: Dec 19, 2025 10:30:05 AM     ║
   ║ • Completed: Dec 19, 2025 10:30:07 AM   ║
   ║                                          ║
   ║ Payload:                                 ║
   ║ {                                        ║
   ║   "to": "user@example.com",             ║
   ║   "subject": "Test Email",              ║
   ║   "body": "This is a test"              ║
   ║ }                                        ║
   ║                                          ║
   ║ Result:                                  ║
   ║ {                                        ║
   ║   "success": true,                       ║
   ║   "message_id": "msg_abc123"            ║
   ║ }                                        ║
   ║                                          ║
   ║ Actions:                                 ║
   ║ [Cancel Task]  [Retry Task]             ║
   ╚══════════════════════════════════════════╝
   ```

### Real-time Updates

**Tasks update automatically!** The page uses WebSocket connections to show live updates:

- ✅ Task starts processing → Status changes to "Processing"
- ✅ Task completes → Status changes to "Completed"
- ❌ Task fails → Status changes to "Failed"
- 🔄 No page refresh needed!

---

## Managing Queues

### View Queue Statistics

1. **Click "Queues"** in the navigation

2. **You'll see all queues** with their stats:
   ```
   ┌─────────────────────────────────────────────────┐
   │ Default Queue                                   │
   ├─────────────┬─────────────┬──────────┬─────────┤
   │  Pending: 5 │Processing: 2│Complete:│Failed: 0│
   │             │             │   128   │         │
   └─────────────┴─────────────┴──────────┴─────────┘

   ┌─────────────────────────────────────────────────┐
   │ Emails Queue                                    │
   ├─────────────┬─────────────┬──────────┬─────────┤
   │  Pending: 3 │Processing: 1│Complete:│Failed: 0│
   │             │             │    45   │         │
   └─────────────┴─────────────┴──────────┴─────────┘
   ```

### Queue Actions

For each queue, you can:

**1. View Details** - Click the queue name
   - Shows all tasks in that queue
   - Detailed statistics
   - Task distribution by status

**2. Pause Queue** - Temporarily stop processing
   - Workers won't pick up new tasks from this queue
   - Useful for maintenance

**3. Resume Queue** - Start processing again
   - Workers resume picking up tasks

**4. Clear Dead Letter Queue** - Remove failed tasks
   - Cleans up tasks that failed after max retries

---

## Viewing Workers

### Worker Status Page

1. **Click "Workers"** in the navigation

2. **See all connected workers:**
   ```
   ┌──────────────────────────────────────────────────┐
   │ Worker: worker-1              Status: 🟢 Active  │
   ├──────────────────────────────────────────────────┤
   │ Queues: default, emails                          │
   │ Tasks Processed: 245                             │
   │ Current Task: send_email (ID: 550e8...)         │
   │ Uptime: 2h 35m                                   │
   │ Last Heartbeat: 2 seconds ago                    │
   └──────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────┐
   │ Worker: worker-2              Status: 🟡 Idle    │
   ├──────────────────────────────────────────────────┤
   │ Queues: images, data                             │
   │ Tasks Processed: 189                             │
   │ Current Task: None                               │
   │ Uptime: 2h 35m                                   │
   │ Last Heartbeat: 1 second ago                     │
   └──────────────────────────────────────────────────┘
   ```

### Understanding Worker Status

- 🟢 **Active (Busy)** - Currently processing a task
- 🟡 **Idle** - Waiting for tasks (healthy)
- 🔴 **Offline** - Not connected (problem!)

---

## Testing All Features

Follow this checklist to verify everything works:

### ✅ Feature Testing Checklist

#### 1. Task Submission ✓
- [ ] Submit a task via web interface
- [ ] Submit a task via API
- [ ] Task appears in "Tasks" list
- [ ] Task has correct priority
- [ ] Task is in correct queue

**Test Command:**
```powershell
# Submit test task
$body = @{ name = "send_email"; payload = @{ to = "test@example.com" }; priority = 5 } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $body
```

#### 2. Task Processing ✓
- [ ] Worker picks up the task
- [ ] Status changes from "Pending" to "Processing"
- [ ] Status changes to "Completed" after processing
- [ ] Processing time is recorded
- [ ] Result is stored

**How to Test:**
1. Submit a task
2. Watch the status change in real-time
3. Click task ID to see full details
4. Verify timestamps and result

#### 3. Priority Scheduling ✓
- [ ] Submit tasks with different priorities (1, 5, 10)
- [ ] Higher priority tasks are processed first
- [ ] Lower priority tasks wait

**Test Commands:**
```powershell
# Submit low priority
$low = @{ name = "send_email"; payload = @{}; priority = 1 } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $low

# Submit high priority
$high = @{ name = "send_email"; payload = @{}; priority = 10 } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $high

# High priority should complete first!
```

#### 4. Retry Mechanism ✓
- [ ] Submit a task that will fail
- [ ] Task automatically retries
- [ ] Retry count increments
- [ ] Task moves to DLQ after max retries

**Test Command:**
```powershell
# Submit task with invalid payload (will fail)
$fail = @{ name = "send_email"; payload = @{ invalid = "data" }; priority = 5; max_retries = 2 } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $fail

# Watch it fail and retry
```

#### 5. Real-time Updates ✓
- [ ] Submit a task
- [ ] Watch dashboard update without refresh
- [ ] Stats update in real-time
- [ ] Chart updates live

**How to Test:**
1. Open Dashboard
2. Submit multiple tasks via API
3. Watch the dashboard update automatically
4. No page refresh needed!

#### 6. Queue Management ✓
- [ ] View all queues
- [ ] See queue statistics
- [ ] Pause a queue
- [ ] Resume a queue
- [ ] Submit task to specific queue

**How to Test:**
1. Go to "Queues" page
2. Click "Pause" on default queue
3. Submit a task
4. Verify task stays pending
5. Click "Resume"
6. Task should process

#### 7. Worker Monitoring ✓
- [ ] View active workers
- [ ] See what each worker is processing
- [ ] See worker statistics
- [ ] Heartbeat shows worker is alive

**How to Test:**
1. Go to "Workers" page
2. Check for connected workers
3. If none, start a worker:
   ```bash
   python -m src.worker.main --worker-id test-worker --queues default
   ```

#### 8. API Health Check ✓
- [ ] Health endpoint returns 200
- [ ] Redis connection is true
- [ ] Version is displayed

**Test:**
```powershell
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/health"
```

#### 9. Error Handling ✓
- [ ] Submit invalid task (should get clear error)
- [ ] Try to access non-existent task (should get 404)
- [ ] Check failed task shows error message

**Test:**
```powershell
# Invalid task name
$invalid = @{ name = "invalid_task"; payload = @{} } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $invalid

# Should get clear error message
```

#### 10. Different Task Types ✓
- [ ] Send email task
- [ ] Process data task
- [ ] Process image task

**Test All Types:**
```powershell
# Email task
$email = @{ name = "send_email"; payload = @{ to = "user@example.com"; subject = "Test" } } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $email

# Data task
$data = @{ name = "process_data"; payload = @{ data = @(1,2,3,4,5) } } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $data

# Image task
$image = @{ name = "process_image"; payload = @{ url = "https://example.com/image.jpg"; operation = "resize" } } | ConvertTo-Json
Invoke-RestMethod -Uri "https://your-app.vercel.app/api/tasks" -Method POST -ContentType "application/json" -Body $image
```

---

## Troubleshooting

### ❌ "No workers available"

**Problem**: Workers page shows no workers

**Solutions:**
1. Workers must run separately from Vercel
2. Start a worker on your local machine:
   ```bash
   python -m src.worker.main --worker-id worker-1 --queues default
   ```
3. Or deploy workers to a server (see [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md))

### ❌ Tasks stay "Pending" forever

**Problem**: Tasks are submitted but never process

**Cause**: No workers are running

**Solution**: Start at least one worker (see above)

### ❌ "redis_connected: false" in health check

**Problem**: API can't connect to Redis

**Solutions:**
1. Check Vercel environment variables:
   - Go to Vercel Dashboard → Your Project → Settings → Environment Variables
   - Verify `REDIS_URL` is set correctly
2. Test Redis connection:
   ```powershell
   # If using Upstash, test from browser
   # Your Redis dashboard should have a "Test" button
   ```
3. Make sure Redis instance is running
4. Check Redis URL format: `redis://[user]:[pass]@[host]:[port]`

### ❌ "Unknown error" when submitting tasks

**Problem**: Task submission fails with generic error

**Solutions:**
1. Check browser console for details (F12 → Console)
2. Check API health: `/api/health`
3. Verify Redis is connected
4. Check payload is valid JSON
5. Ensure task name exists in handlers

### ❌ Tasks fail immediately

**Problem**: Tasks go straight to "Failed" status

**Solutions:**
1. Check task details to see error message
2. Verify payload matches what handler expects
3. Check worker logs for errors
4. Ensure handler is registered correctly

### ❌ Dashboard not updating in real-time

**Problem**: Have to refresh to see changes

**Solutions:**
1. Check browser console for WebSocket errors
2. Ensure your browser supports WebSockets
3. Check if firewall is blocking WebSocket connections
4. Try a different browser

### ❌ Can't access API documentation

**Problem**: `/api/docs` shows 404

**Solution:** Try these URLs:
- `https://your-app.vercel.app/api/docs`
- `https://your-app.vercel.app/api/redoc`
- Make sure you're using the correct Vercel URL

---

## Quick Reference

### Task Names (Handlers)
- `send_email` - Email simulation
- `process_data` - Data transformation
- `process_image` - Image processing

### Priority Levels
- **1-3**: Low priority (processed last)
- **4-6**: Normal priority
- **7-9**: High priority
- **10**: Critical (processed first)

### Task Status
- 🟡 **Pending** - Waiting in queue
- 🔵 **Processing** - Being worked on
- 🟢 **Completed** - Successfully finished
- 🔴 **Failed** - Error occurred

### Important URLs
- Dashboard: `https://your-app.vercel.app/`
- API Docs: `https://your-app.vercel.app/api/docs`
- Health Check: `https://your-app.vercel.app/api/health`
- Tasks API: `https://your-app.vercel.app/api/tasks`

### Common API Endpoints

**Submit Task:**
```
POST /api/tasks
Body: { "name": "send_email", "payload": {...}, "priority": 5 }
```

**Get Task:**
```
GET /api/tasks/{task_id}
```

**List Tasks:**
```
GET /api/tasks?status=pending&limit=10
```

**Get Queues:**
```
GET /api/queues
```

**Get Workers:**
```
GET /api/workers
```

---

## Need More Help?

- **Deployment Issues**: See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)
- **Technical Issues**: See [PRODUCTION_FIXES.md](PRODUCTION_FIXES.md)
- **Testing Locally**: See [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **API Reference**: Visit `/api/docs` on your deployed app

---

**Happy Task Queuing! 🚀**
