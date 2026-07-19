# -*- coding: utf-8 -*-
"""Earnings-quality analysis using SEC Company Facts and Yahoo Finance prices.

The script calculates Beneish M-Scores and Sloan accrual ratios from annual
10-K facts, flags cross-sectional anomalies, measures forward returns from each
company's actual fiscal year-end, and writes CSV/PNG/PDF results to an output
directory beside this script.
"""

from __future__ import annotations

import base64
import html as html_lib
import time
import warnings
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
import yfinance as yf
from matplotlib.backends.backend_pdf import PdfPages
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid")
pd.set_option("display.float_format", lambda x: f"{x:,.3f}")

SEC_HEADERS = {
    # SEC EDGAR requires a descriptive User-Agent with a valid contact email.
    # Replace this with your own name/email before running.
    "User-Agent": "Amol Saini amolsaini19506@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}

TICKERS = [
    "ADBE", "AMD", "ABNB", "ALNY", "GOOGL", "GOOG", "AMZN", "AEP", "AMGN", "ADI",
    "AAPL", "AMAT", "APP", "ARM", "ASML", "ALAB", "ADSK", "ADP", "AXON", "BKR",
    "BKNG", "AVGO", "CDNS", "CTAS", "CSCO", "CCEP", "CMCSA", "CPRT", "CRWD", "DDOG",
    "DXCM", "DLTR", "EA", "EXC", "FANG", "FAST", "FTNT", "GEV", "GILD", "HON",
    "IDXX", "ILMN", "INTC", "INTU", "ISRG", "KDP", "KLAC", "KHC", "LRCX", "LULU",
    "MAR", "MRVL", "MELI", "META", "MCHP", "MU", "MDLZ", "MDB", "MNST", "NFLX",
    "NVDA", "NXPI", "ODFL", "ON", "ORLY", "PCAR", "PANW", "PAYX", "PYPL", "PEP",
    "PDD", "QCOM", "REGN", "ROST", "SGEN", "SIRI", "SNPS", "SPLK", "SWKS", "TTWO",
    "TMUS", "TSLA", "TXN", "KHC", "TCOM", "VRSK", "VRTX", "WBA", "WBD", "WDAY",
    "WMT", "ZS"
]
Z_THRESHOLD = 2.0
BENEISH_THRESHOLD_8VAR = -1.78
BENEISH_THRESHOLD_5VAR = -2.22
BENEISH_THRESHOLD = BENEISH_THRESHOLD_8VAR  # default/display reference (8-variable model)
MEDIUM_Z_THRESHOLD = 1.0
MEDIUM_M_SCORE_MARGIN = 0.50
DATA_QUALITY_COMPLETE_CUTOFF = 90.0
DATA_QUALITY_PARTIAL_CUTOFF = 50.0
MIN_FISCAL_YEAR = datetime.now().year - 6
OUTPUT_DIR = Path(__file__).with_name("output")

COMPANY_INFO = {
    "ADBE": {"industry": "Software"},
    "AMD": {"industry": "Semiconductors"},
    "ABNB": {"industry": "Travel & Leisure"},
    "GOOGL": {"industry": "Internet Services"},
    "AMZN": {"industry": "E-Commerce & Cloud"},
    "AMGN": {"industry": "Biotechnology"},
    "ADI": {"industry": "Semiconductors"},
    "AAPL": {"industry": "Consumer Electronics"},
    "AMAT": {"industry": "Semiconductor Equipment"},
    "ARM": {"industry": "Semiconductors"},
    "ASML": {"industry": "Semiconductor Equipment"},
    "ADSK": {"industry": "Software"},
    "ADP": {"industry": "Business Services"},
    "AXON": {"industry": "Aerospace & Defense"},
    "BKNG": {"industry": "Travel & Leisure"},
    "AVGO": {"industry": "Semiconductors"},
    "CDNS": {"industry": "Software"},
    "CTAS": {"industry": "Business Services"},
    "CSCO": {"industry": "Networking Equipment"},
    "CMCSA": {"industry": "Media & Entertainment"},
    "CPRT": {"industry": "Business Services"},
    "CRWD": {"industry": "Cybersecurity"},
    "DDOG": {"industry": "Cloud Software"},
    "DXCM": {"industry": "Medical Devices"},
    "DLTR": {"industry": "Retail"},
    "EA": {"industry": "Video Games"},
    "EXC": {"industry": "Utilities"},
    "FAST": {"industry": "Industrial Supplies"},
    "FTNT": {"industry": "Cybersecurity"},
    "GEV": {"industry": "Industrial Manufacturing"},
    "GILD": {"industry": "Biotechnology"},
    "HON": {"industry": "Industrial Conglomerates"},
    "IDXX": {"industry": "Medical Diagnostics"},
    "ILMN": {"industry": "Life Sciences"},
    "INTC": {"industry": "Semiconductors"},
    "INTU": {"industry": "Financial Software"},
    "ISRG": {"industry": "Medical Devices"},
    "KDP": {"industry": "Beverages"},
    "KLAC": {"industry": "Semiconductor Equipment"},
    "KHC": {"industry": "Food & Beverage"},
    "LRCX": {"industry": "Semiconductor Equipment"},
    "LULU": {"industry": "Apparel"},
    "MAR": {"industry": "Hotels & Resorts"},
    "MRVL": {"industry": "Semiconductors"},
    "MELI": {"industry": "E-Commerce"},
    "META": {"industry": "Internet Services"},
    "MCHP": {"industry": "Semiconductors"},
    "MU": {"industry": "Semiconductors"},
    "MDLZ": {"industry": "Food & Beverage"},
    "MDB": {"industry": "Cloud Software"},
    "MNST": {"industry": "Beverages"},
    "NFLX": {"industry": "Streaming Media"},
    "NVDA": {"industry": "Semiconductors"},
    "NXPI": {"industry": "Semiconductors"},
    "ODFL": {"industry": "Transportation"},
    "ON": {"industry": "Semiconductors"},
    "ORLY": {"industry": "Retail"},
    "PCAR": {"industry": "Automobiles"},
    "PANW": {"industry": "Cybersecurity"},
    "PAYX": {"industry": "Business Services"},
    "PYPL": {"industry": "Financial Services"},
    "PEP": {"industry": "Beverages"},
    "PDD": {"industry": "E-Commerce"},
    "QCOM": {"industry": "Semiconductors"},
    "REGN": {"industry": "Biotechnology"},
    "ROST": {"industry": "Retail"},
    "SIRI": {"industry": "Media & Entertainment"},
    "SNPS": {"industry": "Software"},
    "SPLK": {"industry": "Cloud Software"},
    "SWKS": {"industry": "Semiconductors"},
    "TTWO": {"industry": "Video Games"},
    "TMUS": {"industry": "Telecommunications"},
    "TSLA": {"industry": "Automobiles"},
    "TXN": {"industry": "Semiconductors"},
    "TCOM": {"industry": "Travel & Leisure"},
    "VRSK": {"industry": "Business Services"},
    "VRTX": {"industry": "Biotechnology"},
    "WBA": {"industry": "Retail"},
    "WBD": {"industry": "Media & Entertainment"},
    "WDAY": {"industry": "Software"},
    "WMT": {"industry": "Retail"},
    "ZS": {"industry": "Cybersecurity"}
}

# kind="duration" means a full-year flow; kind="instant" means a balance at
# fiscal year-end. Tags are ordered from most to least preferred.
CONCEPTS = {
    "Revenues": {
        "kind": "duration",
        "tags": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],
    },
    "CostOfRevenue": {
        "kind": "duration",
        "tags": ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold"],
    },
    "NetIncome": {
        "kind": "duration",
        "tags": ["NetIncomeLoss", "ProfitLoss"],
    },
    "Receivables": {
        "kind": "instant",
        "tags": [
            "AccountsReceivableNetCurrent",
            "AccountsNotesAndLoansReceivableNetCurrent",
            "ReceivablesNetCurrent",
            "AccountsReceivableNet",
        ],
    },
    "CurrentAssets": {"kind": "instant", "tags": ["AssetsCurrent"]},
    "PPE": {
        "kind": "instant",
        "tags": [
            "PropertyPlantAndEquipmentNet",
            "PropertyPlantAndEquipmentNetIncludingFinanceLeaseRightOfUseAsset",
        ],
    },
    "TotalAssets": {"kind": "instant", "tags": ["Assets"]},
    "Depreciation": {
        "kind": "duration",
        "tags": [
            "DepreciationDepletionAndAmortization",
            "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
            "DepreciationAmortizationAndAccretionNet",
            "Depreciation",
            "DepreciationAndAmortization",
        ],
    },
    "SGA": {
        "kind": "duration",
        "tags": [
            "SellingGeneralAndAdministrativeExpense",
            "GeneralAndAdministrativeExpense",
        ],
    },
    "CurrentLiabilities": {
        "kind": "instant",
        "tags": ["LiabilitiesCurrent"],
    },
    "LongTermDebt": {
        "kind": "instant",
        "tags": [
            "LongTermDebtNoncurrent",
            "LongTermDebt",
            "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
        ],
    },
    "OperatingCashFlow": {
        "kind": "duration",
        "tags": [
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        ],
    },
}

