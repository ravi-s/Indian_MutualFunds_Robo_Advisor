#!/usr/bin/env python3
"""
Advanced Metadata Scraper with Multiple Strategies
Uses AMFI data + web scraping + intelligent fallbacks
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from datetime import datetime
import time
import re
import sys

# --- Configuration ---
# Use requests.exceptions for specific error handling
from requests.exceptions import RequestException, Timeout, HTTPError 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

METADATA_FILE = "fund_metadata.csv"
BACKUP_FILE = f"fund_metadata_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
MFAPI_BASE_URL = "https://api.mfapi.in"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- Core Functions ---

def backup_metadata():
    """Create backup of existing metadata, handling file not found"""
    try:
        # Handle case where METADATA_FILE might not exist yet
        df = pd.read_csv(METADATA_FILE)
        df.to_csv(BACKUP_FILE, index=False)
        logger.info(f"✓ Backup created: {BACKUP_FILE}")
        return df
    except FileNotFoundError:
        logger.error(f"FATAL: Source file '{METADATA_FILE}' not found. Cannot proceed without initial metadata.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to backup metadata: {e}")
        sys.exit(1)


def fetch_amfi_scheme_master():
    """Fetch scheme master from AMFI via MFAPI with specific error handling"""
    try:
        logger.info("Fetching AMFI scheme master...")
        response = requests.get(f"{MFAPI_BASE_URL}/mf", headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        schemes = response.json()
        amfi_df = pd.DataFrame(schemes)
        
        # Ensure schemeCode is treated as string for merging later
        amfi_df['schemeCode'] = amfi_df['schemeCode'].astype(str)
        
        logger.info(f"✓ Fetched {len(schemes)} schemes from AMFI")
        return amfi_df
    except (Timeout, HTTPError, RequestException) as e:
        logger.error(f"Failed to fetch AMFI data due to network/API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to process AMFI data: {e}")
        return None


# --- Web Scraping Functions (Enhanced Robustness) ---

def search_groww(fund_name):
    """Search and scrape from Groww (added AUM flexibility)"""
    try:
        # Simplified and cleaned up search term for URL
        search_term = fund_name.replace(" - Direct Plan - Growth", "").strip()
        search_term = re.sub(r'[^a-zA-Z0-9\s]', '', search_term).replace(" ", "-").lower()
        
        url = f"https://groww.in/mutual-funds/{search_term}"
        
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        data = {}
        
        # Extract AUM (More flexible regex: Cr, crore, Lakh, etc.)
        aum_elements = soup.find_all(text=re.compile(r'Fund Size|AUM', re.IGNORECASE))
        for elem in aum_elements:
            parent = elem.find_parent()
            if parent:
                aum_text = parent.get_text()
                # Pattern: optional currency, space, digits/commas/decimal, space, unit (Cr/crore)
                aum_match = re.search(r'₹?\s*([\d,]+\.?\d*)\s*(Cr|crore|Lakh|Lac|Mn|Bn)', aum_text, re.IGNORECASE)
                if aum_match:
                    # Always treat scraped AUM as Crores for consistency (standard for these sites)
                    value = float(aum_match.group(1).replace(',', ''))
                    unit = aum_match.group(2).lower()
                    
                    if unit in ('lakh', 'lac'):
                        data['aum_cr'] = value / 100 # Convert Lakh to Crore
                    elif unit in ('mn'):
                        data['aum_cr'] = value / 10 # Convert Million to Crore (approx)
                    elif unit in ('bn'):
                        data['aum_cr'] = value * 100 # Convert Billion to Crore (approx)
                    else: # Cr or crore
                        data['aum_cr'] = value
                    break
        
        # Extract Expense Ratio (Ensuring it captures the number adjacent to %)
        ter_elements = soup.find_all(text=re.compile(r'Expense Ratio|TER', re.IGNORECASE))
        for elem in ter_elements:
            parent = elem.find_parent()
            if parent:
                # Look specifically for a number followed by a percentage sign
                ter_match = re.search(r'(\d+\.?\d*)\s*%', parent.get_text())
                if ter_match:
                    data['exp_ratio'] = float(ter_match.group(1))
                    break
        
        # Extract Rating (Look for an element that signals star count)
        rating_div = soup.find('div', class_=re.compile(r'rating|star', re.IGNORECASE))
        if rating_div:
            # Check for specific star elements if available
            stars = rating_div.find_all('i', class_=re.compile(r'star|icon'))
            if stars:
                data['rating'] = len(stars)
            else:
                # Fallback to finding a digit in the text
                rating_text = rating_div.get_text()
                rating_match = re.search(r'(\d)\s*(?:star|★)', rating_text, re.IGNORECASE)
                if rating_match:
                    data['rating'] = int(rating_match.group(1))
        
        return data if data else None
        
    except (Timeout, RequestException) as e:
        logger.debug(f"Groww scrape failed (Network/Timeout): {e}")
        return None
    except Exception as e:
        logger.debug(f"Groww scrape failed (Parsing): {e}")
        return None


def search_etmoney(fund_name):
    """Search and scrape from ET Money (Simplified search, robust parsing)"""
    try:
        search_term = fund_name.replace(" - Direct Plan - Growth", "").strip()
        
        # ET Money uses a direct URL structure (usually /mutual-funds/amc-fund-name-direct-growth)
        # Attempt a direct URL construction first (more efficient)
        url_segment = re.sub(r'[^a-zA-Z0-9\s]', '', search_term).replace(" ", "-").lower()
        fund_url = f"https://www.etmoney.com/mutual-funds/{url_segment}"
        
        fund_response = requests.get(fund_url, headers=HEADERS, timeout=10)
        
        # If direct URL fails, fall back to searching if necessary, but keep it simple
        if fund_response.status_code != 200:
             return None # Skip complex search, as it often fails for scrapers
        
        fund_soup = BeautifulSoup(fund_response.content, 'html.parser')
        data = {}
        
        # Extract AUM (Using flexible regex)
        aum_elem = fund_soup.find(text=re.compile(r'AUM|Fund Size', re.IGNORECASE))
        if aum_elem:
            aum_text = aum_elem.find_parent().get_text()
            aum_match = re.search(r'₹?\s*([\d,]+\.?\d*)\s*(Cr|crore|Lakh|Lac|Mn|Bn)', aum_text, re.IGNORECASE)
            if aum_match:
                data['aum_cr'] = float(aum_match.group(1).replace(',', ''))
        
        # Extract Expense Ratio
        ter_elem = fund_soup.find(text=re.compile(r'Expense Ratio|TER', re.IGNORECASE))
        if ter_elem:
            ter_text = ter_elem.find_parent().get_text()
            ter_match = re.search(r'(\d+\.?\d*)\s*%', ter_text)
            if ter_match:
                data['exp_ratio'] = float(ter_match.group(1))
        
        # Extract Rating
        rating_elem = fund_soup.find('span', class_=re.compile(r'rating|star', re.IGNORECASE))
        if rating_elem:
            rating_match = re.search(r'(\d)', rating_elem.get_text())
            if rating_match:
                data['rating'] = int(rating_match.group(1))
        
        return data if data else None
        
    except (Timeout, RequestException) as e:
        logger.debug(f"ET Money scrape failed (Network/Timeout): {e}")
        return None
    except Exception as e:
        logger.debug(f"ET Money scrape failed (Parsing): {e}")
        return None


def search_valueresearch(fund_name):
    """Enhanced ValueResearch scraper (more precise link searching)"""
    try:
        search_term = fund_name.replace(" - Direct Plan - Growth", "").strip()
        
        search_url = "https://www.valueresearchonline.com/funds/newsearch.asp"
        params = {'q': search_term}
        
        response = requests.get(search_url, headers=HEADERS, params=params, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Prioritize Direct Growth link
        fund_links = soup.find_all('a', href=re.compile(r'/funds/.*direct.*growth', re.IGNORECASE))
        
        # Fallback to any fund link if direct is not found
        if not fund_links:
            fund_links = soup.find_all('a', href=re.compile(r'/funds/'))
        
        if not fund_links:
            return None
        
        # Take the first link found
        fund_url = "https://www.valueresearchonline.com" + fund_links[0]['href']
        fund_response = requests.get(fund_url, headers=HEADERS, timeout=10)
        fund_soup = BeautifulSoup(fund_response.content, 'html.parser')
        
        data = {}
        
        # Extract data from the main snapshot/fund-info table
        snapshot_table = fund_soup.find('table', class_=re.compile(r'snapshot|fund-info', re.IGNORECASE))
        if snapshot_table:
            rows = snapshot_table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text().strip().lower()
                    value = cells[1].get_text().strip()
                    
                    if 'aum' in key or 'fund size' in key:
                        # Extract number and assume unit is Crore (standard on detail pages)
                        aum_match = re.search(r'₹?\s*([\d,]+\.?\d*)', value.replace(',', ''))
                        if aum_match:
                            data['aum_cr'] = float(aum_match.group(1))
                    
                    if 'expense' in key or 'ter' in key:
                        ter_match = re.search(r'(\d+\.?\d*)', value)
                        if ter_match:
                            data['exp_ratio'] = float(ter_match.group(1))
        
        # Extract Rating (More robust check for star icons)
        rating_div = fund_soup.find('div', class_=re.compile(r'rating', re.IGNORECASE))
        if rating_div:
            stars = rating_div.find_all('i', class_=re.compile(r'star-icon')) # Look for VRO-specific icons
            if stars:
                data['rating'] = len(stars)
            else:
                # Fallback to searching text
                rating_text = rating_div.get_text()
                rating_match = re.search(r'(\d)', rating_text)
                if rating_match:
                    data['rating'] = int(rating_match.group(1))
        
        return data if data else None
        
    except (Timeout, RequestException) as e:
        logger.debug(f"ValueResearch scrape failed (Network/Timeout): {e}")
        return None
    except Exception as e:
        logger.debug(f"ValueResearch scrape failed (Parsing): {e}")
        return None


def scrape_with_fallback(fund_name):
    """Try multiple sources with intelligent fallback"""
    logger.info(f"Scraping: {fund_name[:60].strip()}...")
    
    # Prioritize sources that are known to be reliable or faster
    sources = [
        ("Groww", search_groww),
        ("ET Money", search_etmoney),
        ("ValueResearch", search_valueresearch)
    ]
    
    for source_name, scraper_func in sources:
        try:
            data = scraper_func(fund_name)
            if data and len(data) > 0:
                logger.info(f"  ✓ Got {len(data)} fields from {source_name}")
                return data, source_name
        except Exception as e:
            # This should only catch non-network/parsing errors, but helps safety
            logger.debug(f"  {source_name} failed unexpectedly: {e}")
        
        time.sleep(0.5) # Politeness delay between source attempts
    
    logger.warning(f"  ✗ No data from any source")
    return {}, None


# --- Pandas Enhancements (Merge for efficiency) ---

def enrich_with_amfi_data(df, amfi_df):
    """
    Cross-reference with AMFI scheme master for validation.
    FIX: Uses pd.merge for efficiency instead of iterrows.
    """
    if amfi_df is None or amfi_df.empty:
        logger.warning("AMFI data is missing or empty, skipping enrichment.")
        return df
    
    # Prepare AMFI DataFrame for merge
    amfi_df_clean = amfi_df[['schemeCode', 'fundHouse']].copy()
    amfi_df_clean.rename(
        columns={'schemeCode': 'scheme_code', 'fundHouse': 'amfi_fund_house'},
        inplace=True
    )
    amfi_df_clean['scheme_code'] = amfi_df_clean['scheme_code'].astype(str)
    
    # Ensure primary DataFrame's scheme_code is string for merge
    df['scheme_code'] = df['scheme_code'].astype(str)
    
    # 1. Merge the two DataFrames
    merged_df = pd.merge(df, amfi_df_clean, on='scheme_code', how='left')
    
    # Calculate how many records will be updated (for logging)
    # Check where current fund_house is missing AND amfi data is present
    update_mask = (merged_df['fund_house'].isna() | (merged_df['fund_house'] == '')) & merged_df['amfi_fund_house'].notna()
    enriched_count = update_mask.sum()
    
    # 2. Fill missing fund_house values from the merged column
    merged_df['fund_house'] = merged_df.apply(
        lambda row: row['amfi_fund_house'] 
        if pd.isna(row['fund_house']) or row['fund_house'] == ''
        else row['fund_house'],
        axis=1
    )
    
    # 3. Drop the temporary column
    merged_df = merged_df.drop(columns=['amfi_fund_house'])
    
    logger.info(f"✓ Enriched {enriched_count} records with AMFI data (Fund House)")
    return merged_df


def update_metadata_with_scraped_data(df, amfi_df):
    """Main update logic with progress tracking"""
    stats = {
        'aum_cr': 0,
        'exp_ratio': 0,
        'rating': 0,
        'sources': {}
    }
    
    total_funds = len(df)
    
    # Initialize new columns if they don't exist (prevents KeyError on first run)
    for col in ['aum_cr', 'exp_ratio', 'rating', 'fund_house']:
        if col not in df.columns:
            df[col] = pd.NA
            
    for idx, row in df.iterrows():
        fund_name = row['fund_name']
        logger.info(f"\n[{idx+1}/{total_funds}] Processing...")
        
        scraped_data, source = scrape_with_fallback(fund_name)
        
        if scraped_data:
            if source:
                stats['sources'][source] = stats['sources'].get(source, 0) + 1
            
            # FIX: Using .loc for explicit assignment to avoid SettingWithCopyWarning
            if 'aum_cr' in scraped_data:
                df.loc[idx, 'aum_cr'] = scraped_data['aum_cr']
                stats['aum_cr'] += 1
            
            if 'exp_ratio' in scraped_data:
                df.loc[idx, 'exp_ratio'] = scraped_data['exp_ratio']
                stats['exp_ratio'] += 1
            
            if 'rating' in scraped_data:
                df.loc[idx, 'rating'] = scraped_data['rating']
                stats['rating'] += 1
        
        time.sleep(1) # Reduced sleep from 2s to 1s per fund to speed up, still polite
    
    # Final enrichment pass (efficient merge)
    df = enrich_with_amfi_data(df, amfi_df)
    
    return df, stats


def generate_detailed_report(stats, total_funds):
    """Generate comprehensive update report"""
    logger.info("\n" + "="*60)
    logger.info("METADATA UPDATE REPORT")
    logger.info("="*60)
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"\nTotal Funds Processed: {total_funds}")
    logger.info("-"*60)
    logger.info("Fields Updated:")
    # Prevent division by zero if no funds processed
    if total_funds > 0:
        logger.info(f"  AUM: {stats['aum_cr']} ({stats['aum_cr']/total_funds*100:.1f}%)")
        logger.info(f"  Expense Ratio: {stats['exp_ratio']} ({stats['exp_ratio']/total_funds*100:.1f}%)")
        logger.info(f"  Rating: {stats['rating']} ({stats['rating']/total_funds*100:.1f}%)")
    else:
        logger.info("  No funds to report updates for.")
    logger.info("-"*60)
    logger.info("Data Sources:")
    for source, count in stats['sources'].items():
        logger.info(f"  {source}: {count} funds")
    logger.info("="*60)


def main():
    """Main execution"""
    logger.info("="*60)
    logger.info("ADVANCED METADATA SCRAPER - Starting")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    # Backup existing metadata (will exit if METADATA_FILE is missing)
    df = backup_metadata()
    
    # Fetch AMFI data
    amfi_df = fetch_amfi_scheme_master()
    
    # Update metadata
    if len(df) > 0:
        logger.info(f"\nScraping metadata for {len(df)} funds...")
        estimated_time = len(df) * 1.5 / 60 # Approx 1.5s per fund
        logger.info(f"Estimated time: {estimated_time:.1f} minutes. Please wait...\n")
        
        updated_df, stats = update_metadata_with_scraped_data(df, amfi_df)
        
        # Save updated metadata
        updated_df.to_csv(METADATA_FILE, index=False)
        logger.info(f"\n✓ Updated metadata saved to: {METADATA_FILE}")
        
        # Generate report
        generate_detailed_report(stats, len(df))
    else:
        logger.info("No funds in metadata file to process.")
    
    logger.info(f"\n💾 Backup preserved at: {BACKUP_FILE}")
    logger.info(f"📄 Detailed logs saved to: scraper.log")


if __name__ == "__main__":
    main()