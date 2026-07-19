# SEC Earnings Quality Analysis

## About

This project analyzes the earnings quality of companies using financial data from the SEC Company Facts API.

It calculates the Beneish M-Score and Sloan Accrual Ratio to identify companies that may have a higher risk of earnings manipulation.

The project also compares future stock returns and generates reports.

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

2. Run the Python file.

```bash
python Final_Project_FS.py
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