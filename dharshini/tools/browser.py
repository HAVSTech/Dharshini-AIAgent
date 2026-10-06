from pathlib import Path
from playwright.sync_api import sync_playwright

class BrowserTool:
    def __init__(self,headless=False):
        self.headless=headless
        self.playwright=None
        self.browser=None
        self.page=None

    def start(self):
        if self.page:return "Browser is already running."
        self.playwright=sync_playwright().start()
        self.browser=self.playwright.chromium.launch(headless=self.headless)
        self.page=self.browser.new_page(viewport={"width":1440,"height":900})
        return "Browser started."

    def open(self,url):
        if not url.startswith(("http://","https://")):
            raise ValueError("Only HTTP and HTTPS URLs are allowed.")
        if not self.page:self.start()
        self.page.goto(url,wait_until="domcontentloaded",timeout=30000)
        return f"Opened {self.page.title()} at {url}."

    def search(self,query):
        from urllib.parse import quote_plus
        return self.open("https://www.google.com/search?q="+quote_plus(query))

    def read_page(self):
        if not self.page:raise RuntimeError("Browser is not running.")
        return self.page.locator("body").inner_text()[:12000]

    def screenshot(self,path):
        if not self.page:raise RuntimeError("Browser is not running.")
        p=Path(path).resolve()
        p.parent.mkdir(parents=True,exist_ok=True)
        self.page.screenshot(path=str(p),full_page=True)
        return f"Browser screenshot saved to {p}."

    def close(self):
        if self.browser:self.browser.close()
        if self.playwright:self.playwright.stop()
        self.page=self.browser=self.playwright=None
        return "Browser closed."
