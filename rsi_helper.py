#!/usr/bin/env python3
"""RSI Helper Tool.

Fetch RSI values from FMP API and analyze with GPT.
"""

import os
import sys
import json
from urllib import request

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

# Default configuration
RSI_PERIOD = 7
LOW_RSI = 25
HIGH_RSI = 80

# List of common large-cap tickers used when no symbols are provided on the
# command line. Feel free to modify as needed.
DEFAULT_SYMBOLS = [
    "MSFT", "NVDA", "AAPL", "AMZN", "GOOG", "META", "TSLA", "AVGO",
    "WMT", "JPM", "LLY", "V", "NFLX", "COST", "XOM", "ORCL", "PG", "JNJ",
    "ABBV", "KO", "ASML", "UNH", "CRM", "GE", "IBM", "CSCO", "TM", "CVX",
    "MCD", "ACN", "SPGI", "AMAT", "ISRG", "VZ", "UPS", "NEE", "DIS", "TMO",
    "BABA", "DE", "BLK", "SBUX", "TSM", "PDD",
]


def fetch_quote(symbol: str, api_key: str) -> dict:
    """Return basic quote info including price and market cap."""
    url = f"{FMP_BASE_URL}/quote/{symbol}?apikey={api_key}"
    data = _http_get_json(url)
    if not data:
        raise ValueError(f"No quote data for {symbol}")
    return data[0]


def fetch_stock_overview(symbol: str, api_key: str) -> dict:
    """Gather RSI values and price information for the symbol."""
    info = {}
    info["rsi7"] = fetch_rsi(symbol, api_key, 7)
    try:
        info["rsi14"] = fetch_rsi(symbol, api_key, 14)
        info["rsi21"] = fetch_rsi(symbol, api_key, 21)
    except Exception:
        pass
    q = fetch_quote(symbol, api_key)
    info["price"] = q.get("price")
    info["market_cap"] = q.get("marketCap")
    info["year_high"] = q.get("yearHigh")
    info["year_low"] = q.get("yearLow")
    return info


def fetch_market_environment(api_key: str) -> dict:
    """Fetch basic market indicators."""
    data = {}
    try:
        data["sp500"] = fetch_quote("SPY", api_key).get("price")
        data["sp500_rsi"] = fetch_rsi("SPY", api_key, 14)
    except Exception:
        pass
    try:
        data["vix"] = fetch_quote("VIX", api_key).get("price")
    except Exception:
        pass
    try:
        data["us10y"] = fetch_quote("US10Y", api_key).get("price")
    except Exception:
        pass
    try:
        data["dxy"] = fetch_quote("DXY", api_key).get("price")
    except Exception:
        pass
    # Simple trend: difference between current SPY and 30 days ago
    try:
        hist = _http_get_json(f"{FMP_BASE_URL}/historical-price-full/SPY?timeseries=30&apikey={api_key}")
        if hist and hist.get("historical"):
            prices = [h.get("close") for h in hist["historical"] if h.get("close")]
            if len(prices) >= 2:
                data["trend"] = prices[0] - prices[-1]
    except Exception:
        pass
    return data


def _http_get_json(url: str):
    req = request.Request(url, headers={"User-Agent": "rsi-helper"})
    with request.urlopen(req, timeout=10) as resp:
        data = resp.read()
    return json.loads(data.decode())


def fetch_rsi(symbol: str, api_key: str, period: int = RSI_PERIOD) -> float:
    url = f"{FMP_BASE_URL}/technical_indicator/daily/{symbol}?period={period}&type=rsi&apikey={api_key}"
    data = _http_get_json(url)
    if not data:
        raise ValueError(f"No RSI data for {symbol}")
    return float(data[-1]["rsi"])


def _openai_request(messages, model="gpt-3.5-turbo"):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = json.dumps({"model": model, "messages": messages}).encode()
    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers=headers,
    )
    with request.urlopen(req, timeout=30) as resp:
        resp_data = resp.read().decode()
    return json.loads(resp_data)


