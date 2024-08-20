import os
import random
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import glob
import pandas as pd
from datetime import datetime
import sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)


def random_sleep(min_seconds, max_seconds):
    time = random.uniform(min_seconds, max_seconds)
    sleep(time)


def setup_chrome_options(download_dir):
    """
    Setup the chrome options for the driver.
    This is to ensure that the driver is setup to download the files to the specified directory.
    This is done by setting the download directory to the specified directory and disabling the download prompt.

    Args:
        download_dir (str): The directory to download the files to.

    Returns:
        chrome_options (Options): The chrome options for the driver.
    """
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )

    return chrome_options


def setup_driver(chrome_options):
    """
    Setup the driver for the browser.
    This is to ensure that the driver is setup to use the specified chrome options.

    Args:
        chrome_options (Options): The chrome options for the driver.

    Returns:
        driver (webdriver.Chrome): The driver for the browser.
    """
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def wait_for_element(driver, selector, timeout=20):
    """
    Wait for an element to be present on the page.
    This is to ensure that the element is present on the page before we try to interact with it.

    Args:
        driver (webdriver.Chrome): The driver for the browser.
        selector (str): The CSS selector for the element.
        timeout (int): The timeout for the wait.

    Returns:
        element (WebElement): The element if it is present on the page, None otherwise.
    """
    try:
        wait = WebDriverWait(driver, timeout)
        return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    except TimeoutException:
        print(f"Timeout waiting for element with selector: {selector}")
        return None


def download_file(driver, url, download_dir):
    """
    Download a file from the specified URL.
    This is to ensure that the file is downloaded from the specified URL.

    Args:
        driver (webdriver.Chrome): The driver for the browser.
        url (str): The URL to download the file from.
        download_dir (str): The directory to download the files to.
    """
    driver.get(url)
    random_sleep(3, 5)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 4);")
    random_sleep(1, 2)

    download_button = wait_for_element(driver, "div.downloads a")
    if not download_button:
        return False

    driver.execute_script("arguments[0].scrollIntoView();", download_button)
    random_sleep(1, 2)
    driver.execute_script("arguments[0].click();", download_button)

    random_sleep(10, 15)

    downloaded_files = os.listdir(download_dir)
    if downloaded_files:
        print(f"File downloaded: {downloaded_files[0]}")
        return True
    else:
        print("No file was downloaded")
        return False


def merge_csv_files(directory):
    """
    Merge all CSV files in the specified directory.
    This is to ensure that all CSV files are merged into a single file.

    Args:
        directory (str): The directory to merge the CSV files from.

    Returns:
        bool: True if the CSV files were merged successfully, False otherwise.
    """
    # Get all CSV files in the directory
    csv_files = glob.glob(os.path.join(directory, "*.csv"))

    if not csv_files:
        print("No CSV files found to merge.")
        return False

    print(f"Found {len(csv_files)} CSV files.")

    df_list = []
    for file in csv_files:
        try:
            df = process_csv_file(file)
            df_list.append(df)
        except Exception as e:
            print(f"Error processing file {file}: {str(e)}")

    if not df_list:
        print("No valid data found in CSV files.")
        return False

    merged_df = pd.concat(df_list, ignore_index=True)
    merged_df = clean_and_sort_data(merged_df)
    save_merged_file(merged_df, directory)

    return True


def process_csv_file(file):
    """
    Process a CSV file and return a dataframe.
    This is to ensure that the CSV file is processed and returned as a dataframe.

    Args:
        file (str): The path to the CSV file.

    Returns:
        df (pd.DataFrame): The dataframe containing the CSV data.
    """
    # Read the file without headers
    df = pd.read_csv(file, header=None)

    # Set column names manually
    df.columns = ["SR. NO", "SYMBOL", "COMPANY NAME", "ISIN", "STAGE"]

    # Remove unwanted rows and columns
    df = df[
        (df["SR. NO"] != "Long Term")
        & (df["SR. NO"] != "Short Term")
        & (df["SR. NO"].notna())
    ]
    df = df.dropna(how="all")

    # Keep only required columns
    columns_to_keep = ["SR. NO", "SYMBOL", "COMPANY NAME", "ISIN"]
    return df[columns_to_keep]


def clean_and_sort_data(df):
    """
    Clean and sort the dataframe.
    This is to ensure that the dataframe is cleaned and sorted.

    Args:
        df (pd.DataFrame): The dataframe to clean and sort.

    Returns:
        df (pd.DataFrame): The cleaned and sorted dataframe.
    """
    # Remove duplicates
    df.drop_duplicates(inplace=True)

    # Convert 'SR. NO' to numeric, coercing errors to NaN
    df["SR. NO"] = pd.to_numeric(df["SR. NO"], errors="coerce")

    # Drop rows where 'SR. NO' is NaN
    df.dropna(subset=["SR. NO"], inplace=True)

    # Sort the dataframe by 'SR. NO'
    df.sort_values("SR. NO", inplace=True)

    # Reset the index to create a new 'SR. NO' column
    df.reset_index(drop=True, inplace=True)
    df["SR. NO"] = df.index + 1

    return df


def save_merged_file(df, directory):
    """
    Save the merged dataframe to a CSV file.
    This is to ensure that the dataframe is saved to a CSV file.

    Args:
        df (pd.DataFrame): The dataframe to save.
        directory (str): The directory to save the CSV file to.
    """
    # Generate a timestamp for the filename
    timestamp = datetime.now().strftime("%Y-%m-%d")
    merged_filename = f"merged_asm_gsm_{timestamp}.csv"
    merged_filepath = os.path.join(directory, merged_filename)

    # Save the merged dataframe
    df.to_csv(merged_filepath, index=False)
    print(f"Merged CSV saved as: {merged_filepath}")


def main():
    download_dir = os.getenv("ASM_GSM_LIST_DIR")
    os.makedirs(download_dir, exist_ok=True)  # Ensure the directory exists

    chrome_options = setup_chrome_options(download_dir)
    driver = setup_driver(chrome_options)

    links = [
        "https://www.nseindia.com/reports/gsm",
        "https://www.nseindia.com/reports/asm",
    ]

    try:
        for link in links:
            print(f"Attempting to download from: {link}")
            success = download_file(driver, link, download_dir)
            if success:
                print(f"Successfully downloaded file from {link}")
            else:
                print(f"Failed to download file from {link}")

        # Merge CSV files after all downloads are complete
        print("Attempting to merge CSV files...")
        merge_success = merge_csv_files(download_dir)
        if merge_success:
            print("CSV files merged successfully.")
        else:
            print("Failed to merge CSV files.")

        # delete asm-latest.csv and gsm-latest.csv
        os.remove(os.path.join(download_dir, "asm-latest.csv"))
        os.remove(os.path.join(download_dir, "gsm-latest.csv"))

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
