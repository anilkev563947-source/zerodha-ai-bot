import pandas as pd
import yfinance as yf

# ==========================================
# NIFTY AI BOT - BACKTESTER
# Version 4
# Paper trading / backtesting only
# ==========================================

SYMBOL = "^NSEI"
PERIOD = "2y"
INTERVAL = "1d"

STARTING_CAPITAL = 100000

# Risk management
RISK_PER_TRADE = 0.01       # 1% of capital
ATR_STOP_MULTIPLIER = 1.5
ATR_TARGET_MULTIPLIER = 3.0

# Approximate trading cost for backtesting
COST_PER_TRADE = 0.0005     # 0.05%


def calculate_indicators(data):

    data = data.copy()

    # Moving averages
    data["SMA20"] = data["Close"].rolling(20).mean()
    data["SMA50"] = data["Close"].rolling(50).mean()

    # RSI
    delta = data["Close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)

    data["RSI"] = 100 - (100 / (1 + rs))

    # ATR
    high_low = data["High"] - data["Low"]

    high_close = (
        data["High"] - data["Close"].shift(1)
    ).abs()

    low_close = (
        data["Low"] - data["Close"].shift(1)
    ).abs()

    true_range = pd.concat(
        [high_low, high_close, low_close],
        axis=1
    ).max(axis=1)

    data["ATR"] = true_range.rolling(14).mean()

    # ==========================================
    # BUY CONDITION
    # ==========================================
    #
    # 1. Short-term trend above long-term trend
    # 2. RSI confirms positive momentum
    #
    data["BuySignal"] = (
        (data["SMA20"] > data["SMA50"]) &
        (data["RSI"] > 50) &
        (data["RSI"] < 70)
    )

    # ==========================================
    # EXIT CONDITION
    # ==========================================

    data["SellSignal"] = (
        (data["SMA20"] < data["SMA50"]) |
        (data["RSI"] < 45)
    )

    return data


def backtest(data):

    capital = STARTING_CAPITAL

    position = 0
    entry_price = 0

    stop_loss = 0
    target = 0

    trades = []
    equity_curve = []

    for i in range(len(data)):

        price = float(data["Close"].iloc[i])

        buy_signal = bool(data["BuySignal"].iloc[i])
        sell_signal = bool(data["SellSignal"].iloc[i])

        atr = data["ATR"].iloc[i]

        if pd.isna(atr):
            equity_curve.append(capital)
            continue

        atr = float(atr)

        # ==========================================
        # EXISTING POSITION
        # ==========================================

        if position > 0:

            # Stop loss
            if price <= stop_loss:

                exit_price = stop_loss

                gross_profit = (
                    exit_price - entry_price
                ) * position

                trading_cost = (
                    entry_price * position * COST_PER_TRADE
                    + exit_price * position * COST_PER_TRADE
                )

                profit = gross_profit - trading_cost

                capital += profit

                trades.append({
                    "Entry": entry_price,
                    "Exit": exit_price,
                    "Quantity": position,
                    "Profit": profit,
                    "Reason": "ATR Stop Loss"
                })

                position = 0
                entry_price = 0

            # Target
            elif price >= target:

                exit_price = target

                gross_profit = (
                    exit_price - entry_price
                ) * position

                trading_cost = (
                    entry_price * position * COST_PER_TRADE
                    + exit_price * position * COST_PER_TRADE
                )

                profit = gross_profit - trading_cost

                capital += profit

                trades.append({
                    "Entry": entry_price,
                    "Exit": exit_price,
                    "Quantity": position,
                    "Profit": profit,
                    "Reason": "ATR Target"
                })

                position = 0
                entry_price = 0

            # Strategy exit
            elif sell_signal:

                exit_price = price

                gross_profit = (
                    exit_price - entry_price
                ) * position

                trading_cost = (
                    entry_price * position * COST_PER_TRADE
                    + exit_price * position * COST_PER_TRADE
                )

                profit = gross_profit - trading_cost

                capital += profit

                trades.append({
                    "Entry": entry_price,
                    "Exit": exit_price,
                    "Quantity": position,
                    "Profit": profit,
                    "Reason": "Strategy Exit"
                })

                position = 0
                entry_price = 0

        # ==========================================
        # NEW BUY
        # ==========================================

        if position == 0 and buy_signal:

            stop_distance = atr * ATR_STOP_MULTIPLIER
            target_distance = atr * ATR_TARGET_MULTIPLIER

            if stop_distance > 0:

                risk_amount = capital * RISK_PER_TRADE

                quantity = int(
                    risk_amount / stop_distance
                )

                # Never use more capital than available
                max_quantity = int(
                    capital / price
                )

                quantity = min(
                    quantity,
                    max_quantity
                )

                if quantity > 0:

                    position = quantity
                    entry_price = price

                    stop_loss = (
                        entry_price - stop_distance
                    )

                    target = (
                        entry_price + target_distance
                    )

        # ==========================================
        # EQUITY
        # ==========================================

        current_equity = capital

        if position > 0:

            unrealized = (
                price - entry_price
            ) * position

            current_equity += unrealized

        equity_curve.append(current_equity)

    # ==========================================
    # CLOSE OPEN POSITION
    # ==========================================

    if position > 0:

        final_price = float(
            data["Close"].iloc[-1]
        )

        gross_profit = (
            final_price - entry_price
        ) * position

        trading_cost = (
            entry_price * position * COST_PER_TRADE
            + final_price * position * COST_PER_TRADE
        )

        profit = gross_profit - trading_cost

        capital += profit

        trades.append({
            "Entry": entry_price,
            "Exit": final_price,
            "Quantity": position,
            "Profit": profit,
            "Reason": "End of Backtest"
        })

    return capital, trades, equity_curve


def print_results(capital, trades, equity_curve):

    print("\n===================================")
    print("        NIFTY VERSION 4")
    print("===================================")

    print(
        f"Starting Capital : ₹{STARTING_CAPITAL:,.2f}"
    )

    print(
        f"Final Capital    : ₹{capital:,.2f}"
    )

    total_profit = capital - STARTING_CAPITAL

    print(
        f"Total P/L        : ₹{total_profit:,.2f}"
    )

    return
