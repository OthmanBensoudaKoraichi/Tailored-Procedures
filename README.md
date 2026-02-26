## Overview

This repository contains the full data processing and extraction pipeline used to conduct the underlying analysis and production of Figures 1-3 of Tailored Procedures, published by New York University Law Review in 2026.  It analyzes the volume and type of Arizona Supreme Court rulemaking and administrative orders issued since 1961. 

The repository documents every stage of the workflow, from raw document acquisition to structured datasets and published figures. All scripts are deterministic and reproducible, and LLM-assisted classification steps are clearly separated from rule-based logic to allow methodological auditing.

The project consists of two primary data streams:

1. **Arizona Blackbook Rule Changes (1961–2024)**
2. **Arizona Supreme Court Administrative Orders (1956–2024)**

---

# Part I — Arizona Blackbook Rule Changes

## 1. Source Documents

Original Blackbook files were obtained in PDF/DOCX format from Arizona Court publications and stored in:

```
files/blackbooks/initial_format/
```

These documents contain annual compilations of rule amendments promulgated by the Arizona Supreme Court.

---

## 2. Document Conversion (Azure Document Intelligence)

Script:

```
code/blackbook_markdown_converter.py
```

### Purpose

Converts PDF and DOCX Blackbook files into structured Markdown using Azure Document Intelligence (“prebuilt-layout” model).

### Methodological Justification

Unlike traditional OCR, Azure Document Intelligence:

* Uses deep learning to understand document structure
* Preserves headings, hierarchy, and formatting
* Retains table and layout information
* Produces structured Markdown output

This ensures high-fidelity preservation of legal formatting, which is essential for rule extraction.

### Output

Converted Markdown files are saved to:

```
files/blackbooks/md_format_raw/
```

---

## 3. Overlap Removal (1971–1975 Cleaning)

Script:

```
code/blackbook_cleaner.py
```

### Research Issue

Two Blackbook files overlapped:

* Blackbook Rule Updates 1961–1975
* Blackbook 1971–1980

To avoid double-counting 1971–1975, the script:

* Identifies a boundary marker in the 1971–1980 file
* Removes all content prior to July 1975
* Renames output to reflect 1975–1980 coverage

### Clean Output

```
files/blackbooks/md_format_clean/
```

This produces a non-overlapping continuous dataset from 1961 forward.

---

## 4. Order-Level Extraction (LLM-Assisted)

Notebook:

```
code/blackbook_rules_processing.ipynb
```

### Method

Using GPT-5-mini via structured output:

* Files are chunked (~5000 characters)
* Chunks extend to the next “Effective” date boundary
* Orders are extracted with:

  * Order title
  * Filed date
  * Dated date
  * Approved date
  * Effective date

Issued year is computed deterministically using priority:

```
Filed > Dated > Approved > Effective
```

### Output

```
files/order_extraction/extracted_orders_all_files.xlsx
```

---

## 5. Body-of-Rules Extraction (LLM-Assisted)

Orders often amend multiple rule systems in a single entry.

Example:

> ORDER AMENDING RULES OF EVIDENCE …; ARIZONA RULES OF CRIMINAL PROCEDURE …; ARIZONA RULES OF PROCEDURE FOR THE JUVENILE COURT …

Each rule system is separated into its own row.

Script (within notebook):

* Splits one order into one row per distinct body of rules
* Reattaches:

  * Order number
  * Bracket codes
  * Filed/effective dates
* Extracts standardized `body_of_rules` column

### Output

```
files/order_extraction/extracted_rule_bodies.xlsx
```

Final dataset:

* 2,178 rule-body entries
* De-duplicated
* Year assigned

---

## 6. Robust Date Construction

Issued dates are parsed using regex-based extraction supporting:

* MM/DD/YYYY
* M/D/YY
* Month Day, Year

Priority logic:

```
filed_date
→ dated_date
→ approved_date
→ effective_date
```

Final columns:

* issued_date
* issued_year

---

## 7. Rule Classification (Deterministic + LLM Comparison)

Each rule-body entry is classified under three parallel systems:

### A. Regex (Strict Definition)

* Local Rule (Regex) = 1 if “local” appears anywhere
* Statewide Rule (Regex) = 1 − Local
* Statewide Trial Court Rule (Regex) =
  Statewide AND
  NOT “Rules of the Supreme Court” AND
  NOT “Appellate” unless also “Superior”

### B. LLM Classification

LLM identifies local rules that do not explicitly use the word “local,” such as:

> Rules of Practice for the Maricopa County Superior Court

Override rule:
If “local” appears anywhere → classified as Local automatically.

Columns created:

* Local Rule (LLM)
* Statewide Rule (LLM)
* Statewide Trial Court Rule (LLM)

Final dataset:

```
files/order_extraction/extracted_rule_bodies_llm_regex.xlsx
```

Disagreements between regex and LLM are logged for audit. Please note that we created three different versions of the LLM classification and checked a sample of 50 cases from each decade against the source documents to determine if the classification was accurate.  When we noticed errors, we revised the instructions for the LLM and re-ran the code before verifying again.

---

## 8. Figures

Figures generated include:

* Statewide rule changes per year
* Share of local vs statewide trial court rulemaking by decade
* 100% stacked bar charts (Local vs Statewide Trial)

All figures are reproducible from the final Excel dataset. Note that they use the LLM classification.

---

# Part II — Administrative Orders Scraper

Script:

```
code/scraper.py
```

## Coverage

Scrapes Arizona Supreme Court administrative orders from:

```
https://www.azcourts.gov/orders/
```

Years:
1956–2024

Handles:

* Pre-2015 .aspx format
* Post-2016 dash-format URLs

Extracts:

* Order_Number
* Administrative_Order_Description
* Date_Signed
* PDF Link
* Year

Output:

```
files/order_extraction/az_court_orders.xlsx
```

---

# Replication Instructions

1. Add Azure credentials to `.env`
2. Run:

   * `blackbook_markdown_converter.py`
   * `blackbook_cleaner.py`
3. Run notebook to:

   * Extract orders
   * Extract rule bodies
   * Classify rules
4. Run scraper for administrative orders
5. Generate figures from final dataset

All paths are relative and project-structured.

---

# Transparency & Methodological Notes

* LLM steps are explicitly labeled and auditable.
* Deterministic rules are preserved alongside LLM outputs.
* Classification disagreements are logged for sensitivity analysis.
* Date parsing includes defensive cleaning.
* All intermediate datasets are saved for reproducibility.

---

# Repository Structure

```
code/
  blackbook_markdown_converter.py
  blackbook_cleaner.py
  blackbook_rules_processing.ipynb
  scraper.py

files/
  blackbooks/
    initial_format/
    md_format_raw/
    md_format_clean/
  order_extraction/
    extracted_orders_all_files.xlsx
    extracted_rule_bodies.xlsx
    extracted_rule_bodies_llm_regex.xlsx
    az_court_orders.xlsx
```

