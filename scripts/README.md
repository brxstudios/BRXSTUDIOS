# Meta (Facebook/Instagram) active-ads reporting

Two scripts, no dependencies beyond Python 3.8+:

- `fb_active_ads.py` — pulls every **ACTIVE** ad from one or all ad accounts → JSON + CSV
- `fb_ads_report.py` — turns that JSON into a readable markdown report

`effective_status=ACTIVE` already accounts for paused parents, so an ad only
shows up here if its campaign and ad set are live too — i.e. it is genuinely
eligible to deliver.

## 1. Get an access token

Business Manager → **Business Settings → Users → System Users** → add a system
user with access to the ad account → **Generate new token** → select your app →
check the **`ads_read`** scope. System user tokens don't expire, which is what
you want for recurring reports.

Quick alternative for a one-off: [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
→ pick your app → add `ads_read` → Generate Access Token. These expire in ~1 hour.

## 2. Find the ad account ID

Ads Manager URL contains `act_XXXXXXXXXX`, or leave it unset and the script
sweeps every active account the token can see.

## 3. Run it

```bash
export META_ACCESS_TOKEN="EAA..."
export META_AD_ACCOUNT_ID="act_1234567890"     # optional

python3 scripts/fb_active_ads.py --insights last_30d
python3 scripts/fb_ads_report.py out/fb-active-ads-*.json > report.md
```

`--insights` accepts any Meta date preset: `today`, `last_7d`, `last_30d`,
`this_month`, `maximum`. Omit it for a faster structural pull with no metrics.

Other flags: `--account`, `--out`, `--format json|csv|both`, `--api-version`.

## 4. Getting a report from Claude

**Option A — run locally, hand over the JSON.** Run step 3 on your machine and
drop the JSON into the session (or commit it to a `reports/` folder). No
credentials ever touch the sandbox.

**Option B — let Claude run the pull.** The remote sandbox's network policy
blocks `graph.facebook.com` by default. Allow that host in the environment's
network settings and set `META_ACCESS_TOKEN` / `META_AD_ACCOUNT_ID` as
environment variables there, then Claude can run both scripts on request.

Never paste the token into chat — set it as an environment variable or a
secret. Don't commit tokens or the pulled `out/` data to the repo.
