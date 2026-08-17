"""
NSE AI PAPER TRADING BOT
========================

Starting capital : Rs. 30,000
Mode             : PAPER TRADING ONLY
Market           : NSE India
Strategy         : Machine Learning + Technical Indicators

IMPORTANT:
- This program DOES NOT place real orders.
- It is intended for research/backtesting/paper trading.
- A profit target is NOT guaranteed.
"""

import os
import time
import math
import warnings
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

warnings.filterwarnings("ignore")


# ============================================================
# CONFIGURATION
# ============================================================

INITIAL_CAPITAL = 30000.0

# Stocks to monitor.
# Add/remove NSE symbols as required.
STOCKS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "ITC.NS",
    "LT.NS",
    "BHARTIARTL.NS",
    "AXISBANK.NS",
]

# Historical data
HISTORY_PERIOD = "2y"
INTERVAL = "1d"

# Risk management
RISK_PER_TRADE = 0.01       # 1% of portfolio
MAX_POSITION_PERCENT = 0.30 # Maximum 30% of portfolio in one stock

STOP_LOSS_PERCENT = 0.015   # 1.5%
TAKE_PROFIT_PERCENT = 0.03  # 3%

# ML
MIN_TRAINING_ROWS = 150
PROBABILITY_THRESHOLD = 0.60

# Trading hours in IST
MARKET_OPEN = dt_time(9, 15)
MARKET_CLOSE = dt_time(15, 30)

# Files
TRADE_LOG = "paper_trades.csv"
DAILY_LOG = "daily_pnl.csv"
PORTFOLIO_FILE = "portfolio.csv"

IST = ZoneInfo("Asia/Kolkata")


# ============================================================
# PORTFOLIO
# ============================================================

