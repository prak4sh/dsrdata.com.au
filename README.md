# DSRData Automation Scripts

This repository contains two main scripts for automating data extraction and image processing from dsrdata.com.au:

## 1. main.py

**Purpose:**
- Logs in and fetches market data from dsrdata.com.au using cookies and HTTP requests.
- Saves the extracted data to a CSV file (default: `markets.csv`).

**How to Run:**
1. Ensure you have Python 3.7+ installed.
2. Install dependencies:
	```bash
	pip install -r requirements.txt
	```
3. Place your `cookies.json` file (exported from your browser) in the project directory.
4. Run the script:
	```bash
	python3 main.py
	```

**Notes:**
- The script expects a valid `cookies.json` file for authentication.
- Output data will be saved in `markets.csv`.

## 2. chart.py

**Purpose:**
- Downloads property market charts as images for a list of suburbs.
- Combines the downloaded images into a single high-resolution image (vertical layout).

**How to Run:**
1. Ensure you have Python 3.7+ installed.
2. Install dependencies:
	```bash
	pip install -r requirements.txt
	```
3. Prepare your input file (default: `suburbs.csv`). Supported formats: `.csv`, `.xlsx`, `.xls`.
	- Example `suburbs.csv`:
	  ```csv
	  Zetland,NSW,2017,house
	  Cabramatta,NSW,2166,house
	  Wetherill park,NSW,2164,house
	  Greenfield park,NSW,2176,house
	  ```
4. Run the script (optionally specify input file):
	```bash
	python3 chart.py --input suburbs.csv
	```
5. The script will:
	- Download chart images to a temporary folder.
	- Combine all images into a single image saved in the `images` folder.
	- Remove temporary images after combining.

**Notes:**
- The combined image will be saved in the `images` folder with a timestamped filename.
- You can change the number of columns, cell size, and padding by editing the config variables at the top of `chart.py`.

---

For any issues, please check the script output for error messages or contact the maintainer.
# dsrdata.com.au
