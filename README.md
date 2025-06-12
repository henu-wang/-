# RSI Helper

A simple tool that fetches Relative Strength Index (RSI) data from the Financial Modeling Prep API and asks GPT-4o for trading suggestions when RSI values hit configurable thresholds.

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variables `FMP_API_KEY` and `OPENAI_API_KEY`.
3. Run the tool with one or more stock symbols. If no symbols are supplied, the script falls back to a built-in list of popular tickers:
   ```bash
   python rsi_helper.py AAPL GOOGL
   ```

The script will output GPT-4o suggestions for symbols whose RSI is below 25 or above 80.

The RSI period and thresholds can be changed by editing the constants at the top
of `rsi_helper.py`.