class PaperPortfolio:

    def __init__(self, capital=INITIAL_CAPITAL):

        self.initial_capital = capital
        self.cash = capital
        self.positions = {}

        self.trade_history = []

        self.load_state()

    # --------------------------------------------------------
    # Load saved portfolio
    # --------------------------------------------------------

    def load_state(self):

        if os.path.exists(PORTFOLIO_FILE):

            try:

                df = pd.read_csv(PORTFOLIO_FILE)

                if len(df) > 0:

                    self.cash = float(df.iloc[0]["cash"])

                    for _, row in df.iterrows():

                        symbol = row["symbol"]

                        if symbol != "CASH":

                            self.positions[symbol] = {
                                "quantity": int(row["quantity"]),
                                "entry_price": float(row["entry_price"]),
                                "stop_loss": float(row["stop_loss"]),
                                "take_profit": float(row["take_profit"])
                            }

                    print("Previous portfolio loaded.")

            except Exception as e:

                print("Could not load portfolio:", e)

    # --------------------------------------------------------
    # Save portfolio
    # --------------------------------------------------------

    def save_state(self):

        rows = [
            {
                "symbol": "CASH",
                "quantity": 0,
                "entry_price": 0,
                "stop_loss": 0,
                "take_profit": 0,
                "cash": self.cash
            }
        ]

        for symbol, position in self.positions.items():

            rows.append({
                "symbol": symbol,
                "quantity": position["quantity"],
                "entry_price": position["entry_price"],
                "stop_loss": position["stop_loss"],
                "take_profit": position["take_profit"],
                "cash": self.cash
            })

        pd.DataFrame(rows).to_csv(
            PORTFOLIO_FILE,
            index=False
        )

    # --------------------------------------------------------
    # Portfolio value
    # --------------------------------------------------------

    def portfolio_value(self, prices):

        value = self.cash

        for symbol, position in self.positions.items():

            if symbol in prices:

                value += (
                    position["quantity"]
                    * prices[symbol]
                )

        return value

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    def buy(self, symbol, price):

        if symbol in self.positions:

            return False

        portfolio_value = self.portfolio_value({
            symbol: price
        })

        # Risk-based position sizing
        risk_amount = portfolio_value * RISK_PER_TRADE

        risk_per_share = price * STOP_LOSS_PERCENT

        if risk_per_share <= 0:

            return False

        quantity_by_risk = math.floor(
            risk_amount / risk_per_share
        )

        # Maximum capital allocation
        max_position_value = (
            portfolio_value * MAX_POSITION_PERCENT
        )

        quantity_by_capital = math.floor(
            max_position_value / price
        )

        quantity = min(
            quantity_by_risk,
            quantity_by_capital
        )

        # Cannot purchase fractional shares
        if quantity < 1:

            return False

        cost = quantity * price

        if cost > self.cash:

            quantity = math.floor(
                self.cash / price
            )

            if quantity < 1:

                return False

            cost = quantity * price

        stop_loss = price * (
            1 - STOP_LOSS_PERCENT
        )

        take_profit = price * (
            1 + TAKE_PROFIT_PERCENT
        )

        self.cash -= cost

        self.positions[symbol] = {
            "quantity": quantity,
            "entry_price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }

        self.record_trade(
            symbol=symbol,
            action="BUY",
            price=price,
            quantity=quantity,
            pnl=0
        )

        self.save_state()

        print(
            f"BUY  {symbol:15} "
            f"{quantity:5} @ Rs.{price:.2f}"
        )

        return True

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    def sell(self, symbol, price, reason="SIGNAL"):

        if symbol not in self.positions:

            return False

        position = self.positions[symbol]

        quantity = position["quantity"]

        entry_price = position["entry_price"]

        proceeds = quantity * price

        pnl = (
            price - entry_price
        ) * quantity

        self.cash += proceeds

        del self.positions[symbol]

        self.record_trade(
            symbol=symbol,
            action=f"SELL_{reason}",
            price=price,
            quantity=quantity,
            pnl=pnl
        )

        self.save_state()

        print(
            f"SELL {symbol:15} "
            f"{quantity:5} @ Rs.{price:.2f} "
            f"P&L Rs.{pnl:.2f}"
        )

        return True

    # --------------------------------------------------------
    # Trade log
    # --------------------------------------------------------

    def record_trade(
        self,
        symbol,
        action,
        price,
        quantity,
        pnl
    ):

        trade = {
            "datetime": datetime.now(IST).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "symbol": symbol,
            "action": action,
            "price": price,
            "quantity": quantity,
            "pnl": pnl
        }

        self.trade_history.append(trade)

        file_exists = os.path.exists(
            TRADE_LOG
        )

        pd.DataFrame(
            [trade]
        ).to_csv(
            TRADE_LOG,
            mode="a",
            header=not file_exists,
            index=False
        )


# ============================================================
# TECHNICAL INDICATORS
# ============================================================

def calculate_indicators(df):

    df = df.copy()

    # --------------------------------------------------------
    # Returns
    # --------------------------------------------------------

    df["return_1"] = df["Close"].pct_change(1)

    df["return_5"] = df["Close"].pct_change(5)

    df["return_10"] = df["Close"].pct_change(10)

    # --------------------------------------------------------
    # Moving averages
    # --------------------------------------------------------

    df["sma_10"] = (
        df["Close"]
        .rolling(10)
        .mean()
    )

    df["sma_20"] = (
        df["Close"]
        .rolling(20)
        .mean()
    )

    df["sma_50"] = (
        df["Close"]
        .rolling(50)
        .mean()
    )

    # --------------------------------------------------------
    # EMA
    # --------------------------------------------------------

    df["ema_12"] = (
        df["Close"]
        .ewm(span=12)
        .mean()
    )

    df["ema_26"] = (
        df["Close"]
        .ewm(span=26)
        .mean()
    )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    df["macd"] = (
        df["ema_12"]
        - df["ema_26"]
    )

    df["macd_signal"] = (
        df["macd"]
        .ewm(span=9)
        .mean()
    )

    df["macd_hist"] = (
        df["macd"]
        - df["macd_signal"]
    )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    delta = df["Close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = (
        gain
        .rolling(14)
        .mean()
    )

    avg_loss = (
        loss
        .rolling(14)
        .mean()
    )

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    df["rsi"] = (
        100
        - (
            100
            / (1 + rs)
        )
    )

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    df["volatility"] = (
        df["return_1"]
        .rolling(20)
        .std()
    )

    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    df["volume_ma"] = (
        df["Volume"]
        .rolling(20)
        .mean()
    )

    df["volume_ratio"] = (
        df["Volume"]
        / df["volume_ma"]
    )

    # --------------------------------------------------------
    # Price position
    # --------------------------------------------------------

    df["high_20"] = (
        df["High"]
        .rolling(20)
        .max()
    )

    df["low_20"] = (
        df["Low"]
        .rolling(20)
        .min()
    )

    df["price_position"] = (
        (
            df["Close"]
            - df["low_20"]
        )
        /
        (
            df["high_20"]
            - df["low_20"]
        )
    )

    # --------------------------------------------------------
    # ML target
    #
    # Predict whether next day's close is higher.
    # --------------------------------------------------------

    df["future_return"] = (
        df["Close"]
        .shift(-1)
        /
        df["Close"]
        - 1
    )

    df["target"] = (
        df["future_return"] > 0
    ).astype(int)

    return df


# ============================================================
# MACHINE LEARNING
# ============================================================

FEATURES = [
    "return_1",
    "return_5",
    "return_10",
    "sma_10",
    "sma_20",
    "sma_50",
    "ema_12",
    "ema_26",
    "macd",
    "macd_signal",
    "macd_hist",
    "rsi",
    "volatility",
    "volume_ratio",
    "price_position"
]


def train_model(df):

    data = df.dropna(
        subset=FEATURES + ["target"]
    ).copy()

    if len(data) < MIN_TRAINING_ROWS:

        return None

    # Time-series split.
    # Do NOT randomly shuffle financial data.
    split = int(
        len(data) * 0.80
    )

    train = data.iloc[:split]

    X_train = train[FEATURES]

    y_train = train["target"]

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=7,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced_subsample"
    )

    model.fit(
        X_train,
        y_train
    )

    # Basic out-of-sample check
    test = data.iloc[split:]

    if len(test) > 0:

        X_test = test[FEATURES]

        y_test = test["target"]

        predictions = model.predict(
            X_test
        )

        accuracy = accuracy_score(
            y_test,
            predictions
        )

        print(
            f"Model test accuracy: "
            f"{accuracy * 100:.2f}%"
        )

    return model


