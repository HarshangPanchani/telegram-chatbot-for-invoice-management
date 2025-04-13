
Invoice Data Extraction: When users send a PDF invoice, image file, or take a photo of an invoice, the bot automatically 
=>extracts critical information like:

  Sender (company that issued the invoice)
  Buyer (recipient of the invoice)
  Invoice number
  Date
  Total amount

=>Data Verification: After extracting information, the bot shows users what it found and asks them to confirm if the data is correct. Users can:

=>Confirm the information (which saves it to a spreadsheet)
  Edit the information if something is incorrect
  Cancel the operation

=>Document Storage: The bot uploads all invoice documents to a specified Google Drive folder, organizing them with a naming convention based on the date and sender.
=>Spreadsheet Tracking: All confirmed invoice data is stored in a Google Sheets document in a folder called "summary," making it easy for users to track and manage all their invoices in one place.
=>General AI Capabilities: Users can also send regular text messages to the bot, which will generate AI responses using Google's Gemini model.

This bot is particularly useful for businesses that need to process, organize, and track multiple invoices efficiently. It combines document management, data extraction, and record-keeping in a single tool accessible through Telegram.


Required Setup:

>Python Environment

You'll need Python 3.7+ installed
Create a virtual environment (recommended)


>Python Dependencies
Install these packages with pip:
pip install python-telegram-bot PyPDF2 pdf2image pytesseract google-api-python-client google-auth-httplib2 google-auth-oauthlib google.generativeai

>Tesseract OCR

Install Tesseract OCR on your system (required for pytesseract)
For Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
For Linux: sudo apt-get install tesseract-ocr
For macOS: brew install tesseract


>Poppler (required for pdf2image)

For Windows: Download and install from https://github.com/oschwartz10612/poppler-windows/releases/
For Linux: sudo apt-get install poppler-utils
For macOS: brew install poppler


>API Keys and Tokens
The code has several placeholders that need to be replaced with actual values:

Bot_token='telegram bot token': Replace with your Telegram Bot token (get from BotFather)
drive_folder_id = 'drive folder id': Replace with your Google Drive folder ID
service_account_file='path to service-account.-key.json': Path to your Google service account key
api_key="gemini api key": Google Gemini API key


>Google Service Account Setup

Create a Google Cloud Project
Enable Google Drive API and Google Sheets API
Create a service account with appropriate permissions
Download the JSON key file
Share the Google Drive folder with the service account email



>Configuration Steps

>Create a Telegram Bot

Open Telegram and search for BotFather (@BotFather)
Start a chat and send /newbot
Follow the instructions to create your bot
Copy the token provided and replace the placeholder in the code


>Google Cloud Setup

Go to Google Cloud Console (https://console.cloud.google.com/)
Create a new project
Enable the Drive API and Sheets API
Create a service account (IAM & Admin > Service Accounts)
Generate and download the JSON key file
Replace the service_account_file path in the code with the path to this file


>Google Drive Setup

Create a folder in your Google Drive for storing invoices
Get the folder ID (from the URL when viewing the folder)
Share the folder with the service account email (with Editor permissions)
Replace the drive_folder_id in the code


>Get Gemini API Key

Go to https://ai.google.dev/
Create an API key for Gemini
Replace the api_key placeholder in the code


>File Structure

Create a directory called asdf2 in the same directory as your script (or the code will create it for you)



>Starting the Bot
Once everything is set up, you can run the script with:
python your_script_name.py
The bot should connect to Telegram and be ready to process invoice PDFs and images. You'll be able to:

====>Send PDF invoices to the bot
====>Send images of invoices
====>Get extracted invoice data added to Google Sheets
====>Confirm or edit the extracted data via buttons in Telegram
