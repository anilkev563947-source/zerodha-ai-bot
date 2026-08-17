import time
import datetime
import pandas as pd
import yfinance as yf
from kiteconnect import KiteConnect

# --- ACCOUNT CONFIGURATION ---
TOTAL_CAPITAL = 30000.0
MAX_TRADE_RISK = 300.0       # Max loss per trade (1% of capital)
MAX_DAILY_LOSS = -600.0      # Daily circuit breaker (2% of capital)
DAILY_TARGET = 450.0         # Realistic daily profit target (1.5%)

# API Credentials
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
REQUEST_TOKEN = "YOUR_REQUEST_TOKEN"

kite = KiteConnect(api_key=API_KEY)
session = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
kite.set_access_token(session["access_token"])

def calculate_quantity(current_price, stop_loss_points):
    """Calculates share quantity so total trade risk stays <= ₹300."""
    if stop_loss_points <= 0:
        return 0
    qty = int(MAX_TRADE_RISK / stop_loss_points)
    # Ensure position size does not exceed maximum leverage capacity
    max_allowed_qty = int((TOTAL_CAPITAL * 5) / current_price) 
    return min(qty, max_allowed_qty)

def run_bot():
    realized_pnl = 0.0
    in_position = False
    quantity = 0
    
    print(f"Bot initialized for ₹{TOTAL_CAPITAL} Capital. Monitoring markets...")

    while True:
        now = datetime.datetime.now().time()

        # Execute only during standard Indian stock market hours (09:15 AM - 03:15 PM IST)
        if not (datetime.time(9, 15) <= now <= datetime.time(15, 15)):
            time.sleep(120)
            continue

        # Enforce Daily Risk Circuit Breaker
        if realized_pnl <= MAX_DAILY_LOSS or realized_pnl >= DAILY_TARGET:
            print(f"Daily Risk Limit reached. Net PnL: ₹{realized_pnl}. Halting bot.")
            break

        try:
            # Fetch 15-minute candle data for strategy indicators
            df = yf.download("INFY.NS", period="5d", interval="15m")
            df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()

            latest = df.iloc[-1]
            price = float(latest['Close'])
            ema9 = float(latest['EMA9'])
            ema21 = float(latest['EMA21'])

            # ENTRY SIGNAL: Fast EMA crosses above Slow EMA
            if ema9 > ema21 and not in_position:
                stop_loss_pts = price * 0.008 # 0.8% stop loss distance
                quantity = calculate_quantity(price, stop_loss_pts)
                
                if quantity > 0:
                    order = kite.place_order(
                        variety=kite.VARIETY_REGULAR,
                        exchange=kite.EXCHANGE_NSE,
                        tradingsymbol="INFY",
                        transaction_type=kite.TRANSACTION_TYPE_BUY,
                        quantity=quantity,
                        product=kite.PRODUCT_MIS,
                        order_type=kite.ORDER_TYPE_MARKET
                    )
                    in_position = True
                    print(f"BUY Order Placed: Qty {quantity} at ₹{price}")

            # EXIT SIGNAL: Fast EMA crosses below Slow EMA
            elif ema9 < ema21 and in_position:
                order = kite.place_order(
                    variety=kite.VARIETY_REGULAR,
                    exchange=kite.EXCHANGE_NSE,
                    tradingsymbol="INFY",
                    transaction_type=kite.TRANSACTION_TYPE_SELL,
                    quantity=quantity,
                    product=kite.PRODUCT_MIS,
                    order_type=kite.ORDER_TYPE_MARKET
                )
                in_position = False
                print(f"SELL Order Placed: Qty {quantity} at ₹{price}")

        except Exception as err:
            print(f"Execution Exception: {err}")

        time.sleep(60) # Poll strategy every minute

if __name__ == "__main__":
    run_bot()