# ============================================================
# SIGNAL GENERATION
# ============================================================

def generate_signal(model, df):

    if model is None:

        return "HOLD", 0.0

    latest = df.dropna(
        subset=FEATURES
    ).iloc[-1]

    X = pd.DataFrame(
        [latest[FEATURES].values],
        columns=FEATURES
    )

    probabilities = (
        model.predict_proba(X)[0]
    )

    classes = model.classes_

    probability_up = 0

    if 1 in classes:

        index = list(classes).index(1)

        probability_up = probabilities[index]

    # --------------------------------------------------------
    # Trend filter
    # --------------------------------------------------------

    bullish_trend = (
        latest["Close"]
        > latest["sma_20"]
        > latest["sma_50"]
    )

    bearish_trend = (
        latest["Close"]
        < latest["sma_20"]
    )

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if (
        probability_up
        >= PROBABILITY_THRESHOLD
        and bullish_trend
        and 45 <= latest["rsi"] <= 70
        and latest["macd"] > latest["macd_signal"]
        and latest["volume_ratio"] >= 0.8
    ):

        return "BUY", probability_up

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    if (
        probability_up
        <= 1 - PROBABILITY_THRESHOLD
        and bearish_trend
        and latest["rsi"] < 55
    ):

        return "SELL", probability_up

    return "HOLD", probability_up


