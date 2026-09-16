import requests

class TlrefFetcher:
    def __init__(self):
        self.url = "https://www.borsaistanbul.com/bist-tlrefk.php?op=fetchTlrefkData&dataType=tlref-history&day=10"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.borsaistanbul.com",
            "Referer": "https://www.borsaistanbul.com/endeksler/tlref"
        }

    def fetch_current_rate(self) -> float:
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "success" and len(data.get("data", [])) > 0:
                    latest_rate = float(data["data"][0]["clval"])
                    return latest_rate / 100
                    
            print(f"TLREF API ERROR: {response.status_code}")
            return 0.0
            
        except Exception as e:
            print(f"TLREF Connection Error: {e}")
            return 0.0

if __name__ == "__main__":
    fetcher = TlrefFetcher()
    guncel_tlref = fetcher.fetch_current_rate()
    
    if guncel_tlref > 0:
        print(f"Current TLREF: {guncel_tlref}")
    else:
        print("TLREF cannot be retrieved.")