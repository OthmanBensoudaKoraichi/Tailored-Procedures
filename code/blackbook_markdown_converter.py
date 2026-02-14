"""
Arizona Blackbook PDF/DOCX to Markdown Converter
==================================================

This module converts Arizona Court Blackbook PDF and DOCX files to clean 
Markdown format using Azure's Document Intelligence service (formerly Form Recognizer).
The conversion uses machine learning to understand document structure and preserve 
hierarchy and formatting.

METHODOLOGY:
Uses Azure's "prebuilt-layout" model which leverages deep learning to:
1. Understand document structure (headers, paragraphs, tables, lists)
2. Preserve page breaks and hierarchical organization
3. Extract text with layout information
4. Output in clean Markdown format

ADVANTAGES OVER OCR:
- NOT traditional OCR (which just recognizes characters)
- Uses deep learning to UNDERSTAND semantic structure (not just read letters)
- Understands what is a heading, paragraph, section, table, etc.
- Handles scanned and digital PDFs equally well
- Preserves tables, lists, and formatting hierarchies
- Works with complex legal documents (Blackbooks, court rules, etc.)
- More accurate because it understands document meaning, not just characters

INPUT:
- PDF files (.pdf)
- Word documents (.docx)
Located in: ../files/initial_format/ (relative to this script)

OUTPUT:
- Markdown files (.md) with one per source document
- Located in: ../files/md_format_raw/ (relative to this script)
- Page breaks indicated with "---" separators
- Hierarchical structure preserved

PREREQUISITES:
- Azure credentials (AZURE_KEY, AZURE_ENDPOINT) in .env file
- Azure Document Intelligence service must be enabled
- Documents must be readable (not corrupted)

DEPENDENCIES:
  - azure-ai-document-intelligence: Azure Document Intelligence SDK
  - python-dotenv: Environment variable loading
  - pathlib: Cross-platform path handling
  - base64: Encoding binary files for API transmission

Author: [Your Name]
Date: [Date]
Purpose: Document processing for legal research analysis

IMPORTANT: This script uses paths relative to ITS OWN LOCATION, not the working directory.
You can run it from anywhere (code/, root, etc.) and it will still find the files correctly.
"""

import os
import base64
import sys
import time
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Azure SDK imports for document processing
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentContentFormat


# ====== CONFIGURATION ======
# IMPORTANT: Paths are calculated RELATIVE TO THIS SCRIPT'S LOCATION
# This works correctly no matter where you run the script from
#
# Example directory structure:
# project_root/
#   ├── code/
#   │   └── blackbook_markdown_converter.py  ← This script
#   └── files/
#       ├── initial_format/  ← INPUT (PDFs/DOCXs go here)
#       └── md_format_raw/       ← OUTPUT (Markdown files saved here)

# Get the directory where THIS script file is located
# __file__ = absolute path to this script
# .resolve().parent = directory containing this script
SCRIPT_DIR = Path(__file__).resolve().parent
print(f"[CONFIG] Script location: {SCRIPT_DIR}")

# Input directory: ../files/initial_format (relative to script)
# If script is in code/, this resolves to: project_root/files/initial_format/
IN_DIR = SCRIPT_DIR.parent / "files" / "initial_format"

# Output directory: ../files/md_format_raw (relative to script)
# If script is in code/, this resolves to: project_root/files/md_format/
OUT_DIR = SCRIPT_DIR.parent / "files" / "md_format_raw"

# Create output directory if it doesn't exist
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ====== MAIN CONVERSION PIPELINE ======

