#!/usr/bin/env python3
"""RSI Helper Tool.

Fetch RSI values from FMP API and analyze with GPT.
"""

import os
import sys
import requests
import openai

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

FMP_API_URL = "https://financialmodelingprep.com/api/v3/technical_indicator/daily"

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


def fetch_rsi(symbol: str, api_key: str, period: int = RSI_PERIOD) -> float:
    url = f"{FMP_API_URL}/{symbol}?period={period}&type=rsi&apikey={api_key}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError(f"No RSI data for {symbol}")
    return float(data[-1]["rsi"])


def fetch_latest_news(symbol: str) -> str:
    """Use OpenAI's search model to gather recent news about the symbol."""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # using a cheaper model for search-style queries
        messages=[
            {
                "role": "system",
                "content": "You search the web and summarize the most recent news about a stock."
            },
            {"role": "user", "content": f"Latest news about {symbol}"},
        ],
    )
    return response["choices"][0]["message"]["content"].strip()


def analyze_with_gpt(symbol: str, rsi: float, news: str) -> str:
    prompt = (
        f"The current RSI for {symbol} using a {RSI_PERIOD}-day period is {rsi}. "
        f"RSI below {LOW_RSI} is oversold and above {HIGH_RSI} is overbought. "
        f"Recent news: {news}\n"
        "Given this information, should we buy, sell, or wait?"
    )
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response["choices"][0]["message"]["content"].strip()


def send_to_feishu(content: str) -> None:
    """Post the final analysis to Feishu if webhook is configured."""
    if not FEISHU_WEBHOOK:
        return
    payload = {"msg_type": "text", "content": {"text": content}}
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        print(f"Failed to send Feishu notification: {exc}", file=sys.stderr)


def main(symbols):
    fmp_key = os.environ.get("FMP_API_KEY")
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    if not fmp_key or not openai.api_key:
        print("FMP_API_KEY and OPENAI_API_KEY must be set in environment", file=sys.stderr)
        return 1

    results = []
    for sym in symbols or DEFAULT_SYMBOLS:
        try:
            rsi = fetch_rsi(sym, fmp_key)
            news = fetch_latest_news(sym)
            if rsi < LOW_RSI or rsi > HIGH_RSI:
                advice = analyze_with_gpt(sym, rsi, news)
                msg = f"{sym}: RSI={rsi:.2f} -> {advice}"
            else:
                msg = f"{sym}: RSI={rsi:.2f} -> within normal range"
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
