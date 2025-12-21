# Deployment Guide - Railway

## Prerequisites

1. **GitHub Account** (private repos are free)
2. **Railway Account** (free tier available at https://railway.app)
3. **Resend Account** (free tier: 3,000 emails/month at https://resend.com)

## Step-by-Step Deployment

### 1. Create GitHub Repository

1. Go to https://github.com
2. Click "New repository"
3. Name: `multicam-partner-portal`
4. Set to **Private**
5. Initialize with README (optional)
6. Create repository

### 2. Push Code to GitHub

```bash
cd /Users/llepore/Documents/MULTICAM/MCP-3

# Initialize git if not already done
git init
git add .
git commit -m "Initial commit - Multicam Partner Portal"

# Add remote and push
git remote add origin <your-github-repo-url>
git branch -M main
git push -u origin main
```

### 3. Create Railway Account

1. Go to https://railway.app
2. Sign up with GitHub (recommended)
3. Authorize Railway to access your GitHub

### 4. Create Railway Project

1. In Railway dashboard, click "New Project"
2. Select "Deploy from GitHub repo"
3. Select `multicam-partner-portal` repository
4. Railway will start deploying automatically

### 5. Add PostgreSQL Database

1. In Railway project dashboard, click "New"
2. Select "Database" → "Add PostgreSQL"
3. Railway creates PostgreSQL instance
4. `DATABASE_URL` is automatically added as environment variable

### 6. Configure Environment Variables

In Railway project → Variables tab, add:

```
SECRET_KEY=<generate-with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=False
ALLOWED_HOSTS=multicampattern.com,*.railway.app
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<your-resend-api-key>
DEFAULT_FROM_EMAIL=noreply@multicampattern.com
SITE_URL=https://your-project.railway.app
```

**Note:** `DATABASE_URL` is automatically provided by Railway PostgreSQL.

### 7. Get Resend API Key

1. Go to https://resend.com
2. Sign up for free account
3. Go to API Keys section
4. Create new API key
5. Copy the key
6. Add to Railway as `EMAIL_HOST_PASSWORD`

### 8. Run Migrations on Railway

After first deployment succeeds:

**Option A: Railway CLI**
```bash
# Install Railway CLI (if not installed)
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# Run migrations
railway run python manage.py migrate
railway run python manage.py load_initial_data
railway run python manage.py createsuperuser
```

**Option B: Railway Dashboard**
1. Go to project → PostgreSQL → Query tab
2. Or use Railway shell: project → Deployments → Click on deployment → Shell

### 9. Verify Deployment

1. Visit your Railway URL (e.g., `your-project.railway.app`)
2. Test login
3. Test FA submission
4. Check email notifications

### 10. Custom Domain (Optional)

1. In Railway project → Settings → Domains
2. Add custom domain: `multicampattern.com`
3. Railway provides DNS records
4. Update DNS at your domain registrar
5. Railway automatically provisions SSL certificate

## Post-Deployment

### Import Partners

```bash
railway run python manage.py import_printers partners_import.csv
```

> Note: the management command is named `import_printers` for legacy reasons, but it imports **Partners**.

### Import Historical Data (After Export from Google Sheets)

```bash
railway run python manage.py import_historical_fas fa_export.csv
railway run python manage.py import_historical_lots lot_export.csv
railway run python manage.py verify_migration
```

## Monitoring

- **Logs**: Railway dashboard → Deployments → View logs
- **Metrics**: Railway dashboard → Metrics tab
- **Database**: Railway dashboard → PostgreSQL → Query tab

## Troubleshooting

### Deployment Fails

1. Check Railway logs for errors
2. Verify all environment variables are set
3. Check `requirements.txt` is correct
4. Verify `Procfile` syntax

### Database Connection Issues

1. Verify `DATABASE_URL` is set (auto-provided by Railway)
2. Check PostgreSQL is running in Railway
3. Verify migrations ran successfully

### Email Not Sending

1. Verify Resend API key is correct
2. Check `EMAIL_HOST_PASSWORD` environment variable
3. Test email sending in Railway shell:
   ```python
   python manage.py shell
   >>> from django.core.mail import send_mail
   >>> send_mail('Test', 'Test message', 'noreply@multicampattern.com', ['your-email@example.com'])
   ```

## Cost Estimate

**Railway Free Tier:**
- $5 credit/month
- PostgreSQL: 500MB storage (free tier)
- Web service: Basic resources
- Good for development and small production

**If you exceed free tier:**
- PostgreSQL: ~$5/month for 1GB
- Web service: ~$5-10/month for small traffic
- **Total: ~$10-15/month** for small production site

## Security Checklist

- [ ] `DEBUG=False` in production
- [ ] `SECRET_KEY` is strong and unique
- [ ] `ALLOWED_HOSTS` includes your domain
- [ ] SSL/HTTPS enabled (automatic with Railway)
- [ ] Database backups enabled (Railway provides)
- [ ] Email credentials secure (environment variables)