# ============================================================
# DOWNLOAD DATA
# ============================================================

def get_stock_data(symbol):

    try:

        df = yf.download(
            symbol,
            period=HISTORY_PERIOD,
            interval=INTERVAL,
            auto_adjust=True,
            progress=False
        )

        if df.empty:

            print(
                f"No data: {symbol}"
            )

            return None

        # yfinance can return MultiIndex columns
        if isinstance(
            df.columns,
            pd.MultiIndex
        ):

            df.columns = (
                df.columns
                .get_level_values(0)
            )

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        df = df[
            [
                c for c in required
                if c in df.columns
            ]
        ]

        df.dropna(
            inplace=True
        )

        return df

    except Exception as e:

        print(
            f"Data error {symbol}: {e}"
        )

        return None


# ============================================================
# DAILY BACKTEST
# ============================================================

def backtest_symbol(
    symbol,
    starting_capital=30000
):

    print("\n")
    print("=" * 70)
    print(
        f"BACKTESTING {symbol}"
    )
    print("=" * 70)

    df = get_stock_data(symbol)

    if df is None:

        return None

    df = calculate_indicators(df)

    data = df.dropna(
        subset=FEATURES + ["target"]
    ).copy()

    if len(data) < 250:

        print(
            "Not enough historical data."
        )

        return None

    capital = starting_capital

    position = None

    trades = []

    # --------------------------------------------------------
    # Walk-forward backtest
    # --------------------------------------------------------

    for i in range(
        MIN_TRAINING_ROWS,
        len(data) - 1
    ):

        train_data = data.iloc[:i]

        current = data.iloc[i]

        price = float(
            current["Close"]
        )

        # Train using only information
        # available before current bar.
        model = train_model_silent(
            train_data
        )

        if model is None:

            continue

        X = pd.DataFrame(
            [current[FEATURES].values],
            columns=FEATURES
        )

        probability = model.predict_proba(
            X
        )[0]

        classes = model.classes_

        if 1 in classes:

            p_up = probability[
                list(classes).index(1)
            ]

        else:

            p_up = 0

        bullish = (
            current["Close"]
            > current["sma_20"]
            > current["sma_50"]
        )

        bearish = (
            current["Close"]
            < current["sma_20"]
        )

        rsi = current["rsi"]

        # ----------------------------------------------------
        # Existing position
        # ----------------------------------------------------

        if position is not None:

            entry = position["entry"]

            stop = (
                entry
                * (1 - STOP_LOSS_PERCENT)
            )

            target = (
                entry
                * (1 + TAKE_PROFIT_PERCENT)
            )

            # Stop loss
            if price <= stop:

                pnl = (
                    price - entry
                ) * position["quantity"]

                capital += (
                    price
                    * position["quantity"]
                )

                trades.append(pnl)

                position = None

                continue

            # Take profit
            if price >= target:

                pnl = (
                    price - entry
                ) * position["quantity"]

                capital += (
                    price
                    * position["quantity"]
                )

                trades.append(pnl)

                position = None

                continue

            # ML sell
            if (
                p_up
                < 1 - PROBABILITY_THRESHOLD
                and bearish
            ):

                pnl = (
                    price - entry
                ) * position["quantity"]

                capital += (
                    price
                    * position["quantity"]
                )

                trades.append(pnl)

                position = None

                continue

        # ----------------------------------------------------
        # New position
        # ----------------------------------------------------

        if position is None:

            if (
                p_up
                >= PROBABILITY_THRESHOLD
                and bullish
                and 45 <= rsi <= 70
            ):

                risk_amount = (
                    capital
                    * RISK_PER_TRADE
                )

                risk_per_share = (
                    price
                    * STOP_LOSS_PERCENT
                )

                quantity = math.floor(
                    risk_amount
                    / risk_per_share
                )

                max_value = (
                    capital
                    * MAX_POSITION_PERCENT
                )

                quantity = min(
                    quantity,
                    math.floor(
                        max_value / price
                    )
                )

                if quantity >= 1:

                    cost = (
                        quantity
                        * price
                    )

                    if cost <= capital:

                        capital -= cost

                        position = {
                            "entry": price,
                            "quantity": quantity
                        }

    # --------------------------------------------------------
    # Close open position at last price
    # --------------------------------------------------------

    if position is not None:

        final_price = float(
            data.iloc[-1]["Close"]
        )

        pnl = (
            final_price
            - position["entry"]
        ) * position["quantity"]

        capital += (
            final_price
            * position["quantity"]
        )

        trades.append(pnl)

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    total_profit = (
        capital
        - starting_capital
    )

    wins = [
        t for t in trades
        if t > 0
    ]

    losses = [
        t for t in trades
        if t < 0
    ]

    win_rate = (
        len(wins) / len(trades) * 100
        if trades
        else 0
    )

    print("\nBACKTEST RESULT")
    print("-" * 50)

    print(
        f"Initial capital : Rs.{starting_capital:,.2f}"
    )

    print(
        f"Final capital   : Rs.{capital:,.2f}"
    )

    print(
        f"Profit/Loss     : Rs.{total_profit:,.2f}"
    )

    print(
        f"Trades          : {len(trades)}"
    )

    print(
        f"Win rate        : {win_rate:.2f}%"
    )

    return {
        "symbol": symbol,
        "initial": starting_capital,
        "final": capital,
        "profit": total_profit,
        "trades": len(trades),
        "win_rate": win_rate
    }


