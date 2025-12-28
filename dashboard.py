import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import matplotlib.pyplot as plt
import io

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="NSE Intraday Stock Screener", layout="wide")

st.title("📈 NSE Intraday Stock Screener")
st.caption("Live data fetched on refresh (Streamlit Cloud)")

# ======================================================
# STOCK LIST
# ======================================================
symbols = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS"
]

# ======================================================
# BACKTEST FUNCTION (30 DAYS | NO LOOK-AHEAD)
# ======================================================
def backtest_stock(symbol, days=30):
    try:
        data = yf.Ticker(symbol).history(period=f"{days + 30}d")

        if data is None or len(data) < 25:
            return None, None, None

        trades = 0
        wins = 0
        losses = 0
        pnl = 0
        equity = [0]
        trade_log = []

        for i in range(len(data) - 1):
            open_price = data["Open"].iloc[i]
            close_price = data["Close"].iloc[i]
            next_close = data["Close"].iloc[i + 1]
            date = data.index[i].date()

            if open_price == 0:
                continue

            change_pct = ((close_price - open_price) / open_price) * 100
            ma5 = data["Close"].rolling(5).mean().iloc[i]
            ma20 = data["Close"].rolling(20).mean().iloc[i]

            if pd.isna(ma5) or pd.isna(ma20):
                continue

            # ================= ENTRY LOGIC =================
            # BUY
            if change_pct >= 0.60 and ma5 > ma20:
                trades += 1
                result = "WIN" if next_close > close_price else "LOSS"
                wins += result == "WIN"
                losses += result == "LOSS"
                pnl += 1 if result == "WIN" else -1
                equity.append(pnl)

                trade_log.append([
                    date, symbol.replace(".NS",""), "BUY",
                    round(close_price,2), round(next_close,2), result
                ])

            # SHORT
            elif change_pct <= -0.60 and ma5 < ma20:
                trades += 1
                result = "WIN" if next_close < close_price else "LOSS"
                wins += result == "WIN"
                losses += result == "LOSS"
                pnl += 1 if result == "WIN" else -1
                equity.append(pnl)

                trade_log.append([
                    date, symbol.replace(".NS",""), "SHORT",
                    round(close_price,2), round(next_close,2), result
                ])

        if trades == 0:
            return None, None, None

        summary = {
            "Trades": trades,
            "Wins": wins,
            "Losses": losses,
            "Win %": round((wins / trades) * 100, 2)
        }

        return summary, equity, trade_log

    except:
        return None, None, None

# ======================================================
# LIVE TRADE SIGNALS
# ======================================================
live_rows = []

for symbol in symbols:
    try:
        hist = yf.Ticker(symbol).history(period="1d")
        if hist is None or hist.empty:
            continue

        open_price = hist["Open"].iloc[0]
        close_price = hist["Close"].iloc[0]
        change_pct = ((close_price - open_price) / open_price) * 100

        hist30 = yf.Ticker(symbol).history(period="30d")
        ma5 = hist30["Close"].rolling(5).mean().iloc[-1]
        ma20 = hist30["Close"].rolling(20).mean().iloc[-1]

        signal = "WAIT"
        if change_pct >= 0.60 and ma5 > ma20:
            signal = "BUY"
        elif change_pct <= -0.60 and ma5 < ma20:
            signal = "SHORT"

        live_rows.append({
            "Stock": symbol.replace(".NS", ""),
            "Change %": round(change_pct, 2),
            "Signal": signal
        })

    except:
        continue

# ======================================================
# DISPLAY LIVE SIGNALS
# ======================================================
st.subheader("📊 Live Trade Signals")

if not live_rows:
    st.warning("Live data temporarily unavailable. Please refresh.")
else:
    st.dataframe(pd.DataFrame(live_rows), use_container_width=True)

st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ======================================================
# BACKTEST SECTION
# ======================================================
st.divider()
st.subheader("📊 Strategy Backtest (Last 30 Trading Days)")

bt_rows = []
all_trades = []
combined_equity = [0]
total_trades = total_wins = total_losses = 0

for symbol in symbols:
    result, equity, trade_log = backtest_stock(symbol, days=30)

    if result:
        bt_rows.append({
            "Stock": symbol.replace(".NS", ""),
            "Trades": result["Trades"],
            "Wins": result["Wins"],
            "Losses": result["Losses"],
            "Win %": result["Win %"]
        })

        total_trades += result["Trades"]
        total_wins += result["Wins"]
        total_losses += result["Losses"]

        if equity:
            combined_equity += [combined_equity[-1] + x for x in equity[1:]]

        if trade_log:
            all_trades.extend(trade_log)

if bt_rows:
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Total Trades", total_trades)
    col2.metric("✅ Wins : ❌ Losses", f"{total_wins} : {total_losses}")
    col3.metric("📈 Win Percentage", f"{round((total_wins/total_trades)*100,2)}%")

    st.dataframe(pd.DataFrame(bt_rows), use_container_width=True)

    # ================= EQUITY CURVE =================
    st.divider()
    st.subheader("📈 Equity Curve")

    fig, ax = plt.subplots()
    ax.plot(combined_equity, linewidth=2)
    ax.set_xlabel("Trades")
    ax.set_ylabel("Net Wins")
    ax.grid(True)
    st.pyplot(fig)

# ======================================================
# EXPORT REPORT
# ======================================================
st.divider()
st.subheader("📤 Export Backtest Report")

if st.button("📥 Download Full Backtest Report"):
    summary_df = pd.DataFrame([{
        "Total Trades": total_trades,
        "Wins": total_wins,
        "Losses": total_losses,
        "Win %": round((total_wins/total_trades)*100,2),
        "Period": "Last 30 Trading Days",
        "Strategy": "Trend + Momentum (MA5/MA20)"
    }])

    stock_df = pd.DataFrame(bt_rows)
    trade_df = pd.DataFrame(
        all_trades,
        columns=["Date","Stock","Signal","Entry Price","Exit Price","Result"]
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:

        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        stock_df.to_excel(writer, sheet_name="Per_Stock", index=False)
        trade_df.to_excel(writer, sheet_name="Trade_Log", index=False)

    st.download_button(
        label="⬇️ Download Excel",
        data=buffer.getvalue(),
        file_name="NSE_Backtest_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
