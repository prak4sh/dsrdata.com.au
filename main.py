from rich import print
import requests
from datetime import datetime
import json 
import os
import pandas as pd
import time
import random
from bs4 import BeautifulSoup
from sheet import SheetManager

HEADERS = {
    'Host': 'dsrdata.com.au',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.5',
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': 'https://dsrdata.com.au',
    'Referer': 'https://dsrdata.com.au/products/dsr_market_matcher_show',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Priority': 'u=0',
    'Connection': 'keep-alive',
}
COOKIES = dict()
COUNT = 0
ACCESS_TOKEN = None
SHEET_MANAGER = None
    
def make_post_requests(url, data):
    global COOKIES
    response = requests.post(url, json=data, headers=HEADERS, cookies=COOKIES)
    print_info(f'Url: {url}, Status: {response.status_code}', mtype="INF")
    return response

def make_get_requests(url):
    global COOKIES
    response = requests.get(url, headers=HEADERS, cookies=COOKIES)
    print_info(f'Url: {url}, Status: {response.status_code}', mtype="INF")
    return response

def time_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_info(msg, mtype='INF'):
    if mtype == 'INF':
        print(f"[green]{time_now()} [INF][/green] {msg}")
    elif mtype == 'ERR':
        log_error(msg)
        print(f"[red]{time_now()} [ERR][/red] {msg}")
    elif mtype == 'WRN':
        print(f"[yellow]{time_now()} [WRN][/yellow] {msg}")
    else:
        print(f"[{mtype}] {msg}")

def log_error(msg):
    with open("error.log", "a") as f:
        f.write(f"{time_now()} [ERR] {msg}\n")

def get_data(min_dsr, max_dsr,min_renters = 0, max_renters=100 ,state=None, save_info=False):
    global COUNT
    global ACCESS_TOKEN
    if not state:
        state_value = 'ACT,NSW,NT,QLD,SA,TAS,VIC,WA'
    else:
        state_value = state
    json_data = {
        'request': {
            'type': 'matching_mkts',
            'criteria': {
                'and': [
                    {
                        'state': {
                            'val': state_value,
                            'capital_cities_only': 'false',
                        },
                        "prop_type_code":{
                            "val":"H"
                            },
                        'dsr': {
                            'min': str(min_dsr),
                            'max': str(max_dsr),
                        },
                        'renters': {
                            'min': str(min_renters),
                            'max': str(max_renters),
                        },
                    },
                ],
            },
        'display': {
                    'state': {
                        'sort_order': '35',
                    },
                    'post_code': {
                        'sort_order': '36',
                    },
                    'prop_type_code': {
                        'sort_order': '37',
                    },
                    'locality': {
                        'sort_order': '38',
                    },
                    'acr': {
                        'sort_order': '39',
                        'sort_dir': 'desc',
                    },
                    'discount': {
                        'sort_order': '40',
                    },
                    'dom': {
                        'sort_order': '41',
                    },
                    'dsr': {
                        'sort_order': '42',
                        'sort_dir': 'desc',
                    },
                    'median_12': {
                        'sort_order': '43',
                        'sort_dir': 'desc',
                    },
                    'osi': {
                        'sort_order': '44',
                        'sort_dir': 'desc',
                    },
                    'renters': {
                        'sort_order': '45',
                    },
                    'som_perc': {
                        'sort_order': '46',
                    },
                    'sr': {
                        'sort_order': '47',
                        'sort_dir': 'desc',
                    },
                    'tv': {
                        'sort_order': '48',
                        'sort_dir': 'desc',
                    },
                    'vacancy': {
                        'sort_order': '49',
                    },
                    'yield': {
                        'sort_order': '50',
                        'sort_dir': 'desc',
                    },
                },
            },
        }
    
    url = f'https://dsrdata.com.au/DSRWeb/secure/getMatchingMkts.json?access_token={ACCESS_TOKEN}'
    response = make_post_requests(url, data=json_data)  
    jsonResults = json.loads(response.text)
    res = jsonResults['response']
    warnings = res.get('warnings')
    if warnings:
        warning = warnings.get("WRN")
        print_info(f"Warnings: {warning}", mtype="WRN")
        if save_info:
            print_info(f"Saving warning to info.txt", mtype="INF")
            with open('info.txt', 'a') as f:
                f.write(f"{time_now()} Warning: {warning}\n")
                f.write(f"{time_now()} Min DSR: {min_dsr}, Max DSR: {max_dsr}, state: {state}, min_renters: {min_renters}, max_renters: {max_renters}\n")
                f.write('')
    mkts = res.get('mkt')
    # check if mkts is list or dictionary
    if isinstance(mkts, dict):
        mkts = [mkts]
    infos = []
    if not mkts:
        print_info('No markets found', mtype='error')
        more = False
        return infos, more
    print_info(f"Markets found: {len(mkts)}. Total data: {COUNT}", mtype="INF")
    
    # Log if we hit the 250 limit
    if len(mkts) >= 250:
        log_message = f"{time_now()} - Hit 250+ results limit: Min DSR: {min_dsr}, Max DSR: {max_dsr}, State: {state}, Min Renters: {min_renters}, Max Renters: {max_renters}, Results: {len(mkts)}\n"
        print_info(f"Hit 250+ results limit - logging to logs.txt", mtype="WRN")
        with open('logs.txt', 'a') as f:
            f.write(log_message)
    
    for mkt in mkts:
        mkt_stats = mkt['mkt_stats']
        info = {
            'Timestamp': time_now(),
            'State': mkt['st'],
            'Post Code': mkt['pc'],
            'Property Type': mkt['pt'],
            'Suburb': mkt['lo'],
            'Auction clearance rate': mkt_stats.get('ACR'),
            'Avg vendor discount': mkt_stats.get('DISCOUNT'),
            'Days on market': mkt_stats.get('DOM'),
            'Demand to Supply Ratio': mkt_stats.get('DSR'),
            'Median 12 months': mkt_stats.get('MEDIAN_12'),
            'Online search interest': mkt_stats.get('OSI'),
            'Percent renters in market': mkt_stats.get('RENTERS'),
            'Percent stock on market': mkt_stats.get('SOM_PERC'),
            'Statistical reliability': mkt_stats.get('SR'),
            'Typical value': mkt_stats.get('TV'),
            'Vacancy rate': mkt_stats.get('VACANCY'),
            'Gross rental yield': mkt_stats.get('YIELD'),
        }
        if SHEET_MANAGER:
            SHEET_MANAGER.log_to_sheet(info)
        infos.append(info)
        more = True
    sleep_time = random.uniform(2, 5)
    print_info(f"Sleeping for {sleep_time:.2f} seconds to avoid hitting the server too hard", mtype="INF")
    time.sleep(sleep_time)  # Sleep to avoid hitting the server too hard
    return infos, more

