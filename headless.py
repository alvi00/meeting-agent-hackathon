import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os # For saving screenshots

def join_meeting(meeting_link, bot_name):
    options = Options()
    options.add_argument("--headless=new") # Make sure this is uncommented for headless
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_argument("--mute-audio")
    options.add_argument("--disable-gpu")

    # IMPORTANT: If your bot needs to stay logged in or use a specific profile,
    # you might need to specify a user data directory.
    # For example: options.add_argument("user-data-dir=/home/alvi00/selenium_profiles/meet_bot_profile")
    # Make sure this path exists and is writable. Create it if it doesn't.
    # This profile will store cookies/login info.

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30) # Increased general wait time

    try:
        print(f"Navigating to {meeting_link}")
        driver.get(meeting_link)
        time.sleep(5) # Initial wait for the page to start loading
        driver.save_screenshot(os.path.join(os.getcwd(), "screenshot_01_after_navigation.png")) # Save screenshot

        # --- Handle Potential Google Account Sign-in/Pre-fill ---
        # The HTML you provided suggests you might be logged in, and the name is pre-filled.
        # This section tries to gracefully handle that or click a "Continue without account" if present.

        try:
            # Check if an explicit name input field *needs* to be filled
            name_field = None
            try:
                # Look for an input field that is not pre-filled with an existing user's name
                # This XPath attempts to find an input that is likely designed for new input,
                # or is an explicit "Your name" field.
                name_field = wait.until(EC.element_to_be_clickable((By.XPATH, 
                    "//input[@placeholder='Your name' and not(@value)] | //input[@aria-label='Your name' and not(@value)] | //input[@data-initial-value='' or @data-initial-value='']")))
                
                # If found and is an actual input field, clear and send keys
                name_field.clear()
                name_field.send_keys(bot_name)
                print(f"Entered name: {bot_name} into an empty name field.")
                driver.save_screenshot(os.path.join(os.getcwd(), "screenshot_02_name_entered.png"))
            except:
                print("Name field likely pre-filled or not present for manual input.")
                # If the name field isn't found for manual input, assume it's pre-filled
                # You might want to verify the pre-filled name here if needed.
                pass # Continue if name field isn't explicitly found for input

            # Try to dismiss any "Sign in" or "Continue without account" prompts that might appear
            try:
                # Look for buttons related to sign-in or guest join
                continue_button_xpath = "//button[contains(., 'Continue without an account')] | //span[contains(text(), 'Continue as guest')]//ancestor::button"
                continue_button = wait.until(EC.element_to_be_clickable((By.XPATH, continue_button_xpath)))
                driver.execute_script("arguments[0].click();", continue_button)
                print("Clicked 'Continue without an account' or similar button.")
                driver.save_screenshot(os.path.join(os.getcwd(), "screenshot_02_after_continue_button.png"))
                time.sleep(2) # Give time for the page to transition
            except:
                print("No 'Continue without an account' or guest option found (or not needed).")
                driver.save_screenshot(os.path.join(os.getcwd(), "screenshot_02_no_continue_button.png"))

        except Exception as e:
            print(f"Error during name/login handling: {e}")
            driver.save_screenshot(os.path.join(os.getcwd(), "ERROR_02_name_login_handling.png"))
            raise # Re-raise to stop execution

        # --- Mic and Camera Handling ---
        # The error "Mic already disabled or button not found in active state" suggests
        # they might already be muted or the locators are wrong.
        # Your HTML shows `data-is-muted="true"` for mic/cam, meaning they are already off.
        # So, the current code snippet might be trying to click an already off button.
        # We'll adapt it to check if they are *not* muted and then click to mute.

        try:
            # Check for microphone button that is NOT muted and click it to mute
            mic_button_on_xpath = "//div[@data-device-type='microphone' and @data-is-muted='false']//ancestor::button | //button[@aria-label='Turn off microphone' and @data-is-muted='false']"
            try:
                mic_button = wait.until(EC.element_to_be_clickable((By.XPATH, mic_button_on_xpath)))
                driver.execute_script("arguments[0].click();", mic_button)
                print("Mic was ON, turned OFF.")
                driver.save_screenshot(os.path.join(os.getcwd(), "screenshot_03_mic_off.png"))
            except:
                print("Mic already disabled or active mic button not found.")

            # Check for camera button that is NOT muted and click it to mute
            cam_button_on_xpath = "//div[@data-device-type='camera' and @data-is-muted='false']//ancestor::button | //button[@aria-label='Turn off camera' and @data-is-muted='false']"
            try:
                cam_button = wait.until(EC.element_to_be_clickable((By.XPATH, cam_button_on_xpath)))
                driver.execute_script("arguments[0].click();", cam_button)
                print("Camera was ON, turned OFF.")
                driver.save_screenshot(os.path.join(os.getcwd(), "screenshot_03_cam_off.png"))
            except:
                print("Camera already disabled or active camera button not found.")
        except Exception as e:
            print(f"Microphone/camera handling failed: {e}")
            driver.save_screenshot(os.path.join(os.getcwd(), "ERROR_03_mic_cam_handling.png"))


        # --- Dismiss any overlays or pop-ups (still tricky, rely on screenshots) ---
        try:
            dismiss_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Dismiss')] | //button[contains(@aria-label, 'Dismiss')] | //button[contains(text(), 'No thanks')]")
            for button in dismiss_buttons:
                if button.is_displayed() and button.is_enabled():
                    driver.execute_script("arguments[0].click();", button)
                    print("Dismissed overlay/pop-up.")
                    time.sleep(0.5)
                    driver.save_screenshot(os.path.join(os.getcwd(), f"screenshot_04_dismissed_popup_{int(time.time())}.png"))
        except Exception as e:
            print(f"No overlays found to dismiss or error dismissing: {e}")
            driver.save_screenshot(os.path.join(os.getcwd(), "ERROR_04_dismiss_failed.png"))

        # --- Click "Join now" or "Ask to join" ---
        print("Attempting to find and click Join/Ask to join button...")
        join_button = None
        try:
            # The most robust locator for the button that CONTAINS the text
            join_button_xpath = "//button[./span[contains(text(), 'Join now')] or ./span[contains(text(), 'Ask to join')]]"
            join_button = wait.until(EC.element_to_be_clickable((By.XPATH, join_button_xpath)))

            driver.execute_script("arguments[0].scrollIntoView(true);", join_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", join_button)
            print("Clicked Join/Ask to join button.")
            driver.save_screenshot(os.path.join(os.getcwd(), "screenshot_05_after_join_click.png"))
        except Exception as e:
            print(f"Critical: Could not find Join now or Ask to join button: {e}")
            driver.save_screenshot(os.path.join(os.getcwd(), "ERROR_05_join_button_missing.png"))
            raise # Re-raise to indicate a critical failure

        print("Bot has attempted to join. Staying in meeting for 1 hour.")
        time.sleep(3600)

    except Exception as e:
        print(f"Bot execution error: {str(e)}")
        driver.save_screenshot(os.path.join(os.getcwd(), "ERROR_final_exception.png"))
    finally:
        print("Quitting driver.")
        driver.quit()

# Example usage (for local testing, outside Django)
if __name__ == "__main__":
    # IMPORTANT: Use a meeting link that is active for testing.
    # If the link requires Google login, remember to use a pre-authenticated user-data-dir.
    test_meeting_link = "https://meet.google.com/dzy-mzsz-sfn" # Replace with your actual test link
    test_bot_name = "HeadlessBot"
    print("Running direct test of join_meeting function...")
    try:
        join_meeting(test_meeting_link, test_bot_name)
    except Exception as e:
        print(f"Test run failed: {e}")