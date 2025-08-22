# create_meeting_app/bot_scripts/google_meet_bot.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException

import threading, time, os, subprocess
from datetime import datetime

from create_meeting_app.models import Screenshot

# Install once, reuse same binary
CHROMEDRIVER_PATH = ChromeDriverManager().install()

def start_audio_recorder(meeting_id: int):
    os.makedirs("media/recordings", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    wav_path  = f"media/recordings/meet_{meeting_id}_{timestamp}.wav"
    MONITOR   = "alsa_output.pci-0000_00_1f.3.analog-stereo.monitor"
    cmd = ["ffmpeg","-y","-f","pulse","-i",MONITOR,"-ac","1","-ar","16000",wav_path]
    return subprocess.Popen(cmd), wav_path

def join_meeting(meeting_link: str, bot_name: str, meeting):
    options = Options()
    # Core flags to auto-accept permissions & prevent popups
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Linux stability flags
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(CHROMEDRIVER_PATH)
    driver  = webdriver.Chrome(service=service, options=options)
    print("📎 Chrome session_id:", driver.session_id)

    try:
        # Retry loading the page
        for i in range(3):
            try:
                driver.get(meeting_link)
                break
            except Exception as e:
                print(f"⚠️ driver.get failed (attempt {i+1}): {e}")
                time.sleep(2)
        else:
            raise RuntimeError("Could not load Meet page after 3 attempts")

        wait = WebDriverWait(driver, 30)
        name_field = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='Your name']")
        ))
        name_field.clear(); name_field.send_keys(bot_name)

        # Mute mic & camera if possible
        try:
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label='Turn off microphone']")
            )).click()
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label='Turn off camera']")
            )).click()
        except:
            pass

        # Dismiss any popups
        for btn in driver.find_elements(By.XPATH, "//button[contains(text(),'Dismiss')]"):
            btn.click()

        # Click Join / Ask to join
        try:
            join_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(text(),'Join now')]")
            ))
        except:
            join_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(text(),'Ask to join')]")
            ))
        driver.execute_script("arguments[0].click();", join_btn)

        # Start audio and screenshots watcher
        recorder, _ = start_audio_recorder(meeting.id)
        stop_flag = threading.Event()
        os.makedirs("media/screenshots", exist_ok=True)

        def watcher():
            # On-arrival screenshot
            shot0 = f"media/screenshots/{meeting.id}_joined.png"
            driver.save_screenshot(shot0)
            Screenshot.objects.create(meeting=meeting, image_path=shot0)

            while not stop_flag.is_set():
                for _ in range(30):
                    if stop_flag.is_set(): break
                    time.sleep(1)

                try:
                    # Detect end
                    if driver.find_elements(By.XPATH,
                        "//div[contains(text(),'Call ended') or contains(text(),'You left the call')]"
                    ):
                        stop_flag.set()
                        try: driver.quit()
                        except: pass
                        return

                    # Periodic screenshot
                    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
                    shot = f"media/screenshots/{meeting.id}_{ts}.png"
                    driver.save_screenshot(shot)
                    Screenshot.objects.create(meeting=meeting, image_path=shot)
                except WebDriverException:
                    stop_flag.set()
                    return

        threading.Thread(target=watcher, daemon=True).start()
        stop_flag.wait()

    finally:
        try: recorder.terminate()
        except: pass
        # Browser quit is handled in watcher

# Quick local test
if __name__ == "__main__":
    dummy = type("M", (), {"id": 0})
    join_meeting("https://meet.google.com/xyz", "TestBot", dummy)