def load_cookies_from_json(json_path="cookies.json"):
    """
    Load cookies from a JSON file (Chrome/Firefox export format) and return as a dict for requests.
    Checks if the file exists and prints info or error.
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

# save list of dictionary data into csv file and check if file exists. If yes append data to it
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

def is_logged_in():
    global ACCESS_TOKEN
    url = 'https://dsrdata.com.au/'
    response = make_get_requests(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    email = soup.find('div', class_='email')
    access_token = soup.find(id='accesstoken')
    if access_token:
        ACCESS_TOKEN = access_token.get('value')
    if email and access_token:
        print_info(f"User is logged in as: {email.text.strip()}", mtype="INF")
        print_info(f"Access token: {ACCESS_TOKEN}", mtype="INF")
        return True
    else:
        print_info("User is not logged in.", mtype="WRN")
        return False

def create_filename():
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")
    filename = f"markets_{date_str}_{time_str}.csv"
    return filename

# check every row in markets.csv and remove duplicates and show log about initial and final count
def remove_duplicates(filename='markets.csv'):
    if not os.path.exists(filename):
        print_info(f"File {filename} does not exist. No duplicates to remove.", mtype="WRN")
        return
    df = pd.read_csv(filename)
    if df.empty:
        print_info(f"File {filename} is empty. No duplicates to remove.", mtype="WRN")
        return

    initial_count = df.shape[0]
    # Remove duplicates based on all columns
    df.drop_duplicates(inplace=True)
    final_count = df.shape[0]
    
    # Create new filename properly by splitting directory and filename
    directory = os.path.dirname(filename)
    basename = os.path.basename(filename)
    new_filename = os.path.join(directory, f'new_{basename}')
    
    # Save the DataFrame back to the CSV file
    df.to_csv(new_filename, index=False)
    print_info(f"Removed duplicates from {filename}. Initial count: {initial_count}, Final count: {final_count}", mtype="INF")
    print_info(f"Clean data saved to {new_filename}", mtype="INF")


def main():
    global COUNT
    global COOKIES
    global SHEET_MANAGER

    save_to_sheet = input("Do you want to log data to Google Sheets? (y/n): ").strip().lower() == 'y'
    if save_to_sheet:
        SHEET_MANAGER = SheetManager("DSR Data")
        print_info("Google Sheets logging is enabled.", mtype="INF")
    else:
        SHEET_MANAGER = None
        print_info("Google Sheets logging is disabled.", mtype="INF")

    COOKIES = load_cookies_from_json()

    logged_in = is_logged_in()

    if not logged_in:
        print_info("User is not logged in. Please update cookies..", mtype='error')
        return

    stat_values = ['QLD', 'NSW', 'VIC', 'WA', 'SA', 'TAS', 'NT', 'ACT']  # All states
    filename = create_filename()
    if not os.path.exists('output'):
        os.makedirs('output')
    filename = os.path.join('output', filename)
    
    min_dsr, max_dsr = 30, 40  # Start from beginning
    all_state_data = []
    
    while True:
        print_info(f"Searching for markets with DSR between {min_dsr} and {max_dsr}", mtype="INF")
        data, _ = get_data(min_dsr, max_dsr)
        
        if len(data) >= 250:
            # Need to break down by states
            all_state_data = []
            for state in stat_values:
                print_info(f"Searching for markets with DSR between {min_dsr} and {max_dsr} in {state}", mtype="INF")
                state_data, _ = get_data(min_dsr, max_dsr, state=state)
                
                if len(state_data) >= 250:
                    print_info(f"Hit 250+ results limit for DSR {min_dsr}-{max_dsr} in {state}. Segmenting by renter ranges.", mtype="WRN")
                    for i in range(4):
                        min_renters = i * 25
                        max_renters = min_renters + 25
                        print_info(f"Searching for markets with DSR {min_dsr}-{max_dsr} in {state} with renters between {min_renters} and {max_renters}", mtype="INF")
                        segmented_data, _ = get_data(min_dsr, max_dsr, state=state, min_renters=min_renters, max_renters=max_renters)
                        # if semented length is greater than 250, try two times set min_dsr and max_dsr
                        if len(segmented_data) >= 250:
                            print_info(f"Segmented data for DSR {min_dsr}-{max_dsr} in {state} with renters {min_renters}-{max_renters} still has 250+ results. Breaking down by individual DSR values.", mtype="WRN")
                            
                            # Get data for min_dsr
                            segmented_data1, _ = get_data(min_dsr, min_dsr, state=state, min_renters=min_renters, max_renters=max_renters)
                            if len(segmented_data1) >= 250:
                                print_info(f"DSR {min_dsr} data still has 250+ results. Breaking down renter range {min_renters}-{max_renters} into smaller segments.", mtype="WRN")
                                
                                # Calculate range size and split into 5 equal parts
                                range_size = max_renters - min_renters
                                segment_size = range_size // 5
                                
                                for j in range(5):
                                    segment_min = min_renters + (j * segment_size)
                                    segment_max = segment_min + segment_size if j < 4 else max_renters  # Last segment goes to max_renters
                                    
                                    print_info(f"Searching DSR {min_dsr} in {state} with renters {segment_min}-{segment_max}", mtype="INF")
                                    micro_segment_data, _ = get_data(min_dsr, min_dsr, state=state, min_renters=segment_min, max_renters=segment_max)
                                    all_state_data.extend(micro_segment_data)
                            else:
                                print_info(f"Found {len(segmented_data1)} markets for DSR {min_dsr} in {state} with renters {min_renters}-{max_renters}. Adding to all_state_data.", mtype="INF")
                                all_state_data.extend(segmented_data1)
                            
                            # Get data for max_dsr
                            segmented_data2, _ = get_data(max_dsr, max_dsr, state=state, min_renters=min_renters, max_renters=max_renters)
                            if len(segmented_data2) >= 250:
                                print_info(f"DSR {max_dsr} data still has 250+ results. Breaking down renter range {min_renters}-{max_renters} into smaller segments.", mtype="WRN")
                                
                                # Calculate range size and split into 5 equal parts
                                range_size = max_renters - min_renters
                                segment_size = range_size // 5
                                
                                for j in range(5):
                                    segment_min = min_renters + (j * segment_size)
                                    segment_max = segment_min + segment_size if j < 4 else max_renters  # Last segment goes to max_renters
                                    
                                    print_info(f"Searching DSR {max_dsr} in {state} with renters {segment_min}-{segment_max}", mtype="INF")
                                    micro_segment_data, _ = get_data(max_dsr, max_dsr, state=state, min_renters=segment_min, max_renters=segment_max)
                                    all_state_data.extend(micro_segment_data)
                            else:
                                print_info(f"Found {len(segmented_data2)} markets for DSR {max_dsr} in {state} with renters {min_renters}-{max_renters}. Adding to all_state_data.", mtype="INF")
                                all_state_data.extend(segmented_data2)                               
                            
                        else:
                            print_info(f"Found {len(segmented_data)} markets for DSR {min_dsr}-{max_dsr} in {state} with renters between {min_renters} and {max_renters}. Adding to all_state_data.", mtype="INF")
                            all_state_data.extend(segmented_data)
                else:
                    print_info(f"Found {len(state_data)} markets for DSR {min_dsr}-{max_dsr} in {state}. Adding to all_state_data.", mtype="INF")
                    all_state_data.extend(state_data)
        else:
            # Less than 250 results, use the original data
            all_state_data = data
            print_info(f"Found {len(data)} markets for DSR {min_dsr}-{max_dsr}. No segmentation needed.", mtype="INF")
        

        # Save data if we have any
        if all_state_data:
            COUNT += len(all_state_data)
            save_to_csv(all_state_data, filename=filename)
            print_info(f"Saved {len(all_state_data)} records for DSR {min_dsr}-{max_dsr}. Total: {COUNT}", mtype="INF")
        else:
            print_info(f"No data found for DSR {min_dsr}-{max_dsr}", mtype="WRN")


        # Move to next DSR range
        min_dsr = max_dsr + 1
        max_dsr = min_dsr + 1  # You can adjust the increment
        
        # Stop condition - you can modify this based on your needs
        if min_dsr > 75:  # Example: stop at DSR 75
            print_info("Reached maximum DSR limit", mtype="INF")
            break
    remove_duplicates(filename=filename)
    print_info(f"Data saved to {filename}", mtype="INF")


if __name__=="__main__":
    main()