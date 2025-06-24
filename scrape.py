from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
from urllib.parse import urlparse

class PrintifyImageDownloader:
    def __init__(self, download_dir):
        """Initialize the downloader with Chrome options and download directory."""
        self.download_dir = os.path.abspath(download_dir)
        self.setup_driver()
        
    def setup_driver(self):
        """Configure and initialize the Chrome WebDriver."""
        chrome_options = webdriver.ChromeOptions()
        
        # Set up download preferences
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Initialize the driver
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def manual_login(self):
        """Open browser and wait for user to login manually."""
        self.driver.get("https://printify.com/app/login")
        print("\nPlease:")
        print("1. Log in to your account")
        print("2. Navigate to the uploaded files page")
        print("3. Press Enter when you're ready to start downloading")
        input("\nPress Enter when ready...")
        
    def get_total_pages(self):
        """Get the total number of pages from pagination."""
        try:
            # Find the last page number from pagination
            pagination_items = self.driver.find_elements(By.CSS_SELECTOR, ".page-number")
            if pagination_items:
                last_page = int(pagination_items[-1].text.strip())
                return last_page
            return 1
        except Exception as e:
            print(f"Error getting total pages: {str(e)}")
            return 1

    def download_images_on_current_page(self):
        """Download all images on the current page."""
        try:
            # Find all image elements
            image_elements = self.wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "[data-testid='filesListItem']")
                )
            )
            
            total_images = len(image_elements)
            print(f"\nFound {total_images} images on this page")
            
            for i, image_element in enumerate(image_elements, 1):
                try:
                    # Click on image to open modal
                    image_element.click()
                    time.sleep(1.5)  # Wait for modal to open
                    
                    # Get image name for logging
                    try:
                        image_name = self.driver.find_element(
                            By.CSS_SELECTOR, ".file-label span"
                        ).text
                    except:
                        image_name = f"Image {i}"
                    
                    # Find and click download button
                    download_button = self.wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "pfa-download-via-blob button")
                        )
                    )
                    download_button.click()
                    time.sleep(2)  # Wait for download to start
                    
                    # Close modal by clicking back button
                    back_button = self.driver.find_element(
                        By.CSS_SELECTOR, "[data-testid='backButton']"
                    )
                    back_button.click()
                    time.sleep(1)  # Wait for modal to close
                    
                    print(f"Downloaded {i}/{total_images}: {image_name}")
                    
                except Exception as e:
                    print(f"Error downloading image {i}: {str(e)}")
                    # Try to close modal if open
                    try:
                        self.driver.find_element(
                            By.CSS_SELECTOR, "[data-testid='backButton']"
                        ).click()
                    except:
                        pass
                    continue
                    
        except Exception as e:
            print(f"Error processing page: {str(e)}")
            
    def go_to_next_page(self):
        """Navigate to the next page if available."""
        try:
            next_button = self.driver.find_element(
                By.CSS_SELECTOR, "nav.pages pfy-button:last-child button"
            )
            if 'disabled' not in next_button.get_attribute('class'):
                next_button.click()
                time.sleep(2)  # Wait for page load
                return True
            return False
        except NoSuchElementException:
            return False

    def download_pages(self, start_page=1, end_page=None):
        """Download images from specified range of pages."""
        current_page = 1
        total_pages = self.get_total_pages()
        
        if end_page is None or end_page > total_pages:
            end_page = total_pages
            
        print(f"\nTotal pages found: {total_pages}")
        print(f"Will download pages {start_page} to {end_page}")
        
        # Navigate to start page if needed
        while current_page < start_page:
            if self.go_to_next_page():
                current_page += 1
            else:
                print("Couldn't reach start page!")
                return
        
        # Download images from each page
        while current_page <= end_page:
            print(f"\nProcessing page {current_page}/{end_page}")
            self.download_images_on_current_page()
            
            if current_page < end_page:
                if not self.go_to_next_page():
                    print("Couldn't go to next page!")
                    break
                current_page += 1
            else:
                break
            
    def cleanup(self):
        """Close the browser and clean up."""
        self.driver.quit()

def main():
    # Create downloads directory if it doesn't exist
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "printify_images")
    os.makedirs(download_dir, exist_ok=True)
    print(f"\nFiles will be downloaded to: {download_dir}")
    
    # Initialize downloader
    downloader = PrintifyImageDownloader(download_dir)
    
    try:
        # Let user handle login and navigation
        downloader.manual_login()
        
        # Get page range from user
        total_pages = downloader.get_total_pages()
        print(f"\nFound {total_pages} total pages")
        
        start_page = input(f"Enter start page (1-{total_pages}, default=1): ").strip()
        start_page = int(start_page) if start_page else 1
        
        end_page = input(f"Enter end page ({start_page}-{total_pages}, default={total_pages}): ").strip()
        end_page = int(end_page) if end_page else total_pages
        
        # Validate page range
        if start_page < 1 or end_page > total_pages or start_page > end_page:
            print("Invalid page range!")
            return
            
        # Run the downloader
        downloader.download_pages(start_page, end_page)
        print("\nDownload complete!")
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    finally:
        input("\nPress Enter to close the browser...")
        downloader.cleanup()

if __name__ == "__main__":
    main()