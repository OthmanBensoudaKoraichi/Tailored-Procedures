Here is your complete `README.md` file, formatted cleanly and professionally for a law review replication repository.

You can copy this directly into `README.md`.

---

# Arizona Supreme Court Rulemaking & Administrative Orders Dataset

### Replication Repository

This repository contains the full data construction pipeline used to build a structured dataset of:

1. **Arizona Supreme Court rulemaking orders ("Blackbooks")**
2. **Arizona Supreme Court administrative orders (1956–2024)**

The codebase converts archival court documents into machine-readable format, extracts individual orders, identifies the body of rules amended, constructs issuance dates, and classifies rules as local or statewide.

The pipeline is designed for **law review transparency and replicability**.

---

# Repository Structure

```
project_root/
│
├── code/
│   ├── blackbook_markdown_converter.py
│   ├── blackbook_cleaner.py
│   ├── blackbook_rules_processing.ipynb
│   └── scraper.py
│
├── files/
│   ├── blackbooks/
│   │   ├── initial_format/        (original PDF/DOCX files)
│   │   ├── md_format_raw/         (machine-converted Markdown)
│   │   └── md_format_clean/       (cleaned Markdown)
│   │
│   └── order_extraction/
│       ├── extracted_orders_all_files.xlsx
│       ├── extracted_rule_bodies.xlsx
│       ├── extracted_rule_bodies_llm_regex.xlsx
│       └── az_court_orders.xlsx
│
├── .env
└── README.md
```

---

# Part I — Blackbook Rulemaking Dataset Construction

---

## Step 1: Document Conversion (PDF/DOCX → Markdown)

**Script:** `code/blackbook_markdown_converter.py`

### Method

* Uses Azure Document Intelligence (`prebuilt-layout` model)
* Converts PDF and DOCX to structured Markdown
* Preserves headings, hierarchy, and tables
* Maintains page boundaries using `---` separators

This is not simple OCR. The model infers document structure using machine learning.

**Input:**
`files/blackbooks/initial_format/`

**Output:**
`files/blackbooks/md_format_raw/`

---

## Step 2: Overlap Removal (1971–1975)

**Script:** `code/blackbook_cleaner.py`

Two Blackbook volumes overlap (1971–1975). To prevent double counting:

* Pre-1975 content is removed from:

  ```
  Blackbook 1971-1980.md
  ```
* The cleaned file is renamed:

  ```
  Blackbook 1975-1980.md
  ```

All other files are copied unchanged.

**Output directory:**
`files/blackbooks/md_format_clean/`

This guarantees:

* 1961–1975 coverage from the earlier file
* 1975–1980 coverage from the cleaned file
* No duplicate orders

---

## Step 3: Order-Level Extraction (LLM-Assisted)

**Notebook:** `code/blackbook_rules_processing.ipynb`

### Objective

Extract each individual court order from the Markdown files.

### Procedure

1. Files are chunked (~5000 characters).
2. Chunk boundaries extend to the next "Effective" line.
3. GPT-5-mini is used with structured output (Pydantic schema).
4. Extracted fields:

   * `order_title`
   * `filed_date`
   * `dated_date`
   * `approved_date`
   * `effective_date`

### Issued Year Rule (Deterministic Priority)

Issued year is assigned using:

1. Filed date
2. Dated date
3. Approved date
4. Effective date

Duplicates are removed using normalized title + effective date.

**Output:**

```
files/order_extraction/extracted_orders_all_files.xlsx
```

Total extracted orders: **2,157**

---

## Step 4: Splitting Orders by Body of Rules

Some orders amend multiple bodies of rules. Each body is separated into its own row.

### Method

* Deterministic extraction of metadata (bracket codes, dates)
* GPT-5 structured output used only to split rule systems
* Metadata reattached after splitting
* Conservative deduplication applied

**Output:**

```
files/order_extraction/extracted_rule_bodies.xlsx
```

---

## Step 5: Issued Date Construction

A unified `issued_date` column is created using:

```
filed_date
→ dated_date
→ approved_date
→ effective_date
```

The first non-null value is used.

---

## Step 6: Local vs Statewide Classification

Three parallel classification strategies are implemented:

### 1. Strict Deterministic

Flags orders containing:

```
"local rules"
```

### 2. Expanded Deterministic

Flags as local if:

* Mentions an Arizona county
* Mentions Superior, Justice, or Municipal Court

### 3. LLM Classification

Binary GPT-5 classification:

```
1 = Local rule
0 = Statewide rule
```

Outputs include:

* Local Rule (Strict)
* Local Rule (Expanded)
* Local Rule (LLM)
* Statewide equivalents

**Output:**

```
files/order_extraction/extracted_rule_bodies_llm_regex.xlsx
```

Comparison summary:

* Strict Local: 190
* Expanded Local: 195
* LLM Local: 77

This enables robustness analysis across classification methods.

---

# Part II — Administrative Orders Dataset (1956–2024)

---

## Script: `code/scraper.py`

### Source

Arizona Supreme Court website:
[https://www.azcourts.gov/orders](https://www.azcourts.gov/orders)

### Coverage

1956–2024

### Method

* Requests + BeautifulSoup
* Handles two URL formats (pre-2016 and post-2016 restructuring)
* Extracts:

  * Order number
  * Description
  * Date signed
  * PDF link
  * Year

Includes 1-second delay between requests.

**Output:**

```
files/order_extraction/az_court_orders.xlsx
```

---

# Dependencies

### Core Python

* pandas
* tqdm
* requests
* beautifulsoup4
* openpyxl
* python-dotenv

### Azure

* azure-ai-document-intelligence
* azure-core

Requires `.env` file containing:

```
AZURE_KEY=your_key
AZURE_ENDPOINT=your_endpoint
```

### LLM

* langchain_openai
* GPT-5-compatible API access

---

# Reproducibility Instructions

To reproduce the dataset:

1. Place original Blackbook files in:

   ```
   files/blackbooks/initial_format/
   ```

2. Run document conversion:

   ```
   python code/blackbook_markdown_converter.py
   ```

3. Clean overlapping period:

   ```
   python code/blackbook_cleaner.py
   ```

4. Run rule extraction:

   ```
   python code/blackbook_rules_processing.ipynb
   ```

5. (Optional) Scrape administrative orders:

   ```
   python code/scraper.py
   ```

---

# Research Design Principles

This pipeline was constructed to satisfy:

* Law review replication standards
* Transparent transformation steps
* Conservative deduplication
* Deterministic issuance-year logic
* Parallel classification strategies
* Structured LLM output only

LLMs are used only for:

1. Extracting order blocks
2. Splitting rule systems

All dates and metadata are handled deterministically.

No substantive doctrinal interpretation is delegated to the model.

---

# Contact

For replication questions or dataset clarification, please contact Daniel Bernal.

