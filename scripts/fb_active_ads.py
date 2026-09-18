#!/usr/bin/env python3
"""Pull every ACTIVE ad from one or more Meta (Facebook/Instagram) ad accounts.

Uses only the Python standard library.

Auth:
  export META_ACCESS_TOKEN="EAA..."      # needs ads_read
  export META_AD_ACCOUNT_ID="act_123..." # optional; omit to sweep all accounts

Usage:
  python3 scripts/fb_active_ads.py                      # all accounts the token can see
  python3 scripts/fb_active_ads.py --account act_123    # one account
  python3 scripts/fb_active_ads.py --insights last_30d  # attach spend/impressions
  python3 scripts/fb_active_ads.py --out ./out --format both
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_API_VERSION = "v23.0"
GRAPH = "https://graph.facebook.com"

AD_FIELDS = ",".join([
    "id",
    "name",
    "status",
    "effective_status",
    "created_time",
    "updated_time",
    "preview_shareable_link",
    "campaign{id,name,objective,effective_status,start_time,stop_time}",
    "adset{id,name,effective_status,daily_budget,lifetime_budget,optimization_goal,"
    "start_time,end_time}",
    "creative{id,name,title,body,thumbnail_url,object_story_id,"
    "effective_object_story_id,instagram_permalink_url}",
])

CSV_COLUMNS = [
    "account_id", "account_name", "campaign_name", "campaign_objective",
    "adset_name", "adset_daily_budget", "ad_id", "ad_name", "effective_status",
    "created_time", "updated_time", "creative_title", "creative_body",
    "preview_link", "spend", "impressions", "clicks", "ctr", "cpc",
]


class GraphError(RuntimeError):
    pass


def graph_get(path, params, token, api_version, retries=4):
    """GET a Graph API edge, retrying on throttles and transient 5xx."""
    query = dict(params)
    query["access_token"] = token
    url = f"{GRAPH}/{api_version}/{path.lstrip('/')}?{urllib.parse.urlencode(query)}"
    return _get_url(url, retries)


def _get_url(url, retries=4):
    delay = 2
    last_error = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            try:
                detail = json.loads(body)["error"]
            except Exception:
                detail = {"message": body[:500]}
            code = detail.get("code")
            # 4 = app throttle, 17 = user throttle, 613 = rate limit, 80004 = ads throttle
            transient = exc.code >= 500 or code in (4, 17, 613, 80000, 80004)
            last_error = GraphError(
                f"Graph API {exc.code}: {detail.get('message', '?')} "
                f"(code={code}, subcode={detail.get('error_subcode')})"
            )
            if not transient or attempt == retries:
                raise last_error
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            blocked = "403" in reason or "Tunnel connection failed" in reason
            last_error = GraphError(
                f"Network error reaching graph.facebook.com: {reason}."
                + (" The network policy is blocking Meta — run this script somewhere"
                   " with egress to graph.facebook.com." if blocked else "")
            )
            # A proxy/policy denial will never succeed on retry; fail fast.
            if blocked or attempt == retries:
                raise last_error
        time.sleep(delay)
        delay *= 2
    raise last_error


def paged(path, params, token, api_version):
    """Yield every node across cursor-paginated pages."""
    page = graph_get(path, params, token, api_version)
    while True:
        for node in page.get("data", []):
            yield node
        next_url = page.get("paging", {}).get("next")
        if not next_url:
            return
        page = _get_url(next_url)


def normalize_account_id(raw):
    raw = str(raw).strip()
    return raw if raw.startswith("act_") else f"act_{raw}"


def list_ad_accounts(token, api_version):
    accounts = list(paged(
        "me/adaccounts",
        {"fields": "id,name,account_status,currency", "limit": 200},
        token,
        api_version,
    ))
    # account_status 1 == ACTIVE; keep everything else out of the sweep.
    return [a for a in accounts if a.get("account_status") == 1]


def fetch_active_ads(account_id, token, api_version, insights_preset=None):
    fields = AD_FIELDS
    if insights_preset:
        fields += (
            f",insights.date_preset({insights_preset})"
            "{spend,impressions,clicks,ctr,cpc,reach,actions}"
        )
    params = {
        "fields": fields,
        # effective_status already accounts for paused parents, so ACTIVE here
        # means the ad is genuinely eligible to deliver.
        "effective_status": json.dumps(["ACTIVE"]),
        "limit": 50 if insights_preset else 100,
    }
    return list(paged(f"{account_id}/ads", params, token, api_version))


def flatten(ad, account_id, account_name):
    campaign = ad.get("campaign") or {}
    adset = ad.get("adset") or {}
    creative = ad.get("creative") or {}
    insight = ((ad.get("insights") or {}).get("data") or [{}])[0]
    return {
        "account_id": account_id,
        "account_name": account_name,
        "campaign_name": campaign.get("name", ""),
        "campaign_objective": campaign.get("objective", ""),
        "adset_name": adset.get("name", ""),
        "adset_daily_budget": adset.get("daily_budget", ""),
        "ad_id": ad.get("id", ""),
        "ad_name": ad.get("name", ""),
        "effective_status": ad.get("effective_status", ""),
        "created_time": ad.get("created_time", ""),
        "updated_time": ad.get("updated_time", ""),
        "creative_title": creative.get("title", ""),
        "creative_body": (creative.get("body", "") or "").replace("\n", " ")[:300],
        "preview_link": ad.get("preview_shareable_link", ""),
        "spend": insight.get("spend", ""),
        "impressions": insight.get("impressions", ""),
        "clicks": insight.get("clicks", ""),
        "ctr": insight.get("ctr", ""),
        "cpc": insight.get("cpc", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Pull all ACTIVE Meta ads.")
    parser.add_argument("--account", default=os.environ.get("META_AD_ACCOUNT_ID"),
                        help="Ad account id (act_123 or 123). Omit to sweep all.")
    parser.add_argument("--token", default=os.environ.get("META_ACCESS_TOKEN"),
                        help="Access token with ads_read. Prefer META_ACCESS_TOKEN env.")
    parser.add_argument("--insights", metavar="DATE_PRESET",
                        help="Attach spend/impressions, e.g. last_7d, last_30d.")
    parser.add_argument("--api-version", default=DEFAULT_API_VERSION)
    parser.add_argument("--out", default="out", help="Output directory.")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    args = parser.parse_args()

    if not args.token:
        parser.error("No access token. Set META_ACCESS_TOKEN or pass --token.")

    if args.account:
        accounts = [{"id": normalize_account_id(args.account), "name": args.account}]
    else:
        print("No --account given; listing ad accounts this token can see...",
              file=sys.stderr)
        accounts = list_ad_accounts(args.token, args.api_version)
        if not accounts:
            print("This token has no active ad accounts.", file=sys.stderr)
            return 1
        print(f"Found {len(accounts)} active ad account(s).", file=sys.stderr)

    rows, raw = [], []
    for account in accounts:
        account_id, account_name = account["id"], account.get("name", "")
        print(f"Fetching active ads for {account_id} ({account_name})...",
              file=sys.stderr)
        ads = fetch_active_ads(account_id, args.token, args.api_version, args.insights)
        print(f"  {len(ads)} active ad(s).", file=sys.stderr)
        for ad in ads:
            ad["_account_id"] = account_id
            ad["_account_name"] = account_name
            raw.append(ad)
            rows.append(flatten(ad, account_id, account_name))

    os.makedirs(args.out, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    if args.format in ("json", "both"):
        path = os.path.join(args.out, f"fb-active-ads-{stamp}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(raw, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}", file=sys.stderr)
    if args.format in ("csv", "both"):
        path = os.path.join(args.out, f"fb-active-ads-{stamp}.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {path}", file=sys.stderr)

    print(f"\nTotal active ads: {len(rows)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GraphError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)
