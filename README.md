# 4GMC

4GMC is a FastAPI application that prepares and publishes a US-focused Shopify storefront. It automates business details, policies and pages, products, collections, inventory, GMC product identifiers, branded Gemini images, USA market configuration, and free US shipping.

The dashboard is protected by an administrator password. Store data and encrypted Shopify credentials are kept in `data/`. Claude Fable 5 is accessed through SmartAPI for content generation, and Gemini 3.1 Flash Image creates the branded product gallery.

## Run locally

On Windows, copy `.env.example` to `.env`, fill in the private values, and double-click **Launch 4GMC.bat**. Choose:

1. **Local preview** for dashboard work without Shopify OAuth.
2. **Live Shopify store** when an HTTPS tunnel forwards to the local server.

You can validate the launcher configuration without starting the server:

```powershell
python local_launcher.py --check
```

Or start the app directly:

```powershell
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

## Connect Shopify

Shopify OAuth requires one stable public HTTPS origin. Register these values in the Shopify app:

```text
App URL: https://YOUR_APP_DOMAIN
Allowed redirect URL: https://YOUR_APP_DOMAIN/api/shopify/callback
```

Set `PUBLIC_URL` to the same origin. In **Connections**, add the destination `.myshopify.com` address and authorize the store. Existing `SHOPIFY_CLIENT_ID` and `SHOPIFY_CLIENT_SECRET` environment variables remain the fallback credentials for the first store.

The app currently requests product, inventory, location, publication, content, legal-policy, market, and shipping scopes. A store must reconnect after new required scopes are added.

## Automated content workflow

1. Under **Business & brand**, enter the destination store name, customer-facing domain, contact email, physical address, country, currency, and phone. Live chat and business hours use the fixed support text in the form.
2. Under **Pages & policies**, enter the source storefront. 4GMC uses the public page structure as a reference, then creates destination-brand content using the saved business facts. It creates fallback About, Contact, and FAQ pages where required.
3. Under **Products**, enter a public storefront. 4GMC selects physical products, groups them into collections, prepares original destination-brand copy, configures inventory, creates a three-image branded gallery, publishes each product, and verifies the live result.
4. Under **Store design**, upload the logo and favicon, choose the brand colors, and generate the complete store preview after all required content succeeds.

There is no manual content-review step before the configured automatic publication actions. Use only accurate destination-business details and source material you are authorized to adapt. The application helps maintain consistency but cannot guarantee Google Merchant Center approval.

## Product imagery

Gemini model `gemini-3.1-flash-image` creates hero, detail, and lifestyle images. Each request uses the source product facts, destination brand name, saved colors, and uploaded logo. The generator may place the logo on physically plausible product surfaces. 4GMC then composites the exact uploaded logo into a consistent corner badge on every final image.

The generated base64 image is sent to Shopify as an attachment. A generation or upload failure stops that product before publication, and unchanged completed galleries are not uploaded twice.

## GMC product identification

Every imported product records its destination brand, condition, product type, Google category, availability, SKU, MPN, GTIN status, identifier source, and inventory source. GTINs are checksum-validated and never invented. Private-label products without an authorized destination-brand GTIN receive a stable destination-brand MPN and SKU.

## USA market and shipping

After connecting Shopify, use **Connections > Review USA setup** to inspect the changes. **Apply USA market & free shipping** activates the USA market and replaces eligible merchant rates with USD 0.00. App-owned carrier and fulfillment rates are not modified.

## Hosting

The production target is a private GitHub repository connected to a Render Docker web service. `render.yaml` defines:

- a Frankfurt web service;
- a health check at `/api/health`;
- private environment values;
- a persistent disk mounted at `/app/data` for the current SQLite storage.

Read [DEPLOYMENT.md](DEPLOYMENT.md) before creating the service. A persistent disk requires a paid Render service and limits the app to one running instance. PostgreSQL and a separate job worker are the planned scaling path for larger multi-store use.

## Verification

Run every application check from PowerShell:

```powershell
Get-ChildItem tests\test_*.py | Sort-Object Name | ForEach-Object {
  python $_.FullName
  if ($LASTEXITCODE -ne 0) { throw "Test failed: $($_.Name)" }
}
```

GitHub Actions runs the same checks after every push and pull request.

Live Shopify publishing still needs an authorized development or test store before production use. Direct Google Merchant Center account authorization, Shopify theme publication, navigation automation, PostgreSQL migration, and background jobs remain separate milestones.
