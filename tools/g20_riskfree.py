import requests
import pandas as pd
from bs4 import BeautifulSoup

url = "https://tradingeconomics.com/country-list/interest-rate?continent=g20"

headers = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

rows = soup.find_all('tr')

data = []

for row in rows:
    cols = row.find_all('td')
    
    if len(cols) >= 4: 
        country_span = cols[0].find('span', class_='whitespace-nowrap')
        
        if country_span:
            country = country_span.text.strip()
            last_val = cols[1].text.strip()
            previous_val = cols[2].text.strip()
            reference_date = cols[3].text.strip() 
            data.append([country, last_val, previous_val, reference_date])

if data:
    df = pd.DataFrame(data, columns=["Country", "Last", "Previous", "Reference/Date"])
    print(df.to_string(index=False))
else:
    print("Date not found or no data available.")