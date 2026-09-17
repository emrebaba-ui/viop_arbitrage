from config import CURRENCIES, METALS, RATES 

def calculate_target_rate(base_asset: str) -> float:
    asset_clean = base_asset[:6] 
    
    is_currency = any(base_asset.startswith(c) for c in CURRENCIES)
    is_metal = any(base_asset.startswith(m[:6]) for m in METALS)
    
    if not (is_currency or is_metal):
        return RATES.get('TRY', 0.0) 
        
    cur1 = asset_clean[:3]
    cur2 = asset_clean[3:6]
    
    rate1 = RATES.get(cur1, 0.0)
    rate2 = RATES.get(cur2, 0.0)
    
    if is_metal:
        if cur2 == 'TRY':
            usd_rate = RATES.get('USD', 0.0)
            try_rate = RATES.get('TRY', 0.0)
            return (1 + usd_rate) * (1 + try_rate) - 1
        else:
            return rate2
            
    if is_currency:
        return (1 + rate2) / (1 + rate1) - 1
        
    return RATES.get('TRY', 0.0)

if __name__ == "__main__":
    test_assets = ['USDTRY', 'EURUSD','XAUTRY', 'XAUTRYM', 'XPTUSD']
    
    for asset in test_assets:
        target_rate = calculate_target_rate(asset)
        print(f"Asset: {asset}, Target Rate: {target_rate:.6f}")