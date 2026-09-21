# Deploy 4GMC to Render

## What this deployment creates

The repository includes a `render.yaml` Blueprint for one Docker web service in Frankfurt. A 1 GB persistent disk is mounted at `/app/data`, which is where the current SQLite databases are stored. The service exposes `/api/health` for Render health checks.

Only one web instance can use this disk. Do not enable autoscaling while 4GMC uses SQLite. Move the application to PostgreSQL before adding a worker or additional web instances.

## 1. Create the private GitHub repository

Create a private repository named `4gmc-shopify-app`. Do not add a GitHub README, `.gitignore`, or license because this project already includes them.

The following paths must never be uploaded:

```text
.env
data/
.venv/
__pycache__/
*.db
```

They are covered by `.gitignore`, but confirm they are absent from the repository after the first push.

## 2. Push the project

From this folder, use the repository URL GitHub displays after creation:

```powershell
git init
git add .
git commit -m "Prepare 4GMC for Render"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/4gmc-shopify-app.git
git push -u origin main
```

If GitHub created a repository with a different name, use its exact URL on the `git remote add` line.

## 3. Create the Render service

Recommended Blueprint flow:

1. In Render, choose **New > Blueprint**.
2. Connect the private GitHub repository.
3. Select the repository and `render.yaml`.
4. Confirm the Frankfurt region and the paid 512 MB service.
5. Enter every secret requested by the Blueprint.

Manual web-service flow:

1. Choose **New Web Service** and connect the private GitHub repository.
2. Select **Docker** as the runtime.
3. Set the region to **Frankfurt**.
4. Set the health check path to `/api/health`.
5. Add a persistent disk with mount path `/app/data` and size 1 GB.
6. Add the environment variables listed below.

A free Render web service cannot attach the persistent disk required by the current SQLite implementation.

## 4. Configure environment values

Set these in Render. Do not add them to GitHub.

| Variable | Value |
| --- | --- |
| `PUBLIC_URL` | Exact public HTTPS origin, without a trailing slash |
| `ADMIN_PASSWORD` | Unique dashboard password |
| `SESSION_SECRET` | Long random value; the Blueprint can generate it |
| `TOKEN_ENCRYPTION_KEY` | Fernet key generated using the command below |
| `SMARTAPI_KEY` | SmartAPI server key |
| `GEMINI_API_KEY` | Google Gemini server key |
| `SHOPIFY_CLIENT_ID` | Shopify app Client ID |
| `SHOPIFY_CLIENT_SECRET` | Shopify app Client Secret |

Generate the Fernet encryption key locally:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

After Render creates the service, copy its exact HTTPS URL into `PUBLIC_URL`, then redeploy. The URL will resemble:

```text
https://4gmc-shopify-app.onrender.com
```

## 5. Configure the Shopify application

Publish a Shopify app version using:

```text
App URL: https://YOUR_RENDER_DOMAIN
Allowed redirect URL: https://YOUR_RENDER_DOMAIN/api/shopify/callback
API version: 2026-07
```

The current 4GMC backend performs the authorization-code callback itself. Its Shopify installation-flow configuration must match that implementation. Install the app on a development or test store before using a live merchant store.

## 6. Verify the deployment

Open:

```text
https://YOUR_RENDER_DOMAIN/api/health
```

A healthy instance returns:

```json
{"ok": true}
```

Then open the main domain, sign in, save a test-store connection, and complete Shopify authorization. Verify a single test product and page before running complete-store generation.

## Security checks

- Never commit `.env`, Shopify tokens, SmartAPI keys, Gemini keys, database files, or uploaded customer assets.
- Keep the GitHub repository private.
- Keep the Render service public over HTTPS, because Shopify must reach its OAuth callback.
- Rotate any key that has appeared in a screenshot or message.
- Back up the Render disk before major deployments.
- Replace SQLite with PostgreSQL before multi-instance scaling.
