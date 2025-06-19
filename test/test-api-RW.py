import requests
import pandas as pd
from datetime import datetime, timezone

# ReliefWeb API endpoint
url = "https://api.reliefweb.int/v1/reports?appname=sudan-assessment-tool"

# POST query payload
payload = {
    "filter": {
        "operator": "AND",
        "conditions": [
            {"field": "country", "value": "Sudan"},
            {"field": "format.name", "value": "Assessment"},
            {
                "field": "date.created",
                "value": {
                    "from": "2023-01-01T00:00:00+00:00",
                    "to": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
                }
            },
            {
                "field": "status",
                "value": ["published", "to-review"],
                "operator": "OR"
            }
        ]
    },
    "fields": {
        "include": [
            "title",
            "date.created",
            "source.name",
            "theme.name",
            "format.name",
            "primary_country.name",
            "language.code",
            "url",
            "file.url"
        ]
    },
    "limit": 1000,
    "sort": ["date.created:desc"],
    "preset": "latest"
}

# Send the request
response = requests.post(url, json=payload)
data = response.json()["data"]

# Extract metadata, filter for Sudan only
records = []
for report in data:
    f = report["fields"]
    # Safely extract primary_country
    primary_country = f.get("primary_country")
    if isinstance(primary_country, list) and primary_country:
        country_name = primary_country[0].get("name")
    elif isinstance(primary_country, dict):
        country_name = primary_country.get("name")
    else:
        country_name = None

    if country_name == "Sudan":
        records.append({
            "title": f.get("title"),
            "date_created": f.get("date", {}).get("created"),
            "source": f.get("source", [{}])[0].get("name") if isinstance(f.get("source"), list) and f.get("source") else None,
            "themes": ", ".join(t.get("name") for t in f.get("theme", []) if t.get("name")),
            "format": f.get("format", [{}])[0].get("name") if isinstance(f.get("format"), list) and f.get("format") else None,
            "country": country_name,
            "language": f.get("language", [{}])[0].get("code") if isinstance(f.get("language"), list) and f.get("language") else None,
            "url": f.get("url"),
            "download": f.get("file", [{}])[0].get("url") if isinstance(f.get("file"), list) and f.get("file") else None
        })

df = pd.DataFrame(records)

# Create summary stats (all Sudan only)
summary_by_cluster = df["themes"].value_counts().to_frame("count").reset_index().rename(columns={"index": "cluster"})
summary_by_org = df["source"].value_counts().to_frame("count").reset_index().rename(columns={"index": "organization"})
summary_by_country = df["country"].value_counts().to_frame("count").reset_index().rename(columns={"index": "country"})

# Display main data
print(df.head())

# Return summary tables
print("\nSummary by cluster:")
print(summary_by_cluster)
print("\nSummary by organization:")
print(summary_by_org)
print("\nSummary by country:")
print(summary_by_country)
