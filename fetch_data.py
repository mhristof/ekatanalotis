from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Initialize the Chrome WebDriver
driver = webdriver.Chrome(options=chrome_options)

# URL to fetch
url = 'https://www.sklavenitis.gr/eidi-artozacharoplasteioy/'

# Fetch the webpage
driver.get(url)

# You can add more Selenium code here to interact with the page and extract information

# Print the page title as an example
print(driver.title)

# Close the WebDriver
driver.quit()
