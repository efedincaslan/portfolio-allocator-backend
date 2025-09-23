# fastapi_backend.py — simple allocator API with more buckets + dollars + CORS + /buckets
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Optional

app = FastAPI(title="Simple Alloc API")

# Allow the static HTML page (file:// or localhost) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # ok for local dev; tighten later
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Buckets -> ETFs (edit freely) =========================================
BUCKET_ETFS = {
    # --- US Equity (by theme/sector/style) ---
    "Tech":                ["QQQ", "VGT", "XLK"],                           # 3
    "AI & Cloud & Semi":   ["SMH", "SOXX", "SKYY", "AIQ"],                  # 4  (7)
    "Communication":       ["XLC"],                                         # 1  (8)
    "Consumer Discretion": ["XLY"],                                         # 1  (9)
    "Consumer Staples":    ["XLP"],                                         # 1  (10)
    "Healthcare":          ["XLV", "IBB"],                                  # 2  (12)
    "Financials":          ["XLF"],                                         # 1  (13)
    "Industrials":         ["XLI"],                                         # 1  (14)
    "Materials":           ["XLB"],                                         # 1  (15)
    "Energy":              ["XLE", "VDE"],                                  # 2  (17)
    "Utilities":           ["XLU"],                                         # 1  (18)
    "Real Estate":         ["VNQ", "IYR", "SCHH"],                          # 3  (21)
    "US Broad Market":     ["VTI", "ITOT", "SCHB"],                         # 3  (24)
    "US Mid/Small":        ["VO", "MDY", "VB", "IWM"],                      # 4  (28)
    "US Value":            ["VTV", "IWD"],                                  # 2  (30)
    "US Growth":           ["VUG", "IWF"],                                  # 2  (32)
    "Dividends":           ["SCHD", "VYM", "DGRO"],                         # 3  (35)
    "Covered Call Income": ["JEPI", "JEPQ", "QYLD"],                        # 3  (38)

    # --- Fixed Income ---
    "Aggregate Bonds":     ["BND", "AGG", "SCHZ"],                          # 3  (41)
    "Treasuries Ladder":   ["SHY", "IEF", "TLT"],                           # 3  (44)
    "TIPS":                ["TIP", "SCHP"],                                 # 2  (46)
    "Corporate Bonds":     ["LQD"],                                         # 1  (47)
    "High Yield Bonds":    ["HYG", "JNK"],                                  # 2  (49)

    # --- International Equity ---
    "Intl Developed":      ["VEA", "IEFA"],                                 # 2  (51)
    "Emerging Markets":    ["VWO", "EEM"],                                  # 2  (53)
    "Total ex-US":         ["VXUS"],                                        # 1  (54)
}
# fastapi_backend.py (add once)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
