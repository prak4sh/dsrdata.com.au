import json
import os
import pandas as pd
from rich import print
from datetime import datetime
import requests
import base64
import time
import random
from PIL import Image, ImageDraw
import glob, math
from bs4 import BeautifulSoup

import argparse

# --- CONFIG ---
CELL_SIZE = 400            # size of each small image in the grid
PADDING = 10               # space between images
COLS = 4                   # number of columns in the grid
TEMP_FOLDER = "tmp"        # temporary folder for processing
OUTPUT_FOLDER = "images"   # folder to save final combined images

COOKIES = dict()
HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Referer': 'https://dsrdata.com.au/products/suburb_analyser_show',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-GPC': '1',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not;A=Brand";v="99", "Brave";v="139", "Chromium";v="139"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
}
ACCESS_TOKEN = None

def make_get_requests(url, params=None, retries=3):
    global HEADERS, COOKIES
    """
    Make a GET request to the specified URL with the given headers and cookies.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params)
            print_info(f"GET {url} - {response.status_code}", mtype="INF")
            response.raise_for_status()  # Raise an error for HTTP errors
            return response
        except requests.RequestException as e:
            print_info(f"Failed to make GET request: {e}", mtype="ERR")
            return None

def read_suburbs(filepath):
    df = pd.read_csv(filepath)
    return df.values.tolist()

def print_info(msg, mtype):
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if mtype == "INF":
        print(f"[blue]{time_now} [INFO] {msg}[/blue]")
    elif mtype == "WRN":
        print(f"[yellow]{time_now} [WARNING] {msg}[/yellow]")
    elif mtype == "ERR":
        print(f"[red]{time_now} [ERROR] {msg}[/red]")
    elif mtype == "SUC":
        print(f"[green]{time_now} [SUCCESS] {msg}[/green]")

def is_logged_in():
    global ACCESS_TOKEN
    url = 'https://dsrdata.com.au/'
    response = make_get_requests(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    email = soup.find('div', class_='email')
    access_token = soup.find(id='accesstoken')
    if access_token:
        ACCESS_TOKEN = access_token.get('value')
    if email and ACCESS_TOKEN:
        print_info(f"User is logged in as: {email.text.strip()}", mtype='INF')
        print_info(f"Access token: {ACCESS_TOKEN}", mtype='INF')
        return True
    else:
        print_info("User is not logged in.", mtype='WRN')
        return False


def load_cookies_from_json(json_path="cookies.json"):
    """
    Load cookies from a JSON file and return as a dict for requests.
    Uses print_info to display status messages.
    """
    if not os.path.exists(json_path):
        print_info(f"Cookie file '{json_path}' does not exist.", mtype="ERR")
        return {}
    try:
        with open(json_path, "r") as f:
            cookies_list = json.load(f)
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies_list}
        print_info(f"Loaded cookies from '{json_path}'.", mtype="INF")
        return cookies_dict
    except Exception as e:
        print_info(f"Failed to load cookies: {e}", mtype="ERR")
        return {}

def get_charts(locality, state, postCode, propertyType):
    if 'house' in propertyType.lower():
        propType = 'H'
    elif 'unit' in propertyType.lower():
        propType = 'U'
    url = f"https://dsrdata.com.au/DSRWeb/secure/getHistoricalChart.png"
    params = {
        'access_token': '04ecc9c2-9fab-480d-a774-f1b71fd7cf44',
        'state': state.strip(),
        'postCode': postCode,
        'locality': locality.strip(),
        'propTypeCode': propType,
        'statCode': 'DSR',
    }
    response = make_get_requests(url, params=params)
    if response and response.status_code == 200:
        try:
            img_data = base64.b64decode(response.text)
        except Exception as e:
            img_data = response.content

        if not os.path.exists(TEMP_FOLDER):
            os.makedirs(TEMP_FOLDER)
        filename = f"{TEMP_FOLDER}/chart_{locality.strip()}_{state.strip()}_{postCode}_{propType}.png"

        if os.path.exists(filename):
            os.remove(filename)

        with open(filename, "wb") as f:
            f.write(img_data)

        print_info(f"Chart saved as '{filename}'.", mtype="SUC")


def combine_images():
    if not os.path.exists(TEMP_FOLDER):
        print_info(f"Temporary folder '{TEMP_FOLDER}' does not exist!", mtype="ERR")
        raise SystemExit(f"Temporary folder '{TEMP_FOLDER}' does not exist!")

    img_paths = glob.glob(f"{TEMP_FOLDER}/*")
    imgs = [Image.open(f) for f in img_paths]
    if not imgs:
        print_info("No images found in temp folder!", mtype="ERR")
        raise SystemExit("No images found in temp folder!")

    # --- CALCULATE GRID SIZE ---
    n_imgs = len(imgs)
    cols = 1
    rows = n_imgs

    # For vertical layout, only one column, so max width is max of all images, heights are each image's height
    col_widths = [max(img.width for img in imgs)]
    row_heights = [img.height for img in imgs]

    # Calculate canvas size
    canvas_width = col_widths[0] + 2 * PADDING
    canvas_height = sum(row_heights) + (rows + 1) * PADDING

    # --- CREATE HIGH-RES CANVAS ---
    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")

    # --- PASTE IMAGES ---
    y = PADDING
    for idx, img in enumerate(imgs):
        # Center image horizontally in the column
        x_offset = PADDING + (col_widths[0] - img.width) // 2
        canvas.paste(img, (x_offset, y))
        y += img.height + PADDING

    # --- SAVE HIGH-RES IMAGE (PNG for lossless quality) ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"combined_chart_{timestamp}.png"
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    out_path = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(out_path):
        os.remove(out_path)
    canvas.save(out_path, format="PNG")
    print_info(f"Saved {out_path}", mtype="SUC")

    # Remove all images in temp folder
    for f in img_paths:
        try:
            os.remove(f)
        except Exception as e:
            print_info(f"Failed to remove {f}: {e}", mtype="WRN")




def parse_args():
    parser = argparse.ArgumentParser(description="Combine property charts from a CSV/XLSX/XLS file.")
    parser.add_argument(
        "-i", "--input",
        type=str,
        default="suburbs.csv",
        help="Input file (csv, xlsx, or xls). Default: suburbs.csv"
    )
    return parser.parse_args()

def save_to_csv(data, filename='markets.csv'):
    new_df = pd.DataFrame(data)
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        # Drop all-NA columns to avoid FutureWarning
        df = df.dropna(axis=1, how='all')
        new_df = new_df.dropna(axis=1, how='all')
        if not df.empty and not new_df.empty:
            df = pd.concat([df, new_df], ignore_index=True)
        elif df.empty:
            df = new_df
        # If new_df is empty, no need to concatenate
    else:
        df = new_df

    # Save the DataFrame to the CSV file only if it's not empty
    if not df.empty:
        df.to_csv(filename, index=False)

def main():
    global COOKIES
    global ACCESS_TOKEN
    COOKIES = load_cookies_from_json()

    logged_in = is_logged_in()
    if not logged_in:
        print_info("User is not logged in. Please update cookies.", mtype="ERR")
        return
    args = parse_args()
    input_file = args.input

    # Check file extension
    valid_ext = [".csv", ".xlsx", ".xls"]
    ext = os.path.splitext(input_file)[1].lower()
    if ext not in valid_ext:
        print_info(f"Input file must be .csv, .xlsx, or .xls. Got: {ext}", mtype="ERR")
        exit(1)

    if not os.path.exists(input_file):
        print_info(f"Suburb file '{input_file}' does not exist!", mtype="ERR")
        return

    suburbs = read_suburbs(input_file)

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    for suburb in suburbs:
        locality, state, postCode, propertyType = suburb
        get_charts(locality, state, postCode, propertyType)
        random_sleep_duration = random.uniform(2, 5)
        print_info(f"Retrieved charts for {locality}, {state}, {postCode}, {propertyType}", mtype="SUC")    
        print_info(f"Sleeping for {random_sleep_duration:.2f} seconds to mimic human behavior.", mtype="INF")
        time.sleep(random_sleep_duration)

    combine_images()    

if __name__ == "__main__":
    main()
