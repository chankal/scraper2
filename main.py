import logging
import json
import pandas as pd
import geopy
import xmltodict
import time
import boto3
import requests


from bs4 import BeautifulSoup
from datetime import datetime
from urllib.request import urlopen, Request
from seleniumwire.utils import decode as sw_decode
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
#from seleniumwire import webdriver


def timenow():
    return datetime.strftime(datetime.now(), "%m-%d-%Y %H:%M:%S")


# Example: Use selenium for clicking a button
def scraper1(url, driver):
    def fetch():
        print(f"fetching outages from {url}")

        driver.get(url)
        time.sleep(10)

        button = driver.find_elements("xpath", '//*[@id="OMS.Customers Summary"]')

        if button:
            wait = WebDriverWait(driver, 10)
            label = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="OMS.Customers Summary"]')
                )
            )
            label.click()
            time.sleep(5)
            page_source = {}
            select_elements = driver.find_elements(By.CLASS_NAME, "gwt-ListBox")
            menu = Select(select_elements[0])
            for idx, option in enumerate(menu.options):
                level = option.text
                menu.select_by_index(idx)
                time.sleep(3)
                page_source.update({f"per_{level}": driver.page_source})
        return page_source

    def parse():
        data = fetch()
        for level, pg in data.items():
            df = _parse(pg)
            data.update({level: df})
        return data

    def _parse(page_source):
        soup = BeautifulSoup(page_source, "html.parser")
        tables = soup.find_all("table")
        # separate rows
        rows = tables[1].find_all("tr")
        header_row = rows[0]
        data_rows = rows[1:]

        # Extract the table header cells
        header_cells = header_row.find_all("th")
        header = [cell.get_text().strip() for cell in header_cells]
        cols = [h for h in header if h != ""]

        # Extract the table data cells
        data = []
        for row in data_rows:
            cells = row.find_all("td")
            data.append([cell.get_text().strip() for cell in cells])

        # Print the table data as a list of dictionaries
        table = [dict(zip(header, row)) for row in data]
        df = pd.DataFrame(table)
        if len(df.columns) > 1:
            df = df[cols]
            df = df.dropna(axis=0)
            df["timestamp"] = timenow()
            # df = df[df["# Out"] != "0"]
        else:
            df = pd.DataFrame()
        # print("Storing info.csv ...")
        # df.to_csv("info.csv")
        return df

    return parse()


# TODO: Implement your scraper function here
# Input: url to scrape, chromedriver
# Output: A dictionary of dataframe, Ex: {"per_county": <pandas dataframe>, "per_zipcode": <pandas dataframe>, ...}
# Scraper 1 is an example
def scraper(url):
   
    try:
        response = requests.get(url)
    
        # Check if the request was successful
        if response.status_code == 200:
            # Parse JSON data
            outages_data = response.json()

            # DataFrame
            df = pd.DataFrame(outages_data)

            return df

            
            # Dataframe to CSV
            # if not df.empty:
            #     df.to_csv("info.csv", index=False)
            #     print(f"Data saved to info.csv at {timenow()} successfully.")
            # else:
            #     print(f"No data to save at {timenow()}.")

        else:
            print(f"Failed to fetch data from the URL at {timenow()}.") #if no data
    except:
        print("exception request failed")


def handler(event, context):
    s3 = boto3.client("s3")
    bucket = "chandinibucketing"  # TODO: Modify it to your own s3 bucket

    # options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    # options.add_argument("--no-sandbox")
    # options.add_argument("--single-process")
    # options.add_argument("--disable-dev-shm-usage")
    # options.binary_location = "/opt/chrome/chrome"

    # driver = webdriver.Chrome(
    #     executable_path="/opt/chromedriver", chrome_options=options
    # )

    url = "https://www2.ngemc.com/data/outages.json"

    data = scraper(url)  # TODO: Modify it to your own scraper()

    # driver.close()
    # driver.quit()
    print("test")

    current_time = timenow()
        
    filename = (
        f"Canochee_{current_time}.csv"  # TODO: Modify it to your filename
    )
    csv_buffer = pd.DataFrame(data).to_csv(index=False)
    s3.put_object(Bucket=bucket, Key=filename, Body=csv_buffer)
    
    #print(f"filename {filename}, {csv_buffer}")

    return {
        "statusCode": 200,
        "body": "Successfully Scrap the Canochee EMC!",
    }  # TODO: Modify it to your own message

