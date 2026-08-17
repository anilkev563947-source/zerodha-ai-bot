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

def backtest_mean_reversion_rr(symbol):
    print(f"\n--- Backtesting Strict 1:2 RR Mean Reversion on {symbol} ---")
    df = yf.download(symbol, period="1y", interval="1d", auto_adjust=True)
    if df.empty:
        print(f"❌ Could not fetch data for {symbol}")
        return []

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df['RSI'] = calculate_rsi(df['Close'], period=14)
    df['SMA200'] = df['Close'].rolling(window=200).mean()  # Long-term trend filter

    in_position = False
    buy_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    qty = 0
    trades = []

    for i in range(15, len(df)):
        curr_row = df.iloc[i]
        price = float(curr_row['Close'].iloc[0]) if isinstance(curr_row['Close'], pd.Series) else float(curr_row['Close'])
        high = float(curr_row['High'].iloc[0]) if isinstance(curr_row['High'], pd.Series) else float(curr_row['High'])
        low = float(curr_row['Low'].iloc[0]) if isinstance(curr_row['Low'], pd.Series) else float(curr_row['Low'])
        rsi = float(curr_row['RSI'].iloc[0]) if isinstance(curr_row['RSI'], pd.Series) else float(curr_row['RSI'])
        sma200 = float(curr_row['SMA200'].iloc[0]) if isinstance(curr_row['SMA200'], pd.Series) else float(curr_row['SMA200'])

        if in_position:
            # Check Take Profit or Stop Loss
            if high >= take_profit:
                pnl = (take_profit - buy_price) * qty
                trades.append(pnl)
                in_position = False
            elif low <= stop_loss:
                pnl = (stop_loss - buy_price) * qty
                trades.append(pnl)
                in_position = False

        # ENTRY: RSI <= 30 AND Stock is above 200 SMA (Long-term uptrend only)
        elif rsi <= 30 and price > sma200 and not in_position:
            buy_price = price
            stop_loss = buy_price * 0.97      # 3% Stop Loss
            take_profit = buy_price * 1.06    # 6% Take Profit (1:2 Risk-Reward)
            
            risk_per_share = buy_price - stop_loss
            if risk_per_share > 0:
                qty = int(MAX_TRADE_RISK / risk_per_share)
                if qty > 0:
                    in_position = True

    pnl_sum = sum(trades)
    print(f"Trades: {len(trades)} | Net PnL: ₹{pnl_sum:.2f}")
    return trades

def run_optimized_backtest():
    print("==========================================")
    print(" 1-YEAR RSI MEAN REVERSION (1:2 R:R + SMA200)")
    print("==========================================")
    
    all_trades = []
    for symbol in SYMBOLS:
        trades = backtest_mean_reversion_rr(symbol)
        all_trades.extend(trades)

    total_trades = len(all_trades)
    winning_trades = len([t for t in all_trades if t > 0])
    total_pnl = sum(all_trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    print("\n==========================================")
    print("         OPTIMIZED SUMMARY                ")
    print("==========================================")
    print(f"Total Stocks Tested   : {len(SYMBOLS)}")
    print(f"Total Trades Executed : {total_trades}")
    print(f"Winning Trades        : {winning_trades}")
    print(f"Overall Win Rate      : {win_rate:.2f}%")
    print(f"Total Basket PnL      : ₹{total_pnl:.2f}")
    print("==========================================")

if __name__ == "__main__":
    run_optimized_backtest()
