import pandas as pd
import yfinance as yf

# --- BACKTEST CONFIGURATION ---
TOTAL_CAPITAL = 30000.0
MAX_TRADE_RISK = 300.0  # Max risk per trade (1%)
SYMBOLS = ["INFY.NS", "TCS.NS", "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS"]

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

def backtest_single_stock(symbol):
    print(f"\n--- Testing {symbol} ---")
    df = yf.download(symbol, period="1mo", interval="15m", auto_adjust=True)
    if df.empty:
        print(f"❌ Could not fetch data for {symbol}")
        return []

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

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

        if in_position:
            new_sl = price * (1 - 0.008)
            if new_sl > trailing_sl:
                trailing_sl = new_sl

            if price <= trailing_sl or (prev_ema9 >= prev_ema21 and curr_ema9 < curr_ema21):
                pnl = (price - buy_price) * qty
                trades.append(pnl)
                in_position = False
                continue

        if prev_ema9 <= prev_ema21 and curr_ema9 > curr_ema21 and rsi > 50 and not in_position:
            stop_loss_pts = price * 0.008
            qty = calculate_quantity(price, stop_loss_pts)
            if qty > 0:
                buy_price = price
                trailing_sl = price - stop_loss_pts
                in_position = True

    pnl_sum = sum(trades)
    print(f"Trades: {len(trades)} | PnL: ₹{pnl_sum:.2f}")
    return trades

def run_multi_stock_backtest():
    print("==========================================")
    print("   MULTI-STOCK BASKET BACKTEST (30 DAYS)  ")
    print("==========================================")
    
    all_trades = []
    for symbol in SYMBOLS:
        trades = backtest_single_stock(symbol)
        all_trades.extend(trades)

    total_trades = len(all_trades)
    winning_trades = len([t for t in all_trades if t > 0])
    total_pnl = sum(all_trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    print("\n==========================================")
    print("      OVERALL BASKET BACKTEST SUMMARY     ")
    print("==========================================")
    print(f"Total Stocks Tested   : {len(SYMBOLS)}")
    print(f"Total Trades Executed : {total_trades}")
    print(f"Winning Trades        : {winning_trades}")
    print(f"Overall Win Rate      : {win_rate:.2f}%")
    print(f"Total Basket PnL      : ₹{total_pnl:.2f}")
    print("==========================================")

if __name__ == "__main__":
    run_multi_stock_backtest()
