# Robo-Advisor Mutual Fund Recommendation MVP

## Introduction
This project is a minimal web application that helps users assess investment risk and recommends suitable Indian mutual funds using up-to-date CSV data.

## Prerequisites
- Python 3.8+
- Streamlit (recommended for rapid UI) or basic Python environment
- pandas library (`pip install pandas`)
- CSV data file: `robo_advisor_fund_recommendations.csv`
  - Columns: risk_profile, duration, rank, fund_name, fund_category, fund_type, aum_cr, exp_ratio, return_1y, return_3y, return_5y, min_investment, rating, remarks

## How to Run
1. Install dependencies:
    ```
    pip install streamlit pandas
    # install others as needed
    ```
2. Place your CSV data file in the project root.
3. Run the app:
    ```
    streamlit run app.py
    ```
   (If using another Python framework, run as per that framework’s instructions.)

## How to Update Data
- Download or regenerate new mutual fund data monthly from public sources.
- Overwrite/replace `robo_advisor_fund_recommendations.csv` with the latest file.
- Restart/reload the app to use the new data.

## Usage Instructions
1. Open the web app in your browser.
2. Complete the risk assessment questionnaire.
3. Input your investment amount and desired duration.
4. View the top 3 recommendations. Click "Show More" to display additional options.
5. Read fund remarks and details before deciding.

## Folder/File Structure
/project-root
- app.py
- funds.csv
- README.md
- requirements documents


## License
MIT
