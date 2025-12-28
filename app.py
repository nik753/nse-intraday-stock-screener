import time
from datetime import datetime
import pandas as pd
import yfinance as yf
import os

# ===================== SETTINGS =====================
REFRESH_SECONDS = 60   # change to 300 for 5 minutes
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"

symbols = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
    "LT.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS","ITC.NS"
]

# ===================================================

def market_is_open():
    now = datetime.now().strftime("%H:%M")
    return MARKET_OPEN <= now <= MARKET_CLOSE

while True:
    print("\n" + "=" * 70)
    print("🔄 NSE AUTO SCREENER")
    print("🕒 Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    if not market_is_open():
        print("❌ Market Closed — waiting...")
        time.sleep(REFRESH_SECONDS)
        continue

    data = []

    for symbol in symbols:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1d")

        if df.empty:
            continue

        open_price = df["Open"].iloc[0]
        close_price = df["Close"].iloc[0]
        change_pct = ((close_price - open_price) / open_price) * 100

        # ===== STRATEGY (Momentum + ORB logic simplified) =====
        if change_pct >= 0.25:
            signal = "BUY"
            target = round(close_price * 1.006, 2)
            stoploss = round(close_price * 0.997, 2)
        elif change_pct <= -0.75:
            signal = "SHORT"
            target = round(close_price * 0.994, 2)
            stoploss = round(close_price * 1.003, 2)
        else:
            signal = "WAIT"
            target = "-"
            stoploss = "-"

        data.append({
            "Stock": symbol.replace(".NS",""),
            "Open": round(open_price,2),
            "Close": round(close_price,2),
            "Change %": round(change_pct,2),
            "Signal": signal,
            "Target": target,
            "Stop Loss": stoploss
        })

    result = pd.DataFrame(data)
    print("\n📊 LIVE TRADE SIGNALS")
    print(result[["Stock","Change %","Signal","Target","Stop Loss"]])

    # ===== EXPORT TO EXCEL =====
    os.makedirs("output", exist_ok=True)
    result.to_excel("output/signals.xlsx", index=False)
    print("\n📁 Exported to output/signals.xlsx")

    print("\n⏳ Next refresh in", REFRESH_SECONDS, "seconds...")
    time.sleep(REFRESH_SECONDS)
