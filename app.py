from flask import Flask, request, jsonify
import requests
import json 
from time import sleep
import urllib.parse
import datetime

app = Flask(__name__)

@app.route('/test', methods=['GET', 'POST'])
def test_endpoint():
    print('=' * 40)
    print('TEST ENDPOINT HIT!')
    print('=' * 40)
    print(f'Method: {request.method}')
    print(f'Headers: {dict(request.headers)}')
    print(f'Body: {request.get_data()}')
    return jsonify({"status": "Server is working!", "method": request.method}), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Server is running"}), 200

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def catch_all(path):
    print('=' * 60)
    print(f'CATCH-ALL ROUTE HIT: /{path}')
    print('=' * 60)
    print(f'Method: {request.method}')
    print(f'Headers: {dict(request.headers)}')
    print(f'Body: {request.get_data()}')
    return jsonify({"message": f"Received {request.method} request to /{path}"}), 200

@app.route('/trigger-script', methods=['POST'])
def trigger_script():
    try:
        print('=' * 60)
        print('INCOMING REQUEST RECEIVED!')
        print('=' * 60)
        print(f'Method: {request.method}')
        print(f'URL: {request.url}')
        print(f'Remote Address: {request.remote_addr}')
        print(f'Content Type: {request.content_type}')
        print(f'Content Length: {request.content_length}')
        print()
        
        print('ALL HEADERS:')
        for header_name, header_value in request.headers:
            print(f'  {header_name}: {header_value}')
        print()
        
        print('RAW BODY:')
        raw_body = request.get_data()
        print(f'  Body length: {len(raw_body)}')
        print(f'  Body content: {raw_body}')
        print()
        
        print('Running Zoho CRM Deal Processing...')

        # Extract data from headers instead of body
        headers = request.headers
        
        # Get all required data from headers
        deal_name = headers.get('name', '')
        deal_id = headers.get('id', '')
        deal_no = headers.get('dealno', '')
        sector = headers.get('sector', '')
        company = headers.get('company', '')
        
        print()
        print("Step 1 - Extracted Deal Data:")
        print(f"Deal Name: {deal_name}")
        print(f"Deal ID: {deal_id}")
        print(f"Deal No: {deal_no}")
        print(f"Sector: {sector}")
        print(f"Company: {company}")
        print()

        # Validate required fields
        if not all([deal_name, deal_id, deal_no, sector, company]):
            missing_fields = []
            if not deal_name: missing_fields.append('name')
            if not deal_id: missing_fields.append('id')
            if not deal_no: missing_fields.append('dealno')
            if not sector: missing_fields.append('sector')
            if not company: missing_fields.append('company')
            
            return jsonify({"error": f"Missing required headers: {', '.join(missing_fields)}"}), 400

        # Map sector names to SharePoint drive IDs
        SECTOR_DRIVES = {
            'Education': 'b!dNYn6KfbD0Ws6l-EFMOeUsNV2mYfOYhCkouRqBMJlxouK5-XNLP7Sb-Y8EcTtaV_',
            'Healthcare': 'b!dNYn6KfbD0Ws6l-EFMOeUsNV2mYfOYhCkouRqBMJlxqnDxggUT1CRIsDy0Q3njyo',
            'Oil & Gas': 'b!dNYn6KfbD0Ws6l-EFMOeUsNV2mYfOYhCkouRqBMJlxowaZxCb2drQbyajIF6qw1x',
            'IT & AV': 'b!dNYn6KfbD0Ws6l-EFMOeUsNV2mYfOYhCkouRqBMJlxq-VQoCk7fJR5cuA5Knkn75'
        }

        # Get the drive ID for the sector
        drive_id = SECTOR_DRIVES.get(sector)
        if not drive_id:
            print(f"Error: Unknown sector '{sector}'. Available sectors: {list(SECTOR_DRIVES.keys())}")
            return jsonify({"error": f"Unknown sector: {sector}"}), 400

        print(f"Step 2 - Sector Mapping: {sector} -> Drive ID: {drive_id}")

        # Azure AD Application credentials
        client_id = '02b268b9-f118-4d7c-8a87-f56853add793'
        client_secret = 'dbT8Q~DWc_fQK_NIv5A9asBEZGlHT1ht8..-hdqZ'
        tenant_id = 'b51fd322-76d3-4fe0-9e0a-40984ac1dcfd'

        # Microsoft Graph API endpoint
        graph_api_url = 'https://graph.microsoft.com/v1.0/'

        # Authenticate and get access token
        print("Step 3 - Authenticating with Microsoft Graph...")
        token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        token_response = requests.post(token_url, data=token_data)
        
        if token_response.status_code != 200:
            print(f"Authentication failed: {token_response.text}")
            return jsonify({"error": "Authentication failed"}), 500
            
        access_token = token_response.json()['access_token']
        print("Authentication successful!")

        # Create folder name: dealno + name
        folder_name = f"{deal_no} {deal_name}"
        
        # Get current year for folder organization
        today = datetime.date.today()
        year = today.year

        # Set folder location path
        folder_location = f'root:/{year}/{company}:'

        # Create the folder endpoint URL
        folder_endpoint = f'{graph_api_url}drives/{drive_id}/items/{folder_location}/children'

        print(f"Step 4 - Creating main folder: '{folder_name}'")
        print(f"Location: {folder_location}")
        print(f"Endpoint: {folder_endpoint}")

        # Define folder structure
        folder_data = {
            'name': folder_name,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'rename'
        }

        headers_auth = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Create main folder
        response = requests.post(folder_endpoint, json=folder_data, headers=headers_auth)

        if response.status_code == 201:
            print(f"Step 5 - Main folder '{folder_name}' created successfully in {company}'s folder")
            data = response.json()
            folder_id = data.get('id', '')
            access_link = data.get('webUrl', '')

            print(f"Folder ID: {folder_id}")
            print(f"Access Link: {access_link}")

            # Update folder location to point inside the newly created folder
            updated_folder_location = f'root:/{year}/{company}/{folder_name}:'
            subfolder_endpoint = f'{graph_api_url}drives/{drive_id}/items/{updated_folder_location}/children'

            print(f"Step 6 - Creating subfolders in: {updated_folder_location}")

            # Define standard subfolders
            subfolders = [
                "01 RFQ",
                "02 Vendor Quotes", 
                "03 Costing",
                "04 Customer Quotes",
                "05 Deal Files"
            ]

            # Create each subfolder
            for subfolder in subfolders:
                subfolder_data = {
                    'name': subfolder,
                    'folder': {},
                    '@microsoft.graph.conflictBehavior': 'rename'
                }
                
                subfolder_response = requests.post(subfolder_endpoint, json=subfolder_data, headers=headers_auth)
                
                if subfolder_response.status_code == 201:
                    print(f"  ✓ Created subfolder: {subfolder}")
                else:
                    print(f"  ✗ Failed to create subfolder: {subfolder} - Status: {subfolder_response.status_code}")

            print()
            print("=" * 60)
            print("DEAL PROCESSING COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"Deal No: {deal_no}")
            print(f"Deal Name: {deal_name}")
            print(f"Company: {company}")
            print(f"Sector: {sector}")
            print(f"SharePoint Folder: {folder_name}")
            print(f"Access Link: {access_link}")
            print("=" * 60)
            print()

            # Store the link for future use (not sending back to CRM as requested)
            deal_data = {
                'deal_id': deal_id,
                'deal_no': deal_no,
                'deal_name': deal_name,
                'company': company,
                'sector': sector,
                'folder_name': folder_name,
                'sharepoint_link': access_link,
                'created_date': datetime.datetime.now().isoformat()
            }

            return jsonify({
                "message": "Deal folder created successfully",
                "deal_data": deal_data
            }), 200

        else:
            error_msg = f"Failed to create main folder. Status code: {response.status_code}, Response: {response.text}"
            print(error_msg)
            return jsonify({"error": error_msg}), 500

    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500

if __name__ == '__main__':
    app.run()
