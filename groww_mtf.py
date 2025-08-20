# groww_mtf.py
import requests
import csv

def fetch_groww_mtf_data():
    base_url = "https://groww.in/v1/api/mtf/approved_mtf_stocks"
    page = 0
    limit = 50
    all_data = []

    while True:
        params = {
            "limit": limit,
            "order": "ASC",
            "page": page,
            "query": "",
            "sort": "COMPANY_NAME"
        }
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            break

        json_data = response.json()
        stocks = json_data.get("data", [])

        if not stocks:
            break

        for stock in stocks:
            market_cap = stock.get("marketCap", 0.0)
            leverage = stock.get("leverage", 0.0)
            if market_cap == 0:
                continue

            all_data.append({
                "companyName": stock.get("companyName"),
                "symbolIsin": stock.get("symbolIsin"),
                "leverage": leverage,
                "searchId": stock.get("searchId"),
            })

        page += 1

    return all_data

def save_to_csv(data, filename):
    if not data:
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def generate_mtf_csv_files():
    mtf_data = fetch_groww_mtf_data()
    leverage_2_to_3 = [stock for stock in mtf_data if 2 <= stock["leverage"] <= 3]
    leverage_3_to_4 = [stock for stock in mtf_data if 3 <= stock["leverage"] <= 4]

    file1 = "groww_mtf_leverage_2_to_3.csv"
    file2 = "groww_mtf_leverage_3_to_4.csv"

    save_to_csv(leverage_2_to_3, file1)
    save_to_csv(leverage_3_to_4, file2)

    return [file1, file2]