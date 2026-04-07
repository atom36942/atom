# DSR Process Script

This is an independent FastAPI-based script designed to process `.eml` files and extract structured data into CSV format.

## Setup Instructions

### 1. Prerequisite
Ensure you have the project's virtual environment set up in the root directory. If not, follow the main project's setup guide.

### 2. Install Dependencies
Run the following command from the project root to install the necessary libraries for this script:
```bash
./venv/bin/pip install -r script/dsr/requirements.txt
```

### 3. Run the Script
To start the DSR processor, navigate to this directory and run the application:
```bash
cd script/dsr
../../venv/bin/python app.py
```
By default, the script will run on **http://0.0.0.0:8000**.

## Usage
Once the script is running, you can access the following endpoints:
- `GET /`: Health check.
- `POST /process`: Upload an `.eml` file to receive a processed CSV.
