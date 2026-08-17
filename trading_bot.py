# Zerodha AI Trading Bot
# Version 1 - Paper Trading / Strategy Test

def trading_signal(price, moving_average):
    if price > moving_average:
        return "BUY"
    elif price < moving_average:
        return "SELL"
    else:
        return "HOLD"


# Simple test
price = 100
moving_average = 98

signal = trading_signal(price, moving_average)

print("Current Price:", price)
print("Moving Average:", moving_average)
print("Trading Signal:", signal)
