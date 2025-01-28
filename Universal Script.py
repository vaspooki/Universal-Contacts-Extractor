"""
Universal Contact Information Extractor
Extracts contact information from websites including phone, email, fax, and address details.
"""

import os
import sys
import json
import validators
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Comment
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from collections import defaultdict
from validate_email import validate_email

# Set default encoding
os.environ["LANG"] = "en_US.UTF-8"

class ContactExtractor:
    def __init__(self):
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode (optional)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Initialize Chrome WebDriver with ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        self.browser = webdriver.Chrome(service=service, options=chrome_options)
        
        self.website_dict = defaultdict(list)
        self.contact_lang: Set[str] = set()
        self.phone_lang: Set[str] = set()
        self.email_lang: Set[str] = set()
        self.fax_lang: Set[str] = set()
        self.address_lang: Set[str] = set()
        self.hosts: Set[str] = set()
        
        # Load language data
        self._load_language_data()
        self._load_hosts()

    def _load_json_file(self, json_str: str) -> List[Dict]:
        """Load and parse JSON string data."""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            print(f"Error parsing JSON data")
            return []

    def _load_language_data(self):
        """Load all language-specific terms from JSON data."""
        # Note: Keep your existing JSON string definitions here
        contact_data = self._load_json_file(contact_json)
        phone_data = self._load_json_file(tel_json)
        email_data = self._load_json_file(email_json)
        fax_data = self._load_json_file(fax_json)
        address_data = self._load_json_file(address_json)

        for item in contact_data:
            self.contact_lang.add(item["string"].lower())
        for item in phone_data:
            self.phone_lang.add(item["string"].lower())
        for item in email_data:
            self.email_lang.add(item["string"].lower())
        for item in fax_data:
            self.fax_lang.add(item["string"].lower())
        for item in address_data:
            self.address_lang.add(item["string"].lower())

    def _load_hosts(self):
        """Load email hosts from providers.csv file."""
        try:
            with open("providers.csv") as csvfile:
                self.hosts = {line.strip() for line in csvfile}
        except FileNotFoundError:
            print("providers.csv file not found")

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        return validators.url(url) if url else False

    def _normalize_url(self, url: str, domain: str) -> str:
        """Normalize URL by adding domain if necessary."""
        if not url:
            return ""
        if url.startswith("/"):
            return urljoin(domain, url)
        if url.startswith("#"):
            return urljoin(domain, "/" + url)
        if not url.startswith(("http://", "https://")):
            return "http://" + url
        return url

    def _extract_visible_text(self, html_content: str) -> str:
        """Extract visible text content from HTML."""
        def tag_visible(element):
            if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
                return False
            if isinstance(element, Comment):
                return False
            return True

        soup = BeautifulSoup(html_content, 'html.parser')
        texts = soup.findAll(text=True)
        visible_texts = filter(tag_visible, texts)  
        return " ".join(t.strip() for t in visible_texts)

    def extract_contact_info(self, text: str):
        """Extract various types of contact information from text."""
        # Phone numbers
        for phone in self.phone_lang:
            if phone in text.lower():
                print(f"\nPhone: {text[text.lower().index(phone):text.lower().index(phone)+50]}")

        # Email addresses
        for email in self.email_lang:
            if email in text.lower():
                print(f"\nEmail: {text[max(0, text.lower().index(email)-15):text.lower().index(email)+len(email)+50]}")

        # Fax numbers
        for fax in self.fax_lang:
            if fax in text.lower():
                print(f"\nFax: {text[text.lower().index(fax):text.lower().index(fax)+50]}")

        # Address
        for addr in self.address_lang:
            if addr in text.lower():
                print(f"\nAddress: {text[text.lower().index(addr):text.lower().index(addr)+100]}")

    def process_website(self, url: str):
        """Process a single website to extract contact information."""
        if not self._is_valid_url(url):
            print(f"Invalid URL: {url}")
            return

        try:
            parsed_url = urlparse(url)
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            self.browser.get(url)
            soup = BeautifulSoup(self.browser.page_source, "html.parser")
            
            # Extract and process all links
            for link in soup.find_all("a", href=True):
                href = link.get("href")
                normalized_url = self._normalize_url(href, domain)
                
                if self._is_valid_url(normalized_url):
                    if any(term in href.lower() for term in self.contact_lang):
                        try:
                            self.browser.get(normalized_url)
                            text = self._extract_visible_text(self.browser.page_source)
                            self.extract_contact_info(text)
                        except Exception as e:
                            print(f"Error processing link {normalized_url}: {str(e)}")

        except Exception as e:
            print(f"Error processing website {url}: {str(e)}")

    def process_websites_file(self, filename: str):
        """Process multiple websites from a file."""
        try:
            with open(filename) as csvfile:
                for row in csvfile:
                    website = row.strip()
                    print(f"\nProcessing website: {website}")
                    self.process_website(website)
        except FileNotFoundError:
            print(f"File {filename} not found")

    def cleanup(self):
        """Clean up resources."""
        self.browser.quit()

def main():
    print("\t\t\tUniversal Contacts Extractor\n")
    
    extractor = ContactExtractor()
    try:
        extractor.process_websites_file("websites.csv")
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    main()
