# Project Specifications: Sudan Assessment Registry Integration & Summarisation Tool

## 1. Objective

Automate the end-to-end process of acquiring, validating, and integrating humanitarian assessment data for Sudan from ReliefWeb and ReliefWeb Response, ensuring their inclusion in the OCHA-managed Monday.com Assessment Registry.

**Additional Goals:**
- Ensure historical reconciliation for the last two years.
- Store all assessment documents locally.
- Generate AI-powered summaries grouped by geographic area, using a custom template for internal reporting.

---

## 2. Core Functionalities

### Phase 1: Data Acquisition

#### Overview
The first phase focuses on building a user-friendly Flask web application that enables users to extract, review, and store humanitarian assessment data for Sudan from ReliefWeb and ReliefWeb Response APIs. The application supports flexible querying, metadata extraction, document download, and persistent storage in SQLite.

#### User Flow & Features
- **Web Interface:**  
  Users interact with a web form to select extraction parameters such as country, document type (format), date range, and whether to download full documents or just metadata.
- **API Query:**  
  The backend constructs and sends queries to the ReliefWeb API based on user input, following the API integration guide.
- **Metadata Extraction:**  
  For each assessment, the app extracts metadata fields: title, date, document type, organization, clusters/sectors, geographic tags, language, URL, and file links.
- **Document Download:**  
  If selected, original documents (PDF, DOCX) are downloaded to a local `downloads/` folder.
- **Database Storage:**  
  All extracted metadata is saved in a local SQLite database (`database/sudan_assessments.db`).
- **Review & Export:**  
  Users can review saved metadata in the browser and optionally download metadata or documents.

#### Example Directory Structure for Phase 1

```
sudan-assessment-sync/
│
├── app.py                  # Flask app entry point
├── templates/
│   └── index.html          # Main form UI for parameter selection and feedback
├── downloads/              # Downloaded documents (PDF, DOCX, etc.)
├── database/
│   └── sudan_assessments.db # SQLite database for metadata
├── utils/
│   └── reliefweb_api.py    # Helper functions for querying ReliefWeb API
│   └── db_utils.py         # Helper functions for SQLite operations
└── requirements.txt        # Python dependencies
```

#### Key Implementation Points

- **Flask App (`app.py`):**  
  Handles routing, form submission, and user feedback. Calls utility functions to fetch data and save to the database.
- **Templates (`templates/index.html`):**  
  Provides a simple form for user input and displays messages/results.
- **API Helpers (`utils/reliefweb_api.py`):**  
  Contains logic to build API payloads, send requests, parse responses, and optionally download files.
- **Database Helpers (`utils/db_utils.py`):**  
  Handles SQLite schema creation, metadata insertion, and retrieval for display.
- **Downloads Folder:**  
  Stores all downloaded assessment documents for offline access or further processing.

---

### Phase 2: Registry Integration

- Connect to OCHA-managed Monday.com assessment registry via Monday API.
- Fetch existing registry entries for deduplication and validation.
- Compare with new ReliefWeb assessments (hashes, metadata matching).
- Push only new/unique assessments with full metadata and file attachments to Monday.com.

### Phase 3: Historical Reconciliation

- Retrieve last 2 years of assessments from Monday.com.
- Cross-reference with ReliefWeb archives.
- Identify gaps and upload validated missing entries; flag inconsistencies.

### Phase 4: AI-Based Geographic Summarisation (Planned)

- Group assessments by region (e.g., Darfur, Khartoum).
- Extract structured insights using NLP/LLM tools.
- Populate a predefined template with:
  - Key Needs
  - Target Populations
  - Sector-specific Insights
  - Operational Recommendations
- Output summaries in Markdown/JSON and optionally persist in SQLite or Monday.com.

---

## 3. Technical Stack

| Component         | Technology/Tools                                      |
|-------------------|-------------------------------------------------------|
| Application Core  | Flask (Python)                                        |
| Database          | SQLite (sqlite3)                                      |
| APIs              | ReliefWeb API, ReliefWeb Response API, Monday.com API |
| Document Handling | requests, os, hashlib, tqdm                           |
| NLP/AI            | OpenAI / HuggingFace / LangChain (Future)             |
| Parsing Utilities | pdfplumber, python-docx, PyYAML                       |
| Metadata Logic    | pandas, datetime, re, json                            |

---

## 4. Virtual Environment Requirements (`requirements.txt`)

```
Flask==3.0.3
requests==2.32.3
python-dotenv==1.1.0
pandas==2.2.2
sqlite-utils==3.36
PyYAML==6.0.2
pdfplumber==0.11.0
python-docx==1.2.0
tqdm==4.67.1
retrying==1.3.4
schedule==1.2.2
ace_tools

# Future AI summarisation modules
openai==1.32.0
langchain==0.2.2
transformers==4.43.2
llama-cpp-python==0.2.72
sentence-transformers==3.0.0
```

---

## 5. Development Phases

| Phase      | Tasks                                                                 |
|------------|-----------------------------------------------------------------------|
| ✅ Phase 1 | Download metadata and documents from ReliefWeb and ReliefWeb Response |
| 🔄 Phase 2 | Deduplicate and upload validated assessments to Monday.com            |
| 🔄 Phase 3 | Reconcile historical records (last 2 years)                           |
| 🔜 Phase 4 | Generate AI-based geographic summaries using LLM and templates        |
