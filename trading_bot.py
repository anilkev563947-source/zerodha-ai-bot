import time
import datetime
import pandas as pd
import yfinance as yf

TOTAL_CAPITAL = 30000.0
MAX_TRADE_RISK = 300.0
MAX_DAILY_LOSS = -600.0
DAILY_TARGET = 450.0

def calculate_quantity(current_price, stop_loss_points):
    if stop_loss_points <= 0:
        return 0
    qty = int(MAX_TRADE_RISK / stop_loss_points)
    max_allowed_qty = int((TOTAL_CAPITAL * 5) / current_price) 
    return min(qty, max_allowed_qty)

def run_paper_trading_bot():
    realized_pnl = 0.0
    in_position = False
    quantity = 0
    buy_price = 0.0
    
    print("==========================================")
    print(f"   PAPER TRADING BOT TEST (2-DAY TRIAL)   ")
    print(f"   Capital: ₹{TOTAL_CAPITAL} | Risk/Trade: ₹{MAX_TRADE_RISK}")
    print("==========================================\n")

    # Fetch data and auto-adjust MultiIndex columns
    df = yf.download("INFY.NS", period="5d", interval="15m", auto_adjust=True)
    if df.empty:
        print("❌ Error fetching market data from Yahoo Finance.")
        return

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Calculate indicators
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()

    # Extract scalar float values safely
    latest = df.iloc[-1]
    price = float(latest['Close'].iloc[0]) if isinstance(latest['Close'], pd.Series) else float(latest['Close'])
    ema9 = float(latest['EMA9'].iloc[0]) if isinstance(latest['EMA9'], pd.Series) else float(latest['EMA9'])
    ema21 = float(latest['EMA21'].iloc[0]) if isinstance(latest['EMA21'], pd.Series) else float(latest['EMA21'])

    print(f"📊 Market Check: INFY Price = ₹{price:.2f} | EMA9 = {ema9:.2f} | EMA21 = {ema21:.2f}")

    if ema9 > ema21 and not in_position:
        stop_loss_pts = price * 0.008
        quantity = calculate_quantity(price, stop_loss_pts)
        buy_price = price
        in_position = True
        print(f"🟢 [BUY SIGNAL] Paper Trade Executed:")
        print(f"    - Quantity: {quantity} shares")
        print(f"    - Execution Price: ₹{price:.2f}")

    elif ema9 < ema21 and in_position:
        pnl = (price - buy_price) * quantity
        realized_pnl += pnl
        in_position = False
        print(f"🔴 [SELL SIGNAL] Paper Trade Executed:")
        print(f"    - Exit Price: ₹{price:.2f}")
        print(f"    - Trade PnL: ₹{pnl:.2f}")

    else:
        print("ℹ️ No crossover signal detected on current candle. Holding status.")

if __name__ == "__main__":
    run_paper_trading_bot()
