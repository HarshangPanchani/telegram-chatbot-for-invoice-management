from telegram.ext import Application,CommandHandler, ContextTypes,MessageHandler,filters,CallbackQueryHandler
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
import os
import PyPDF2
from pdf2image import convert_from_path
import logging
from datetime import datetime
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pytesseract import image_to_string
import json
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Set higher logging level for httpx to avoid excessive logs
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
Bot_token='telegram bot token'
drive_folder_id = 'drive folder id'
service_account_file='path to service-account.-key.json'
invoice_folder="summary"
invoice_file="invoices"
# columns=['sender','buyer','invoice_no','date','total_amount','filename','file_path']
columns=['sender','buyer','invoice_no','date','total_amount','filename','inserted_by']

api_key="gemini api key"
genai.configure(api_key=api_key)
modal=genai.GenerativeModel("gemini-1.5-flash")

def check_if_file_exists(service,drive_folder_id,file_name):
    query=f"name='{file_name}' and '{drive_folder_id}' in parents and trashed=false"
    results= service.files().list(q=query,spaces='drive',fields='files(id,name)').execute()
    items= results.get('files',[])
    if items:
        return items[0]['id']
    else:
        return None

def get_or_create_folder(drive_service,folder_name,parent_id=None):
    query=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    query += f" and trashed=false"
    response= drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id,name)',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    folders= response.get('files',[])
    if folders:
        # folder alreasy exists
        return folders[0]['id']
    
    folder_metadata= {
        'name':folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        folder_metadata['parents']=[parent_id]
    folder= drive_service.files().create(
        body= folder_metadata,
        fields= 'id',
        supportsAllDrives=True
    ).execute()
    folder_id= folder.get('id')
    #created folder
    return folder_id

def get_or_create_sheet(drive_service, sheet_service, spreadsheet_name,folder_id,columns):
    
    query = f"name='{spreadsheet_name}' and mimeType='application/vnd.google-apps.spreadsheet'"
    query += f" and '{folder_id}' in parents and trashed=false"
    # print(query)
    # print(folder_id)
    response= drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    spreadsheets= response.get('files',[])
    # print(len(spreadsheets))
    if spreadsheets:
        spreadsheet_id= spreadsheets[0]['id']
        # print(spreadsheet_id)
        try:
            sheet_metadata= sheet_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets= sheet_metadata.get('sheets','')
            if sheets:
                print(len(sheets))
                return spreadsheet_id
        except Exception as e:
            print(f"Error accessing existing spreadsheet: {str(e)}")
            
    # print("creating: " +spreadsheet_name)
    spreadsheet_body={
        'properties':{
            'title': spreadsheet_name
        },
        'sheets':[
            {
                'properties':{
                    'title':'Sheet1'
                }
            }
        ]
    }
    try:
        spreadsheet = sheet_service.spreadsheets().create(
            body= spreadsheet_body
        ).execute()
        spreadsheet_id= spreadsheet.get('spreadsheetId')
        # print(f"Created new spreadsheet with ID: {spreadsheet_id}")
        
        file= drive_service.files().get(
            fileId= spreadsheet_id,
            fields='parents'
        ).execute()
        previous_parents=",".join(file.get('parents',[]))
        # print(f"Moving spreadsheet from {previous_parents} to folder {folder_id}")
        drive_service.files().update(
            fileId= spreadsheet_id,
            addParents=folder_id,
            removeParents= previous_parents,
            fields= 'id, parents'
        ).execute()
        
        # print(f"Adding columns: {columns}")
        sheet_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A1',
            valueInputOption='RAW',
            body={
                'values':[columns]
            }
        ).execute()
        return spreadsheet_id
    except Exception as e:
            print(f"Error creating  spreadsheet: {str(e)}")
    
    

    
