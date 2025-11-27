#!/usr/bin/env python3
"""
Interactive metadata updater
Helps you manually update values from factsheets
"""

import pandas as pd
from datetime import datetime

METADATA_FILE = "fund_metadata.csv"

def interactive_update():
    """Interactive CLI for updating metadata"""
    df = pd.read_csv(METADATA_FILE)
    
    print("="*60)
    print("INTERACTIVE METADATA UPDATER")
    print("="*60)
    print(f"\nFunds to update: {len(df)}")
    print("\nOptions:")
    print("1. Update all AUM values")
    print("2. Update all Expense Ratios")
    print("3. Update specific fund")
    print("4. Export to Google Sheets format")
    print("5. Exit")
    
    choice = input("\nSelect option (1-5): ")
    
    if choice == "1":
        print("\nUpdating AUM values...")
        print("Visit fund factsheets and enter AUM (in Crores):\n")
        for idx, row in df.iterrows():
            print(f"{idx+1}. {row['fund_name'][:50]}")
            current = row['aum_cr']
            new_value = input(f"   Current: {current} Cr | New value (or press Enter to skip): ")
            if new_value.strip():
                df.at[idx, 'aum_cr'] = float(new_value)
        
        df.to_csv(METADATA_FILE, index=False)
        print("\n✓ AUM values updated!")
    
    elif choice == "4":
        # Export to Google Sheets friendly format
        output_file = "metadata_for_sheets.csv"
        df[['fund_name', 'aum_cr', 'exp_ratio', 'rating']].to_csv(output_file, index=False)
        print(f"\n✓ Exported to {output_file}")
        print("Upload to Google Sheets, update values, then re-import")

if __name__ == "__main__":
    interactive_update()
