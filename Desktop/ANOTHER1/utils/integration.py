import os
import uuid
import requests
import base64
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MTNMoMoAPI:
    """MTN Mobile Money API integration for token management and payments"""
    
    def __init__(self, environment: str = "sandbox"):
        """
        Initialize MTN MoMo API client
        
        Args:
            environment: "sandbox" or "production"
        """
        self.environment = environment
        
        # API Configuration
        if environment == "sandbox":
            self.base_url = "https://sandbox.momodeveloper.mtn.com"
        else:
            self.base_url = "https://momodeveloper.mtn.com"
        
        # Get credentials from environment variables with fallback values
        self.subscription_key = os.getenv("MTN_MOMO_SUBSCRIPTION_KEY", "3094c764c45d4aca89f79c91a54907f9")
        self.api_user_id = os.getenv("MTN_MOMO_USER_ID", "88c9e8fc-51de-481a-83e2-ce249522c578")
        self.api_key = os.getenv("MTN_MOMO_API_KEY", "2274df75966541e88b164aaa5a179bde")

        # Validate required credentials
        if not all([self.subscription_key]):
            raise ValueError("MTN_MOMO_SUBSCRIPTION_KEY is required")
        
        # Token storage
        self.access_token = None
        self.token_expires_at = None
    
    def create_api_user(self, callback_host: str = "webhook.site") -> Dict[str, Any]:
        """
        Step 1: Create API User (Required for sandbox)
        This creates a user account for API access
        """
        try:
            # Generate a unique reference ID (this becomes your API User ID)
            reference_id = str(uuid.uuid4())
            
            url = f"{self.base_url}/v1_0/apiuser"
            headers = {
                "X-Reference-Id": reference_id,
                "Ocp-Apim-Subscription-Key": self.subscription_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "providerCallbackHost": callback_host
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                # Store the API User ID for future use
                self.api_user_id = reference_id
                logger.info(f"API User created successfully: {reference_id}")
                
                return {
                    "success": True,
                    "api_user_id": reference_id,
                    "message": "API User created successfully"
                }
            else:
                logger.error(f"Failed to create API User: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error creating API User: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_api_user_details(self, api_user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Step 2: Get API User details to retrieve API Key
        """
        try:
            user_id = api_user_id or self.api_user_id
            if not user_id:
                raise ValueError("API User ID is required")
            
            url = f"{self.base_url}/v1_0/apiuser/{user_id}"
            headers = {
                "Ocp-Apim-Subscription-Key": self.subscription_key
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Store the API key
                if "apiKey" in user_data:
                    self.api_key = user_data["apiKey"]
                
                logger.info("API User details retrieved successfully")
                return {
                    "success": True,
                    "data": user_data
                }
            else:
                logger.error(f"Failed to get API User details: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error getting API User details: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_api_key(self, api_user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Step 3: Create API Key for the API User
        """
        try:
            user_id = api_user_id or self.api_user_id
            if not user_id:
                raise ValueError("API User ID is required")
            
            url = f"{self.base_url}/v1_0/apiuser/{user_id}/apikey"
            headers = {
                "Ocp-Apim-Subscription-Key": self.subscription_key
            }
            
            response = requests.post(url, headers=headers)
            
            if response.status_code == 201:
                api_key_data = response.json()
                
                # Store the API key
                if "apiKey" in api_key_data:
                    self.api_key = api_key_data["apiKey"]
                
                logger.info("API Key created successfully")
                return {
                    "success": True,
                    "api_key": api_key_data.get("apiKey"),
                    "data": api_key_data
                }
            else:
                logger.error(f"Failed to create API Key: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error creating API Key: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_access_token(self, product_type: str = "collection") -> Dict[str, Any]:
        """
        Step 4: Generate Access Token (JWT)
        This is the main token used for API calls
        
        Args:
            product_type: "collection", "disbursement", or "remittance"
        """
        try:
            if not self.api_user_id or not self.api_key:
                raise ValueError("API User ID and API Key are required. Run setup process first.")
            
            # Check if current token is still valid
            if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
                return {
                    "success": True,
                    "access_token": self.access_token,
                    "token_type": "Bearer",
                    "expires_at": self.token_expires_at.isoformat(),
                    "cached": True
                }
            
            url = f"{self.base_url}/{product_type}/token/"
            
            # Create basic auth header
            credentials = f"{self.api_user_id}:{self.api_key}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Ocp-Apim-Subscription-Key": self.subscription_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Store token and expiration
                self.access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                logger.info("Access token generated successfully")
                return {
                    "success": True,
                    "access_token": self.access_token,
                    "token_type": token_data.get("token_type", "Bearer"),
                    "expires_in": expires_in,
                    "expires_at": self.token_expires_at.isoformat()
                }
            else:
                logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def setup_api_access(self, callback_host: str = "webhook.site") -> Dict[str, Any]:
        """
        Complete setup process: Create API User, get API Key, and generate Access Token
        Run this once for sandbox setup
        """
        try:
            # Step 1: Create API User
            user_result = self.create_api_user(callback_host)
            if not user_result["success"]:
                return user_result
            
            # Step 2: Create API Key
            key_result = self.create_api_key()
            if not key_result["success"]:
                return key_result
            
            # Step 3: Get Access Token
            token_result = self.get_access_token()
            if not token_result["success"]:
                return token_result
            
            return {
                "success": True,
                "api_user_id": self.api_user_id,
                "api_key": self.api_key,
                "access_token": self.access_token,
                "message": "API access setup completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in setup process: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_auth_headers(self, product_type: str = "collection") -> Dict[str, str]:
        """
        Get authorization headers for API calls
        Automatically refreshes token if needed
        """
        # Get valid access token
        token_result = self.get_access_token(product_type)
        if not token_result["success"]:
            raise ValueError(f"Failed to get access token: {token_result['error']}")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "X-Target-Environment": self.environment,
            "Content-Type": "application/json"
        }
    
    def request_to_pay(self, amount: float, phone_number: str, payer_message: str = "Loan payment", payee_note: str = "Loan disbursement") -> Dict[str, Any]:
        """
        Example: Request payment from customer
        """
        try:
            headers = self.get_auth_headers("collection")
            
            # Generate unique transaction ID
            reference_id = str(uuid.uuid4())
            headers["X-Reference-Id"] = reference_id
            
            url = f"{self.base_url}/collection/v1_0/requesttopay"
            
            data = {
                "amount": str(amount),
                "currency": "EUR",  # Use appropriate currency
                "externalId": reference_id,
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": phone_number
                },
                "payerMessage": payer_message,
                "payeeNote": payee_note
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 202:
                return {
                    "success": True,
                    "transaction_id": reference_id,
                    "status": "PENDING"
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error in request to pay: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def transfer_money(self, amount: float, phone_number: str, reference_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Example: Transfer money to customer (disbursement)
        """
        try:
            headers = self.get_auth_headers("disbursement")
            
            # Generate unique transaction ID
            if not reference_id:
                reference_id = str(uuid.uuid4())
            headers["X-Reference-Id"] = reference_id
            
            url = f"{self.base_url}/disbursement/v1_0/transfer"
            
            data = {
                "amount": str(amount),
                "currency": "EUR",  # Use appropriate currency
                "externalId": reference_id,
                "payee": {
                    "partyIdType": "MSISDN",
                    "partyId": phone_number
                },
                "payerMessage": "Loan disbursement",
                "payeeNote": "Your loan has been approved and disbursed"
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 202:
                return {
                    "success": True,
                    "transaction_id": reference_id,
                    "status": "PENDING"
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error in money transfer: {str(e)}")
            return {"success": False, "error": str(e)}


# Integration with your existing database
class MoMoIntegration:
    """Integration class for your micro-loans application"""
    
    def __init__(self, db_manager, environment: str = "sandbox"):
        self.db_manager = db_manager
        self.momo_api = MTNMoMoAPI(environment)
    
    def setup_momo_access(self) -> bool:
        """Setup MoMo API access (run once)"""
        result = self.momo_api.setup_api_access()
        if result["success"]:
            logger.info("MoMo API setup completed successfully")
            # You might want to store these credentials securely
            return True
        else:
            logger.error(f"MoMo API setup failed: {result['error']}")
            return False
    
    def disburse_loan(self, loan_id: str) -> Dict[str, Any]:
        """Disburse approved loan via MoMo"""
        try:
            # Get loan details from database
            loans = self.db_manager.get_loans()
            loan = next((l for l in loans if l["id"] == loan_id), None)
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            # Initiate disbursement via MoMo
            result = self.momo_api.transfer_money(
                amount=loan["amount"],
                phone_number=loan["borrower_phone"]
            )
            
            if result["success"]:
                # Record transaction in database
                transaction_data = {
                    "loan_id": loan_id,
                    "transaction_type": "disbursement",
                    "amount": loan["amount"],
                    "external_transaction_id": result["transaction_id"],
                    "provider": "mtn_momo",
                    "status": "pending",
                    "phone_number": loan["borrower_phone"]
                }
                
                transaction_id = self.db_manager.record_transaction(transaction_data)
                
                return {
                    "success": True,
                    "transaction_id": result["transaction_id"],
                    "database_transaction_id": transaction_id
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error disbursing loan: {str(e)}")
            return {"success": False, "error": str(e)}


# Create a global momo_client instance that can be imported
momo_client = MTNMoMoAPI("sandbox")

# Example usage
if __name__ == "__main__":
    # Initialize MoMo API
    momo = MTNMoMoAPI("sandbox")
    
    # Setup API access (run once)
    setup_result = momo.setup_api_access()
    print("Setup Result:", setup_result)
    
    # Get access token (for subsequent API calls)
    token_result = momo.get_access_token()
    print("Token Result:", token_result)
    
    # Example: Request payment
    if token_result["success"]:
        payment_result = momo.request_to_pay(
            amount=100.0,
            phone_number="256781234567",
            payer_message="Loan repayment"
        )
        print("Payment Result:", payment_result)