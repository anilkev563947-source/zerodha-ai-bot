import pandas as pd
import yfinance as yf

# --- BACKTEST CONFIGURATION ---
TOTAL_CAPITAL = 30000.0
MAX_TRADE_RISK = 300.0  # Max risk per trade (1%)
RISK_REWARD_RATIO = 2.0  # 1:2 Risk-to-Reward
SYMBOLS = ["INFY.NS", "TCS.NS", "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS"]

def calculate_quantity(entry_price, stop_loss_price):
    risk_per_share = abs(entry_price - stop_loss_price)
    if risk_per_share <= 0:
        return 0
    qty = int(MAX_TRADE_RISK / risk_per_share)
    max_allowed = int((TOTAL_CAPITAL * 5) / entry_price)
    return min(qty, max_allowed)

def backtest_institutional_orb(symbol):
    print(f"\n--- Testing Institutional Volume Breakout on {symbol} ---")
    
    # Fetch 15m intraday data and 1d trend data
    df_15m = yf.download(symbol, period="1mo", interval="15m", auto_adjust=True)
    df_daily = yf.download(symbol, period="3mo", interval="1d", auto_adjust=True)
    
    if df_15m.empty or df_daily.empty:
        print(f"❌ Could not fetch data for {symbol}")
        return []

    if isinstance(df_15m.columns, pd.MultiIndex):
        df_15m.columns = df_15m.columns.get_level_values(0)
    if isinstance(df_daily.columns, pd.MultiIndex):
        df_daily.columns = df_daily.columns.get_level_values(0)

    # Calculate 50 SMA on Daily Chart
    df_daily['SMA50'] = df_daily['Close'].rolling(window=50).mean()
    daily_trend = df_daily[['SMA50']].dropna()

    # Calculate 20-period Volume Average on 15m Chart
    df_15m['Vol_SMA20'] = df_15m['Volume'].rolling(window=20).mean()
    df_15m['Date'] = df_15m.index.date

    trades = []

    for trade_date, group in df_15m.groupby('Date'):
        if len(group) < 4:
            continue

        # Check Macro Trend Filter (Stock > Daily 50 SMA)
        date_str = pd.Timestamp(trade_date)
        past_daily = daily_trend[daily_trend.index <= date_str]
        if past_daily.empty:
            continue
        
        last_sma50 = past_daily.iloc[-1]['SMA50']
        first_close = float(group.iloc[0]['Close'].iloc[0]) if isinstance(group.iloc[0]['Close'], pd.Series) else float(group.iloc[0]['Close'])
        
        # FILTER 1: Skip trading if stock is in a daily downtrend
        if first_close < last_sma50:
            continue

        # Opening Range: First 15-min candle
        orb_candle = group.iloc[0]
        orb_high = float(orb_candle['High'].iloc[0]) if isinstance(orb_candle['High'], pd.Series) else float(orb_candle['High'])
        orb_low = float(orb_candle['Low'].iloc[0]) if isinstance(orb_candle['Low'], pd.Series) else float(orb_candle['Low'])

        in_position = False
        buy_price = 0.0
        stop_loss = 0.0
        target_price = 0.0
        qty = 0

        for i in range(1, len(group)):
            curr_row = group.iloc[i]
            high = float(curr_row['High'].iloc[0]) if isinstance(curr_row['High'], pd.Series) else float(curr_row['High'])
            low = float(curr_row['Low'].iloc[0]) if isinstance(curr_row['Low'], pd.Series) else float(curr_row['Low'])
            close = float(curr_row['Close'].iloc[0]) if isinstance(curr_row['Close'], pd.Series) else float(curr_row['Close'])
            vol = float(curr_row['Volume'].iloc[0]) if isinstance(curr_row['Volume'], pd.Series) else float(curr_row['Volume'])
            vol_avg = float(curr_row['Vol_SMA20'].iloc[0]) if isinstance(curr_row['Vol_SMA20'], pd.Series) else float(curr_row['Vol_SMA20'])

            # Trade Management
            if in_position:
                if high >= target_price:
                    trades.append((target_price - buy_price) * qty)
                    in_position = False
                    break
                elif low <= stop_loss:
                    trades.append((stop_loss - buy_price) * qty)
                    in_position = False
                    break

            # FILTER 2: Breakout AND Volume Spike (1.5x average)
            elif close > orb_high and vol >= (1.5 * vol_avg) and not in_position:
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

def run_filtered_backtest():
    print("==========================================")
    print("  INSTITUTIONAL BREAKOUT + VOLUME BACKTEST")
    print("==========================================")
    
    all_trades = []
    for symbol in SYMBOLS:
        trades = backtest_institutional_orb(symbol)
        all_trades.extend(trades)

    total_trades = len(all_trades)
    winning_trades = len([t for t in all_trades if t > 0])
    total_pnl = sum(all_trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    print("\n==========================================")
    print("        FILTERED BASKET SUMMARY            ")
    print("==========================================")
    print(f"Total Stocks Tested   : {len(SYMBOLS)}")
    print(f"Total Trades Executed : {total_trades}")
    print(f"Winning Trades        : {winning_trades}")
    print(f"Overall Win Rate      : {win_rate:.2f}%")
    print(f"Total Basket PnL      : ₹{total_pnl:.2f}")
    print("==========================================")

if __name__ == "__main__":
    run_filtered_backtest()
