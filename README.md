
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
