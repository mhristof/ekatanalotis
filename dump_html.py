from selenium import webdriver

# Set Chrome options
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")  # Run in headless mode

print("Starting Chrome browser in headless mode...")

# Start Chrome browser
driver = webdriver.Chrome(options=chrome_options)

print("Chrome browser started.")

# Navigate to the website
driver.get("https://e-katanalotis.gov.gr/product/2790")

print("Navigated to the website.")

# Dump HTML code
html = driver.page_source
print(html)

# Close the browser
driver.quit()
