"""
Arizona Court Administrative Orders Scraper
============================================

This module scrapes administrative orders from the Arizona Court system website
(https://www.azcourts.gov/orders/) spanning from 1956 to 2024 and exports them 
to an Excel file for research and analysis purposes.

METHODOLOGY:
The scraper uses HTTP requests and BeautifulSoup to parse HTML tables from the
Arizona Courts website. It handles two distinct URL formats due to website 
restructuring in 2016:
  - Pre-2015: /AdministrativeOrdersIndex/{year}AdministrativeOrders.aspx
  - 2016+:    /Administrative-Orders-Index/{year}-Administrative-Orders

DATA EXTRACTED:
For each administrative order, the following information is captured:
  - Order_Number: Unique identifier (e.g., "56-01", "2024-42")
  - Administrative_Order_Description: Order title/subject
  - Date_Signed: Date of signature
  - Link_Order: URL to PDF document
  - Year: Year of order (derived from source URL)

OUTPUT:
Excel spreadsheet with columns for each data field above, sorted by year 
and order number.

DEPENDENCIES:
  - requests: HTTP library for fetching web pages
  - beautifulsoup4: HTML parsing
  - pandas: Data manipulation and Excel export
  - tqdm: Progress bar visualization

Author: [Your Name]
Date: [Date]
Purpose: Legal research and analysis for law review
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import urljoin, urlparse
import time
from datetime import datetime
import os
from tqdm import tqdm


class AZCourtOrdersScraper:
    """
    Web scraper for Arizona Court administrative orders.
    
    This class handles the complete scraping workflow: fetching pages, 
    parsing HTML tables, extracting order data, and exporting to Excel.
    
    Attributes:
        base_url (str): Base URL for Arizona Courts orders directory
        session (requests.Session): HTTP session for connection pooling
        all_orders (list): Accumulated list of order dictionaries
    """
    
    def __init__(self):
        """
        Initialize the scraper with base URL and HTTP session.
        
        Sets up:
        - Base URL pointing to Arizona Courts orders directory
        - HTTP session with realistic User-Agent header (to avoid bot detection)
        - Empty orders list for accumulating results
        """
        self.base_url = "https://www.azcourts.gov/orders"
        self.session = requests.Session()
        # Set User-Agent to identify as browser rather than bot
        # This reduces likelihood of being blocked by server
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.all_orders = []
    
    def get_years_to_scrape(self):
        """
        Generate list of years to scrape (1956-2024).
        
        Returns:
            list: Years from 1956 to 2024 inclusive.
        """
        return list(range(1956, 2025))
    
    def construct_year_url(self, year):
        """
        Construct the URL for a specific year's orders page.
        
        The Arizona Courts website uses two different URL patterns due to 
        a website restructuring that occurred in 2016. This method accounts
        for both formats:
        
        Args:
            year (int): Year to construct URL for
            
        Returns:
            str: Complete URL for that year's administrative orders page
            
        Note:
            - Years ≤2015 use .aspx format
            - Years ≥2016 use dash-separated format
        """
        if year <= 2015:
            # Old .aspx format (2015 and before)
            return f"{self.base_url}/AdministrativeOrdersIndex/{year}AdministrativeOrders.aspx"
        else:
            # New dash format (2016 and after)
            return f"{self.base_url}/Administrative-Orders-Index/{year}-Administrative-Orders"
    
    def try_url_patterns(self, year):
        """
        Attempt to fetch the page for a given year.
        
        Makes an HTTP GET request to the constructed URL with a 30-second 
        timeout. Logs success/failure for debugging purposes.
        
        Args:
            year (int): Year to fetch
            
        Returns:
            tuple: (response object, URL) if successful (status 200)
                   (None, None) if request fails or returns non-200 status
                   
        Side Effects:
            Prints debug information about the request (status code, URL)
        """
        url = self.construct_year_url(year)
        
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                format_type = ".aspx format" if year <= 2015 else "dash format"
                print(f"DEBUG: Year {year} - SUCCESS ({format_type}): {url}")
                return response, url
            else:
                print(f"DEBUG: Year {year} - HTTP {response.status_code}: {url}")
                return None, None
        except Exception as e:
            print(f"DEBUG: Year {year} - ERROR: {str(e)[:50]}... URL: {url}")
            return None, None
    
    def scrape_year_page(self, year):
        """
        Scrape all administrative orders for a specific year.
        
        This is the main scraping logic. Steps:
        1. Fetch the HTML page for the year
        2. Parse with BeautifulSoup
        3. Find all tables
        4. For each table:
           - Verify it has 3+ columns (Order | Description | Date)
           - Extract header to understand column layout
           - Iterate through data rows and extract order information
           - Validate extracted data before adding to results
        5. Return list of order dictionaries
        
        Args:
            year (int): Year to scrape
            
        Returns:
            list: List of order dictionaries with keys:
                  - Order_Number: str
                  - Administrative_Order_Description: str
                  - Date_Signed: str
                  - Link_Order: str (URL to PDF)
                  - Year: int
        """
        
        # Fetch the page for this year
        response, working_url = self.try_url_patterns(year)
        
        if not response or not working_url:
            print(f"ERROR: No working URL found for year {year}")
            return []
        
        try:
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            orders = []
            
            # Debug output to verify page access
            print(f"\nDEBUG: Successfully accessing {year} - {working_url}")
            
            # Locate all tables in the page
            tables = soup.find_all('table')
            print(f"DEBUG: Found {len(tables)} tables")
            
            # Check for div-based table containers (alternative layout)
            divs_with_tables = soup.find_all('div', class_=lambda x: x and 'table' in x.lower() if x else False)
            print(f"DEBUG: Found {len(divs_with_tables)} divs with table-related classes")
            
            # Count PDF links as sanity check
            all_links = soup.find_all('a', href=True)
            pdf_links = [link for link in all_links if '.pdf' in link.get('href', '').lower()]
            print(f"DEBUG: Found {len(pdf_links)} PDF links on page")
            
            # Process each table found on the page
            for table_idx, table in enumerate(tables):
                print(f"DEBUG: Processing table {table_idx + 1}")
                rows = table.find_all('tr')
                print(f"DEBUG: Table has {len(rows)} rows")
                
                # Skip tables with insufficient rows (need header + at least 1 data row)
                if len(rows) < 2:
                    continue
                
                # Display first few rows for debugging structure
                for row_idx, row in enumerate(rows[:3]):
                    cells = row.find_all(['td', 'th'])
                    cell_texts = [cell.get_text().strip()[:50] for cell in cells]
                    print(f"DEBUG: Row {row_idx}: {cell_texts}")
                
                # Analyze header row to understand table structure
                header_row = rows[0] if rows else None
                if header_row:
                    header_cells = header_row.find_all(['th', 'td'])
                    header_texts = [cell.get_text().strip().lower() for cell in header_cells]
                    print(f"DEBUG: Header row: {header_texts}")
                    
                    # Check for key columns
                    has_order_header = any('order' in h or 'no.' in h for h in header_texts)
                    has_date_header = any('date' in h or 'signed' in h for h in header_texts)
                    has_description_header = any('description' in h or 'title' in h or 'subject' in h for h in header_texts)
                    
                    print(f"DEBUG: Table analysis - Order: {has_order_header}, Date: {has_date_header}, Description: {has_description_header}")
                    
                    # Require minimum of 3 columns
                    if len(header_cells) < 3:
                        print(f"DEBUG: Skipping table {table_idx + 1} - less than 3 columns")
                        continue
                
                # Extract data rows (skip header)
                data_rows = rows[1:] if len(rows) > 1 else []
                
                if not data_rows:
                    print(f"DEBUG: No data rows in table {table_idx + 1}")
                    continue
                
                # Progress bar for row processing
                with tqdm(total=len(data_rows), 
                         desc=f"Year {year}", 
                         leave=False, 
                         unit="rows",
                         ncols=80,
                         ascii=True,
                         disable=False) as pbar:
                    
                    for row in data_rows:
                        cells = row.find_all(['td', 'th'])
                        
                        # Require minimum of 3 cells per row
                        if len(cells) >= 3:
                            try:
                                # COLUMN 0: Extract order number and PDF link
                                order_cell = cells[0]
                                order_link = order_cell.find('a')
                                
                                if order_link:
                                    # Order number is the link text
                                    order_number = order_link.text.strip()
                                    # PDF link is the href
                                    href = order_link.get('href', '')
                                    # Use urljoin to create absolute URL
                                    pdf_link = urljoin(self.base_url, href) if href else ""
                                else:
                                    # No link, just extract text
                                    order_number = order_cell.get_text().strip()
                                    pdf_link = ""
                                
                                # COLUMN 1: Extract description
                                description = cells[1].get_text().strip()
                                
                                # COLUMN 2+: Extract date (search for date pattern)
                                date_signed = ""
                                for i in range(2, len(cells)):
                                    cell_text = cells[i].get_text().strip()
                                    # Look for common date patterns: MM/DD/YYYY or MM-DD-YYYY
                                    if re.search(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', cell_text):
                                        date_signed = cell_text
                                        break
                                
                                # Fallback: use last column if no date found
                                if not date_signed and len(cells) > 2:
                                    date_signed = cells[-1].get_text().strip()
                                
                                print(f"DEBUG: Raw data - Order: '{order_number}', Desc: '{description[:30]}...', Date: '{date_signed}'")
                                
                                # VALIDATION: Check data quality before adding
                                # Skip orders with invalid/missing order numbers
                                if not order_number or len(order_number) > 50:
                                    print(f"DEBUG: Skipping - invalid order number length")
                                    pbar.update(1)
                                    continue
                                
                                # Skip if description is missing or too short
                                if not description or len(description) < 5:
                                    print(f"DEBUG: Skipping - description too short")
                                    pbar.update(1)
                                    continue
                                
                                # DATA CLEANING: Remove excess whitespace
                                order_number = re.sub(r'\s+', ' ', order_number)
                                description = re.sub(r'\s+', ' ', description)
                                date_signed = re.sub(r'\s+', ' ', date_signed)
                                
                                # Create order record
                                order_data = {
                                    'Order_Number': order_number,
                                    'Administrative_Order_Description': description,
                                    'Date_Signed': date_signed,
                                    'Link_Order': pdf_link,
                                    'Year': year
                                }
                                orders.append(order_data)
                                print(f"DEBUG: ✓ Added order: {order_number}")
                            
                            except Exception as e:
                                # Skip rows that fail to parse
                                print(f"DEBUG: Error processing row in {year}: {e}")
                                continue
                        
                        # Update progress bar
                        pbar.update(1)
                        pbar.set_postfix({'Found': len(orders)})
            
            print(f"DEBUG: Year {year} complete. Found {len(orders)} valid orders")
            return orders
            
        except Exception as e:
            print(f"ERROR: Unexpected error for {year}: {e}")
            return []
    
    def scrape_all_years(self, start_year=1956, end_year=2024):
        """
        Scrape administrative orders for a range of years.
        
        This method iterates through each year in the specified range,
        calls scrape_year_page() for each year, accumulates results,
        and displays progress.
        
        Args:
            start_year (int): First year to scrape (default 1956)
            end_year (int): Last year to scrape (default 2024)
            
        Returns:
            list: All accumulated order dictionaries from all years
            
        Side Effects:
            - Prints progress to console
            - Sleeps 1 second between requests to be respectful to server
            - Accumulates results in self.all_orders
        """
        years = list(range(start_year, end_year + 1))
        total_years = len(years)
        
        print(f"Starting scrape of {total_years} years from {start_year} to {end_year}")
        print("Years with no orders will be skipped automatically.")
        
        # Force console output to flush
        import sys
        sys.stdout.flush()
        
        # Main progress bar
        with tqdm(total=total_years, 
                 desc="Overall Progress", 
                 unit="year",
                 ncols=100,
                 ascii=True,
                 position=0,
                 leave=True) as main_pbar:
            
            for i, year in enumerate(years):
                main_pbar.set_description(f"Scraping {year}")
                # Scrape orders for this year
                orders = self.scrape_year_page(year)
                
                # Only accumulate if orders were found
                if orders:
                    self.all_orders.extend(orders)
                    print(f"Year {year}: Found {len(orders)} orders")
                else:
                    print(f"Year {year}: No orders found - skipping")
                
                # Update main progress bar with statistics
                main_pbar.update(1)
                main_pbar.set_postfix({
                    'Year': year,
                    'This_Year': len(orders) if orders else 0,
                    'Total_Orders': len(self.all_orders),
                    'Completed': f"{i+1}/{total_years}"
                })
                
                # Periodic status updates
                if (i + 1) % 5 == 0 or i == 0:
                    print(f"Completed {i+1}/{total_years} years. Total orders: {len(self.all_orders)}")
                    sys.stdout.flush()
                
                # Be respectful to the server - 1 second delay between requests
                time.sleep(1)
        
        print(f"\nScraping complete! Total orders scraped: {len(self.all_orders)}")
        return self.all_orders
    
    def save_to_excel(self, filename="az_court_administrative_orders.xlsx"):
        """
        Save accumulated orders to an Excel file.
        
        This method:
        1. Converts order list to pandas DataFrame
        2. Reorders columns for readability
        3. Sorts by year and order number
        4. Exports to Excel using openpyxl engine
        5. Creates parent directories if they don't exist
        
        Args:
            filename (str): Output file path (default: current directory)
            
        Returns:
            pandas.DataFrame: The exported dataframe
            
        Raises:
            IOError: If file cannot be written
        """
        if not self.all_orders:
            print("No data to save. Run scrape_all_years() first.")
            return
        
        # Create directory structure if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Progress bar for data processing
        with tqdm(total=4, desc="Processing data") as pbar:
            pbar.set_description("Creating DataFrame")
            # Convert list of dicts to pandas DataFrame
            df = pd.DataFrame(self.all_orders)
            pbar.update(1)
            
            pbar.set_description("Reordering columns")
            # Organize columns for optimal readability
            column_order = ['Order_Number', 'Administrative_Order_Description', 'Date_Signed', 'Link_Order']
            df = df[column_order + [col for col in df.columns if col not in column_order]]
            pbar.update(1)
            
            pbar.set_description("Sorting data")
            # Sort chronologically, then by order number within each year
            df = df.sort_values(['Year', 'Order_Number']) if 'Year' in df.columns else df.sort_values('Order_Number')
            pbar.update(1)
            
            pbar.set_description("Saving to Excel")
            # Export to Excel file
            df.to_excel(filename, index=False, engine='openpyxl')
            pbar.update(1)
        
        print(f"Data saved to {filename}")
        print(f"Total records: {len(df)}")
        
        # Display sample of output
        print("\nSample data:")
        print(df.head())
        
        return df


def main():
    """
    Main entry point for the scraper.
    
    Workflow:
    1. Initialize scraper
    2. Scrape all years 1956-2024
    3. Save results to Excel in ../order_extraction/ directory
    4. Display statistics
    """
    print("Arizona Court Administrative Orders Scraper")
    print("=" * 50)
    
    scraper = AZCourtOrdersScraper()
    
    # Full historical scrape from 1956 to 2024
    print(f"Starting FULL historical scrape from 1956 to 2024...")
    print(f"Checking 69 years. Years with no orders will be skipped.")
    print("This may take 30-60 minutes depending on your connection speed.")
    
    print(f"\n🚀 Starting scrape of 69 years...")
    print("Progress bars and updates will appear below.")
    
    # Execute scraping (1956 to 2024 inclusive)
    orders = scraper.scrape_all_years(1956, 2024)
    
    if orders:
        print(f"\n✅ Scraping completed! Found {len(orders)} total orders.")
        # Save to ../order_extraction directory
        output_path = os.path.join(os.path.dirname(__file__), '..', 'order_extraction', 'az_court_orders.xlsx')
        df = scraper.save_to_excel(output_path)
        
        # Display summary statistics
        if not df.empty:
            print(f"\n📊 FINAL STATISTICS:")
            print(f"   Years covered: {df['Year'].min()} - {df['Year'].max()}")
            print(f"   Total orders: {len(df):,}")
            print(f"   Years with data: {len(df['Year'].unique())}")
            
            print(f"\n📈 Orders by decade:")
            df['Decade'] = (df['Year'] // 10) * 10
            decade_counts = df['Decade'].value_counts().sort_index()
            for decade, count in decade_counts.items():
                print(f"   {decade}s: {count:,} orders")
            
            print(f"\n📅 Most recent years:")
            recent_years = df['Year'].value_counts().sort_index().tail(10)
            for year, count in recent_years.items():
                print(f"   {year}: {count} orders")
                
            print(f"\n💾 Data saved to: {output_path}")
    else:
        print("❌ No orders were scraped. Please check the URLs and HTML structure.")


if __name__ == "__main__":
    main()