# Helper concepts are fetched from SEC facts too, but only ever used to
# *derive* a missing core field (e.g. CostOfRevenue = Revenues - GrossProfit).
# They are never required themselves and never appear in REQUIRED_FIELDS.
HELPER_CONCEPTS = {
    "GrossProfit": {
        "kind": "duration",
        "tags": ["GrossProfit"],
    },
    "Liabilities": {
        "kind": "instant",
        "tags": ["Liabilities"],
    },
    "SellingAndMarketingExpense": {
        "kind": "duration",
        "tags": ["SellingAndMarketingExpense"],
    },
    "GeneralAndAdministrativeExpense": {
        "kind": "duration",
        "tags": ["GeneralAndAdministrativeExpense"],
    },
    "PropertyPlantAndEquipmentGross": {
        "kind": "instant",
        "tags": ["PropertyPlantAndEquipmentGross"],
    },
    "AccumulatedDepreciationPPE": {
        "kind": "instant",
        "tags": [
            "AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
            "AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAsset",
        ],
    },
}

ALL_CONCEPTS = {**CONCEPTS, **HELPER_CONCEPTS}

REQUIRED_FIELDS = list(CONCEPTS)


def make_sec_session() -> requests.Session:
    """Create a retrying SEC HTTP session."""
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update(SEC_HEADERS)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def load_ticker_cik_map(session: requests.Session) -> dict[str, str]:
    """Download the SEC's official ticker-to-CIK lookup table."""
    response = session.get(
        "https://www.sec.gov/files/company_tickers.json", timeout=30
    )
    response.raise_for_status()
    return {
        entry["ticker"].upper(): str(entry["cik_str"]).zfill(10)
        for entry in response.json().values()
    }


