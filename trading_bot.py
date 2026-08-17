import pandas as pd
import yfinance as yf


# ==============================
# Zerodha AI Bot - Backtester
# Version 2
# ==============================

SYMBOL = "^NSEI"          # NIFTY 50
PERIOD = "2y"
INTERVAL = "1d"

STARTING_CAPITAL = 100000
TARGET_DAILY_PROFIT = 2000


def calculate_strategy(data):
    data["SMA20"] = data["Close"].rolling(20).mean()
    data["SMA50"] = data["Close"].rolling(50).mean()

    data["Signal"] = 0

    # Buy when short-term trend moves above long-term trend
    data.loc[data["SMA20"] > data["SMA50"], "Signal"] = 1

    # Exit when short-term trend moves below long-term trend
    data.loc[data["SMA20"] < data["SMA50"], "Signal"] = 0

    data["Position"] = data["Signal"].diff()

    return data


def backtest(data):
    capital = STARTING_CAPITAL
    position = 0
    entry_price = 0

    trades = []
    daily_profit = []

    for i in range(1, len(data)):
        price = float(data["Close"].iloc[i])
        signal = int(data["Signal"].iloc[i])

        # BUY
        if signal == 1 and position == 0:
            position = 1
            entry_price = price

        # SELL
        elif signal == 0 and position == 1:
            profit = price - entry_price

            capital += profit
            trades.append(profit)
            daily_profit.append(profit)

            position = 0
            entry_price = 0

    # Close remaining position
    if position == 1:
        final_price = float(data["Close"].iloc[-1])
        profit = final_price - entry_price
        capital += profit
        trades.append(profit)

    return capital, trades


def main():

    print("Downloading NIFTY 50 data...")

    data = yf.download(
        SYMBOL,
        period=PERIOD,
        interval=INTERVAL,
        auto_adjust=True,
        progress=False
    )

    if data.empty:
        print("Could not download market data.")
        return

    data = data.dropna()

    data = calculate_strategy(data)

    final_capital, trades = backtest(data)

    total_profit = final_capital - STARTING_CAPITAL

    winning_trades = [x for x in trades if x > 0]

    if len(trades) > 0:
        win_rate = len(winning_trades) / len(trades) * 100
    else:
        win_rate = 0

    print("\n========== BACKTEST RESULTS ==========")
    print(f"Starting Capital : ₹{STARTING_CAPITAL:,.2f}")
    print(f"Final Capital    : ₹{final_capital:,.2f}")
    print(f"Total Profit     : ₹{total_profit:,.2f}")
    print(f"Number of Trades : {len(trades)}")
    print(f"Win Rate         : {win_rate:.2f}%")
    print("======================================")

    if total_profit > 0:
        print("Strategy was profitable during this test.")
    else:
        print("Strategy lost money during this test.")


if __name__ == "__main__":
    main()
