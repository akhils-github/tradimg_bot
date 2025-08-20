# chart_generator.py
import yfinance as yf
import matplotlib.pyplot as plt
import datetime

def generate_chart(stock_type, symbol="RELIANCE.NS"):
    # Define time range
    if stock_type.lower() == "swing":
        start_date = datetime.datetime.now() - datetime.timedelta(days=14)
        interval = "1h"
    else:  # long term
        start_date = datetime.datetime.now() - datetime.timedelta(days=180)
        interval = "1d"

    end_date = datetime.datetime.now()

    # Fetch data
    data = yf.download(symbol, start=start_date, end=end_date, interval=interval)

    if data.empty:
        print(f"No data found for {symbol}")
        return None

    # Plot chart
    plt.figure(figsize=(10, 5))
    plt.plot(data.index, data["Close"], label="Close Price", color="blue")
    plt.title(f"{symbol} - {stock_type.title()} Trade Chart")
    plt.xlabel("Date")
    plt.ylabel("Price (INR)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    filename = f"{stock_type.lower()}_{symbol.replace('.', '_')}_chart.png"
    plt.savefig(filename)
    plt.close()
    return filename