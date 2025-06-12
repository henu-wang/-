#!/usr/bin/env python3
"""RSI Helper Tool.

Fetch RSI values from FMP API and analyze with GPT.
"""

import os
import sys
import requests
import openai

FMP_API_URL = "https://financialmodelingprep.com/api/v3/technical_indicator/daily"

LOW_RSI = 25
HIGH_RSI = 80


def fetch_rsi(symbol: str, api_key: str, period: int = 14) -> float:
    url = f"{FMP_API_URL}/{symbol}?period={period}&type=rsi&apikey={api_key}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError(f"No RSI data for {symbol}")
    return float(data[-1]["rsi"])


def analyze_with_gpt(symbol: str, rsi: float) -> str:
    prompt = (
        f"The current RSI for {symbol} is {rsi}. "
        "RSI below 25 is oversold, above 80 is overbought. "
        "Should we buy, sell, or wait?"
    )
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response["choices"][0]["message"]["content"].strip()


def main(symbols):
    fmp_key = os.environ.get("FMP_API_KEY")
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    if not fmp_key or not openai.api_key:
        print("FMP_API_KEY and OPENAI_API_KEY must be set in environment", file=sys.stderr)
        return 1

    for sym in symbols:
        try:
            rsi = fetch_rsi(sym, fmp_key)
            if rsi < LOW_RSI or rsi > HIGH_RSI:
                advice = analyze_with_gpt(sym, rsi)
                print(f"{sym}: RSI={rsi:.2f} -> {advice}")
            else:
                print(f"{sym}: RSI={rsi:.2f} -> within normal range")
        except Exception as exc:
            print(f"Error processing {sym}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: rsi_helper.py SYMBOL [SYMBOL...]", file=sys.stderr)
        sys.exit(1)
    sys.exit(main(sys.argv[1:]))