def train_model_silent(df):

    data = df.dropna(
        subset=FEATURES + ["target"]
    )

    if len(data) < MIN_TRAINING_ROWS:

        return None

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=7,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced_subsample"
    )

    model.fit(
        data[FEATURES],
        data["target"]
    )

    return model


# ============================================================
# LIVE PAPER TRADING
# ============================================================

def is_market_open():

    now = datetime.now(IST)

    current_time = now.time()

    weekday = now.weekday()

    # Monday-Friday
    if weekday >= 5:

        return False

    return (
        MARKET_OPEN
        <= current_time
        <= MARKET_CLOSE
    )


# ============================================================
# PAPER TRADING SCAN
# ============================================================

def scan_market(portfolio):

    print("\n")
    print("=" * 80)

    now = datetime.now(IST)

    print(
        "NSE PAPER TRADING SCAN"
    )

    print(
        "Time:",
        now.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("=" * 80)

    latest_prices = {}

    for symbol in STOCKS:

        print(
            f"\nAnalyzing {symbol}..."
        )

        df = get_stock_data(symbol)

        if df is None:

            continue

        df = calculate_indicators(df)

        if len(df) < MIN_TRAINING_ROWS:

            continue

        model = train_model(df)

        if model is None:

            continue

        latest = df.dropna(
            subset=FEATURES
        ).iloc[-1]

        price = float(
            latest["Close"]
        )

        latest_prices[symbol] = price

        signal, probability = (
            generate_signal(
                model,
                df
            )
        )

        print(
            f"Price       : Rs.{price:.2f}"
        )

        print(
            f"AI Up Prob. : {probability * 100:.2f}%"
        )

        print(
            f"Signal      : {signal}"
        )

        # ----------------------------------------------------
        # Existing position
        # ----------------------------------------------------

        if symbol in portfolio.positions:

            position = (
                portfolio.positions[symbol]
            )

            if price <= position["stop_loss"]:

                portfolio.sell(
                    symbol,
                    price,
                    "STOP"
                )

            elif price >= position["take_profit"]:

                portfolio.sell(
                    symbol,
                    price,
                    "TARGET"
                )

            elif signal == "SELL":

                portfolio.sell(
                    symbol,
                    price,
                    "AI_SIGNAL"
                )

        # ----------------------------------------------------
        # New position
        # ----------------------------------------------------

        else:

            if signal == "BUY":

                portfolio.buy(
                    symbol,
                    price
                )

    # --------------------------------------------------------
    # Portfolio summary
    # --------------------------------------------------------

    value = portfolio.portfolio_value(
        latest_prices
    )

    pnl = (
        value
        - portfolio.initial_capital
    )

    print("\n")
    print("=" * 80)

    print(
        f"Cash           : Rs.{portfolio.cash:,.2f}"
    )

    print(
        f"Portfolio      : Rs.{value:,.2f}"
    )

    print(
        f"Total P&L      : Rs.{pnl:,.2f}"
    )

    print(
        f"Open positions : {len(portfolio.positions)}"
    )

    print("=" * 80)

    save_daily_pnl(
        value,
        pnl
    )


# ============================================================
# DAILY P&L
# ============================================================

def save_daily_pnl(
    portfolio_value,
    pnl
):

    row = {
        "date": datetime.now(
            IST
        ).strftime("%Y-%m-%d"),
        "portfolio_value": portfolio_value,
        "pnl": pnl
    }

    exists = os.path.exists(
        DAILY_LOG
    )

    pd.DataFrame(
        [row]
    ).to_csv(
        DAILY_LOG,
        mode="a",
        header=not exists,
        index=False
    )


# ============================================================
# BACKTEST ALL STOCKS
# ============================================================

def run_backtests():

    results = []

    for symbol in STOCKS:

        result = backtest_symbol(
            symbol,
            INITIAL_CAPITAL
        )

        if result:

            results.append(result)

    if results:

        df = pd.DataFrame(
            results
        )

        print("\n")
        print("=" * 80)
        print("ALL BACKTEST RESULTS")
        print("=" * 80)

        print(
            df.to_string(
                index=False
            )
        )

        df.to_csv(
            "backtest_results.csv",
            index=False
        )


# ============================================================
# MAIN PAPER TRADING LOOP
# ============================================================

def run_paper_bot():

    portfolio = PaperPortfolio(
        INITIAL_CAPITAL
    )

    print("\n")
    print("=" * 80)
    print("AI NSE PAPER TRADING BOT")
    print("=" * 80)

    print(
        f"Starting capital: "
        f"Rs.{INITIAL_CAPITAL:,.2f}"
    )

    print(
        "Mode: PAPER TRADING ONLY"
    )

    print(
        "Real orders: DISABLED"
    )

    print("=" * 80)

    while True:

        try:

            if is_market_open():

                scan_market(
                    portfolio
                )

                # Scan once every 15 minutes
                print(
                    "\nNext scan in 15 minutes..."
                )

                time.sleep(
                    15 * 60
                )

            else:

                now = datetime.now(
                    IST
                )

                print(
                    f"\rMarket closed "
                    f"({now.strftime('%H:%M:%S')} IST). "
                    f"Waiting...",
                    end=""
                )

                # Check every minute
                time.sleep(60)

        except KeyboardInterrupt:

            print(
                "\nBot stopped by user."
            )

            portfolio.save_state()

            break

        except Exception as e:

            print(
                "\nBot error:",
                e
            )

            time.sleep(60)


# ============================================================
# COMMAND LINE MENU
# ============================================================

def main():

    print("\n")
    print("=" * 60)
    print("NSE AI PAPER TRADING SYSTEM")
    print("=" * 60)

    print("1. Run backtest")
    print("2. Start paper trading")
    print("3. Exit")

    choice = input(
        "\nSelect option: "
    ).strip()

    if choice == "1":

        run_backtests()

    elif choice == "2":

        run_paper_bot()

    elif choice == "3":

        print(
            "Goodbye."
        )

    else:

        print(
            "Invalid selection."
        )


if __name__ == "__main__":

    main()
