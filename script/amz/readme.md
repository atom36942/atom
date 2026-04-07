# Amazon Invoice Process Script

This is an independent FastAPI-based script designed to fetch CSV files from an SFTP server, process them, and send invoices to Amazon via an API.

## Setup Instructions

### 1. Prerequisite
Ensure you have the project's virtual environment set up in the root directory. If not, follow the main project's setup guide.

### 2. Install Dependencies
Run the following command from the project root to install the necessary libraries for this script:
```bash
./venv/bin/pip install -r script/amz/requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory (or ensure the project root's `.env` has these keys):
- `config_amazon_client_id`
- `config_amazon_client_secret`
- `config_sftp_host`
- `config_sftp_username`
- `config_sftp_password`
- `config_postgres_url`

### 4. Run the Script
To start the Amazon invoice processor, navigate to this directory and run the application:
```bash
cd script/amz
../../venv/bin/python app.py
```
By default, the script will run on **http://0.0.0.0:8000**.

## Usage
Once the script is running, you can access the following endpoints:
- `GET /`: Health check.
- `GET /mgh/amazon-invoice-send`: Trigger the invoice processing flow.
