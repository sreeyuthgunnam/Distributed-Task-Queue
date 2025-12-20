# Vercel Deployment Guide

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Redis Instance**: You need a cloud-hosted Redis instance accessible from the internet

## Setting Up Redis

### Option 1: Upstash Redis (Recommended)

1. Go to [upstash.com](https://upstash.com/)
2. Sign up for a free account
3. Create a new Redis database
4. Select a region close to your Vercel deployment region
5. Copy the Redis URL (format: `redis://default:password@host:port`)

### Option 2: Redis Labs

1. Go to [redis.com](https://redis.com/try-free/)
2. Sign up and create a free database
3. Copy the connection URL

## Deploying to Vercel

### Method 1: Using Vercel CLI

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Login to Vercel:
   ```bash
   vercel login
   ```

3. Deploy:
   ```bash
   vercel
   ```

4. Set environment variables:
   ```bash
   vercel env add REDIS_URL
   ```
   Paste your Redis URL when prompted.

### Method 2: Using Vercel Dashboard

1. Push your code to GitHub
2. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
3. Click "New Project"
4. Import your GitHub repository
5. Configure environment variables:
   - Go to "Environment Variables"
   - Add `REDIS_URL` with your Redis connection string
   - Optionally add other variables from `.env.vercel.example`
6. Click "Deploy"

## Environment Variables

Required:
- `REDIS_URL`: Your Redis connection string

Optional:
- `DEFAULT_QUEUE`: Default queue name (default: "default")
- `TASK_TIMEOUT`: Task timeout in seconds (default: 300)
- `MAX_RETRIES`: Maximum retry attempts (default: 3)
- `LOG_LEVEL`: Logging level (default: "INFO")

## Verifying Deployment

1. After deployment, visit your Vercel URL
2. Check health endpoint: `https://your-app.vercel.app/api/health`
3. Should return:
   ```json
   {
     "status": "healthy",
     "redis_connected": true,
     "version": "1.0.0"
   }
   ```

## Important Notes

### Serverless Limitations

Vercel uses serverless functions which have some limitations:

1. **No Background Workers**: Workers cannot run on Vercel (serverless functions)
   - You need to run workers separately (local machine, VPS, or other cloud service)
   - Workers need network access to your Redis instance

2. **Cold Starts**: First request after idle period may be slower

3. **Execution Time Limits**: 
   - Free tier: 10 seconds max
   - Pro tier: 60 seconds max
   - Tasks should complete within these limits

### Running Workers

Workers MUST run separately from Vercel:

**Option A: Local Machine**
```bash
python -m src.worker.main --worker-id worker-1 --queues default
```

**Option B: Cloud VPS (DigitalOcean, AWS EC2, etc.)**
Deploy your worker code to a VPS and run as a background service:
```bash
# Using systemd
sudo systemctl start task-worker
```

**Option C: Docker Container (AWS ECS, Google Cloud Run, etc.)**
Use the provided Dockerfile.worker:
```bash
docker build -f docker/Dockerfile.worker -t task-worker .
docker run -e REDIS_URL=your-redis-url task-worker
```

## Troubleshooting

### "Unknown error" when submitting tasks

1. **Check Redis Connection**:
   - Visit `/api/health` endpoint
   - Verify `redis_connected` is `true`

2. **Verify Environment Variables**:
   - Go to Vercel dashboard → Your Project → Settings → Environment Variables
   - Ensure `REDIS_URL` is set correctly

3. **Check Redis Access**:
   - Ensure your Redis instance allows connections from Vercel IPs
   - Most cloud Redis providers allow all IPs by default

4. **View Logs**:
   - Go to Vercel dashboard → Your Project → Deployments
   - Click on the latest deployment → View Function Logs

### Redis connection fails

- Verify your Redis URL format: `redis://[username]:[password]@[host]:[port]`
- Check if Redis instance is running
- Verify network access from Vercel to Redis
- For Upstash, ensure TLS is configured if required

### Tasks not processing

- Remember: Workers CANNOT run on Vercel
- Ensure at least one worker is running somewhere with access to Redis
- Check worker logs for errors
- Verify worker is connected to the same Redis instance

## Cost Considerations

### Free Tier Includes:
- Vercel: 100GB bandwidth, unlimited deployments
- Upstash Redis: 10,000 commands/day
- Perfect for testing and small projects

### Production Recommendations:
- Upstash Redis Pro: $0.20 per 100K commands
- Vercel Pro: $20/month for better performance
- Dedicated VPS for workers: $5-10/month (DigitalOcean, Linode)

## Next Steps

1. Deploy to Vercel
2. Set up Redis instance
3. Configure environment variables
4. Test with `/api/health`
5. Run workers on separate infrastructure
6. Start submitting tasks!

For more details, see the main [README.md](README.md)
