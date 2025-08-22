from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

service = Service(ChromeDriverManager().install())
driver  = webdriver.Chrome(service=service)
print("🎉 Standalone session_id:", driver.session_id)
driver.quit()
