"""
Blackbook Markdown File Copy with Selective Cleaning
=====================================================

PURPOSE FOR LAW REVIEW:
Copy all markdown files from md_format_raw to md_format_clean, with special
processing for Blackbook 1971-1980.md to remove overlapping historical content.

METHODOLOGY:
1. Copy all .md files from md_format_raw/ to md_format_clean/
2. For the SPECIFIC file "Blackbook 1971-1980.md":
   - Find the 1975 STATE BAR - ADMISSION AND DISCIPLINE entry (boundary point)
   - Remove everything up to and including that entry
   - This removes the 1971-1975 overlap period
   - Keep only the 1975-1980 content
3. All other files are copied as-is

RESEARCH RATIONALE:
You have two Blackbook files:
- Blackbook Rule Updates 1961-1975.md (complete early period)
- Blackbook 1971-1980.md (overlaps 1971-1975)

By removing the overlap from 1971-1980, you have:
- Clean 1961-1975 dataset from first file
- Clean 1975-1980 dataset from second file
- No duplicate analysis needed
"""

from pathlib import Path
import shutil


def copy_and_clean_markdown_files():
    """
    Copy all markdown files from md_format_raw to md_format_clean.
    Apply special cleaning to Blackbook 1971-1980.md to remove pre-1975 content.
    
    - Copies all .md files from source to destination
    - For "Blackbook 1971-1980.md": removes content before 1975 STATE BAR entry
    - All other files are copied unchanged
    - Reports progress and results
    """
    
    # Get the directory where THIS script is located
    SCRIPT_DIR = Path(__file__).resolve().parent
    print(f"[CONFIG] Script location: {SCRIPT_DIR}\n")
    
    # Source and destination directories
    source_dir = SCRIPT_DIR.parent / "files" / "blackbooks" / "md_format_raw"
    dest_dir = SCRIPT_DIR.parent / "files" / "blackbooks" / "md_format_clean"
    
    print(f"[STEP 1] Verifying directories...")
    print(f"  Source: {source_dir}")
    print(f"  Source exists: {source_dir.exists()}")
    print(f"  Destination: {dest_dir}")
    print(f"  Destination exists: {dest_dir.exists()}\n")
    
    # Validate source directory exists
    if not source_dir.exists():
        print(f"❌ ERROR: Source directory not found: {source_dir}")
        return False
    
    # Create destination directory if it doesn't exist
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"[STEP 2] Destination directory ready\n")
    
    # Find all markdown files in source
    print(f"[STEP 3] Finding markdown files...")
    md_files = sorted(list(source_dir.glob("*.md")))
    print(f"Found {len(md_files)} markdown file(s):\n")
    
    if not md_files:
        print("❌ No markdown files found in source directory")
        return False
    
    # The specific file that needs cleaning and its boundary marker
    SPECIAL_FILE = "Blackbook 1971-1980.md"
    SPECIAL_FILE_OUTPUT = "Blackbook 1975-1980.md"  # Renamed output reflecting content period
    MARKER_TEXT = """STATE BAR - ADMISSION AND DISCIPLINE OF ATTORNEYS: "Amending Rules
29 (a) and (b)"

Dated June 27, 1975.
Should DR1.13
Effective July 1, 1975."""
    
    # Copy each file
    print(f"[STEP 4] Copying and cleaning files...\n")
    copied = 0
    failed = 0
    
    for i, source_file in enumerate(md_files, 1):
        dest_file = dest_dir / source_file.name
        try:
            # Check if this is the special file that needs cleaning
            if source_file.name == SPECIAL_FILE:
                dest_file = dest_dir / SPECIAL_FILE_OUTPUT  # Use renamed output filename
                print(f"[{i}/{len(md_files)}] ⚙️  {source_file.name} → {SPECIAL_FILE_OUTPUT} (CLEANING)")
                
                # Read the file
                content = source_file.read_text(encoding='utf-8')
                original_size = len(content)
                
                # Find the marker
                marker_pos = content.find(MARKER_TEXT)
                if marker_pos != -1:
                    # Remove everything up to and including the marker
                    marker_end = marker_pos + len(MARKER_TEXT)
                    cleaned_content = content[marker_end:].lstrip('\n').rstrip()
                    cleaned_size = len(cleaned_content)
                    removed_size = original_size - cleaned_size
                    
                    # Save cleaned content
                    dest_file.write_text(cleaned_content, encoding='utf-8')
                    print(f"    ✓ Removed {removed_size:,} chars (1971-1975 content)")
                    print(f"    ✓ Kept {cleaned_size:,} chars (1975-1980 content)")
                else:
                    # Marker not found, just copy as-is
                    print(f"    ⚠️  Marker not found, copying as-is")
                    shutil.copy2(source_file, dest_file)
                    print(f"    ✓ Copied {original_size:,} bytes")
            else:
                # All other files - copy unchanged with original filename
                shutil.copy2(source_file, dest_file)
                file_size = source_file.stat().st_size
                print(f"[{i}/{len(md_files)}] ✓ {source_file.name} ({file_size:,} bytes)")
            
            copied += 1
            
        except Exception as e:
            print(f"[{i}/{len(md_files)}] ✗ {source_file.name} - ERROR: {e}")
            failed += 1
    
    # Summary report
    print(f"\n[STEP 5] Summary")
    print(f"========================================")
    print(f"✅ Successfully processed: {copied} file(s)")
    if failed > 0:
        print(f"❌ Failed: {failed} file(s)")
    print(f"Total: {copied + failed} file(s)")
    print(f"\nDestination: {dest_dir}")
    print(f"\n📝 Special processing:")
    print(f"   - {SPECIAL_FILE} → {SPECIAL_FILE_OUTPUT}")
    print(f"   - 1971-1975 content removed, renamed to reflect 1975-1980 period")
    print(f"   - All other files: copied unchanged")
    
    return failed == 0


def main():
    """Main entry point."""
    print("=" * 70)
    print("Blackbook Markdown Copy with Selective Cleaning")
    print("=" * 70)
    print()
    
    success = copy_and_clean_markdown_files()
    
    if success:
        print("\n✅ All files processed successfully!")
    else:
        print("\n⚠️ Some files failed. Check errors above.")


if __name__ == "__main__":
    main()