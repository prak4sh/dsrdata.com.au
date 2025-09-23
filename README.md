# DSRData Automation Scripts

This repository contains automation scripts for extracting data from dsrdata.com.au and managing Google Sheets integration:

## Prerequisites

1. **Python 3.7+** installed
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Google Sheets API Setup** (for sheet integration):
   - Create a Google Cloud Project
   - Enable Google Sheets API
   - Download OAuth2 credentials as `credentials.json`
   - Place `credentials.json` in the project directory

## 1. main.py - Data Extraction & Google Sheets Integration

**Purpose:**
- Logs into dsrdata.com.au using cookies
- Fetches market data for suburbs from a CSV file
- Saves data to local CSV files
- Optionally logs data to Google Sheets with duplicate detection

**How to Run:**
1. **Prepare authentication:**
   - Export cookies from your browser as `cookies.json`
   - Ensure `cookies.json` is in the project directory

2. **Prepare input data:**
   - Create `suburbs.csv` with format:
     ```csv
     Suburb,State,Postcode,Property_type
     Zetland,NSW,2017,house
     Cabramatta,NSW,2166,house
     ```

3. **Run the script:**
   ```bash
   python3 main.py
   ```

**Features:**
- **Cookie-based authentication** using `cookies.json`
- **Automatic login verification** and access token extraction
- **Duplicate detection** - skips already processed suburbs
- **Google Sheets integration** - logs data to specified spreadsheets
- **Rate limiting handling** for API calls
- **Progress tracking** with colored console output
- **CSV export** of market data and lookup data

**Output Files:**
- `markets.csv` - Main market data
- `lookup_data.csv` - Suburb lookup information
- Google Sheets (if configured) - Live data sync

## 2. chart.py - Image Processing & Chart Generation

**Purpose:**
- Downloads property market charts as images for suburbs
- Combines downloaded images into a single high-resolution image
- Supports multiple input formats and dynamic sizing

**How to Run:**
1. **Prepare input file** (default: `suburbs.csv`):
   ```csv
   Suburb,State,Postcode,Property_type
   Zetland,NSW,2017,house
   ```

2. **Run with options:**
   ```bash
   # Use default suburbs.csv
   python3 chart.py
   
   # Specify custom input file
   python3 chart.py --input mydata.xlsx
   python3 chart.py --input data.xls
   ```

**Features:**
- **Multiple format support** - CSV, XLSX, XLS files
- **Original image quality preservation** - no scaling/compression
- **Dynamic grid sizing** - adjusts to image dimensions
- **Vertical layout** - images stacked in single column
- **Automatic cleanup** - removes temporary files after processing
- **Configurable settings** - padding, cell size, output folders

**Configuration:**
Edit these variables in `chart.py`:
```python
CELL_SIZE = 400        # Maximum cell size
PADDING = 10           # Space between images
COLS = 1               # Number of columns (1 = vertical)
TEMP_FOLDER = "tmp"    # Temporary processing folder
OUTPUT_FOLDER = "images"  # Final output folder
```

## 3. sheet.py - Google Sheets Management

**Purpose:**
- Manages Google Sheets API integration
- Handles authentication and sheet operations
- Provides batch logging capabilities

**Key Features:**
- **Automatic sheet creation** if sheets don't exist
- **Batch data logging** to avoid rate limits
- **Duplicate data detection** with `get_existing_data()`
- **Error handling** with detailed logging
- **Multiple sheet support** in single spreadsheet

**Usage Examples:**
```python
from sheet import SheetManager

# Initialize
manager = SheetManager("My Spreadsheet Name")

# Log single record
data = {"Suburb": "Zetland", "State": "NSW", "Postcode": "2017"}
manager.log_to_sheet(data, "market_data")

# Log multiple records (batch)
data_list = [
    {"Suburb": "Zetland", "State": "NSW"},
    {"Suburb": "Cabramatta", "State": "NSW"}
]
manager.log_batch_to_sheet(data_list, "market_data")

# Check existing data
existing = manager.get_existing_data()
```

## File Structure

```
dsrdata/
├── main.py              # Main data extraction script
├── chart.py             # Image processing and chart generation
├── sheet.py             # Google Sheets API management
├── suburbs.csv          # Input suburbs data
├── cookies.json         # Browser cookies (not in git)
├── credentials.json     # Google OAuth credentials (not in git)
├── token.json           # Google API token (auto-generated)
├── tmp/                 # Temporary image processing
├── images/              # Final combined images
├── markets.csv          # Extracted market data
├── lookup_data.csv      # Suburb lookup data
└── README.md           # This file
```

## Security Notes

- `cookies.json` and `credentials.json` contain sensitive data
- These files are excluded from git via `.gitignore`
- Use `credentials.json.template` as a reference for setup
- Never commit authentication files to version control

## Troubleshooting

**Google Sheets API Errors:**
- Ensure Google Sheets API is enabled in your Google Cloud Console
- Check that `credentials.json` has correct OAuth2 setup
- Verify spreadsheet sharing permissions

**Rate Limiting:**
- The scripts include automatic rate limiting handling
- Use batch operations for large datasets
- Consider adding delays between requests if needed

**Cookie Authentication:**
- Export fresh cookies if login fails
- Ensure cookies are from the correct domain (dsrdata.com.au)
- Check cookie expiration dates

For detailed error messages, check the console output with colored logging indicators:
- 🟢 **[INF]** - Information
- 🟡 **[WRN]** - Warnings  
- 🔴 **[ERR]** - Errors
- 🟢 **[SUC]** - Success

---

For issues or questions, check the script output for detailed error messages.