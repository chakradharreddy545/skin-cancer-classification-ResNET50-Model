from playwright.sync_api import sync_playwright

def verify_streamlit_app():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Go to the local Streamlit app
            page.goto("http://localhost:8501")

            # Wait for the title to appear (indicates app loaded)
            # The title is in the main-header div we added
            page.wait_for_selector("div.main-header", timeout=10000)

            # Take a screenshot
            page.screenshot(path="verification/app_screenshot.png", full_page=True)
            print("Screenshot taken successfully.")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_streamlit_app()
