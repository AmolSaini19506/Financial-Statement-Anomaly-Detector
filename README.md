# SEC Earnings Quality Analysis

## About

This project analyzes the earnings quality of companies using financial data from the SEC Company Facts API. It calculates the Beneish M-Score and Sloan Accrual Ratio to identify companies that may have a higher risk of earnings manipulation, then benchmarks how flagged vs. unflagged companies performed afterward.

## Results Summary

- Coverage: 20 companies with scoreable observations (recovered from an initial 8 via derived-field recovery, extended SEC XBRL tag fallbacks, and a 5-variable Beneish fallback model)
- Beneish M-Score (5-variable fallback): `-6.065 + 0.823*DSRI + 0.906*GMI + 0.593*AQI + 0.717*SGI + 0.107*DEPI`
- Forward return comparison available in `forward_return_comparison.png` for flagged vs. unflagged companies over 6- and 12-month horizons
- Full flagged/excluded observations broken out in `flagged_observations.csv` and `excluded_company_years.csv`

## Features

- Downloads financial data from the SEC Company Facts API
- Calculates Beneish M-Score
- Calculates Sloan Accrual Ratio
- Handles missing financial data using fallback methods
- Calculates 6-month and 12-month forward stock returns
- Generates CSV, PDF, and HTML reports
- Creates charts for analysis

## Technologies Used

- Python
- Pandas
- NumPy
- Matplotlib
- Seaborn
- Requests
- yfinance

## Data Source

- SEC Company Facts API
- Yahoo Finance

## How to Run

1. Install the required libraries.

```bash
pip install -r requirements.txt
```

2. Run the script.

```bash
python financial_statement_anomaly_detector.py
```

## Output

The project generates:

- CSV files
- PDF report
- HTML report
- Charts and graphs

## Note

This project is for educational and financial analysis purposes. It is intended to identify possible earnings quality concerns and should not be considered proof of financial fraud.

## Author

Amol Saini