def fetch_latest_news(symbol: str) -> str:
    """Use OpenAI's search model to gather recent news about the symbol."""
    messages = [
        {
            "role": "system",
            "content": "You search the web and summarize the most recent news about a stock.",
        },
        {"role": "user", "content": f"Latest news about {symbol}"},
    ]
    response = _openai_request(messages, model="gpt-3.5-turbo")
    return response["choices"][0]["message"]["content"].strip()


def analyze_with_gpt(symbol: str, rsi_info: dict, market_info: dict, news: str) -> str:
    """Send a formatted prompt to GPT-4o."""
    prompt = f"""
You are a top-tier trading expert specializing in 7-day RSI strategy combined with a 5-level risk assessment framework.Use the Web search tool to collect the latest and comprehensive company information of the stock for analysis.

Instructions:Search for the latest information about the company to which the stock belongs and conduct a systematic analysis.

STOCK INFORMATION TEMPLATE
Stock Name/Ticker: {symbol}
Current 7-day RSI:{rsi_info.get('rsi7','N/A')}
Current Price: ${rsi_info.get('price','N/A')}
Market Cap: {rsi_info.get('market_cap','N/A')}
52-week High/Low: ${rsi_info.get('year_high','N/A')} / ${rsi_info.get('year_low','N/A')}
14-day RSI: {rsi_info.get('rsi14','N/A')}
21-day RSI: {rsi_info.get('rsi21','N/A')}

MARKET ENVIRONMENT DATA TEMPLATE
S&P 500 Current Level: {market_info.get('sp500','N/A')}
S&P 500 14-day RSI: {market_info.get('sp500_rsi','N/A')}
VIX Fear Index: {market_info.get('vix','N/A')}
30-day Market Trend: {market_info.get('trend','N/A')}
10-year Treasury Yield: {market_info.get('us10y','N/A')}
Dollar Index (DXY): {market_info.get('dxy','N/A')}
Recent news: {news}
"""
    messages = [{"role": "user", "content": prompt}]
    response = _openai_request(messages, model="gpt-4o")
    return response["choices"][0]["message"]["content"].strip()


def send_to_feishu(content: str) -> None:
    """Post the final analysis to Feishu if webhook is configured."""
    if not FEISHU_WEBHOOK:
        return
    payload = json.dumps({"msg_type": "text", "content": {"text": content}}).encode()
    req = request.Request(
        FEISHU_WEBHOOK,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception as exc:
        print(f"Failed to send Feishu notification: {exc}", file=sys.stderr)


def main(symbols):
    fmp_key = os.environ.get("FMP_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not fmp_key or not openai_key:
        print("FMP_API_KEY and OPENAI_API_KEY must be set in environment", file=sys.stderr)
        return 1

    results = []
    market_data = fetch_market_environment(fmp_key)
    for sym in symbols or DEFAULT_SYMBOLS:
        try:
            info = fetch_stock_overview(sym, fmp_key)
            news = fetch_latest_news(sym)
            rsi_value = info.get("rsi7")
            if rsi_value is not None and rsi_value < LOW_RSI:
                advice = analyze_with_gpt(sym, info, market_data, news)
                msg = f"{sym}: RSI={rsi_value:.2f} -> {advice}"
            else:
                if rsi_value is not None:
                    msg = f"{sym}: RSI={rsi_value:.2f} -> within normal range"
                else:
                    msg = f"{sym}: RSI=N/A -> within normal range"
            print(msg)
            results.append(msg)
        except Exception as exc:
            err = f"Error processing {sym}: {exc}"
            print(err, file=sys.stderr)
            results.append(err)

    summary = "\n".join(results)
    send_to_feishu(summary)


if __name__ == "__main__":
    # Symbols can be provided on the command line. If omitted, DEFAULT_SYMBOLS
    # will be used.
    symbols = sys.argv[1:]
    if not symbols:
        print("No symbols provided. Falling back to built-in list.")
    sys.exit(main(symbols))
