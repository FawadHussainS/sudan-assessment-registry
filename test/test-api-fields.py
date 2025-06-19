import requests
from datetime import datetime, timezone
import json

# ReliefWeb API endpoint
url = "https://api.reliefweb.int/v1/reports?appname=sudan-assessment-tool"

# Use a broad query to get a sample of assessment reports for Sudan
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
            }
        ]
    },
    "limit": 5,  # Small sample for field exploration
    "preset": "latest"
}

# Add profile=full to get all possible fields
response = requests.post(
    url + "&profile=full",
    json=payload
)
data = response.json().get("data", [])

# Collect all unique fields and show example data for each
all_fields = set()
example_data = {}

for report in data:
    fields = report.get("fields", {})
    all_fields.update(fields.keys())
    for k, v in fields.items():
        if k not in example_data:
            example_data[k] = v

print("Unique fields available in ReliefWeb API response for Sudan Assessment reports (profile=full):")
for field in sorted(all_fields):
    print(f"- {field}")

print("\nExample data for each field (first occurrence):")
for field in sorted(example_data.keys()):
    print(f"\nField: {field}")
    print(json.dumps(example_data[field], indent=2, ensure_ascii=False))