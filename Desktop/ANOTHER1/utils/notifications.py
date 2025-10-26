# utils/notifications.py
import os
import requests
import json
import uuid
import base64
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SMSNotificationManager:
    def __init__(self):
        self.collections_key = os.getenv("MOMO_COLLECTIONS_KEY")
        self.api_user = os.getenv("MOMO_API_USER")
        self.api_key = os.getenv("MOMO_API_KEY")
        self.base_url = "https://sandbox.momodeveloper.mtn.com"
        
    def get_access_token(self):
        """Get access token for MoMo API"""
        url = f"{self.base_url}/collection/token/"
        
        # Create basic auth credentials
        credentials = f"{self.api_user}:{self.api_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.collections_key,
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                token_data = response.json()
                logger.info("✅ Access token obtained successfully")
                return token_data.get("access_token")
            else:
                logger.error(f"❌ Failed to get access token: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting access token: {str(e)}")
            return None

    def format_phone_number(self, phone_number):
        """Format phone number to international format"""
        # Remove spaces, dashes, and other characters
        clean_number = ''.join(filter(str.isdigit, phone_number))
        
        # Handle different formats
        if clean_number.startswith('27'):
            return f"+{clean_number}"
        elif clean_number.startswith('0'):
            return f"+27{clean_number[1:]}"
        elif len(clean_number) == 9:
            return f"+27{clean_number}"
        else:
            return f"+27{clean_number}"

    def send_sms_notification(self, phone_number, message_type, **kwargs):
        """Send SMS notification for different loan events"""
        
        # Format phone number
        formatted_phone = self.format_phone_number(phone_number)
        
        # Get access token
        access_token = self.get_access_token()
        if not access_token:
            logger.error("❌ Cannot send SMS: No access token")
            return False

        # Prepare message based on type
        message = self._prepare_message(message_type, **kwargs)
        if not message:
            logger.error(f"❌ Invalid message type: {message_type}")
            return False

        # MTN MoMo SMS API endpoint (using request to pay for SMS)
        url = f"{self.base_url}/collection/v1_0/requesttopay"
        reference_id = str(uuid.uuid4())
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Reference-Id": reference_id,
            "X-Target-Environment": "sandbox",
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": self.collections_key
        }
        
        # For SMS, we use a small amount (0.01) as notification fee
        payload = {
            "amount": "0.01",
            "currency": "ZAR",
            "externalId": f"sms_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": formatted_phone.replace("+", "")
            },
            "payerMessage": message,
            "payeeNote": "CreditSwift SA Notification"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 202:
                logger.info(f"✅ SMS notification sent to {formatted_phone}")
                logger.info(f"📱 Message: {message}")
                return True
            else:
                logger.error(f"❌ Failed to send SMS: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error sending SMS: {str(e)}")
            return False

    def _prepare_message(self, message_type, **kwargs):
        """Prepare SMS message based on type"""
        
        messages = {
            "loan_approved": "🎉 LOAN APPROVED! R{amount:,.0f} disbursed to your account. Repay by {due_date}. CreditSwift SA",
            
            "loan_declined": "❌ LOAN DECLINED: {reason}. Improve your mobile money activity and reapply in 30 days. CreditSwift SA",
            
            "loan_processing": "⏳ LOAN APPLICATION: Your R{amount:,.0f} loan is being processed. Decision within 24hrs. Ref: {reference}. CreditSwift SA",
            
            "payment_due": "💰 PAYMENT DUE: R{amount:,.0f} due on {due_date}. Pay now to avoid late fees. CreditSwift SA",
            
            "payment_reminder": "⚠️ REMINDER: R{amount:,.0f} payment overdue. Pay now + R{late_fee:,.0f} late fee. CreditSwift SA",
            
            "payment_received": "✅ PAYMENT RECEIVED: R{amount:,.0f} received. Thank you! Next payment: {next_due_date}. CreditSwift SA",
            
            "loan_fully_paid": "🎉 CONGRATULATIONS! Loan fully repaid. You're eligible for a higher loan amount. Apply now! CreditSwift SA",
            
            "application_received": "📋 APPLICATION RECEIVED: Your loan application for R{amount:,.0f} is received. Decision in 24hrs. CreditSwift SA",
            
            "account_created": "👋 WELCOME to CreditSwift SA! Your account is ready. Get instant loans based on your mobile money history.",
            
            "loan_extended": "📅 LOAN EXTENDED: New due date {new_due_date}. Amount due: R{amount:,.0f}. Extension fee: R{fee:,.0f}. CreditSwift SA"
        }
        
        if message_type not in messages:
            return None
            
        try:
            return messages[message_type].format(**kwargs)
        except KeyError as e:
            logger.error(f"❌ Missing parameter for message type {message_type}: {e}")
            return None

    def send_bulk_notifications(self, recipients, message_type, **kwargs):
        """Send notifications to multiple recipients"""
        results = []
        
        for phone_number in recipients:
            success = self.send_sms_notification(phone_number, message_type, **kwargs)
            results.append({
                "phone": phone_number,
                "success": success
            })
        
        successful = sum(1 for r in results if r["success"])
        logger.info(f"📊 Bulk SMS: {successful}/{len(recipients)} sent successfully")
        
        return results

# Initialize notification manager
notification_manager = SMSNotificationManager()

# Convenient functions to use in your main app
def notify_loan_approved(phone_number, amount, due_date):
    """Send loan approval notification"""
    return notification_manager.send_sms_notification(
        phone_number, 
        "loan_approved", 
        amount=amount, 
        due_date=due_date
    )

def notify_loan_declined(phone_number, reason):
    """Send loan decline notification"""
    return notification_manager.send_sms_notification(
        phone_number, 
        "loan_declined", 
        reason=reason
    )

def notify_loan_processing(phone_number, amount, reference):
    """Send loan processing notification"""
    return notification_manager.send_sms_notification(
        phone_number, 
        "loan_processing", 
        amount=amount, 
        reference=reference
    )

def notify_payment_due(phone_number, amount, due_date):
    """Send payment due notification"""
    return notification_manager.send_sms_notification(
        phone_number, 
        "payment_due", 
        amount=amount, 
        due_date=due_date
    )

def notify_payment_received(phone_number, amount, next_due_date=None):
    """Send payment received notification"""
    return notification_manager.send_sms_notification(
        phone_number, 
        "payment_received", 
        amount=amount, 
        next_due_date=next_due_date or "N/A"
    )

def notify_application_received(phone_number, amount):
    """Send application received notification"""
    return notification_manager.send_sms_notification(
        phone_number, 
        "application_received", 
        amount=amount
    )

def test_sms_notification(phone_number):
    """Test SMS notification"""
    return notification_manager.send_sms_notification(
        phone_number, 
        "account_created"
    )