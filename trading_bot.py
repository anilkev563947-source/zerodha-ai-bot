import pandas as pd
import yfinance as yf

SYMBOL = "^NSEI"
PERIOD = "2y"
INTERVAL = "1d"

STARTING_CAPITAL = 100000
POSITION_SIZE = 0.50  # Use 50% of capital per trade


def get_data():
    print("Downloading NIFTY 50 data...")

    data = yf.download(
        SYMBOL,
        period=PERIOD,
        interval=INTERVAL,
        auto_adjust=True,
        progress=False
    )

    if data.empty:
        raise ValueError("No market data received.")

    # Handle yfinance MultiIndex columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required = ["Close"]

    for column in required:
        if column not in data.columns:
            raise ValueError(f"Missing column: {column}")

    data = data[["Close"]].copy()
    data["Close"] = pd.to_numeric(data["Close"], errors="coerce")
    data = data.dropna()

    return data


def calculate_strategy(data):
    data["SMA20"] = data["Close"].rolling(20).mean()
    data["SMA50"] = data["Close"].rolling(50).mean()

    data["Signal"] = 0

    data.loc[
        data["SMA20"] > data["SMA50"],
        "Signal"
    ] = 1

    return data


def backtest(data):
    capital = STARTING_CAPITAL
    position = 0
    entry_price = 0
    entry_capital = 0

    trades = []

    for i in range(1, len(data)):

        price = float(data["Close"].iloc[i])
        signal = int(data["Signal"].iloc[i])

        # BUY
        if signal == 1 and position == 0:

            position = 1
            entry_price = price
            entry_capital = capital * POSITION_SIZE

        # SELL
        elif signal == 0 and position == 1:

            price_change = (price - entry_price) / entry_price

            profit = entry_capital * price_change

            capital += profit

            trades.append(profit)

            position = 0
            entry_price = 0
            entry_capital = 0

    # Close open position at the end
    if position == 1:

        final_price = float(data["Close"].iloc[-1])

        price_change = (
            final_price - entry_price
        ) / entry_price

        profit = entry_capital * price_change

        capital += profit
        trades.append(profit)

    return capital, trades


def main():

    data = get_data()

    data = calculate_strategy(data)

    final_capital, trades = backtest(data)

    total_profit = final_capital - STARTING_CAPITAL

    winning_trades = [
        trade for trade in trades
        if trade > 0
    ]

    losing_trades = [
        trade for trade in trades
        if trade < 0
    ]

    if trades:
        win_rate = (
            len(winning_trades)
            / len(trades)
            * 100
        )
    else:
        win_rate = 0

    print()
    print("========== BACKTEST RESULTS ==========")
    print(f"Starting Capital : ₹{STARTING_CAPITAL:,.2f}")
    print(f"Final Capital    : ₹{final_capital:,.2f}")
    print(f"Total Profit     : ₹{total_profit:,.2f}")
    print(f"Trades           : {len(trades)}")
    print(f"Winning Trades   : {len(winning_trades)}")
    print(f"Losing Trades    : {len(losing_trades)}")
    print(f"Win Rate         : {win_rate:.2f}%")
    print("======================================")

    if total_profit > 0:
        print("RESULT: Strategy was profitable.")
    else:
        print("RESULT: Strategy lost money.")


if __name__ == "__main__":
    main()
