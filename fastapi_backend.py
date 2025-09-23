# fastapi_backend.py — rules-based allocator that uses your CSV (with safe fallback)
import os
from typing import Dict, Optional, List
import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Allocator API (CSV + Rules)")

# Allow your dev UI; add your Netlify URL in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:5173", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Buckets (54 ETFs total) ----------
BUCKET_ETFS: Dict[str, List[str]] = {
    "Tech":                ["QQQ", "VGT", "XLK"],
    "AI & Cloud & Semi":   ["SMH", "SOXX", "SKYY", "AIQ"],
    "Communication":       ["XLC"],
    "Consumer Discretion": ["XLY"],
    "Consumer Staples":    ["XLP"],
    "Healthcare":          ["XLV", "IBB"],
    "Financials":          ["XLF"],
    "Industrials":         ["XLI"],
    "Materials":           ["XLB"],
    "Energy":              ["XLE", "VDE"],
    "Utilities":           ["XLU"],
    "Real Estate":         ["VNQ", "IYR", "SCHH"],
    "US Broad Market":     ["VTI", "ITOT", "SCHB"],
    "US Mid/Small":        ["VO", "MDY", "VB", "IWM"],
    "US Value":            ["VTV", "IWD"],
    "US Growth":           ["VUG", "IWF"],
    "Dividends":           ["SCHD", "VYM", "DGRO"],
    "Covered Call Income": ["JEPI", "JEPQ", "QYLD"],
    "Aggregate Bonds":     ["BND", "AGG", "SCHZ"],
    "Treasuries Ladder":   ["SHY", "IEF", "TLT"],
    "TIPS":                ["TIP", "SCHP"],
    "Corporate Bonds":     ["LQD"],
    "High Yield Bonds":    ["HYG", "JNK"],
    "Intl Developed":      ["VEA", "IEFA"],
    "Emerging Markets":    ["VWO", "EEM"],
    "Total ex-US":         ["VXUS"],
}

# ---------- Data loading ----------
PRICES_CSV_PATH = os.getenv("PRICES_CSV_PATH", "data/etf_prices.csv")
_prices: Optional[pd.DataFrame] = None      # Date index, columns=tickers, values=prices
_signals: Optional[pd.DataFrame] = None     # index=tickers, cols: momentum, vol, score
_mode_ready: bool = False                   # True when CSV loaded & signals computed

