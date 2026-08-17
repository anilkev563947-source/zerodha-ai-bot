import pandas as pd
import yfinance as yf

# ==============================
# NIFTY AI BOT - BACKTESTER
# Version 3
# Paper trading / backtesting only
# ==============================

SYMBOL = "^NSEI"       # NIFTY 50
PERIOD = "2y"
INTERVAL = "1d"

STARTING_CAPITAL = 100000
RISK_PER_TRADE = 0.01     # 1% of capital
STOP_LOSS_PCT = 0.01      # 1%
TARGET_PCT = 0.02         # 2%


def calculate_strategy(data):
    data = data.copy()

    # Moving averages
    data["SMA20"] = data["Close"].rolling(20).mean()
    data["SMA50"] = data["Close"].rolling(50).mean()

    # Signal
    data["Signal"] = 0

    # BUY when SMA20 crosses above SMA50
    buy_condition = (
        (data["SMA20"] > data["SMA50"]) &
        (data["SMA20"].shift(1) <= data["SMA50"].shift(1))
    )

    # SELL when SMA20 crosses below SMA50
    sell_condition = (
        (data["SMA20"] < data["SMA50"]) &
        (data["SMA20"].shift(1) >= data["SMA50"].shift(1))
    )

    data.loc[buy_condition, "Signal"] = 1
    data.loc[sell_condition, "Signal"] = -1

    return data


def backtest(data):

    capital = STARTING_CAPITAL
    position = 0
    entry_price = 0

    stop_loss = 0
    target = 0

    trades = []

    for i in range(len(data)):

        price = float(data["Close"].iloc[i])
        signal = int(data["Signal"].iloc[i])

        # =========================
        # CHECK EXISTING POSITION
        # =========================

        if position > 0:

            # Stop loss
            if price <= stop_loss:

                exit_price = stop_loss
                profit = (exit_price - entry_price) * position

                capital += profit

                trades.append({
                    "Entry": entry_price,
                    "Exit": exit_price,
                    "Quantity": position,
                    "Profit": profit,
                    "Reason": "Stop Loss"
                })

                position = 0
                entry_price = 0

            # Target
            elif price >= target:

                exit_price = target
                profit = (exit_price - entry_price) * position

                capital += profit

                trades.append({
                    "Entry": entry_price,
                    "Exit": exit_price,
                    "Quantity": position,
                    "Profit": profit,
                    "Reason": "Target"
                })

                position = 0
                entry_price = 0

            # Strategy SELL signal
            elif signal == -1:

                exit_price = price
                profit = (exit_price - entry_price) * position

                capital += profit

                trades.append({
                    "Entry": entry_price,
                    "Exit": exit_price,
                    "Quantity": position,
                    "Profit": profit,
                    "Reason": "Sell Signal"
                })

                position = 0
                entry_price = 0

        # =========================
        # NEW BUY
        # =========================

        if position == 0 and signal == 1:

            risk_amount = capital * RISK_PER_TRADE

            risk_per_unit = price * STOP_LOSS_PCT

            if risk_per_unit > 0:
                quantity = int(risk_amount / risk_per_unit)

            else:
                quantity = 0

            if quantity > 0:

                position = quantity
                entry_price = price

                stop_loss = entry_price * (1 - STOP_LOSS_PCT)
                target = entry_price * (1 + TARGET_PCT)

    # =========================
    # CLOSE OPEN POSITION
    # =========================

    if position > 0:

        final_price = float(data["Close"].iloc[-1])

        profit = (final_price - entry_price) * position

        capital += profit

        trades.append({
            "Entry": entry_price,
            "Exit": final_price,
            "Quantity": position,
            "Profit": profit,
            "Reason": "End of Backtest"
        })

    return capital, trades


def print_results(capital, trades):

    print("\n==============================")
    print("       NIFTY BACKTEST")
    print("==============================")

    print(f"Starting Capital : ₹{STARTING_CAPITAL:,.2f}")
    print(f"Final Capital    : ₹{capital:,.2f}")

    total_profit = capital - STARTING_CAPITAL

    print(f"Total P/L        : ₹{total_profit:,.2f}")

    if STARTING_CAPITAL > 0:
        return_pct = (total_profit / STARTING_CAPITAL) * 100
    else:
        return_pct = 0

    print(f"Return           : {return_pct:.2f}%")

    print(f"Total Trades     : {len(trades)}")

    if len(trades) > 0:

        winning_trades = [
            trade for trade in trades
            if trade["Profit"] > 0
        ]

        losing_trades = [
            trade for trade in trades
            if trade["Profit"] <= 0
        ]

        win_rate = (
            len(winning_trades) / len(trades)
        ) * 100

        print(f"Winning Trades   : {len(winning_trades)}")
        print(f"Losing Trades    : {len(losing_trades)}")
        print(f"Win Rate         : {win_rate:.2f}%")

        print("\nRecent Trades:")
        print("------------------------------")

        for trade in trades[-10:]:

            print(
                f"Entry ₹{trade['Entry']:.2f} | "
                f"Exit ₹{trade['Exit']:.2f} | "
                f"Qty {trade['Quantity']} | "
                f"P/L ₹{trade['Profit']:.2f} | "
                f"{trade['Reason']}"
            )


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
        print("ERROR: Could not download market data.")
        return

    # Handle Yahoo Finance MultiIndex columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna()

    print(f"Downloaded {len(data)} candles.")

    data = calculate_strategy(data)

    capital, trades = backtest(data)

    print_results(capital, trades)


if __name__ == "__main__":
    main()