def fetch_company_facts(
    session: requests.Session, ticker: str, cik: str
) -> dict | None:
    """Fetch one issuer's SEC Company Facts response."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    try:
        response = session.get(url, timeout=45)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"  {ticker}: Company Facts request failed: {exc}")
        return None


def fetch_company_metadata(
    session: requests.Session, ticker_cik: dict[str, str]
) -> pd.DataFrame:
    """Fetch SEC company names and SIC industries for the report filters."""
    records: list[dict] = []
    for ticker in TICKERS:
        cik = ticker_cik.get(ticker)
        fallback_industry = COMPANY_INFO.get(ticker, {}).get("industry", "Unknown")
        if not cik:
            records.append(
                {
                    "ticker": ticker,
                    "Company_Name": ticker,
                    "SIC": np.nan,
                    "Industry": fallback_industry,
                    "Industry_Source": "fallback",
                }
            )
            continue

        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            profile = response.json()
            industry = profile.get("sicDescription") or fallback_industry
            source = "SEC SIC" if profile.get("sicDescription") else "fallback"
            records.append(
                {
                    "ticker": ticker,
                    "Company_Name": profile.get("name") or ticker,
                    "SIC": profile.get("sic"),
                    "Industry": industry,
                    "Industry_Source": source,
                }
            )
        except (requests.RequestException, ValueError) as exc:
            print(f"  {ticker}: SEC metadata request failed: {exc}")
            records.append(
                {
                    "ticker": ticker,
                    "Company_Name": ticker,
                    "SIC": np.nan,
                    "Industry": fallback_industry,
                    "Industry_Source": "fallback",
                }
            )
        time.sleep(0.12)
    return pd.DataFrame(records)


def _as_date(value) -> pd.Timestamp | pd.NaT:
    return pd.to_datetime(value, errors="coerce")


def extract_annual_series(facts_json: dict | None, concept: str) -> pd.DataFrame:
    """Extract one concept by actual annual period, not the filing's FY label.

    SEC's `fy` describes the filing, so comparative prior-year values repeated
    in a newer filing can carry the newer filing's FY. Actual `start`/`end`
    periods are used here, and the latest filed value is retained so genuine
    restatements are reflected.
    """
    columns = ["fiscal_end", "val", "tag", "filed"]
    if not facts_json:
        return pd.DataFrame(columns=columns)

    spec = ALL_CONCEPTS[concept]
    us_gaap = facts_json.get("facts", {}).get("us-gaap", {})
    candidates: list[dict] = []

    for priority, tag in enumerate(spec["tags"]):
        units = us_gaap.get(tag, {}).get("units", {}).get("USD", [])
        for item in units:
            if item.get("form") not in {"10-K", "10-K/A"} or item.get("fp") != "FY":
                continue

            fiscal_end = _as_date(item.get("end"))
            filed = _as_date(item.get("filed"))
            value = pd.to_numeric(item.get("val"), errors="coerce")
            if pd.isna(fiscal_end) or pd.isna(filed) or not np.isfinite(value):
                continue

            duration_gap = 0
            period_start = pd.NaT
            if spec["kind"] == "duration":
                period_start = _as_date(item.get("start"))
                if pd.isna(period_start):
                    continue
                days = int((fiscal_end - period_start).days) + 1
                # Covers 52/53-week and conventional annual reporting periods
                # while excluding quarters and year-to-date interim values.
                if not 300 <= days <= 430:
                    continue
                duration_gap = abs(days - 365)

            candidates.append(
                {
                    "fiscal_end": fiscal_end.normalize(),
                    "period_start": period_start,
                    "val": float(value),
                    "tag": tag,
                    "tag_priority": priority,
                    "duration_gap": duration_gap,
                    "filed": filed,
                }
            )

    if not candidates:
        return pd.DataFrame(columns=columns)

    data = pd.DataFrame(candidates)
    # Prefer the best semantic tag and a true one-year duration; within that
    # context retain the newest filing to capture restatements.
    data = data.sort_values(
        ["fiscal_end", "tag_priority", "duration_gap", "filed"],
        ascending=[True, True, True, False],
    )
    data = data.drop_duplicates("fiscal_end", keep="first")
    return data[columns].sort_values("fiscal_end").reset_index(drop=True)


def _has(row: dict, key: str) -> bool:
    value = row.get(key)
    return value is not None and pd.notna(value) and np.isfinite(value)


def _apply_derived_fields(row: dict) -> None:
    """Fill in missing core fields from helper concepts when possible.

    Each derivation only fires when the core field is genuinely absent and
    every input it needs is present, so it never overrides a directly
    reported SEC value.
    """
    if not _has(row, "CostOfRevenue") and _has(row, "Revenues") and _has(row, "GrossProfit"):
        row["CostOfRevenue"] = row["Revenues"] - row["GrossProfit"]

    if (
        not _has(row, "PPE")
        and _has(row, "PropertyPlantAndEquipmentGross")
        and _has(row, "AccumulatedDepreciationPPE")
    ):
        row["PPE"] = row["PropertyPlantAndEquipmentGross"] - abs(row["AccumulatedDepreciationPPE"])

    if not _has(row, "LongTermDebt") and _has(row, "Liabilities") and _has(row, "CurrentLiabilities"):
        row["LongTermDebt"] = row["Liabilities"] - row["CurrentLiabilities"]

    if not _has(row, "SGA") and _has(row, "SellingAndMarketingExpense") and _has(
        row, "GeneralAndAdministrativeExpense"
    ):
        row["SGA"] = row["SellingAndMarketingExpense"] + row["GeneralAndAdministrativeExpense"]


def build_raw_dataset(
    session: requests.Session, ticker_cik: dict[str, str]
) -> pd.DataFrame:
    records: list[dict] = []

    for ticker in TICKERS:
        cik = ticker_cik.get(ticker)
        if not cik:
            print(f"Skipping {ticker}: no SEC CIK was found.")
            continue

        print(f"Fetching SEC facts for {ticker}...")
        facts = fetch_company_facts(session, ticker, cik)
        time.sleep(0.12)
        if facts is None:
            continue

        concept_data = {
            concept: extract_annual_series(facts, concept) for concept in ALL_CONCEPTS
        }
        fiscal_ends = sorted(
            set().union(
                *(set(frame["fiscal_end"]) for frame in concept_data.values() if not frame.empty)
            )
        )

        # Keep one extra prior year because year-over-year ratios need it.
        fiscal_ends = [d for d in fiscal_ends if d.year >= MIN_FISCAL_YEAR - 1]
        for fiscal_end in fiscal_ends:
            row = {
                "ticker": ticker,
                "fy": int(fiscal_end.year),
                "fiscal_end": fiscal_end,
            }
            for concept, frame in concept_data.items():
                match = frame.loc[frame["fiscal_end"] == fiscal_end, "val"]
                row[concept] = match.iloc[0] if not match.empty else np.nan
            _apply_derived_fields(row)
            records.append(row)

    columns = ["ticker", "fy", "fiscal_end", *CONCEPTS]
    return pd.DataFrame(records, columns=columns).sort_values(
        ["ticker", "fiscal_end"]
    ).reset_index(drop=True)


def _finite_values(row: pd.Series, names: list[str]) -> bool:
    return all(pd.notna(row[name]) and np.isfinite(row[name]) for name in names)


FIVE_VAR_FIELDS = [
    "Revenues", "Receivables", "CurrentAssets", "PPE", "TotalAssets",
    "NetIncome", "OperatingCashFlow", "CostOfRevenue", "Depreciation",
]


def compute_forensic_ratios(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate M-Score/Sloan ratios and record every excluded comparison.

    Tries the full 8-variable Beneish model first. If LongTermDebt (or
    CurrentLiabilities, needed alongside it for LVGI) is missing even after
    derivation, falls back to the 5-variable Beneish model (Beneish, 1999):

        M = -6.065 + 0.823*DSRI + 0.906*GMI + 0.593*AQI + 0.717*SGI + 0.107*DEPI

    That formula still needs CostOfRevenue and Depreciation (for GMI/DEPI),
    so those two fields are required for both models; only LongTermDebt and
    CurrentLiabilities are dropped in the fallback.
    """
    output: list[dict] = []
    exclusions: list[dict] = []

    for ticker, group in df.groupby("ticker", sort=True):
        group = group.sort_values("fiscal_end").reset_index(drop=True)
        for index in range(1, len(group)):
            current, previous = group.iloc[index], group.iloc[index - 1]
            gap_days = (current["fiscal_end"] - previous["fiscal_end"]).days
            if not 300 <= gap_days <= 430:
                exclusions.append(
                    {
                        "ticker": ticker,
                        "fiscal_end": current["fiscal_end"],
                        "reason": f"prior annual period is {gap_days} days earlier",
                    }
                )
                continue

            # Net income and CFO are needed only in the current year.
            def _missing_fields(fields):
                return [
                    field
                    for field in fields
                    if pd.isna(current[field])
                    or (
                        field not in {"NetIncome", "OperatingCashFlow"}
                        and pd.isna(previous[field])
                    )
                ]

            missing_full = _missing_fields(REQUIRED_FIELDS)
            use_five_variable = bool(missing_full)
            if use_five_variable:
                missing_five = _missing_fields(FIVE_VAR_FIELDS)
                if missing_five:
                    exclusions.append(
                        {
                            "ticker": ticker,
                            "fiscal_end": current["fiscal_end"],
                            "reason": (
                                "missing SEC facts even for 5-variable fallback: "
                                + ", ".join(missing_five)
                            ),
                        }
                    )
                    continue

            sales_t, sales_p = current["Revenues"], previous["Revenues"]
            rec_t, rec_p = current["Receivables"], previous["Receivables"]
            ca_t, ca_p = current["CurrentAssets"], previous["CurrentAssets"]
            ppe_t, ppe_p = current["PPE"], previous["PPE"]
            ta_t, ta_p = current["TotalAssets"], previous["TotalAssets"]
            ni_t, cfo_t = current["NetIncome"], current["OperatingCashFlow"]
            cogs_t, cogs_p = current["CostOfRevenue"], previous["CostOfRevenue"]
            dep_t, dep_p = current["Depreciation"], previous["Depreciation"]
            gm_t = (sales_t - cogs_t) / sales_t if sales_t else np.nan
            gm_p = (sales_p - cogs_p) / sales_p if sales_p else np.nan

            denominators = [
                sales_t,
                sales_p,
                rec_p / sales_p if sales_p else np.nan,
                1 - (ca_p + ppe_p) / ta_p if ta_p else np.nan,
                ta_t,
                (ta_t + ta_p) / 2,
                gm_t,
                dep_t + ppe_t,
                dep_p + ppe_p,
            ]
            if not use_five_variable:
                cl_t, cl_p = current["CurrentLiabilities"], previous["CurrentLiabilities"]
                ltd_t, ltd_p = current["LongTermDebt"], previous["LongTermDebt"]
                denominators += [
                    (cl_p + ltd_p) / ta_p if ta_p else np.nan,
                ]

            if not _finite_values(pd.Series(denominators), list(range(len(denominators)))) or any(
                value == 0 for value in denominators
            ):
                exclusions.append(
                    {
                        "ticker": ticker,
                        "fiscal_end": current["fiscal_end"],
                        "reason": "zero or invalid formula denominator",
                    }
                )
                continue

            dsri = (rec_t / sales_t) / (rec_p / sales_p)
            aqi = (1 - (ca_t + ppe_t) / ta_t) / (1 - (ca_p + ppe_p) / ta_p)
            sgi = sales_t / sales_p
            tata = (ni_t - cfo_t) / ta_t
            sloan_ratio = (ni_t - cfo_t) / ((ta_t + ta_p) / 2)
            gmi = gm_p / gm_t
            depi = (dep_p / (dep_p + ppe_p)) / (dep_t / (dep_t + ppe_t))

            if use_five_variable:
                sgai = np.nan
                lvgi = np.nan
                model_type = "5-variable"
                m_score = (
                    -6.065
                    + 0.823 * dsri
                    + 0.906 * gmi
                    + 0.593 * aqi
                    + 0.717 * sgi
                    + 0.107 * depi
                )
                metrics = [dsri, gmi, aqi, sgi, depi, m_score, sloan_ratio]
            else:
                sga_t, sga_p = current["SGA"], previous["SGA"]
                sga_denominator = sga_p / sales_p if sales_p else np.nan
                if not np.isfinite(sga_denominator) or sga_denominator == 0:
                    exclusions.append(
                        {
                            "ticker": ticker,
                            "fiscal_end": current["fiscal_end"],
                            "reason": "zero or invalid formula denominator",
                        }
                    )
                    continue
                sgai = (sga_t / sales_t) / sga_denominator
                lvgi = ((cl_t + ltd_t) / ta_t) / ((cl_p + ltd_p) / ta_p)
                model_type = "8-variable"
                m_score = (
                    -4.84
                    + 0.920 * dsri
                    + 0.528 * gmi
                    + 0.404 * aqi
                    + 0.892 * sgi
                    + 0.115 * depi
                    - 0.172 * sgai
                    + 4.679 * tata
                    - 0.327 * lvgi
                )
                metrics = [dsri, gmi, aqi, sgi, depi, sgai, lvgi, tata, m_score, sloan_ratio]

            if not all(np.isfinite(metrics)):
                exclusions.append(
                    {
                        "ticker": ticker,
                        "fiscal_end": current["fiscal_end"],
                        "reason": "formula produced a non-finite value",
                    }
                )
                continue

            output.append(
                {
                    "ticker": ticker,
                    "fy": int(current["fy"]),
                    "fiscal_end": current["fiscal_end"],
                    "Model_Type": model_type,
                    "DSRI": dsri,
                    "GMI": gmi,
                    "AQI": aqi,
                    "SGI": sgi,
                    "DEPI": depi,
                    "SGAI": sgai,
                    "LVGI": lvgi,
                    "TATA": tata,
                    "M_Score": m_score,
                    "Sloan_Ratio": sloan_ratio,
                }
            )

    ratios = pd.DataFrame(output)
    excluded = pd.DataFrame(exclusions)
    if not ratios.empty:
        ratios = ratios[ratios["fy"] >= MIN_FISCAL_YEAR].reset_index(drop=True)
    if not excluded.empty:
        excluded = excluded[pd.to_datetime(excluded["fiscal_end"]).dt.year >= MIN_FISCAL_YEAR]
    return ratios, excluded.reset_index(drop=True)


def zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    if pd.isna(std) or std == 0:
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def flag_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["M_Score_Z"] = result.groupby("fy")["M_Score"].transform(zscore)
    result["Sloan_Ratio_Z"] = result.groupby("fy")["Sloan_Ratio"].transform(zscore)
    # The Beneish hard cutoff differs by model: -1.78 for the 8-variable
    # model, -2.22 for the 5-variable fallback.
    result["Beneish_Threshold"] = np.where(
        result["Model_Type"] == "5-variable",
        BENEISH_THRESHOLD_5VAR,
        BENEISH_THRESHOLD_8VAR,
    )
    result["Beneish_Flag"] = (result["M_Score"] > result["Beneish_Threshold"]) | (
        result["M_Score_Z"] > Z_THRESHOLD
    )
    result["Sloan_Flag"] = result["Sloan_Ratio_Z"].abs() > Z_THRESHOLD
    result["Any_Flag"] = result["Beneish_Flag"] | result["Sloan_Flag"]
    return result


def calculate_data_quality(raw: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    """Summarize how complete each ticker's SEC facts are for the analysis."""
    metadata_by_ticker = metadata.set_index("ticker") if not metadata.empty else pd.DataFrame()
    records: list[dict] = []
    for ticker, group in raw.groupby("ticker", sort=True):
        available = int(group[REQUIRED_FIELDS].notna().sum().sum())
        possible = int(len(group) * len(REQUIRED_FIELDS))
        score = round(available / possible * 100, 1) if possible else 0.0
        if score >= DATA_QUALITY_COMPLETE_CUTOFF:
            status = "Complete"
        elif score >= DATA_QUALITY_PARTIAL_CUTOFF:
            status = "Partial"
        else:
            status = "Insufficient"
        if not metadata_by_ticker.empty and ticker in metadata_by_ticker.index:
            company_name = metadata_by_ticker.loc[ticker, "Company_Name"]
            sic = metadata_by_ticker.loc[ticker, "SIC"]
            industry = metadata_by_ticker.loc[ticker, "Industry"]
            industry_source = metadata_by_ticker.loc[ticker, "Industry_Source"]
        else:
            company_name = ticker
            sic = np.nan
            industry = COMPANY_INFO.get(ticker, {}).get("industry", "Unknown")
            industry_source = "fallback"
        records.append(
            {
                "ticker": ticker,
                "Company_Name": company_name,
                "SIC": sic,
                "Industry": industry,
                "Industry_Source": industry_source,
                "Data_Quality_Score": score,
                "Data_Quality_Status": status,
                "Available_SEC_Facts": available,
                "Possible_SEC_Facts": possible,
            }
        )
    return pd.DataFrame(records).sort_values("ticker").reset_index(drop=True)


def risk_label(row: pd.Series) -> str:
    """Convert numerical warning signs into a simple risk label."""
    if bool(row.get("Any_Flag", False)):
        return "High Risk"

    m_score = row.get("M_Score", np.nan)
    m_z = row.get("M_Score_Z", np.nan)
    sloan_z = row.get("Sloan_Ratio_Z", np.nan)
    threshold = row.get("Beneish_Threshold", BENEISH_THRESHOLD_8VAR)
    near_m_score_threshold = (
        pd.notna(m_score) and m_score >= threshold - MEDIUM_M_SCORE_MARGIN
    )
    elevated_m_z = pd.notna(m_z) and abs(m_z) >= MEDIUM_Z_THRESHOLD
    elevated_sloan_z = pd.notna(sloan_z) and abs(sloan_z) >= MEDIUM_Z_THRESHOLD
    if near_m_score_threshold or elevated_m_z or elevated_sloan_z:
        return "Medium Risk"
    return "Low Risk"


def risk_explanation(row: pd.Series) -> str:
    """Explain each risk label in plain English."""
    ticker = row.get("ticker", "This company")
    label = row.get("Risk_Label", risk_label(row))
    reasons: list[str] = []

    threshold = row.get("Beneish_Threshold", BENEISH_THRESHOLD_8VAR)
    if bool(row.get("Beneish_Flag", False)):
        if row.get("M_Score", np.nan) > threshold:
            reasons.append(
                f"its M-Score of {row['M_Score']:.3f} exceeded the "
                f"{threshold:.3f} Beneish threshold"
            )
        if row.get("M_Score_Z", np.nan) > Z_THRESHOLD:
            reasons.append(
                f"its M-Score z-score of {row['M_Score_Z']:.2f} was above "
                f"the {Z_THRESHOLD:.1f} cross-company threshold"
            )

    if bool(row.get("Sloan_Flag", False)):
        reasons.append(
            f"its Sloan accrual z-score of {row['Sloan_Ratio_Z']:.2f} was "
            f"outside the +/-{Z_THRESHOLD:.1f} threshold"
        )

    if label == "High Risk":
        if not reasons:
            reasons.append("one or more high-risk thresholds were exceeded")
        return f"{ticker} was flagged because " + "; ".join(reasons) + "."

    if label == "Medium Risk":
        m_score = row.get("M_Score", np.nan)
        m_z = row.get("M_Score_Z", np.nan)
        sloan_z = row.get("Sloan_Ratio_Z", np.nan)
        if pd.notna(m_score) and m_score >= threshold - MEDIUM_M_SCORE_MARGIN:
            reasons.append(
                f"its M-Score of {m_score:.3f} was close to the high-risk threshold"
            )
        if pd.notna(m_z) and abs(m_z) >= MEDIUM_Z_THRESHOLD:
            reasons.append(f"its M-Score z-score of {m_z:.2f} was elevated")
        if pd.notna(sloan_z) and abs(sloan_z) >= MEDIUM_Z_THRESHOLD:
            reasons.append(f"its Sloan accrual z-score of {sloan_z:.2f} was elevated")
        return f"{ticker} is Medium Risk because " + "; ".join(reasons) + "."

    return (
        f"{ticker} is Low Risk because neither the M-Score nor Sloan accrual "
        "thresholds were exceeded."
    )


def add_risk_and_quality(
    flagged: pd.DataFrame, data_quality: pd.DataFrame
) -> pd.DataFrame:
    """Attach industry, quality status, risk label, and explanation."""
    result = flagged.merge(data_quality, on="ticker", how="left")
    result["Company_Name"] = result["Company_Name"].fillna(result["ticker"])
    result["SIC"] = result["SIC"].fillna("")
    result["Industry"] = result["Industry"].fillna("Unknown")
    result["Industry_Source"] = result["Industry_Source"].fillna("fallback")
    result["Data_Quality_Status"] = result["Data_Quality_Status"].fillna("Insufficient")
    result["Data_Quality_Score"] = result["Data_Quality_Score"].fillna(0.0)
    result["Risk_Label"] = result.apply(risk_label, axis=1)
    result["Risk_Explanation"] = result.apply(risk_explanation, axis=1)
    return result


def _close_series(history: pd.DataFrame) -> pd.Series:
    if history.empty or "Close" not in history:
        return pd.Series(dtype=float)
    close = history["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = pd.to_numeric(close, errors="coerce").dropna().sort_index()
    index = pd.to_datetime(close.index)
    if getattr(index, "tz", None) is not None:
        index = index.tz_localize(None)
    close.index = index.normalize()
    return close[~close.index.duplicated(keep="last")]


def download_prices(ticker: str, fiscal_ends: pd.Series) -> pd.Series:
    first_date = pd.to_datetime(fiscal_ends).min() - pd.Timedelta(days=10)
    # Yahoo's `end` is exclusive. Never request beyond tomorrow.
    end_date = pd.Timestamp(date.today()) + pd.Timedelta(days=1)
    try:
        history = yf.download(
            ticker,
            start=first_date.date().isoformat(),
            end=end_date.date().isoformat(),
            progress=False,
            auto_adjust=True,
            actions=False,
            threads=False,
            multi_level_index=False,
        )
        return _close_series(history)
    except Exception as exc:
        print(f"  {ticker}: price download failed: {exc}")
        return pd.Series(dtype=float)


def forward_return(close: pd.Series, fiscal_end: pd.Timestamp, months: int) -> float:
    """Return from last trading close on/before FYE to the monthly anniversary."""
    if close.empty:
        return np.nan
    fiscal_end = pd.Timestamp(fiscal_end).normalize()
    target = fiscal_end + pd.DateOffset(months=months)
    # Do not substitute the latest available price for a future target date.
    if target > close.index.max():
        return np.nan
    start_prices = close.loc[:fiscal_end]
    end_prices = close.loc[:target]
    if start_prices.empty or end_prices.empty or start_prices.iloc[-1] == 0:
        return np.nan
    return float(end_prices.iloc[-1] / start_prices.iloc[-1] - 1)


def add_forward_returns(df: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for ticker, group in df.groupby("ticker", sort=True):
        print(f"Fetching adjusted prices for {ticker}...")
        group = group.copy()
        close = download_prices(ticker, group["fiscal_end"])
        group["Fwd_6M_Return"] = group["fiscal_end"].map(
            lambda end: forward_return(close, end, 6)
        )
        group["Fwd_12M_Return"] = group["fiscal_end"].map(
            lambda end: forward_return(close, end, 12)
        )
        frames.append(group)
    return pd.concat(frames, ignore_index=True) if frames else df.copy()


def save_plots(df: pd.DataFrame, output_dir: Path) -> None:
    pivot = df.pivot_table(index="ticker", columns="fy", values="M_Score")
    if not pivot.empty:
        plt.figure(figsize=(12, 8))
        sns.heatmap(
            pivot,
            annot=True,
            fmt=".2f",
            cmap="RdYlGn_r",
            center=BENEISH_THRESHOLD,
            cbar_kws={"label": "Beneish M-Score"},
            linewidths=0.5,
            linecolor="white",
        )
        plt.title("Beneish M-Score by Company and Fiscal Year")
        plt.xlabel("Fiscal year (year containing actual fiscal year-end)")
        plt.ylabel("Ticker")
        plt.tight_layout()
        plt.savefig(output_dir / "beneish_mscore_heatmap.png", dpi=180)
        plt.close()

    plt.figure(figsize=(10, 7))
    colors = df["Any_Flag"].map({True: "crimson", False: "steelblue"})
    plt.scatter(
        df["M_Score"], df["Sloan_Ratio"], c=colors, alpha=0.75, edgecolor="k", s=70
    )
    plt.axvline(
        BENEISH_THRESHOLD_8VAR, color="gray", linestyle="--", linewidth=1,
        label=f"8-var threshold ({BENEISH_THRESHOLD_8VAR:.2f})",
    )
    if (df["Model_Type"] == "5-variable").any():
        plt.axvline(
            BENEISH_THRESHOLD_5VAR, color="darkgray", linestyle=":", linewidth=1,
            label=f"5-var threshold ({BENEISH_THRESHOLD_5VAR:.2f})",
        )
    plt.legend(fontsize=8)
    for _, row in df[df["Any_Flag"]].iterrows():
        plt.annotate(
            f"{row['ticker']} {row['fiscal_end'].date()}",
            (row["M_Score"], row["Sloan_Ratio"]),
            fontsize=7,
            xytext=(4, 4),
            textcoords="offset points",
        )
    plt.xlabel("Beneish M-Score")
    plt.ylabel("Sloan Accrual Ratio")
    plt.title("Earnings-Manipulation Risk Map")
    plt.tight_layout()
    plt.savefig(output_dir / "risk_map.png", dpi=180)
    plt.close()

    comparison = df.groupby("Any_Flag")[["Fwd_6M_Return", "Fwd_12M_Return"]].mean()
    if not comparison.empty and comparison.notna().any().any():
        comparison.index = comparison.index.map({True: "Flagged", False: "Not Flagged"})
        comparison.plot(kind="bar", figsize=(8, 5), color=["seagreen", "indianred"])
        plt.title("Average Forward Returns from Actual Fiscal Year-End")
        plt.ylabel("Average adjusted-price return")
        plt.xticks(rotation=0)
        plt.axhline(0, color="black", linewidth=0.8)
        plt.tight_layout()
        plt.savefig(output_dir / "forward_return_comparison.png", dpi=180)
        plt.close()


def generate_scorecard(ticker: str, df: pd.DataFrame, output_dir: Path) -> Path:
    subset = df[df["ticker"] == ticker].sort_values("fiscal_end")
    if subset.empty:
        raise ValueError(f"No computed ratio data is available for {ticker}.")

    fig, axes = plt.subplots(
        2, 1, figsize=(10, 9), gridspec_kw={"height_ratios": [1, 1.4]}
    )
    axis = axes[0]
    axis.plot(subset["fiscal_end"], subset["M_Score"], marker="o", color="crimson")
    axis.axhline(
        BENEISH_THRESHOLD_8VAR, color="gray", linestyle="--", linewidth=1,
        label=f"8-var threshold ({BENEISH_THRESHOLD_8VAR:.2f})",
    )
    if (subset["Model_Type"] == "5-variable").any():
        axis.axhline(
            BENEISH_THRESHOLD_5VAR, color="darkgray", linestyle=":", linewidth=1,
            label=f"5-var threshold ({BENEISH_THRESHOLD_5VAR:.2f})",
        )
    axis.legend(fontsize=7, loc="upper left")
    axis.set_ylabel("M-Score", color="crimson")
    twin = axis.twinx()
    twin.plot(
        subset["fiscal_end"],
        subset["Sloan_Ratio"],
        marker="s",
        color="steelblue",
    )
    twin.set_ylabel("Sloan ratio", color="steelblue")
    axis.set_title(f"{ticker}: Earnings-Quality Trend")

    table_axis = axes[1]
    table_axis.axis("off")
    columns = [
        "fiscal_end",
        "Risk_Label",
        "M_Score",
        "Sloan_Ratio",
        "Fwd_6M_Return",
        "Fwd_12M_Return",
    ]
    table_frame = subset[columns].copy()
    table_frame["fiscal_end"] = table_frame["fiscal_end"].dt.strftime("%Y-%m-%d")
    numeric = table_frame.select_dtypes(include="number").columns
    table_frame[numeric] = table_frame[numeric].round(3)
    table = table_axis.table(
        cellText=table_frame.astype(str).values,
        colLabels=columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.6)
    table_axis.set_title("Red-Flag Scorecard", fontsize=11, pad=20)
    plt.tight_layout()

    destination = output_dir / f"{ticker}_redflag_scorecard.pdf"
    fig.savefig(
        output_dir / f"{ticker}_redflag_scorecard.png",
        dpi=180,
        bbox_inches="tight",
    )
    with PdfPages(destination) as pdf:
        pdf.savefig(fig)
    plt.close(fig)
    return destination


def _embedded_png(path: Path) -> str:
    """Return a PNG as a self-contained data URI for the HTML report."""
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _table_html(frame: pd.DataFrame, float_digits: int = 3) -> str:
    """Render a complete, scrollable DataFrame table for the local report."""
    return frame.to_html(
        index=False,
        border=0,
        classes="data-table",
        na_rep="-",
        escape=True,
        float_format=lambda value: f"{value:,.{float_digits}f}",
    )


def _format_display_value(column: str, value) -> str:
    """Format report values for the filterable table."""
    if pd.isna(value):
        return "-"
    if column == "fiscal_end":
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    if column in {"Fwd_6M_Return", "Fwd_12M_Return"}:
        return f"{float(value) * 100:,.1f}%"
    if column == "Data_Quality_Score":
        return f"{float(value):,.1f}%"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):,.3f}"
    return str(value)


def _interactive_results_table(frame: pd.DataFrame) -> str:
    """Build an HTML table whose rows can be filtered by browser-side controls."""
    columns = [
        ("ticker", "Company"),
        ("Company_Name", "Company Name"),
        ("Industry", "Industry"),
        ("fy", "Year"),
        ("fiscal_end", "Fiscal End"),
        ("Risk_Label", "Risk"),
        ("Risk_Explanation", "Explanation"),
        ("Data_Quality_Status", "Data Quality"),
        ("Data_Quality_Score", "Quality Score"),
        ("Model_Type", "Model"),
        ("M_Score", "M-Score"),
        ("Sloan_Ratio", "Sloan Ratio"),
        ("Fwd_6M_Return", "Forward 6M"),
        ("Fwd_12M_Return", "Forward 12M"),
    ]
    header = "".join(f"<th>{html_lib.escape(label)}</th>" for _, label in columns)
    rows: list[str] = []
    for _, row in frame.sort_values(["fiscal_end", "ticker"]).iterrows():
        risk = str(row.get("Risk_Label", "Low Risk"))
        risk_class = risk.lower().replace(" ", "-")
        attrs = {
            "data-ticker": row.get("ticker", ""),
            "data-year": row.get("fy", ""),
            "data-risk": risk,
            "data-industry": row.get("Industry", "Unknown"),
        }
        attr_html = " ".join(
            f'{name}="{html_lib.escape(str(value), quote=True)}"'
            for name, value in attrs.items()
        )
        cells: list[str] = []
        for column, _ in columns:
            display = html_lib.escape(_format_display_value(column, row.get(column, np.nan)))
            if column == "Risk_Label":
                display = f'<span class="badge {risk_class}">{display}</span>'
            if column == "Risk_Explanation":
                cells.append(f'<td class="reason">{display}</td>')
            else:
                cells.append(f"<td>{display}</td>")
        rows.append(f"<tr {attr_html}>{''.join(cells)}</tr>")
    return f"""
    <div class="filters">
      <label>Company <select id="filter-company"><option value="">All</option></select></label>
      <label>Year <select id="filter-year"><option value="">All</option></select></label>
      <label>Risk <select id="filter-risk"><option value="">All</option></select></label>
      <label>Industry <select id="filter-industry"><option value="">All</option></select></label>
      <button type="button" id="clear-filters">Clear filters</button>
      <span id="filter-count" class="note"></span>
    </div>
    <div class="table-wrap">
      <table id="interactive-results" class="data-table filter-table">
        <thead><tr>{header}</tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """


def generate_html_report(
    raw: pd.DataFrame,
    coverage: pd.DataFrame,
    data_quality: pd.DataFrame,
    flagged: pd.DataFrame,
    flagged_observations: pd.DataFrame,
    exclusions: pd.DataFrame,
    comparison: pd.DataFrame,
    scorecard: Path,
    output_dir: Path,
) -> Path:
    """Create one self-contained page containing every generated result."""
    chart_specs = [
        ("Beneish M-Score Heatmap", output_dir / "beneish_mscore_heatmap.png"),
        ("M-Score vs. Sloan Risk Map", output_dir / "risk_map.png"),
        ("Forward-Return Comparison", output_dir / "forward_return_comparison.png"),
        ("Red-Flag Scorecard", scorecard.with_suffix(".png")),
    ]
    chart_html = "".join(
        f"""
        <section class="panel chart-panel">
          <h2>{title}</h2>
          <img src="{_embedded_png(path)}" alt="{title}">
        </section>
        """
        for title, path in chart_specs
        if path.exists()
    )

    result_columns = [
        "ticker", "Company_Name", "Industry", "Industry_Source", "SIC", "fy",
        "fiscal_end", "Risk_Label", "Risk_Explanation", "Model_Type",
        "Data_Quality_Status", "Data_Quality_Score", "DSRI", "GMI", "AQI",
        "SGI", "DEPI", "SGAI", "LVGI", "TATA", "M_Score", "Sloan_Ratio",
        "M_Score_Z", "Sloan_Ratio_Z", "Beneish_Flag", "Sloan_Flag",
        "Any_Flag", "Fwd_6M_Return", "Fwd_12M_Return",
    ]
    available_result_columns = [column for column in result_columns if column in flagged]
    all_results = flagged[available_result_columns].sort_values(
        ["fiscal_end", "ticker"]
    )
    flagged_table = flagged_observations[available_result_columns]

    exclusion_counts = (
        exclusions["reason"]
        .value_counts()
        .rename_axis("reason")
        .reset_index(name="company_years")
        if not exclusions.empty
        else pd.DataFrame(columns=["reason", "company_years"])
    )

    coverage_display = coverage.reset_index()
    data_quality_display = data_quality.sort_values(["Data_Quality_Status", "ticker"])
    raw_display = raw.copy()
    money_columns = [column for column in CONCEPTS if column in raw_display]
    raw_display[money_columns] = raw_display[money_columns] / 1_000_000_000
    raw_display = raw_display.rename(
        columns={column: f"{column}_USD_bn" for column in money_columns}
    )

    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    flagged_count = int(flagged["Any_Flag"].sum())
    risk_counts = flagged["Risk_Label"].value_counts()
    quality_counts = data_quality["Data_Quality_Status"].value_counts()
    pdf_link = scorecard.name
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SEC Earnings-Quality Analysis</title>
  <style>
    :root {{ color-scheme: light; --ink:#172033; --muted:#607087; --line:#dbe3ec;
      --panel:#ffffff; --page:#f3f6fa; --accent:#2557a7; --danger:#b42318;
      --warn:#b7791f; --safe:#047857; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--page); color:var(--ink); font:14px/1.45 Arial,sans-serif; }}
    main {{ width:min(1600px, 96vw); margin:24px auto 60px; }}
    h1 {{ margin:0 0 4px; font-size:30px; }} h2 {{ margin:0 0 14px; font-size:20px; }}
    .subtitle {{ color:var(--muted); margin-bottom:22px; }}
    .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(145px,1fr)); gap:12px; margin-bottom:18px; }}
    .card,.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:12px;
      box-shadow:0 2px 7px rgba(23,32,51,.05); }}
    .card {{ padding:16px; }} .card .value {{ font-size:26px; font-weight:700; }}
    .card .label {{ color:var(--muted); }} .danger {{ color:var(--danger); }}
    .panel {{ padding:18px; margin:14px 0; overflow:hidden; }}
    .chart-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    .chart-panel {{ margin:0; }} .chart-panel img {{ width:100%; height:auto; display:block; }}
    .table-wrap {{ overflow:auto; max-height:720px; border:1px solid var(--line); border-radius:8px; }}
    .data-table {{ border-collapse:separate; border-spacing:0; width:max-content; min-width:100%; font-size:12px; }}
    .data-table th,.data-table td {{ padding:7px 9px; border-right:1px solid var(--line);
      border-bottom:1px solid var(--line); white-space:nowrap; text-align:right; }}
    .data-table th {{ position:sticky; top:0; z-index:2; background:#eaf0f8; color:#243b5a; }}
    .data-table td:first-child,.data-table th:first-child {{ text-align:left; }}
    .data-table tr:nth-child(even) td {{ background:#f8fafc; }}
    .filter-table .reason,.data-table td:nth-child(8) {{ min-width:420px; max-width:680px; white-space:normal; text-align:left; line-height:1.35; }}
    .filters {{ display:flex; flex-wrap:wrap; gap:10px 14px; align-items:end; margin-bottom:12px; }}
    .filters label {{ display:flex; flex-direction:column; gap:4px; color:var(--muted); font-size:12px; }}
    .filters select,.filters button {{ border:1px solid var(--line); border-radius:8px; background:white;
      color:var(--ink); padding:8px 10px; font:14px Arial,sans-serif; }}
    .filters button {{ cursor:pointer; color:var(--accent); font-weight:700; }}
    .badge {{ display:inline-block; border-radius:999px; padding:3px 9px; font-weight:700; }}
    .high-risk {{ background:#fee2e2; color:var(--danger); }}
    .medium-risk {{ background:#fef3c7; color:var(--warn); }}
    .low-risk {{ background:#dcfce7; color:var(--safe); }}
    .links a {{ color:var(--accent); margin-right:16px; }}
    .note {{ color:var(--muted); font-size:13px; }}
    @media(max-width:900px) {{ .cards,.chart-grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body><main>
  <h1>SEC Earnings-Quality Analysis</h1>
  <div class="subtitle">Generated {generated_at} | Forward returns begin at each company's actual fiscal year-end.</div>
  <div class="cards">
    <div class="card"><div class="value">{len(raw):,}</div><div class="label">Raw company-years</div></div>
    <div class="card"><div class="value">{raw['ticker'].nunique():,}</div><div class="label">SEC issuers fetched</div></div>
    <div class="card"><div class="value">{len(flagged):,}</div><div class="label">Usable ratio observations</div></div>
    <div class="card"><div class="value danger">{risk_counts.get('High Risk', 0):,}</div><div class="label">High Risk</div></div>
    <div class="card"><div class="value">{risk_counts.get('Medium Risk', 0):,}</div><div class="label">Medium Risk</div></div>
    <div class="card"><div class="value">{risk_counts.get('Low Risk', 0):,}</div><div class="label">Low Risk</div></div>
    <div class="card"><div class="value">{quality_counts.get('Complete', 0):,}</div><div class="label">Complete data companies</div></div>
    <div class="card"><div class="value">{len(exclusions):,}</div><div class="label">Excluded comparisons</div></div>
  </div>
  <section class="panel links">
    <strong>Download exact files:</strong>
    <a href="forensic_results.csv">Forensic results CSV</a>
    <a href="flagged_observations.csv">Flags CSV</a>
    <a href="data_quality_summary.csv">Data-quality CSV</a>
    <a href="company_industry_metadata.csv">SEC industry metadata CSV</a>
    <a href="raw_sec_financials.csv">Raw SEC CSV</a>
    <a href="excluded_company_years.csv">Exclusions CSV</a>
    <a href="{pdf_link}">Scorecard PDF</a>
  </section>
  <section class="panel">
    <h2>Filterable Results</h2>
    <p class="note">Use these filters to select by company, fiscal year, risk level, or industry. Risk labels are plain-language wrappers around the same numerical thresholds shown in the table.</p>
    {_interactive_results_table(flagged)}
  </section>
  <section class="panel">
    <h2>Risk and Data-Quality Rules</h2>
    <p class="note">
      High Risk means the Beneish or Sloan hard threshold was exceeded.
      Medium Risk means the observation was close to a hard threshold or had an elevated z-score.
      Low Risk means no M-Score or Sloan threshold was exceeded.
      Data quality is Complete at {DATA_QUALITY_COMPLETE_CUTOFF:.0f}% or more available SEC facts, Partial at {DATA_QUALITY_PARTIAL_CUTOFF:.0f}% to {DATA_QUALITY_COMPLETE_CUTOFF - 0.1:.1f}%, and Insufficient below {DATA_QUALITY_PARTIAL_CUTOFF:.0f}%.
    </p>
  </section>
  <div class="chart-grid">{chart_html}</div>
  <section class="panel"><h2>Flagged Company-Years</h2>
    <div class="table-wrap">{_table_html(flagged_table)}</div></section>
  <section class="panel"><h2>Forward-Return Comparison</h2>
    <div class="table-wrap">{_table_html(comparison.reset_index())}</div></section>
  <section class="panel"><h2>All Forensic Results</h2>
    <div class="table-wrap">{_table_html(all_results)}</div></section>
  <section class="panel"><h2>Exclusions by Reason</h2>
    <div class="table-wrap">{_table_html(exclusion_counts, 0)}</div></section>
  <section class="panel"><h2>Every Excluded Company-Year</h2>
    <div class="table-wrap">{_table_html(exclusions)}</div></section>
  <section class="panel"><h2>Data Quality Summary</h2>
    <div class="table-wrap">{_table_html(data_quality_display)}</div></section>
  <section class="panel"><h2>SEC Fact Coverage</h2>
    <div class="table-wrap">{_table_html(coverage_display, 0)}</div></section>
  <section class="panel"><h2>All Raw SEC Financial Facts (USD billions)</h2>
    <p class="note">Values are scaled only for display. The linked raw CSV retains exact USD amounts.</p>
    <div class="table-wrap">{_table_html(raw_display)}</div></section>
  <script>
    const table = document.getElementById('interactive-results');
    const rows = table ? Array.from(table.querySelectorAll('tbody tr')) : [];
    const filters = {{
      ticker: document.getElementById('filter-company'),
      year: document.getElementById('filter-year'),
      risk: document.getElementById('filter-risk'),
      industry: document.getElementById('filter-industry')
    }};
    const count = document.getElementById('filter-count');
    function populateFilter(select, attr) {{
      const values = [...new Set(rows.map(row => row.dataset[attr]).filter(Boolean))].sort();
      for (const value of values) {{
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      }}
    }}
    function applyFilters() {{
      let visible = 0;
      for (const row of rows) {{
        const show =
          (!filters.ticker.value || row.dataset.ticker === filters.ticker.value) &&
          (!filters.year.value || row.dataset.year === filters.year.value) &&
          (!filters.risk.value || row.dataset.risk === filters.risk.value) &&
          (!filters.industry.value || row.dataset.industry === filters.industry.value);
        row.style.display = show ? '' : 'none';
        if (show) visible += 1;
      }}
      if (count) count.textContent = `${{visible}} of ${{rows.length}} rows shown`;
    }}
    if (table) {{
      populateFilter(filters.ticker, 'ticker');
      populateFilter(filters.year, 'year');
      populateFilter(filters.risk, 'risk');
      populateFilter(filters.industry, 'industry');
      Object.values(filters).forEach(select => select.addEventListener('change', applyFilters));
      document.getElementById('clear-filters').addEventListener('click', () => {{
        Object.values(filters).forEach(select => select.value = '');
        applyFilters();
      }});
      applyFilters();
    }}
  </script>
</main></body></html>"""

    destination = output_dir / "complete_analysis_report.html"
    destination.write_text(html, encoding="utf-8")
    return destination


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Universe: {len(TICKERS)} tickers | ratio years: FY{MIN_FISCAL_YEAR} onward")
    print(f"Results directory: {OUTPUT_DIR.resolve()}")

    session = make_sec_session()
    ticker_cik = load_ticker_cik_map(session)
    missing_ciks = [ticker for ticker in TICKERS if ticker not in ticker_cik]
    if missing_ciks:
        print(f"No SEC CIK found for: {missing_ciks}")

    print("Fetching SEC company metadata for industry filters...")
    metadata = fetch_company_metadata(session, ticker_cik)
    metadata.to_csv(OUTPUT_DIR / "company_industry_metadata.csv", index=False)

    raw = build_raw_dataset(session, ticker_cik)
    raw.to_csv(OUTPUT_DIR / "raw_sec_financials.csv", index=False)
    coverage = raw.groupby("ticker")[REQUIRED_FIELDS].count()
    coverage.to_csv(OUTPUT_DIR / "sec_fact_coverage.csv")
    data_quality = calculate_data_quality(raw, metadata)
    data_quality.to_csv(OUTPUT_DIR / "data_quality_summary.csv", index=False)
    print(f"Raw SEC dataset: {len(raw)} company-years across {raw['ticker'].nunique()} tickers")

    ratios, exclusions = compute_forensic_ratios(raw)
    exclusions.to_csv(OUTPUT_DIR / "excluded_company_years.csv", index=False)
    if ratios.empty:
        raise RuntimeError(
            "No complete company-years could be calculated. See "
            f"{OUTPUT_DIR / 'excluded_company_years.csv'} for exact reasons."
        )

    flagged = flag_anomalies(ratios)
    flagged = add_forward_returns(flagged)
    flagged = add_risk_and_quality(flagged, data_quality)
    flagged.to_csv(OUTPUT_DIR / "forensic_results.csv", index=False)
    flagged_observations = flagged[flagged["Any_Flag"]].sort_values(
        ["fiscal_end", "ticker"]
    )
    flagged_observations.to_csv(
        OUTPUT_DIR / "flagged_observations.csv", index=False
    )

    display_columns = [
        "ticker",
        "Company_Name",
        "Industry",
        "fiscal_end",
        "Risk_Label",
        "Model_Type",
        "M_Score",
        "M_Score_Z",
        "Sloan_Ratio",
        "Sloan_Ratio_Z",
        "Beneish_Flag",
        "Sloan_Flag",
        "Data_Quality_Status",
        "Data_Quality_Score",
        "Fwd_6M_Return",
        "Fwd_12M_Return",
        "Risk_Explanation",
    ]
    print("\n" + "=" * 110)
    print("DETAILED FORENSIC RESULTS")
    print("=" * 110)
    print(
        flagged[display_columns]
        .sort_values(["fiscal_end", "ticker"])
        .round(3)
        .to_string(index=False)
    )

    print("\n" + "=" * 110)
    print("FLAGGED COMPANY-YEARS")
    print("=" * 110)
    if flagged_observations.empty:
        print("No observations were flagged.")
    else:
        print(flagged_observations[display_columns].round(3).to_string(index=False))

    print("\n" + "=" * 110)
    print("DATA QUALITY SUMMARY")
    print("=" * 110)
    print(data_quality.round(1).to_string(index=False))

    comparison = flagged.groupby("Any_Flag")[[
        "Fwd_6M_Return", "Fwd_12M_Return"
    ]].agg(["count", "mean", "median"])
    comparison.index = comparison.index.map(
        {True: "Flagged", False: "Not Flagged"}
    )
    print("\n" + "=" * 110)
    print("FORWARD-RETURN COMPARISON (FROM ACTUAL FISCAL YEAR-END)")
    print("=" * 110)
    print(comparison.round(4).to_string())

    print("\n" + "=" * 110)
    print("EXCLUDED COMPANY-YEARS BY REASON")
    print("=" * 110)
    if exclusions.empty:
        print("None")
    else:
        print(exclusions["reason"].value_counts().to_string())

    save_plots(flagged, OUTPUT_DIR)
    if flagged["Any_Flag"].any():
        scorecard_ticker = flagged.loc[flagged["Any_Flag"], "ticker"].value_counts().idxmax()
    else:
        scorecard_ticker = flagged["ticker"].iloc[0]
    scorecard = generate_scorecard(scorecard_ticker, flagged, OUTPUT_DIR)
    report = generate_html_report(
        raw=raw,
        coverage=coverage,
        data_quality=data_quality,
        flagged=flagged,
        flagged_observations=flagged_observations,
        exclusions=exclusions,
        comparison=comparison,
        scorecard=scorecard,
        output_dir=OUTPUT_DIR,
    )

    flagged_count = int(flagged["Any_Flag"].sum())
    print(
        f"Completed: {len(flagged)} usable company-years across "
        f"{flagged['ticker'].nunique()} tickers; {flagged_count} flagged."
    )
    print(f"Scorecard: {scorecard}")
    print(f"Complete visual report: {report}")
    print(f"All CSV, PNG, and PDF files: {OUTPUT_DIR.resolve()}")
    try:
        opened = webbrowser.open_new_tab(report.resolve().as_uri())
        if not opened:
            print("The browser did not open automatically; open the report path above.")
    except Exception as exc:
        print(f"Could not open the report automatically: {exc}")


if __name__ == "__main__":
    main()

