# 🌐 ReliefWeb API Integration Guide for Humanitarian Assessment Extraction

## 📍 Overview
The ReliefWeb API offers structured access to humanitarian data including assessments, situation reports, and other publication types. This guide helps backend developers integrate reports tagged with `format.name = "Assessment"` into tools like the Sudan Assessment Registry.

---

## 🔗 Base Endpoint
```
https://api.reliefweb.int/v1/
```

### 📘 Primary Endpoint for Reports
```
GET/POST https://api.reliefweb.int/v1/reports
```
Use `GET` for simple URL-encoded queries. Use `POST` to filter by multiple fields, control returned metadata, and apply more complex logic.

---

## ✅ Common Parameters

| Parameter           | Type     | Description                                           |
|--------------------|----------|-------------------------------------------------------|
| `filter`           | object   | Field-based filtering (e.g., country, format, date)  |
| `query`            | object   | Full-text keyword search (optional)                  |
| `fields.include`   | array    | Metadata fields to return                            |
| `limit`            | int      | Max results per call (default: 10, max: 1000)        |
| `offset`           | int      | Pagination offset                                    |
| `sort`             | array    | Sort results (e.g., `date.created:desc`)             |
| `preset`           | string   | Predefined views like `latest` or `minimal`          |
| `profile`          | string   | Use `list` (default) or `full`                       |
| `appname`          | string   | App identifier for monitoring usage                  |

---

## 🧪 Example POST Query: Sudan Assessments (2023–2025)

```json
POST https://api.reliefweb.int/v1/reports?appname=sudan-assessment-tool
{
  "filter": {
    "operator": "AND",
    "conditions": [
      { "field": "country", "value": "Sudan" },
      { "field": "format.name", "value": "Assessment" },
      {
        "field": "date.created",
        "value": {
          "from": "2023-01-01T00:00:00+00:00",
          "to": "2025-06-18T23:59:59+00:00"
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
      "title", "date.created", "source.name", "theme.name",
      "format.name", "primary_country.name", "language.code",
      "url", "file.url"
    ]
  },
  "limit": 1000,
  "sort": ["date.created:desc"],
  "preset": "latest"
}
```

---

## 🧱 Metadata Fields to Include

| Field               | Description                             |
|--------------------|-----------------------------------------|
| `title`            | Report title                            |
| `date.created`     | Original creation date                  |
| `source.name`      | Publishing organization                 |
| `format.name`      | Document format (e.g., Assessment)      |
| `theme.name`       | Humanitarian clusters                   |
| `primary_country.name` | Main country covered                |
| `language.code`    | Language code (e.g., `en`, `fr`)        |
| `file.url`         | Direct download URL of the document     |
| `url`              | Web page for the report                 |

---

## 📦 Known Format Types (`format.name`)

Below are the most common values for `format.name` used to classify ReliefWeb reports:

- **Assessment**
- **Situation Report**
- **Update**
- **Map**
- **Analysis**
- **Manual and Guidelines**
- **Appeal**
- **Annual Report**
- **Evaluation**
- **Fact Sheet**
- **Press Release**
- **Bulletin**
- **Training Material**
- **Meeting Minutes**
- **Brochure**
- **Flyer**
- **Poster**
- **Infographic**
- **Newsletter**
- **News and Press Release**
- **Guideline**

---

## 🎯 Filter Usage Examples

Include only assessments:
```json
{ "field": "format.name", "value": "Assessment" }
```

Exclude situation reports:
```json
{ "operator": "NOT", "field": "format.name", "value": "Situation Report" }
```

Match any of multiple formats:
```json
{
  "operator": "OR",
  "conditions": [
    { "field": "format.name", "value": "Assessment" },
    { "field": "format.name", "value": "Evaluation" }
  ]
}
```

---

## 📌 List All Format Types (Facet Query)
```http
GET https://api.reliefweb.int/v1/reports?facet[fields][]=format.name
```
Returns all available `format.name` values with counts.

---

## 🧠 Developer Tips

- Always use `appname` in all requests.
- Use `POST` for bulk filters or advanced logic.
- Use `fields.include` to limit response size.
- Paginate results using `limit` and `offset`.

---

## 📚 Helpful Resources

- Official API Docs: [https://apidoc.reliefweb.int/](https://apidoc.reliefweb.int/)
- Example: [https://reliefweb.int/country/sdn](https://reliefweb.int/country/sdn)
