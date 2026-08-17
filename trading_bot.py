import pandas as pd
import yfinance as yf

# --- BACKTEST CONFIGURATION ---
TOTAL_CAPITAL = 30000.0
MAX_TRADE_RISK = 300.0  # Max risk per trade (1%)

def calculate_quantity(price, stop_loss_pts):
    if stop_loss_pts <= 0:
        return 0
    qty = int(MAX_TRADE_RISK / stop_loss_pts)
    max_allowed = int((TOTAL_CAPITAL * 5) / price)
    return min(qty, max_allowed)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def run_improved_backtest():
    print("==========================================")
    print("   ENHANCED BACKTEST (EMA + RSI + TSL)    ")
    print(f"   Capital: ₹{TOTAL_CAPITAL} | Risk/Trade: ₹{MAX_TRADE_RISK}")
    print("==========================================\n")

    # Fetch 30 days of 15-minute candles for INFY
    df = yf.download("INFY.NS", period="1mo", interval="15m", auto_adjust=True)
    if df.empty:
        print("❌ Error fetching historical market data.")
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Calculate Indicators
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['RSI'] = calculate_rsi(df['Close'], period=14)

    in_position = False
    buy_price = 0.0
    trailing_sl = 0.0
    qty = 0
    trades = []

    for i in range(14, len(df)):
        prev_row = df.iloc[i - 1]
        curr_row = df.iloc[i]

        prev_ema9 = float(prev_row['EMA9'].iloc[0]) if isinstance(prev_row['EMA9'], pd.Series) else float(prev_row['EMA9'])
        prev_ema21 = float(prev_row['EMA21'].iloc[0]) if isinstance(prev_row['EMA21'], pd.Series) else float(prev_row['EMA21'])
        curr_ema9 = float(curr_row['EMA9'].iloc[0]) if isinstance(curr_row['EMA9'], pd.Series) else float(curr_row['EMA9'])
        curr_ema21 = float(curr_row['EMA21'].iloc[0]) if isinstance(curr_row['EMA21'], pd.Series) else float(curr_row['EMA21'])
        
        price = float(curr_row['Close'].iloc[0]) if isinstance(curr_row['Close'], pd.Series) else float(curr_row['Close'])
        rsi = float(curr_row['RSI'].iloc[0]) if isinstance(curr_row['RSI'], pd.Series) else float(curr_row['RSI'])

        # POSITION MANAGEMENT (TRAILING STOP LOSS)
        if in_position:
            # Update trailing stop loss if price moves higher (0.8% below current price)
            new_sl = price * (1 - 0.008)
            if new_sl > trailing_sl:
                trailing_sl = new_sl

            # EXIT: Trailing Stop Loss hit OR EMA Bearish Crossover
            if price <= trailing_sl or (prev_ema9 >= prev_ema21 and curr_ema9 < curr_ema21):
                pnl = (price - buy_price) * qty
                trades.append(pnl)
                in_position = False
                reason = "TSL HIT" if price <= trailing_sl else "EMA SELL"
                print(f"🔴 [{reason}] Date: {df.index[i]} | Price: ₹{price:.2f} | PnL: ₹{pnl:.2f}")
                continue

        # ENTRY: EMA Bullish Crossover AND RSI > 50 Filter
        if prev_ema9 <= prev_ema21 and curr_ema9 > curr_ema21 and rsi > 50 and not in_position:
            stop_loss_pts = price * 0.008
            qty = calculate_quantity(price, stop_loss_pts)
            if qty > 0:
                buy_price = price
                trailing_sl = price - stop_loss_pts
                in_position = True
                print(f"🟢 [BUY] Date: {df.index[i]} | Price: ₹{price:.2f} | RSI: {rsi:.1f} | Qty: {qty}")

    # Performance Metrics
    total_pnl = sum(trades)
    winning_trades = len([t for t in trades if t > 0])
    total_trades = len(trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    print("\n==========================================")
    print("       ENHANCED BACKTEST SUMMARY          ")
    print("==========================================")
    print(f"Total Trades Executed : {total_trades}")
    print(f"Winning Trades        : {winning_trades}")
    print(f"Win Rate              : {win_rate:.2f}%")
    print(f"Net Realized PnL      : ₹{total_pnl:.2f}")
    print("==========================================")

if __name__ == "__main__":
    run_improved_backtest()
