ETF Portfolio Builder

A full-stack portfolio allocation tool that builds diversified ETF portfolios using rules-based asset allocation and momentum signals.

The application allows users to specify target allocations by sector or asset class, then automatically distributes capital across ETFs using either:

Equal-weight allocation
Momentum + volatility scoring rules

The backend is built with FastAPI (Python) and performs portfolio calculations, while the frontend is a lightweight HTML interface deployed on Netlify.

Live Demo

App -
https://etfbuilder.netlify.app/



Project Overview

This application demonstrates how quantitative investment rules can be implemented in a production API.

Users input:

Asset class targets
Investment amount
Allocation strategy

The system then:

Processes ETF price data from a CSV dataset
Calculates momentum and volatility signals
Selects ETFs within each asset bucket
Allocates portfolio weights accordingly
Returns both weights and dollar allocations

The backend contains 54 ETFs across multiple sectors and asset classes.

System Architecture
Frontend (Netlify)
│
│ POST /allocate
▼
FastAPI Backend
│
├── ETF bucket mapping
├── Price data ingestion
├── Momentum calculations
├── Volatility calculations
├── Portfolio allocation engine
└── API response
Asset Allocation Model

The system organizes ETFs into sector and asset class buckets including:

Technology
AI / Semiconductors
Consumer sectors
Healthcare
Financials
Energy
Utilities
Real estate
US total market
International markets
Bonds
Dividend ETFs
Covered call income ETFs

Example buckets include:

Tech: QQQ, VGT, XLK
AI & Cloud & Semi: SMH, SOXX, SKYY, AIQ
US Broad Market: VTI, ITOT, SCHB
Emerging Markets: VWO, EEM
Treasuries Ladder: SHY, IEF, TLT

These ETFs are used as candidate investments within each bucket.

Allocation Strategies
1. Simple Allocation

Each ETF within a bucket receives an equal share of the target allocation.

Example:

Tech bucket target: 20%

QQQ = 6.67%
VGT = 6.67%
XLK = 6.67%
2. Rules-Based Allocation

A more advanced strategy ranks ETFs using quantitative signals.

Signals calculated:

Momentum

Trailing return over a 126-day window

Volatility

Rolling standard deviation of daily returns (20 days)

Combined score:

score = momentum - 0.5 × volatility

Higher-scoring ETFs receive larger portfolio weights.

Data Pipeline

ETF price data is loaded from a CSV dataset.

Supported formats:

Long format

Date, Ticker, Adj Close

or

Wide format

Date, QQQ, VGT, XLK ...

The system converts the dataset into a time-series matrix where:

Rows = dates
Columns = ETF tickers
Values = prices

From this matrix, the system computes signals and rankings.

API Endpoints
Health Check
GET /health

Returns backend diagnostics including:

dataset status
number of ETFs
last available price date
ETF Buckets
GET /buckets

Returns available asset categories and ETFs.

Portfolio Allocation
POST /allocate

Example request:

{
  "bucketTargets": {
    "Tech": 20,
    "Healthcare": 15,
    "US Broad Market": 40,
    "Aggregate Bonds": 25
  },
  "amount": 10000,
  "mode": "rules"
}

Example response:

{
  "portfolio_weights": {
    "QQQ": 0.12,
    "VGT": 0.08,
    "XLV": 0.15,
    "VTI": 0.25,
    "BND": 0.20
  },
  "portfolio_dollars": {
    "QQQ": 1200,
    "VGT": 800,
    "XLV": 1500,
    "VTI": 2500,
    "BND": 2000
  }
}
Tech Stack

Backend

Python
FastAPI
Pandas
NumPy
Pydantic

Frontend

HTML
JavaScript
Netlify hosting

Data

Historical ETF price dataset (CSV)

Deployment

Render (API hosting)
Netlify (frontend hosting)
Engineering Concepts Demonstrated

This project demonstrates several real-world engineering concepts:

REST API development with FastAPI
financial time-series analysis
momentum-based asset allocation
volatility-adjusted scoring
portfolio weight normalization
quantitative investment rule implementation
frontend-backend API integration
CORS configuration for production deployment
Future Improvements

Potential enhancements include:

live market data integration
portfolio rebalancing simulation
risk parity weighting
Monte Carlo portfolio analysis
Sharpe ratio optimization
interactive visualization dashboard
