import pandas as pd
import yfinance as yf

# --- BACKTEST CONFIGURATION ---
TOTAL_CAPITAL = 100000.0  # ₹1 Lakh simulated index capital
MAX_TRADE_RISK = 1000.0   # ₹1,000 risk per trade (1%)
RISK_REWARD_RATIO = 1.5

def calculate_supertrend(df, period=7, multiplier=3):
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # Calculate ATR
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    hl2 = (high + low) / 2
    basic_ub = hl2 + (multiplier * atr)
    basic_lb = hl2 - (multiplier * atr)

    final_ub = pd.Series(0.0, index=df.index)
    final_lb = pd.Series(0.0, index=df.index)
    supertrend = pd.Series(0.0, index=df.index)

    for i in range(1, len(df)):
        # Upper Band
        if basic_ub.iloc[i] < final_ub.iloc[i-1] or close.iloc[i-1] > final_ub.iloc[i-1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i-1]

        # Lower Band
        if basic_lb.iloc[i] > final_lb.iloc[i-1] or close.iloc[i-1] < final_lb.iloc[i-1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i-1]

        # Supertrend direction
        if supertrend.iloc[i-1] == final_ub.iloc[i-1] and close.iloc[i] <= final_ub.iloc[i]:
            supertrend.iloc[i] = final_ub.iloc[i]
        elif supertrend.iloc[i-1] == final_ub.iloc[i-1] and close.iloc[i] > final_ub.iloc[i]:
            supertrend.iloc[i] = final_lb.iloc[i]
        elif supertrend.iloc[i-1] == final_lb.iloc[i-1] and close.iloc[i] >= final_lb.iloc[i]:
            supertrend.iloc[i] = final_lb.iloc[i]
        elif supertrend.iloc[i-1] == final_lb.iloc[i-1] and close.iloc[i] < final_lb.iloc[i]:
            supertrend.iloc[i] = final_ub.iloc[i]

    return supertrend

def run_nifty_vwap_backtest():
    print("==========================================")
    print("  NIFTY 50 INDEX VWAP + SUPERTREND SYSTEM ")
    print("==========================================\n")

    df = yf.download("^NSEI", period="1mo", interval="15m", auto_adjust=True)
    if df.empty:
        print("❌ Could not fetch Nifty index data.")
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Calculate VWAP
    df['Date'] = df.index.date
    df['Cum_Vol'] = df.groupby('Date')['Volume'].cumsum()
    df['Cum_VP'] = df.groupby('Date').apply(lambda x: (x['Close'] * x['Volume']).cumsum()).reset_index(level=0, drop=True)
    df['VWAP'] = df['Cum_VP'] / df['Cum_Vol']

    # Calculate Supertrend
    df['Supertrend'] = calculate_supertrend(df, period=7, multiplier=3)

    in_position = False
    buy_price = 0.0
    stop_loss = 0.0
    target_price = 0.0
    qty = 0
    trades = []

    for i in range(15, len(df)):
        curr_row = df.iloc[i]
        price = float(curr_row['Close'].iloc[0]) if isinstance(curr_row['Close'], pd.Series) else float(curr_row['Close'])
        high = float(curr_row['High'].iloc[0]) if isinstance(curr_row['High'], pd.Series) else float(curr_row['High'])
        low = float(curr_row['Low'].iloc[0]) if isinstance(curr_row['Low'], pd.Series) else float(curr_row['Low'])
        vwap = float(curr_row['VWAP'].iloc[0]) if isinstance(curr_row['VWAP'], pd.Series) else float(curr_row['VWAP'])
        st = float(curr_row['Supertrend'].iloc[0]) if isinstance(curr_row['Supertrend'], pd.Series) else float(curr_row['Supertrend'])

        if in_position:
            if high >= target_price:
                pnl = (target_price - buy_price) * qty
                trades.append(pnl)
                in_position = False
            elif low <= stop_loss:
                pnl = (stop_loss - buy_price) * qty
                trades.append(pnl)
                in_position = False

        # BUY: Price above VWAP and Supertrend is Bullish (Price > Supertrend)
        elif price > vwap and price > st and not in_position:
            buy_price = price
            stop_loss = st  # Use Supertrend line as dynamic stop-loss
            risk = buy_price - stop_loss
            if risk > 0:
                qty = int(MAX_TRADE_RISK / risk)
                if qty > 0:
                    target_price = buy_price + (risk * RISK_REWARD_RATIO)
                    in_position = True

    total_trades = len(trades)
    winning_trades = len([t for t in trades if t > 0])
    total_pnl = sum(trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    print("==========================================")
    print("      NIFTY 50 STRATEGY SUMMARY           ")
    print("==========================================")
    print(f"Total Trades Executed : {total_trades}")
    print(f"Winning Trades        : {winning_trades}")
    print(f"Overall Win Rate      : {win_rate:.2f}%")
    print(f"Total Net PnL         : ₹{total_pnl:.2f}")
    print("==========================================")

if __name__ == "__main__":
    run_nifty_vwap_backtest()
