# Sudan Assessment Registry Integration & Summarisation Tool

## Overview

This project automates the acquisition, validation, and integration of humanitarian assessment data for Sudan from ReliefWeb and ReliefWeb Response, ensuring their inclusion in the OCHA-managed Monday.com Assessment Registry. It also supports historical reconciliation and AI-powered geographic summarisation.

---

## Features

- **User-Friendly Web Interface:**  
  Flask-based web app for selecting extraction parameters (country, format, date range, etc.).
- **Flexible Data Extraction:**  
  Query ReliefWeb and ReliefWeb Response APIs for Sudan-tagged assessments and other document types.
- **Metadata & Document Download:**  
  Extracts metadata (title, date, document type, organization, clusters/sectors, geographic tags, language, URL, etc.) and optionally downloads original documents (PDF, DOCX) to a local `downloads/` folder.
- **SQLite Storage:**  
  Stores all extracted metadata in a local SQLite database (`database/sudan_assessments.db`).
- **Review & Export:**  
  Users can review saved metadata in the browser and optionally download metadata or documents.
- **Extensible:**  
  Designed for future integration with Monday.com and AI-powered summarisation.

---

## Project Structure

```
sudan-assessment-sync/
│
├── app.py                  # Flask app entry point
├── templates/
│   └── index.html          # Main form UI
├── downloads/              # Downloaded documents
├── database/
│   └── sudan_assessments.db
├── utils/
│   └── reliefweb_api.py    # API query helpers
│   └── db_utils.py         # SQLite helpers
└── requirements.txt
```

---

## Getting Started

### 1. Clone the Repository

```sh
git clone <repo-url>
cd sudan-assessment-sync
```

### 2. Create and Activate Virtual Environment

```sh
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies

```sh
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the Application

```sh
python app.py
```

The app will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## Usage

1. Open the web app in your browser.
2. Select extraction parameters (country, format, date range, etc.).
3. Choose whether to download documents or only metadata.
4. Submit the form to extract and save data.
5. Review and export metadata from the app.

---

## Requirements

See `requirements.txt` for all dependencies.

---

## Development Phases

| Phase      | Tasks                                                                 |
|------------|-----------------------------------------------------------------------|
| ✅ Phase 1 | Download metadata and documents from ReliefWeb and ReliefWeb Response |
| 🔄 Phase 2 | Deduplicate and upload validated assessments to Monday.com            |
| 🔄 Phase 3 | Reconcile historical records (last 2 years)                           |
| 🔜 Phase 4 | Generate AI-based geographic summaries using LLM and templates        |

---

## License

[Specify your license]