#!/usr/bin/env python3
"""Turn fb_active_ads.py JSON output into a readable markdown report.

Usage:
  python3 scripts/fb_ads_report.py out/fb-active-ads-*.json > report.md
"""

import argparse
import json
import sys
from collections import defaultdict


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def first_insight(ad):
    return ((ad.get("insights") or {}).get("data") or [{}])[0]


def main():
    parser = argparse.ArgumentParser(description="Report on active Meta ads.")
    parser.add_argument("json_file", help="JSON produced by fb_active_ads.py")
    args = parser.parse_args()

    with open(args.json_file, encoding="utf-8") as fh:
        ads = json.load(fh)

    if not ads:
        print("# Active Meta Ads\n\nNo active ads found.")
        return 0

    has_insights = any(first_insight(ad) for ad in ads)
    tree = defaultdict(lambda: defaultdict(list))
    for ad in ads:
        account = f"{ad.get('_account_name') or ad.get('_account_id')}"
        campaign = (ad.get("campaign") or {}).get("name", "(no campaign)")
        tree[account][campaign].append(ad)

    total_spend = sum(num(first_insight(a).get("spend")) for a in ads)
    total_impr = sum(num(first_insight(a).get("impressions")) for a in ads)
    total_clicks = sum(num(first_insight(a).get("clicks")) for a in ads)

    print("# Active Meta Ads\n")
    print(f"**{len(ads)} active ads** across {len(tree)} account(s) "
          f"and {sum(len(c) for c in tree.values())} campaign(s).\n")
    if has_insights:
        ctr = (total_clicks / total_impr * 100) if total_impr else 0.0
        print(f"- Spend: **{total_spend:,.2f}**")
        print(f"- Impressions: **{total_impr:,.0f}**")
        print(f"- Clicks: **{total_clicks:,.0f}** (CTR {ctr:.2f}%)\n")

    for account, campaigns in sorted(tree.items()):
        print(f"\n## {account}\n")
        ranked = sorted(
            campaigns.items(),
            key=lambda kv: -sum(num(first_insight(a).get("spend")) for a in kv[1]),
        )
        for campaign, campaign_ads in ranked:
            objective = (campaign_ads[0].get("campaign") or {}).get("objective", "")
            spend = sum(num(first_insight(a).get("spend")) for a in campaign_ads)
            header = f"### {campaign}"
            meta = [f"{len(campaign_ads)} ads"]
            if objective:
                meta.append(objective)
            if has_insights:
                meta.append(f"spend {spend:,.2f}")
            print(f"{header}\n_{' · '.join(meta)}_\n")

            by_adset = defaultdict(list)
            for ad in campaign_ads:
                by_adset[(ad.get("adset") or {}).get("name", "(no ad set)")].append(ad)

            for adset, adset_ads in sorted(by_adset.items()):
                print(f"- **{adset}**")
                for ad in sorted(adset_ads, key=lambda a: a.get("name", "")):
                    insight = first_insight(ad)
                    line = f"  - {ad.get('name', '(unnamed)')} — `{ad.get('id', '')}`"
                    if has_insights and insight:
                        line += (f" — spend {num(insight.get('spend')):,.2f}, "
                                 f"{num(insight.get('impressions')):,.0f} impr, "
                                 f"CTR {num(insight.get('ctr')):.2f}%")
                    print(line)
                print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
