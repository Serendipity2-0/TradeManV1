import asyncio

import pyotp
from kiteconnect import KiteConnect
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


async def login_in_zerodha(user_details):
    """
    Asynchronously logs in a user to Zerodha trading platform using their API key, API secret, username, password, and TOTP key.

    :param user_details: Dictionary containing user details for login
    :return: The kite_access_token or None if login fails
    """
    api_key = user_details["ApiKey"]
    api_secret = user_details["ApiSecret"]
    user_id = user_details["BrokerUsername"]
    user_pwd = user_details["BrokerPassword"]
    totp_key = user_details["TotpAccess"]

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(f"https://kite.trade/connect/login?api_key={api_key}&v=3")

        login_id = WebDriverWait(driver, 10).until(
            lambda x: x.find_element(By.XPATH, "//input[@type='text']")
        )
        login_id.send_keys(user_id)

        pwd = WebDriverWait(driver, 10).until(
            lambda x: x.find_element(By.XPATH, "//input[@type='password']")
        )
        pwd.send_keys(user_pwd)

        submit = WebDriverWait(driver, 10).until(
            lambda x: x.find_element(By.XPATH, "//button[@type='submit']")
        )
        submit.click()

        await asyncio.sleep(5)  # Use asyncio.sleep instead of time.sleep

        totp = WebDriverWait(driver, 10).until(
            lambda x: x.find_element(By.XPATH, "//input[@label='TOTP']")
        )
        authkey = pyotp.TOTP(totp_key)
        totp.send_keys(authkey.now())

        await asyncio.sleep(5)

        url = driver.current_url
        initial_token = url.split("request_token=")[1]
        request_token = initial_token.split("&")[0]

        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=api_secret)
        kite_access_token = data["access_token"]
        logger.info(f"Session ID for {user_id}: {kite_access_token}")
        return kite_access_token

    except Exception as e:
        logger.error(f"Error logging in for Zerodha user {user_id}: {e}")
        return None

    finally:
        driver.quit()
