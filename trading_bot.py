import pandas as pd
import yfinance as yf

# --- BACKTEST CONFIGURATION ---
TOTAL_CAPITAL = 100000.0
MAX_TRADE_RISK = 1000.0
SYMBOLS = ["INFY.NS", "TCS.NS", "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS"]

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_mean_reversion(symbol):
    print(f"\n--- Backtesting RSI Mean Reversion on {symbol} ---")
    # Fetch 1 year of daily historical data
    df = yf.download(symbol, period="1y", interval="1d", auto_adjust=True)
    if df.empty:
        print(f"❌ Could not fetch data for {symbol}")
        return []

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df['RSI'] = calculate_rsi(df['Close'], period=14)

    in_position = False
    buy_price = 0.0
    qty = 0
    trades = []

    for i in range(15, len(df)):
        curr_row = df.iloc[i]
        price = float(curr_row['Close'].iloc[0]) if isinstance(curr_row['Close'], pd.Series) else float(curr_row['Close'])
        rsi = float(curr_row['RSI'].iloc[0]) if isinstance(curr_row['RSI'], pd.Series) else float(curr_row['RSI'])

        if in_position:
            # EXIT Signal: RSI crosses above 60 OR Take Profit 5% / Stop Loss 3%
            profit_pct = (price - buy_price) / buy_price
            if rsi >= 60 or profit_pct >= 0.05 or profit_pct <= -0.03:
                pnl = (price - buy_price) * qty
                trades.append(pnl)
                in_position = False

        # ENTRY Signal: RSI drops below 30 (Oversold Bounce)
        elif rsi <= 30 and not in_position:
            buy_price = price
            stop_loss_pts = buy_price * 0.03  # 3% Stop Loss
            qty = int(MAX_TRADE_RISK / stop_loss_pts)
            if qty > 0:
                in_position = True

    pnl_sum = sum(trades)
    print(f"Trades: {len(trades)} | Net PnL: ₹{pnl_sum:.2f}")
    return trades

def run_mean_reversion_backtest():
    print("==========================================")
    print("   RSI MEAN REVERSION BACKTEST (1 YEAR)   ")
    print("==========================================")
    
    all_trades = []
    for symbol in SYMBOLS:
        trades = backtest_mean_reversion(symbol)
        all_trades.extend(trades)

    total_trades = len(all_trades)
    winning_trades = len([t for t in all_trades if t > 0])
    total_pnl = sum(all_trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    print("\n==========================================")
    print("      MEAN REVERSION BASKET SUMMARY        ")
    print("==========================================")
    print(f"Total Stocks Tested   : {len(SYMBOLS)}")
    print(f"Total Trades Executed : {total_trades}")
    print(f"Winning Trades        : {winning_trades}")
    print(f"Overall Win Rate      : {win_rate:.2f}%")
    print(f"Total Basket PnL      : ₹{total_pnl:.2f}")
    print("==========================================")

if __name__ == "__main__":
    run_mean_reversion_backtest()
