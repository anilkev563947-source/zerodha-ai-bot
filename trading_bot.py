import pandas as pd
import yfinance as yf

# --- BACKTEST CONFIGURATION ---
TOTAL_CAPITAL = 30000.0
MAX_TRADE_RISK = 300.0  # Max risk per trade (1%)
RISK_REWARD_RATIO = 2.0  # 1:2 Risk-to-Reward Ratio
SYMBOLS = ["INFY.NS", "TCS.NS", "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS"]

def calculate_quantity(entry_price, stop_loss_price):
    risk_per_share = abs(entry_price - stop_loss_price)
    if risk_per_share <= 0:
        return 0
    qty = int(MAX_TRADE_RISK / risk_per_share)
    max_allowed = int((TOTAL_CAPITAL * 5) / entry_price)
    return min(qty, max_allowed)

def backtest_orb_strategy(symbol):
    print(f"\n--- Testing Price Action Breakout (1:2 RR) on {symbol} ---")
    df = yf.download(symbol, period="1mo", interval="15m", auto_adjust=True)
    if df.empty:
        print(f"❌ Could not fetch data for {symbol}")
        return []

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Add Date column to identify daily session boundaries
    df['Date'] = df.index.date
    trades = []

    # Iterate through each trading day individually
    for trade_date, group in df.groupby('Date'):
        if len(group) < 4:  # Skip incomplete days
            continue

        # Opening Range: First 15-minute candle of the day
        orb_candle = group.iloc[0]
        orb_high = float(orb_candle['High'].iloc[0]) if isinstance(orb_candle['High'], pd.Series) else float(orb_candle['High'])
        orb_low = float(orb_candle['Low'].iloc[0]) if isinstance(orb_candle['Low'], pd.Series) else float(orb_candle['Low'])

        in_position = False
        buy_price = 0.0
        stop_loss = 0.0
        target_price = 0.0
        qty = 0

        # Evaluate the rest of the day's candles
        for i in range(1, len(group)):
            curr_row = group.iloc[i]
            high = float(curr_row['High'].iloc[0]) if isinstance(curr_row['High'], pd.Series) else float(curr_row['High'])
            low = float(curr_row['Low'].iloc[0]) if isinstance(curr_row['Low'], pd.Series) else float(curr_row['Low'])
            close = float(curr_row['Close'].iloc[0]) if isinstance(curr_row['Close'], pd.Series) else float(curr_row['Close'])

            # MANAGEMENT: Check Target or Stop-Loss if in trade
            if in_position:
                if high >= target_price:  # 🎯 TAKE PROFIT HIT
                    pnl = (target_price - buy_price) * qty
                    trades.append(pnl)
                    in_position = False
                    break
                elif low <= stop_loss:  # 🛑 STOP LOSS HIT
                    pnl = (stop_loss - buy_price) * qty
                    trades.append(pnl)
                    in_position = False
                    break

            # ENTRY: Breakout above Opening Range High
            elif close > orb_high and not in_position:
                buy_price = close
                stop_loss = orb_low
                risk_per_share = buy_price - stop_loss

                if risk_per_share > 0:
                    qty = calculate_quantity(buy_price, stop_loss)
                    if qty > 0:
                        target_price = buy_price + (risk_per_share * RISK_REWARD_RATIO)
                        in_position = True

    pnl_sum = sum(trades)
    print(f"Trades: {len(trades)} | Net PnL: ₹{pnl_sum:.2f}")
    return trades

def run_price_action_backtest():
    print("==========================================")
    print("  OPENING RANGE BREAKOUT (1:2 R:R) BACKTEST")
    print("==========================================")
    
    all_trades = []
    for symbol in SYMBOLS:
        trades = backtest_orb_strategy(symbol)
        all_trades.extend(trades)

    total_trades = len(all_trades)
    winning_trades = len([t for t in all_trades if t > 0])
    total_pnl = sum(all_trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    print("\n==========================================")
    print("     PRICE ACTION BASKET SUMMARY           ")
    print("==========================================")
    print(f"Total Stocks Tested   : {len(SYMBOLS)}")
    print(f"Total Trades Executed : {total_trades}")
    print(f"Winning Trades        : {winning_trades}")
    print(f"Overall Win Rate      : {win_rate:.2f}%")
    print(f"Total Basket PnL      : ₹{total_pnl:.2f}")
    print("==========================================")

if __name__ == "__main__":
    run_price_action_backtest()