def _load_prices_csv(path: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    # LONG format: Date, Ticker, Adj Close (or Close)
    if "Ticker" in df.columns:
        price_col = "Adj Close" if "Adj Close" in df.columns else "Close" if "Close" in df.columns else None
        if price_col is None or "Date" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        px = df.pivot(index="Date", columns="Ticker", values=price_col).sort_index()
    else:
        # WIDE format: Date + columns per ticker
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()
        px = df
    # Clean
    px = px.replace([np.inf, -np.inf], np.nan).dropna(how="all").astype(float)
    return px

def _compute_signals(px: pd.DataFrame, mom_win=126, vol_win=20) -> pd.DataFrame:
    # Momentum = trailing % change; Volatility = rolling std of daily returns
    mom = px.pct_change(mom_win).iloc[-1]
    ret = px.pct_change()
    vol = ret.rolling(vol_win).std().iloc[-1]
    score = mom - 0.5 * vol                     # simple penalty for higher vol
    out = pd.DataFrame({"momentum": mom, "vol": vol, "score": score})
    return out.dropna(how="all")

def _refresh_data():
    global _prices, _signals, _mode_ready
    _prices = _load_prices_csv(PRICES_CSV_PATH)
    if _prices is None or len(_prices) < 60:    # need some history
        _signals, _mode_ready = None, False
        return
    _signals = _compute_signals(_prices)
    _mode_ready = _signals is not None and not _signals.empty

_refresh_data()

# ---------- API models ----------
class AllocationRequest(BaseModel):
    bucketTargets: Dict[str, float] = Field(..., description="Either percents (0–100) or decimals (0–1)")
    amount: Optional[float] = Field(None, description="Total $ to allocate")
    mode: Optional[str] = Field(None, description="'rules' or 'simple'")
    topK: Optional[int] = Field(2, description="Top K tickers per bucket (rules mode)")
    momentum_window: Optional[int] = 126
    vol_window: Optional[int] = 20

@app.get("/ping")
def ping():
    return {"pong": True}

@app.get("/health")
def health():
    return {
        "csv_found": os.path.exists(PRICES_CSV_PATH),
        "mode_ready": _mode_ready,
        "rows": int(_prices.shape[0]) if _prices is not None else 0,
        "cols": int(_prices.shape[1]) if _prices is not None else 0,
        "last_date": None if _prices is None else str(_prices.index.max().date()),
        "path": PRICES_CSV_PATH,
    }

@app.post("/reload")
def reload_data():
    _refresh_data()
    return {"reloaded": True, "mode_ready": _mode_ready}

@app.get("/buckets")
def buckets():
    return {"buckets": [{"name": b, "tickers": tks} for b, tks in BUCKET_ETFS.items()]}

# ---------- Core allocation ----------
def _normalize_targets(raw: Dict[str, float]) -> (Dict[str, float], float):
    clean = {k: max(0.0, float(v)) for k, v in raw.items()}
    s = sum(clean.values())
    targets = clean if s <= 1.000001 else {k: v / 100.0 for k, v in clean.items()}
    s = sum(targets.values())
    if s > 1.0:
        targets = {k: v / s for k, v in targets.items()}
        s = 1.0
    cash = round(1.0 - s, 10)
    return targets, cash

def _allocate_simple(targets: Dict[str, float]) -> Dict[str, float]:
    weights: Dict[str, float] = {}
    for bucket, t in targets.items():
        tks = BUCKET_ETFS.get(bucket, [])
        if not tks or t <= 0:
            continue
        w_each = t / len(tks)
        for tk in tks:
            weights[tk] = weights.get(tk, 0.0) + w_each
    return weights

def _allocate_rules(targets: Dict[str, float], topK: int, mom_win: int, vol_win: int) -> Dict[str, float]:
    # Recompute signals with custom windows if they differ
    sig = _signals
    if _prices is None:
        return _allocate_simple(targets)
    if mom_win != 126 or vol_win != 20:
        sig = _compute_signals(_prices, mom_win, vol_win)

    prices_tickers = set(_prices.columns)
    weights: Dict[str, float] = {}
    for bucket, t in targets.items():
        if t <= 0:
            continue
        candidates = [tk for tk in BUCKET_ETFS.get(bucket, []) if tk in prices_tickers]
        if not candidates:
            # if no price data for this bucket, fall back to simple with whatever list we have
            for tk in BUCKET_ETFS.get(bucket, []):
                weights[tk] = weights.get(tk, 0.0) + t / max(1, len(BUCKET_ETFS.get(bucket, [])))
            continue
        s = sig.loc[[tk for tk in candidates if tk in sig.index]].copy()
        if s.empty:
            # equal split among candidates
            for tk in candidates:
                weights[tk] = weights.get(tk, 0.0) + t / len(candidates)
            continue
        s = s.sort_values("score", ascending=False).head(max(1, topK))
        # positive-score weighting; if all non-positive → equal
        pos = s["score"].clip(lower=0)
        if pos.sum() <= 1e-12:
            w_each = t / len(s)
            for tk in s.index:
                weights[tk] = weights.get(tk, 0.0) + w_each
        else:
            for tk, sc in pos.items():
                weights[tk] = weights.get(tk, 0.0) + t * (float(sc) / float(pos.sum()))
    return weights

@app.post("/allocate")
def allocate(req: AllocationRequest):
    targets, cash_w = _normalize_targets(req.bucketTargets)
    # Decide mode
    desired = (req.mode or "").lower()
    use_rules = (desired == "rules") or (desired == "" and _mode_ready)

    if use_rules and not _mode_ready:
        use_rules = False

    if use_rules:
        weights = _allocate_rules(targets, topK=req.topK or 2,
                                  mom_win=req.momentum_window or 126,
                                  vol_win=req.vol_window or 20)
        mode_used = "rules"
    else:
        weights = _allocate_simple(targets)
        mode_used = "simple"

    # Add CASH
    if cash_w > 1e-9:
        weights["CASH"] = weights.get("CASH", 0.0) + cash_w

    # Dollars
    dollars = None
    if req.amount and req.amount > 0:
        dollars = {tk: round(float(w) * req.amount, 2) for tk, w in weights.items()}

    return {
        "portfolio_weights": {k: round(v, 6) for k, v in weights.items()},
        "portfolio_dollars": dollars,
        "diagnostics": {
            "sum_weights": round(sum(weights.values()), 6),
            "auto_cash_weight": round(cash_w, 6),
            "mode_requested": req.mode or ("(auto)" if _mode_ready else "(auto→simple)"),
            "mode_used": mode_used,
            "csv_found": os.path.exists(PRICES_CSV_PATH),
            "csv_path": PRICES_CSV_PATH,
            "topK": req.topK,
            "momentum_window": req.momentum_window,
            "vol_window": req.vol_window,
        }
    }
