from flask import Flask, request, jsonify
import requests
import json 
from time import sleep
import urllib.parse
import datetime

app = Flask(__name__)

# Zoho CRM API Configuration
ZOHO_CONFIG = {
    'client_id': '1000.WE5EP9UR6A7UIRWI916QV6254LU94G',
    'client_secret': '048691d4c42f1e1ac99ba1738f1878a4eb7a15040e',
    'refresh_token': '1000.1f5e1853261e7f03aa04da2a1e16a87c.45e726b663cc2117db19906cd4b2f4cc',
    'base_url': 'https://www.zohoapis.in/crm/v2/',
    'accounts_url': 'https://accounts.zoho.in'
}

def get_zoho_access_token():
    """Get fresh access token using refresh token"""
    try:
        token_url = f"{ZOHO_CONFIG['accounts_url']}/oauth/v2/token"
        
        data = {
            'refresh_token': ZOHO_CONFIG['refresh_token'],
            'client_id': ZOHO_CONFIG['client_id'],
            'client_secret': ZOHO_CONFIG['client_secret'],
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token')
        else:
            print(f"Failed to get access token: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error getting access token: {str(e)}")
        return None

def update_deal_in_zoho(deal_id, sharepoint_url):
    """Update deal in Zoho CRM with SharePoint URL"""
    try:
        access_token = get_zoho_access_token()
        if not access_token:
            return False
            
        # Zoho CRM API endpoint for updating deals
        update_url = f"{ZOHO_CONFIG['base_url']}Deals/{deal_id}"
        
        headers = {
            'Authorization': f'Zoho-oauthtoken {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Update data - using your Sharepoint_URL field
        data = {
            "data": [
                {
                    "Sharepoint_URL": sharepoint_url
                }
            ]
        }
        
        response = requests.put(update_url, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"Successfully updated deal {deal_id} with SharePoint URL")
            return True
        else:
            print(f"Failed to update deal: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error updating deal in Zoho: {str(e)}")
        return False

@app.route('/callback', methods=['GET'])
def oauth_callback():
    """Handle OAuth callback from Zoho"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return f"<h1>Authorization Error</h1><p>{error}</p>", 400
    
    if code:
        return f"""
        <h1>Authorization Successful!</h1>
        <p><strong>Your authorization code is:</strong></p>
        <code style="background: #f0f0f0; padding: 10px; display: block; margin: 10px 0;">{code}</code>
        <p>Copy this code and paste it into your token generator script.</p>
        """
    
    return "<h1>No authorization code received</h1>", 400

@app.route('/test-zoho', methods=['GET'])
def test_zoho():
    """Test Zoho CRM API connection"""
    access_token = get_zoho_access_token()
    if access_token:
        return jsonify({"message": "Zoho API connection successful!", "token": access_token[:20] + "..."}), 200
    else:
        return jsonify({"error": "Failed to connect to Zoho API"}), 500

@app.route('/test', methods=['GET', 'POST'])
def test():
    return jsonify({"message": "Server is working!", "method": request.method}), 200

@app.route('/trigger-script', methods=['POST'])
def trigger_script():
    try:
        print('=== WEBHOOK RECEIVED ===')
        print(f'Method: {request.method}')
        print(f'Headers: {dict(request.headers)}')
        print(f'Body: {request.get_data()}')
        print('========================')
        
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

            # Update deal in Zoho CRM with SharePoint URL
            print(f"Step 7 - Updating deal {deal_id} in Zoho CRM...")
            sleep(2)  # Wait a moment for folder creation to complete
            
            zoho_update_success = update_deal_in_zoho(deal_id, access_link)
            
            if zoho_update_success:
                print(f"✓ Successfully updated Zoho CRM deal with SharePoint URL")
            else:
                print(f"✗ Failed to update Zoho CRM deal - but folder was created successfully")

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
    app.run(host='0.0.0.0', port=9852, debug=True)