def main():
    """
    Main entry point for the PDF/DOCX to Markdown conversion pipeline.
    
    Workflow:
    1. Load Azure credentials from .env file
    2. Initialize Azure Document Intelligence client
    3. Find all PDF and DOCX files in input directory
    4. For each document:
       a. Read file as binary
       b. Encode as base64 (required by Azure API)
       c. Submit to Azure for processing
       d. Extract Markdown content
       e. Handle page structure preservation
       f. Save as Markdown file
    5. Report conversion results
    
    Error Handling:
    - Missing credentials: exits gracefully with instructions
    - Missing files: reports and continues
    - Per-file failures: logs error and continues to next file
    
    Side Effects:
    - Prints progress to console
    - Creates OUT_DIR if it doesn't exist
    - Reads .env file for Azure credentials
    """
    
    # Record start time for performance reporting
    t0 = time.time()
    
    # ---- STEP 1: Load credentials ----
    print("[STEP 1] Loading Azure credentials...")
    load_dotenv()
    AZURE_KEY = os.getenv("AZURE_KEY")
    AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")

    # Print diagnostic information to verify paths
    print(f"\n[STEP 1] Verifying paths and configuration:")
    print(f"  Script location: {SCRIPT_DIR}")
    print(f"  Input directory: {IN_DIR}")
    print(f"  Input exists: {IN_DIR.exists()}")
    print(f"  Output directory: {OUT_DIR}")
    print(f"  Output exists: {OUT_DIR.exists()}")
    print(f"  AZURE_ENDPOINT set: {bool(AZURE_ENDPOINT)}")
    print(f"  AZURE_KEY set: {bool(AZURE_KEY)}")
    
    # Validate credentials before proceeding
    if not AZURE_KEY or not AZURE_ENDPOINT:
        print("❌ Missing AZURE_KEY or AZURE_ENDPOINT in environment. Check your .env.")
        sys.exit(1)

    # ---- STEP 2: Initialize Azure client ----
    print("\n[STEP 2] Initializing Azure Document Intelligence client...")
    ai_client = DocumentIntelligenceClient(
        endpoint=AZURE_ENDPOINT,
        credential=AzureKeyCredential(AZURE_KEY)
    )

    # ---- STEP 3: Find input files ----
    print("\n[STEP 3] Discovering PDF and DOCX files...")
    # Use recursive glob to find all PDFs and DOCXs in IN_DIR and subdirectories
    files = sorted(list(IN_DIR.rglob("*.pdf")) + list(IN_DIR.rglob("*.docx")))
    print(f"Found {len(files)} file(s):")
    
    # Display first 10 files
    for p in files[:10]:
        print("  -", p)
    # Show count of remaining files if more than 10
    if len(files) > 10:
        print(f"  ... and {len(files)-10} more")

    # Exit gracefully if no files found
    if not files:
        print("\n⚠️ No .pdf or .docx files found in input directory.")
        print(f"Expected location: {IN_DIR}")
        print("\nTroubleshooting:")
        print(f"  - Check if {IN_DIR} exists and contains PDF/DOCX files")
        print(f"  - Verify file extensions are .pdf or .docx (lowercase)")
        print(f"  - Make sure this script is in the code/ directory")
        sys.exit(0)

    # ---- STEP 4: Process each document ----
    print(f"\n[STEP 4] Processing {len(files)} document(s)...")
    processed = 0
    
    for i, path in enumerate(files, 1):
        # Print progress with no newline (will be updated inline)
        print(f"[{i}/{len(files)}] {path.name} …", end="", flush=True)
        try:
            # Read document file as binary
            data = path.read_bytes()
            
            # ---- Azure API Call ----
            # Submit document to Azure Document Intelligence service
            # The "prebuilt-layout" model is trained to understand document structure
            poller = ai_client.begin_analyze_document(
                # Use prebuilt layout model (trained for general document understanding)
                model_id="prebuilt-layout",
                # Body contains the binary document encoded as base64
                # (Azure API requires base64 encoding for file transmission)
                body={"base64Source": base64.b64encode(data).decode()},
                # Request Markdown output format
                # This preserves hierarchical structure better than plain text
                output_content_format=DocumentContentFormat.MARKDOWN,
            )
            
            # Wait for processing to complete
            # Azure processes asynchronously; poller.result() blocks until done
            res = poller.result()

            # ---- Extract Markdown Content ----
            # The response can contain either:
            # 1. Pages array: individual page text with span information (preferred)
            # 2. Single content string: already-assembled markdown
            
            md_text = ""
            
            # Check if pages are available (preferred method)
            # This allows us to insert page breaks and preserve structure better
            if getattr(res, "pages", None):
                parts = []
                # Iterate through each page returned by Azure
                for page in res.pages:
                    # Skip pages with no content
                    if not page.spans:
                        continue
                    # Each page has spans that reference the full content
                    # Extract the substring for this page
                    span = page.spans[0]
                    page_content = res.content[span.offset : span.offset + span.length]
                    parts.append(page_content)
                
                # Join pages with Markdown page break separator
                # "---" is standard Markdown for horizontal rule / page break
                md_text = "\n\n---\n\n".join(parts)
            else:
                # Fallback: use content directly if pages not available
                md_text = res.content or ""

            # ---- Save Output ----
            if not md_text.strip():
                # Report if Azure returned no content (empty document)
                print(" empty markdown returned")
            else:
                # Create output filename: same name as input but .md extension
                out_file = OUT_DIR / f"{path.stem}.md"
                
                # Write Markdown content to file (UTF-8 encoding)
                # This is standard for Markdown files
                out_file.write_text(md_text, encoding="utf-8")
                
                # Report successful conversion
                print(f" saved -> {out_file.name}")
                processed += 1
        
        except Exception as e:
            # Report conversion failure and continue to next file
            print(" FAILED")
            # Print full error traceback for debugging
            traceback.print_exc()

    # ---- SUMMARY ----
    # Calculate and report execution time
    dt = time.time() - t0
    print(f"\n✅ Done. Processed {processed}/{len(files)} file(s) in {dt:.2f}s.")
    
    if processed < len(files):
        print(f"⚠️  {len(files) - processed} file(s) failed. Check errors above.")


if __name__ == "__main__":
    main()