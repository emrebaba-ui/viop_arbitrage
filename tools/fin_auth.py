from playwright.sync_api import sync_playwright

from config import *


class FintablesAuth:
    def __init__(self, headless=False):
        self.profile_dir = FINTABLES_PROFILE_PATH
        self.headless = headless

    def get_fresh_headers(self) -> dict:
        captured_headers = {}

        def intercept_request(request):
            if request.resource_type in ["fetch", "xhr"]:
                if "barbar/server/?type=future" in request.url:
                    headers = request.all_headers()
                    
                    # only capture the relevant headers
                    if "x-ft-request-context" in headers:
                        captured_headers["x-ft-request-context"] = headers["x-ft-request-context"]
                        captured_headers["user-agent"] = headers.get("user-agent", "")

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ]
            )
            
            page = context.pages[0] if context.pages else context.new_page()
            page.on("request", intercept_request)
            
            print("\n[1] Page is loading.")
            page.goto("https://fintables.com/viop/sozlesmeler")
            
            print("[2] Info is being captured.")
            
            for _ in range(120):
                if "x-ft-request-context" in captured_headers:
                    cookies = context.cookies("https://fintables.com")
                    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                    captured_headers["cookie"] = cookie_str
                    
                    print("\n[SUCCESS] Required headers and cookies captured.")
                    break
                
                page.wait_for_timeout(1000)
                
            context.close()

        return captured_headers

if __name__ == "__main__":
    # For the first run, it should be set to headless=False to allow manual login and cookie capture.
    auth = FintablesAuth(headless=False)
    headers = auth.get_fresh_headers()
    
    print("\n--- EXTRACTED INFO ---")
    if headers:
        print(f"X-FT-Context : {(headers.get('x-ft-request-context', 'Not Found'))[:50]}...")
        print(f"Cookie       : {(headers.get('cookie', 'Not Found'))[:50]}...")
    else:
        print("No relevant information captured.")