# def upload_or_update(local_file_path,drive_folder_id,service_account_file,update_if_exists=True):
#     SCOPES = ['https://www.googleapis.com/auth/drive']
#     credentials= service_account.Credentials.from_service_account_file(service_account_file,scopes=SCOPES)
#     service= build('drive','v3',credentials=credentials)
#     file_name= os.path.basename(local_file_path)
#     existing_file_id= check_if_file_exists(service,drive_folder_id,file_name)
#     media= MediaFileUpload(local_file_path,resumable=True)
#     if existing_file_id and update_if_exists:
#         file= service.files().update(
#             fileId=existing_file_id,
#             media_body= media,
#             fields='id'
#         ).execute()
        
#         return file.get('id')
#     elif not existing_file_id:
#         file_metadata={
#             'name':file_name,
#             'parents':[drive_folder_id]
#         }
#         file= service.files().create(body=file_metadata,media_body=media,fields='id').execute()
       
#         return file.get('id')
#     else:
        
#         return existing_file_id
    

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('This is gift from the legend coder to owner of vee Shores infra \n =>enter "/help" for more info \n =>enter invoice pdf')
  
async def help(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("this is chatbot from best coder ever you seen in your life \n  so here \n => enter whatever text for ai generated response \n =>enter pdf file of invoice for to enter into the specified drive folder \n if the file  already exist in folder than it only updates file \n and if file does not exists than it creates that file in google drive and add it's content according to requirement(it will extract all data from pdf whatever type text or image pdf it extraxts data and fetch it's main content with AI and than store that data  ) to invoices file in summary folder(it created both if not exists)")  

async def extract_data(update:Update,context:ContextTypes.DEFAULT_TYPE):
    user= update.message.from_user
    user_name= user.first_name
    file= update.message.document
    file_name=f"{file.file_name}"
    new_file= await context.bot.get_file(file.file_id)
    path=f"asdf2/{file.file_name}"
    os.makedirs('asdf2',exist_ok=True)
    
    await new_file.download_to_drive(path)
    try:
        local_file_path= path
        try:
            # file_id = upload_or_update(local_file_path, drive_folder_id, service_account_file)
            data=''
            with open(path,'rb') as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    
                    for page in reader.pages:
                        data+=page.extract_text()
                    if data=='':
                        images=convert_from_path(path)
                        for image in images:
                            data+= image_to_string(image)
            response2= modal.generate_content(f"fetch me Who sent it as sender,For who it is for as buyer,Invoiceno.,Date in dd/mm/yyyy format,Total amount in numbers from {data} and give response in list of string so i can access it directly in python and remember no extra text or characters only answer also no any comments and answer only in one line also write 'no val' where any of five not found but list should length of 5 and in order by [sender,buyer,Invoiceno.,Date,Total amount]")
            # response3=modal.generate_content(f'From the document data : {data}, extract the following details:'

            #         f'Sender Name – the company or person who issued the invoice. This is usually found at the top and may include a logo, address, or contact details.'

            #         f'Buyer Name – the recipient of the invoice. Often labeled as "Bill To", "Client", "Customer", or "Buyer".'

            #         f'Invoice Number – labeled as "Invoice No.", "Invoice #", "Billing Number", or similar. May appear near the date or title.'

            #         f'Invoice Date – usually labeled as "Date", "Invoice Date", "Billing Date", etc.'

            #         f'Total Amount – the final total due, often labeled as "Total", "Amount Due", "Total Due", or "Grand Total".')
            # await update.message.reply_text(response3.text) 
            await update.message.reply_text(data)
            print(response2.text)
            output_data= response2.text
            output_data= output_data.split("[")[1]
            output_data= output_data.split("]")[0]
            output_data=output_data.replace("'","")
            print(output_data)
                
            final_data=output_data.split(",")
                # print(final_data[0])
                
                

                
                # print(type(file_name))
                # final_data=output_data+[file.file_name, file_path ]
            final_data=final_data+[file_name,user_name]
                
            final_data=[item.strip() for item in final_data]
            print(str(final_data[3]))
            print(final_data)
            
            SCOPES = ['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/spreadsheets']
            credentials= service_account.Credentials.from_service_account_file(service_account_file,scopes=SCOPES)
            service= build('drive','v3',credentials=credentials)
            sheet_service=build('sheets','v4',credentials=credentials)
            # invoice_folder_id= get_or_create_folder(service,invoice_folder)
            # invoice_file_id= get_or_create_sheet(service,sheet_service,invoice_file,invoice_folder_id,columns)
            await update.message.reply_text("processing")       
            invoice_folder_id= get_or_create_folder(service,invoice_folder,drive_folder_id)
            await update.message.reply_text("processing")      
            invoice_file_id= get_or_create_sheet(service,sheet_service,invoice_file,invoice_folder_id,columns)
            
            # append_data_to
            file_name= str(final_data[3])+'_'+str(final_data[0]).replace(' ','_')+'_'+os.path.basename(local_file_path)
            existing_file_id= check_if_file_exists(service,drive_folder_id,file_name)
            update_if_exists=True
            media= MediaFileUpload(local_file_path,resumable=True)
            if existing_file_id and update_if_exists:
                file= service.files().update(
                    fileId=existing_file_id,
                    media_body= media,
                    fields='id'
                ).execute()
                await update.message.reply_text(f"✅ File successfully Updated to Drive. ID: {existing_file_id}")
                # return file.get('id')
            elif not existing_file_id:
                
                # with open(path,'rb') as pdf_file:
                #     reader = PyPDF2.PdfReader(pdf_file)
                # data=''
                # for page in reader.pages:
                #     data+=page.extract_text()
                # if data=='':
                #     images=convert_from_path(path)
                #     for image in images:
                #         data+= image_to_string(image)
                
                file_metadata={
                    'name':file_name,
                    'parents':[drive_folder_id]
                }
                file= service.files().create(body=file_metadata,media_body=media,fields='id').execute()
                # await update.message.reply_text(str(final_data))    
                context.user_data['final_data']=final_data
                context.user_data['invoice_file_id']=invoice_file_id
                context.user_data['sheet_service']=sheet_service
                # await update.message.reply_text(str(final_data))
                formatted_data = (
                    f"📄 Updated Information:\n\n"
                    f"sender: {final_data[0]}\n"
                    f"buyer: {final_data[1]}\n"
                    f"invoice_no: {final_data[2]}\n"
                    f"date: {final_data[3]}\n"
                    f"total_amount: {final_data[4]}\n"
                    f"Filename: {final_data[5]}\n"
                    f"Uploaded By: {final_data[6]}\n\n"
                    f"Is this information correct now?"
                )
                keyboard=[
                    [
                        InlineKeyboardButton("✅ Yes, Confirm",callback_data=json.dumps({"action":"Confirm"})),
                        InlineKeyboardButton("✏️ No, Edit", callback_data=json.dumps({"action":"Edit"})),
                    ],
                    [InlineKeyboardButton("❌ Cancel",callback_data=json.dumps({"action":"Cancel"}))]
                ]
                await update.message.reply_text(
                    f"sender: {final_data[0]}\n"
                    f"buyer: {final_data[1]}\n"
                    f"invoice_no: {final_data[2]}\n"
                    f"date: {final_data[3]}\n"
                    f"total_amount: {final_data[4]}\n"
                )
                reply_markup=InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(formatted_data,reply_markup=reply_markup)
                    # return {
                    # 'success': False,
                    # 'error': str(e),
                    # 'message': 'Failed to append data to sheet'
                    # }
                await update.message.reply_text(f"✅ File successfully Uploaded to Drive. ID: {file.get('id')}")
                # return file.get('id')
            else:
                # await update.message.reply_text(f"✅ File already exists to Drive. ID: {file.get('id')}")
                await update.message.reply_text(f"✅ File already exists to Drive. ")
                # return existing_file_id
                pass
            
            
            
            
            # await update.message.reply_text(f"✅ File successfully uploaded to Drive. ID: {file_id}")
        except Exception as e:
            logger.error(f"Drive upload failed: {str(e)}")
            await update.message.reply_text("❌ Failed to upload to Drive. Please try again later.")
        
        
        

        #     file_info={
        #         "name":file.file_name,
        #         "size": file.file_size,
        #         'type': file.mime_type,
        #         "id": file.file_id,
        #     }
        #     reader= PyPDF2.PdfReader(pdf_file)
        #     doc_info={}
        #     doc_info['page_count']=len(reader.pages)
            
        #     if reader.metadata:
        #         metadata= reader.metadata
            
        #         fields = [
        #                 '/Title', '/Author', '/Subject', '/Keywords', 
        #                 '/Creator', '/Producer', '/CreationDate', 
        #                 '/ModDate'
        #             ]

        #         for field in fields:
        #             value= metadata.get(field)
        #             if value:
        #                 if field in [ '/CreationDate', '/ModDate'] and isinstance(value,str) and value.startswith('D:'):
        #                     date_str= value[2:]
        #                     try:
        #                         final_date=f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}:{date_str[10:12]}:{date_str[12:14]}"
        #                         doc_info[value[1:]]= final_date
        #                     except:
        #                         doc_info[value[1:]]=value
        #                 else:
        #                     doc_info[value[1:]]=value
            
        #     response= "📄 PDF Metadata 📄\n\n"
        #     response += "📁 File Information:\n"
        #     for key,val in file_info.items():
        #         response += f"• {key}: {val}\n"
        #     response += "\n📑 Document Information:\n"
        #     if doc_info:
        #         for key,val in doc_info.items():
        #             response += f"• {key}: {val}\n"
        #     else:
        #         response += "• No document metadata found.\n"
        # await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"error : {str(e)}")
    finally:
        try:
            os.remove(path)
        except:
            pass

async def extract_image_data(update:Update,context:ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_name = user.first_name
    file = update.message.document
    file_name = f"{file.file_name}"
    new_file = await context.bot.get_file(file.file_id)
    path = f"asdf2/{file.file_name}"
    os.makedirs('asdf2', exist_ok=True)
    await new_file.download_to_drive(path)
    try:
        local_file_path= path
        try:
            # file_id = upload_or_update(local_file_path, drive_folder_id, service_account_file)
            data=''
            
            data+= image_to_string(path)
            response2= modal.generate_content(f"fetch me Who sent it as sender,For who it is for as buyer,Invoiceno.,Date in dd/mm/yyyy format,Total amount in numbers from {data} and give response in list of string so i can access it directly in python and remember no extra text or characters only answer also no any comments and answer only in one line also write 'no val' where any of five not found but list should length of 5 and in order by [sender,buyer,Invoiceno.,Date,Total amount]")
            print(response2.text)
            output_data= response2.text
            output_data= output_data.split("[")[1]
            output_data= output_data.split("]")[0]
            output_data=output_data.replace("'","")
            print(output_data)
                
            final_data=output_data.split(",")
                # print(final_data[0])
                
                

                
                # print(type(file_name))
                # final_data=output_data+[file.file_name, file_path ]
            final_data=final_data+[file_name,user_name]
                
            final_data=[item.strip() for item in final_data]
            print(str(final_data[3]))
            
            SCOPES = ['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/spreadsheets']
            credentials= service_account.Credentials.from_service_account_file(service_account_file,scopes=SCOPES)
            service= build('drive','v3',credentials=credentials)
            sheet_service=build('sheets','v4',credentials=credentials)
            # invoice_folder_id= get_or_create_folder(service,invoice_folder)
            # invoice_file_id= get_or_create_sheet(service,sheet_service,invoice_file,invoice_folder_id,columns)
            await update.message.reply_text("processing")       
            invoice_folder_id= get_or_create_folder(service,invoice_folder,drive_folder_id)
            await update.message.reply_text("processing")      
            invoice_file_id= get_or_create_sheet(service,sheet_service,invoice_file,invoice_folder_id,columns)
            
            # append_data_to
            file_name= str(final_data[3])+'_'+str(final_data[0]).replace(' ','_')+'_'+os.path.basename(local_file_path)
            existing_file_id= check_if_file_exists(service,drive_folder_id,file_name)
            update_if_exists=True
            media= MediaFileUpload(local_file_path,resumable=True)
            if existing_file_id and update_if_exists:
                file= service.files().update(
                    fileId=existing_file_id,
                    media_body= media,
                    fields='id'
                ).execute()
                await update.message.reply_text(f"✅ File successfully Updated to Drive. ID: {existing_file_id}")
                # return file.get('id')
            elif not existing_file_id:
                
                # with open(path,'rb') as pdf_file:
                #     reader = PyPDF2.PdfReader(pdf_file)
                # data=''
                # for page in reader.pages:
                #     data+=page.extract_text()
                # if data=='':
                #     images=convert_from_path(path)
                #     for image in images:
                #         data+= image_to_string(image)
                
                # print(final_data)
                file_metadata={
                    'name':file_name,
                    'parents':[drive_folder_id]
                }
                file= service.files().create(body=file_metadata,media_body=media,fields='id').execute()
                # await update.message.reply_text(str(final_data))    
                
                context.user_data['final_data']=final_data
                context.user_data['invoice_file_id']=invoice_file_id
                context.user_data['sheet_service']=sheet_service
                
                formatted_data = (
                    f"📄 Updated Information:\n\n"
                    f"sender: {final_data[0]}\n"
                    f"buyer: {final_data[1]}\n"
                    f"invoice_no: {final_data[2]}\n"
                    f"date: {final_data[3]}\n"
                    f"total_amount: {final_data[4]}\n"
                    f"Filename: {final_data[5]}\n"
                    f"Uploaded By: {final_data[6]}\n\n"
                    f"Is this information correct now?"
                )
                keyboard=[
                    [
                        InlineKeyboardButton("✅ Yes, Confirm",callback_data=json.dumps({"action":"Confirm"})),
                        InlineKeyboardButton("✏️ No, Edit", callback_data=json.dumps({"action":"Edit"})),
                    ],
                    [InlineKeyboardButton("❌ Cancel",callback_data=json.dumps({"action":"Cancel"}))]
                ]
                await update.message.reply_text(
                    f"sender: {final_data[0]}\n"
                    f"buyer: {final_data[1]}\n"
                    f"invoice_no: {final_data[2]}\n"
                    f"date: {final_data[3]}\n"
                    f"total_amount: {final_data[4]}\n"
                )
                reply_markup=InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(formatted_data,reply_markup=reply_markup)
                    # return {
                    # 'success': False,
                    # 'error': str(e),
                    # 'message': 'Failed to append data to sheet'
                    # }
                await update.message.reply_text(f"✅ File successfully Uploaded to Drive. ID: {file.get('id')}")
                # return file.get('id')
            else:
                # await update.message.reply_text(f"✅ File already exists to Drive. ID: {file.get('id')}")
                await update.message.reply_text(f"✅ File already exists to Drive. ")
                # return existing_file_id
                pass
            
            
            
            
            # await update.message.reply_text(f"✅ File successfully uploaded to Drive. ID: {file_id}")
        except Exception as e:
            logger.error(f"Drive upload failed: {str(e)}")
            await update.message.reply_text("❌ Failed to upload to Drive. Please try again later.")
        
        
        

        #     file_info={
        #         "name":file.file_name,
        #         "size": file.file_size,
        #         'type': file.mime_type,
        #         "id": file.file_id,
        #     }
        #     reader= PyPDF2.PdfReader(pdf_file)
        #     doc_info={}
        #     doc_info['page_count']=len(reader.pages)
            
        #     if reader.metadata:
        #         metadata= reader.metadata
            
        #         fields = [
        #                 '/Title', '/Author', '/Subject', '/Keywords', 
        #                 '/Creator', '/Producer', '/CreationDate', 
        #                 '/ModDate'
        #             ]

        #         for field in fields:
        #             value= metadata.get(field)
        #             if value:
        #                 if field in [ '/CreationDate', '/ModDate'] and isinstance(value,str) and value.startswith('D:'):
        #                     date_str= value[2:]
        #                     try:
        #                         final_date=f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}:{date_str[10:12]}:{date_str[12:14]}"
        #                         doc_info[value[1:]]= final_date
        #                     except:
        #                         doc_info[value[1:]]=value
        #                 else:
        #                     doc_info[value[1:]]=value
            
        #     response= "📄 PDF Metadata 📄\n\n"
        #     response += "📁 File Information:\n"
        #     for key,val in file_info.items():
        #         response += f"• {key}: {val}\n"
        #     response += "\n📑 Document Information:\n"
        #     if doc_info:
        #         for key,val in doc_info.items():
        #             response += f"• {key}: {val}\n"
        #     else:
        #         response += "• No document metadata found.\n"
        # await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"error : {str(e)}")
    finally:
        try:
            os.remove(path)
        except:
            pass
    
async def extract_photo_data(update:Update,context:ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_name = user.first_name
    photo = update.message.photo[-1]  # Get the largest available photo
    file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"  # Create a filename
    new_file = await context.bot.get_file(photo.file_id)
    path = f"asdf2/{file_name}"
    os.makedirs('asdf2', exist_ok=True)
    
    await new_file.download_to_drive(path)
    try:
        local_file_path= path
        try:
            # file_id = upload_or_update(local_file_path, drive_folder_id, service_account_file)
            data=''
            
            data+= image_to_string(path)
            response2= modal.generate_content(f"fetch me Who sent it as sender,For who it is for as buyer,Invoiceno.,Date in dd/mm/yyyy format,Total amount in numbers from {data} and give response in list of string so i can access it directly in python and remember no extra text or characters only answer also no any comments and answer only in one line also write 'no val' where any of five not found but list should length of 5 and in order by [sender,buyer,Invoiceno.,Date,Total amount]")
            print(response2.text)
            output_data= response2.text
            output_data= output_data.split("[")[1]
            output_data= output_data.split("]")[0]
            output_data=output_data.replace("'","")
            print(output_data)
                
            final_data=output_data.split(",")
                # print(final_data[0])
                
                

                
                # print(type(file_name))
                # final_data=output_data+[file.file_name, file_path ]
            final_data=final_data+[file_name,user_name]
                
            final_data=[item.strip() for item in final_data]
            print(str(final_data[3]))
            print(final_data)
            
            SCOPES = ['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/spreadsheets']
            credentials= service_account.Credentials.from_service_account_file(service_account_file,scopes=SCOPES)
            service= build('drive','v3',credentials=credentials)
            sheet_service=build('sheets','v4',credentials=credentials)
            # invoice_folder_id= get_or_create_folder(service,invoice_folder)
            # invoice_file_id= get_or_create_sheet(service,sheet_service,invoice_file,invoice_folder_id,columns)
            await update.message.reply_text("processing")       
            invoice_folder_id= get_or_create_folder(service,invoice_folder,drive_folder_id)
            await update.message.reply_text("processing")      
            invoice_file_id= get_or_create_sheet(service,sheet_service,invoice_file,invoice_folder_id,columns)
            
            # append_data_to
            file_name= str(final_data[3])+'_'+str(final_data[0]).replace(' ','_')+'_'+os.path.basename(local_file_path)
            existing_file_id= check_if_file_exists(service,drive_folder_id,file_name)
            update_if_exists=True
            media= MediaFileUpload(local_file_path,resumable=True)
            if existing_file_id and update_if_exists:
                file= service.files().update(
                    fileId=existing_file_id,
                    media_body= media,
                    fields='id'
                ).execute()
                await update.message.reply_text(f"✅ File successfully Updated to Drive. ID: {existing_file_id}")
                # return file.get('id')
            elif not existing_file_id:
                
                # with open(path,'rb') as pdf_file:
                #     reader = PyPDF2.PdfReader(pdf_file)
                # data=''
                # for page in reader.pages:
                #     data+=page.extract_text()
                # if data=='':
                #     images=convert_from_path(path)
                #     for image in images:
                #         data+= image_to_string(image)
                
                file_metadata={
                    'name':file_name,
                    'parents':[drive_folder_id]
                }
                file= service.files().create(body=file_metadata,media_body=media,fields='id').execute()
                # await update.message.reply_text(str(final_data))    
                
                context.user_data['final_data']=final_data
                context.user_data['invoice_file_id']=invoice_file_id
                context.user_data['sheet_service']=sheet_service
                
                formatted_data = (
                    f"📄 Updated Information:\n\n"
                    f"sender: {final_data[0]}\n"
                    f"buyer: {final_data[1]}\n"
                    f"invoice_no: {final_data[2]}\n"
                    f"date: {final_data[3]}\n"
                    f"total_amount: {final_data[4]}\n"
                    f"Filename: {final_data[5]}\n"
                    f"Uploaded By: {final_data[6]}\n\n"
                    f"Is this information correct now?"
                )
                keyboard=[
                    [
                        InlineKeyboardButton("✅ Yes, Confirm",callback_data=json.dumps({"action":"Confirm"})),
                        InlineKeyboardButton("✏️ No, Edit", callback_data=json.dumps({"action":"Edit"})),
                    ],
                    [InlineKeyboardButton("❌ Cancel",callback_data=json.dumps({"action":"Cancel"}))]
                ]
                await update.message.reply_text(
                    f"sender: {final_data[0]}\n"
                    f"buyer: {final_data[1]}\n"
                    f"invoice_no: {final_data[2]}\n"
                    f"date: {final_data[3]}\n"
                    f"total_amount: {final_data[4]}\n"
                )
                reply_markup=InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(formatted_data,reply_markup=reply_markup)
                
                    # return {
                    # 'success': False,
                    # 'error': str(e),
                    # 'message': 'Failed to append data to sheet'
                    # }
                await update.message.reply_text(f"✅ File successfully Uploaded to Drive. ID: {file.get('id')}")
                # return file.get('id')
            else:
                # await update.message.reply_text(f"✅ File already exists to Drive. ID: {file.get('id')}")
                await update.message.reply_text(f"✅ File already exists to Drive. ")
                # return existing_file_id
                pass
            
            
            
            
            # await update.message.reply_text(f"✅ File successfully uploaded to Drive. ID: {file_id}")
        except Exception as e:
            logger.error(f"Drive upload failed: {str(e)}")
            await update.message.reply_text("❌ Failed to upload to Drive. Please try again later.")
        
        
        

        #     file_info={
        #         "name":file.file_name,
        #         "size": file.file_size,
        #         'type': file.mime_type,
        #         "id": file.file_id,
        #     }
        #     reader= PyPDF2.PdfReader(pdf_file)
        #     doc_info={}
        #     doc_info['page_count']=len(reader.pages)
            
        #     if reader.metadata:
        #         metadata= reader.metadata
            
        #         fields = [
        #                 '/Title', '/Author', '/Subject', '/Keywords', 
        #                 '/Creator', '/Producer', '/CreationDate', 
        #                 '/ModDate'
        #             ]

        #         for field in fields:
        #             value= metadata.get(field)
        #             if value:
        #                 if field in [ '/CreationDate', '/ModDate'] and isinstance(value,str) and value.startswith('D:'):
        #                     date_str= value[2:]
        #                     try:
        #                         final_date=f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}:{date_str[10:12]}:{date_str[12:14]}"
        #                         doc_info[value[1:]]= final_date
        #                     except:
        #                         doc_info[value[1:]]=value
        #                 else:
        #                     doc_info[value[1:]]=value
            
        #     response= "📄 PDF Metadata 📄\n\n"
        #     response += "📁 File Information:\n"
        #     for key,val in file_info.items():
        #         response += f"• {key}: {val}\n"
        #     response += "\n📑 Document Information:\n"
        #     if doc_info:
        #         for key,val in doc_info.items():
        #             response += f"• {key}: {val}\n"
        #     else:
        #         response += "• No document metadata found.\n"
        # await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"error : {str(e)}")
    finally:
        try:
            os.remove(path)
        except:
            pass
    
async def handle_edited_data(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_edit',False):
        message_text = update.message.text
        lines= message_text.strip().split("\n")
        
        new_data=context.user_data.get('final_data',[])
        
        for line in lines:
            if ":" in line:
                key,val=line.split(":",1)
                key=key.strip().lower()
                val=val.strip()
                if key == 'sender':
                    new_data[0]=val
                elif key == 'buyer':
                    new_data[1]=val
                elif key == 'invoice_no':
                    new_data[2]=val
                elif key == 'date':
                    new_data[3]=val
                elif key == 'total_amount':
                    new_data[4]=val
        context.user_data['final_data']= new_data
        context.user_data['waiting_for_edit']=False
        
        formatted_data = (
            f"📄 Updated Information:\n\n"
            f"sender: {new_data[0]}\n"
            f"buyer: {new_data[1]}\n"
            f"invoice_no: {new_data[2]}\n"
            f"date: {new_data[3]}\n"
            f"total_amount: {new_data[4]}\n"
            f"Filename: {new_data[5]}\n"
            f"Uploaded By: {new_data[6]}\n\n"
            f"Is this information correct now?"
        )
        
        keyboard=[
            [
                InlineKeyboardButton("✅ Yes, Confirm",callback_data=json.dumps({"action":"Confirm"})),
                InlineKeyboardButton("✏️ No, Edit",callback_data=json.dumps({"action":"Edit"})),
                
            ],
            [InlineKeyboardButton("❌ Cancel",callback_data=json.dumps({"action":"Cancel"}))]
        ]
        reply_markup=InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            formatted_data,
            reply_markup=reply_markup
        )
    else:
        await handle_text(update,context)
                    
async def button_callback(update:Update,context:ContextTypes.DEFAULT_TYPE):
    query= update.callback_query   
    await query.answer()
    
    data= json.loads(query.data) 
    action= data.get("action")
    
    if action == "Confirm":
        final_data= context.user_data.get('final_data',[])
        invoice_file_id= context.user_data.get('invoice_file_id')
        sheet_service= context.user_data.get('sheet_service')
        try:
            result=sheet_service.spreadsheets().values().append(
                spreadsheetId=invoice_file_id,
                range='Sheet1!A1',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={
                    'values':[final_data]
                }
                        
            ).execute()
            await query.message.reply_text(str(final_data)+ "inserted")  
        except Exception as e:
            await query.message.reply_text(f"❌ File error to append data to invoices google sheet {str(e)}")
    
    elif action=="Edit":
        field_names = ['sender', 'buyer', 'invoice_no', 'date', 'total_amount']
        await query.edit_message_text(
            "Please provide corrected information in this format:\n\n"
            "sender: Company Name\n"
            "buyer: Customer Name\n"
            "invoice_no: INV-12345\n"
            "date: DD/MM/YYYY\n"
            "total_amount: 123.45\n\n"
            "Send this information as a reply."
        )
        context.user_data['waiting_for_edit']=True
        
    elif action=="Cancel":
        await query.edit_message_text("❌ Operation cancelled. Data was not saved.")
        context.user_data['waiting_for_edit']=False
            

async def handle_text(update:Update,context:ContextTypes.DEFAULT_TYPE):
    message_text= update.message.text

    response=modal.generate_content(message_text)
    response_text= response.text
    await update.message.reply_text(response_text)            
        
    

def main():
    application= Application.builder().token(Bot_token).build()
    application.add_handler(CommandHandler('start',start))
    application.add_handler(CommandHandler('help',help))
    application.add_handler(MessageHandler(filters.Document.PDF,extract_data))
    application.add_handler(MessageHandler(filters.Document.IMAGE, extract_image_data))  # Add this line
    application.add_handler(MessageHandler(filters.PHOTO, extract_photo_data))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edited_data))
    application.run_polling(allowed_updates=Update.ALL_TYPES)
if __name__ =="__main__":
    main()