import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import requests
import hashlib
import uuid
import base64
from typing import Dict, List, Any, Optional, Tuple
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import dataclass
import random
import os
import re
import logging
import threading
import time
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(
    page_title="CreditSwift SA - AI Micro-Loans",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session State Initialization Function
def initialize_session_state():
    """Initialize all session state variables with default values"""
    default_values = {
        'credit_score': 0,
        'user_authenticated': False,
        'current_user': None,
        'loan_data': {},
        'payment_client': None,
        'analyzer': None,
        'transactions': [],
        'analysis_complete': False,
        'transaction_pattern': None,  # This was causing the NoneType error
        'risk_level': 'Unknown',
        'loan_deals': [],
        'selected_deal': None,
        'application_step': None,
        'language_select': 'en',
        'phone_input': '',
    }
    
    for key, default_value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# Notification functions
def notify_loan_approved(phone_number: str, amount: float, reference_id: str):
    """Send loan approval notification"""
    message = f"Your CreditSwift loan of R{amount:.2f} has been approved! Reference: {reference_id}"
    logger.info(f"SMS to {phone_number}: {message}")
    # Integration with actual SMS gateway would go here

def notify_loan_declined(phone_number: str, reason: str):
    """Send loan decline notification"""
    message = f"Your CreditSwift loan application was declined. Reason: {reason}"
    logger.info(f"SMS to {phone_number}: {message}")

def notify_loan_processing(phone_number: str, amount: float):
    """Send loan processing notification"""
    message = f"Your CreditSwift loan application for R{amount:.2f} is being processed."
    logger.info(f"SMS to {phone_number}: {message}")

def notify_application_received(phone_number: str):
    """Send application received notification"""
    message = "Thank you for your CreditSwift loan application. We're reviewing your request."
    logger.info(f"SMS to {phone_number}: {message}")

def test_sms_notification(phone_number: str, message: str):
    """Test SMS notification"""
    logger.info(f"Test SMS to {phone_number}: {message}")

# Token management decorator for automatic retry
def auto_retry_token(max_retries=3):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except TokenExpiredError:
                    logger.warning(f"Token expired, refreshing... (attempt {attempt + 1})")
                    self.refresh_token()
                    if attempt == max_retries - 1:
                        raise
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Request failed, retrying... (attempt {attempt + 1}): {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
            return None
        return wrapper
    return decorator

class TokenExpiredError(Exception):
    """Exception raised when API token is expired"""
    pass

class TokenManager:
    """Automatic token management with background refresh"""
    
    def __init__(self, payment_config):
        self.config = payment_config
        self.tokens = {}  # {service_type: {'token': str, 'expires': datetime}}
        self.refresh_lock = threading.Lock()
        self.auto_refresh_enabled = True
        self._start_background_refresh()
    
    def _start_background_refresh(self):
        """Start background thread for automatic token refresh"""
        def refresh_loop():
            while self.auto_refresh_enabled:
                try:
                    time.sleep(300)  # Check every 5 minutes
                    with self.refresh_lock:
                        for service_type in ['collections', 'disbursements']:
                            if self._should_refresh_token(service_type):
                                logger.info(f"Auto-refreshing token for {service_type}")
                                self._fetch_new_token(service_type)
                except Exception as e:
                    logger.error(f"Background token refresh error: {e}")
        
        refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()
    
    def _should_refresh_token(self, service_type: str) -> bool:
        """Check if token should be refreshed (expires within 10 minutes)"""
        if service_type not in self.tokens:
            return True
        
        token_info = self.tokens[service_type]
        expires_soon = datetime.now() + timedelta(minutes=10)
        return token_info['expires'] <= expires_soon
    
    def get_token(self, service_type: str = "collections") -> Optional[str]:
        """Get valid token, refreshing if necessary"""
        with self.refresh_lock:
            if self._should_refresh_token(service_type):
                token = self._fetch_new_token(service_type)
                if not token:
                    return None
            
            return self.tokens.get(service_type, {}).get('token')
    
    def _fetch_new_token(self, service_type: str) -> Optional[str]:
        """Fetch new token from API"""
        try:
            # Use the config's token fetching method
            token_data = self.config.get_access_token(service_type)
            if token_data:
                access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                
                # Store token with expiry
                self.tokens[service_type] = {
                    'token': access_token,
                    'expires': datetime.now() + timedelta(seconds=expires_in - 300)  # Refresh 5 min early
                }
                
                logger.info(f"Token refreshed successfully for {service_type}")
                return access_token
            return None
                
        except Exception as e:
            logger.error(f"Error fetching token: {e}")
            return None
    
    def is_token_valid(self, service_type: str) -> bool:
        """Check if current token is still valid"""
        if service_type not in self.tokens:
            return False
        
        token_info = self.tokens[service_type]
        return datetime.now() < token_info['expires']
    
    def force_refresh(self, service_type: str = None):
        """Force refresh of specific or all tokens"""
        with self.refresh_lock:
            if service_type:
                self._fetch_new_token(service_type)
            else:
                for st in ['collections', 'disbursements']:
                    self._fetch_new_token(st)
    
    def get_token_status(self) -> Dict:
        """Get status of all tokens"""
        status = {}
        for service_type, token_info in self.tokens.items():
            time_to_expiry = token_info['expires'] - datetime.now()
            status[service_type] = {
                'valid': time_to_expiry.total_seconds() > 0,
                'expires_in_minutes': max(0, time_to_expiry.total_seconds() / 60),
                'expires_at': token_info['expires'].strftime('%Y-%m-%d %H:%M:%S')
            }
        return status
    
    def cleanup(self):
        """Cleanup resources"""
        self.auto_refresh_enabled = False

# South African Payment Configuration
class SouthAfricaPaymentConfig:
    """Configuration for South African mobile payment systems"""
    
    def __init__(self):
        # Support multiple SA payment providers
        self.SUPPORTED_NETWORKS = {
            'vodacom': {
                'name': 'Vodacom M-Pesa',
                'prefixes': ['082', '083', '084'],
                'api_base': 'https://sandbox.safaricom.co.ke',  # Using Safaricom as example
                'currency': 'ZAR'
            },
            'mtn': {
                'name': 'MTN MoMo SA',
                'prefixes': ['078', '079'],
                'api_base': 'https://sandbox.momodeveloper.mtn.com',
                'currency': 'ZAR'
            },
            'cellc': {
                'name': 'Cell C',
                'prefixes': ['084'],
                'api_base': 'https://api.cellc.co.za',
                'currency': 'ZAR'
            },
            'telkom': {
                'name': 'Telkom Mobile',
                'prefixes': ['081'],
                'api_base': 'https://api.telkom.co.za',
                'currency': 'ZAR'
            }
        }
        
        # Load credentials from environment or session
        self.COLLECTIONS_KEY = self._get_credential("SA_COLLECTIONS_KEY", "sa_collections_key")
        self.DISBURSEMENTS_KEY = self._get_credential("SA_DISBURSEMENTS_KEY", "sa_disbursements_key")
        self.API_USER_ID = self._get_credential("SA_API_USER", "sa_api_user")
        self.API_KEY = self._get_credential("SA_API_KEY", "sa_api_key")
        
        # South African specific settings
        self.TARGET_ENVIRONMENT = "sandbox"
        self.CURRENCY = "ZAR"
        self.COUNTRY_CODE = "+27"
        
        # Compliance with South African regulations
        self.NCR_COMPLIANCE = True  # National Credit Regulator compliance
        self.POPI_ACT_COMPLIANCE = True  # Protection of Personal Information Act
        
        self._validate_credentials()
    
    def _get_credential(self, env_var: str, session_key: str) -> str:
        """Get credential from environment or session state"""
        return (os.getenv(env_var) or 
                st.session_state.get(session_key, "") or 
                "")
    
    def _validate_credentials(self):
        """Validate that required credentials are present"""
        credentials = {
            "Collections Key": self.COLLECTIONS_KEY,
            "Disbursements Key": self.DISBURSEMENTS_KEY,
            "API User ID": self.API_USER_ID,
            "API Key": self.API_KEY
        }
        
        missing = [name for name, value in credentials.items() if not value]
        if missing:
            logger.warning(f"Missing credentials: {', '.join(missing)}")
    
    def detect_network(self, phone_number: str) -> Optional[str]:
        """Detect mobile network from phone number"""
        clean_phone = phone_number.replace('+27', '').replace('-', '').replace(' ', '')
        
        for network, config in self.SUPPORTED_NETWORKS.items():
            for prefix in config['prefixes']:
                if clean_phone.startswith(prefix):
                    return network
        return None
    
    def is_configured(self) -> bool:
        """Check if all credentials are configured"""
        return all([
            self.COLLECTIONS_KEY,
            self.DISBURSEMENTS_KEY,
            self.API_USER_ID,
            self.API_KEY
        ])
    
    def get_access_token(self, service_type: str) -> Optional[Dict]:
        """Get access token for specified service"""
        try:
            # Simulate token generation (replace with actual API calls)
            return {
                "access_token": f"SA_{service_type}_{uuid.uuid4().hex[:16]}",
                "expires_in": 3600,
                "token_type": "Bearer"
            }
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None

# Language support for South Africa
LANGUAGES = {
    "en": "English",
    "af": "Afrikaans", 
    "zu": "isiZulu",
    "xh": "isiXhosa"
}

TRANSLATIONS = {
    "en": {
        "app_title": "CreditSwift SA - AI Micro-Loans",
        "tagline": "Get loans based on your mobile money history in South Africa",
        "phone_number": "Mobile Number",
        "analyze_history": "Analyze Transaction History",
        "loan_amount": "Loan Amount",
        "select_deal": "Select Your Deal",
        "apply_now": "Apply Now",
        "transaction_history": "Transaction History Analysis",
        "deals_for_you": "Deals You Qualify For",
        "repayment_options": "Repayment Options",
        "credit_score": "Credit Score",
        "monthly_income": "Estimated Monthly Income",
        "monthly_expenses": "Estimated Monthly Expenses",
        "risk_level": "Risk Level",
        "approval_probability": "Approval Probability"
    },
    "af": {
        "app_title": "CreditSwift SA - KI Mikro-lenings",
        "tagline": "Kry lenings gebaseer op jou mobiele geld geskiedenis",
        "phone_number": "Selfoon Nommer",
        "analyze_history": "Ontleed Transaksie Geskiedenis",
        "loan_amount": "Lening Bedrag",
        "select_deal": "Kies Jou Deal",
        "apply_now": "Aansoek Nou",
        "transaction_history": "Transaksie Geskiedenis Ontleding",
        "deals_for_you": "Deals Waarvoor Jy Kwalifiseer",
        "repayment_options": "Terugbetaling Opsies",
        "credit_score": "Krediet Telling",
        "monthly_income": "Beraamde Maandelikse Inkomste",
        "monthly_expenses": "Beraamde Maandelikse Uitgawes",
        "risk_level": "Risiko Vlak",
        "approval_probability": "Goedkeurings Waarskynlikheid"
    },
    "zu": {
        "app_title": "CreditSwift SA - I-AI Ama-Micro-Loans",
        "tagline": "Thola imalimboleko ngokusebenzisa umlando wakho wemali yeselula",
        "phone_number": "Inombolo Yeselula",
        "analyze_history": "Hlaziya Umlando Wokuthengiselana",
        "loan_amount": "Imali Yesikweletu",
        "select_deal": "Khetha Isivumelwano Sakho",
        "apply_now": "Faka Isicelo Manje",
        "transaction_history": "Ukuhlaziywa Komlando Wokuthengiselana",
        "deals_for_you": "Izivumelwano Ozifanelekela",
        "repayment_options": "Izinketho Zokubuyisela",
        "credit_score": "Isikolo Sokukweletwa",
        "monthly_income": "Inzuzo Enqunyiwe Yangenyanga",
        "monthly_expenses": "Izindleko Eziqokiwe Zenyanga",
        "risk_level": "Izinga Lengozi",
        "approval_probability": "Amathuba Okuvunyelwa"
    }
}

@dataclass
class LoanDeal:
    id: str
    name: str
    min_amount: float
    max_amount: float
    interest_rate: float
    term_months: int
    requirements: Dict
    description: str
    color: str
    ncr_compliant: bool = True  # NCR compliance flag

@dataclass
class TransactionPattern:
    avg_monthly_inflow: float
    avg_monthly_outflow: float
    airtime_frequency: int
    data_frequency: int
    bill_payment_consistency: float
    transaction_variety: int
    peak_balance: float
    network_provider: str

class SouthAfricaPaymentClient:
    """Enhanced payment client for South African mobile networks"""
    
    def __init__(self):
        self.config = SouthAfricaPaymentConfig()
        self.token_manager = None
        
        if self.config.is_configured():
            self.token_manager = TokenManager(self.config)
        else:
            logger.warning("Payment API not fully configured - some features may not work")
    
    def is_configured(self) -> bool:
        """Check if client is properly configured"""
        return self.config.is_configured()
    
    def get_token_status(self) -> Dict:
        """Get current token status"""
        if not self.token_manager:
            return {"error": "Token manager not initialized"}
        return self.token_manager.get_token_status()
    
    @auto_retry_token()
    def get_account_balance(self, phone_number: str) -> Optional[Dict]:
        """Get account balance for South African mobile money"""
        if not self.token_manager:
            logger.error("Token manager not initialized")
            return None
        
        try:
            network = self.config.detect_network(phone_number)
            if not network:
                logger.error(f"Unsupported network for {phone_number}")
                return None
            
            access_token = self.token_manager.get_token("collections")
            if not access_token:
                raise TokenExpiredError("Could not obtain valid token")
            
            # Simulate balance check (replace with actual API integration)
            network_config = self.config.SUPPORTED_NETWORKS[network]
            
            logger.info(f"Fetching balance for {phone_number} on {network_config['name']}")
            
            # Return simulated balance
            return {
                "availableBalance": str(random.uniform(100, 5000)),
                "currency": "ZAR",
                "network": network_config['name']
            }
                
        except TokenExpiredError:
            raise
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return None
    
    @auto_retry_token()
    def request_payment(self, amount: float, phone_number: str, description: str = "Loan repayment") -> Optional[str]:
        """Request payment from customer"""
        if not self.token_manager:
            logger.error("Token manager not initialized")
            return None
        
        try:
            network = self.config.detect_network(phone_number)
            if not network:
                return None
            
            access_token = self.token_manager.get_token("collections")
            if not access_token:
                raise TokenExpiredError("Could not obtain valid token")
            
            reference_id = str(uuid.uuid4())
            
            # Log transaction request
            logger.info(f"Requesting R{amount} payment from {phone_number} via {network}")
            
            # Return reference ID for tracking
            return reference_id
                
        except TokenExpiredError:
            raise
        except Exception as e:
            logger.error(f"Error requesting payment: {e}")
            return None
    
    @auto_retry_token()
    def transfer_money(self, amount: float, phone_number: str, description: str = "Loan disbursement") -> Optional[str]:
        """Transfer money to customer"""
        if not self.token_manager:
            logger.error("Token manager not initialized")
            return None
        
        try:
            network = self.config.detect_network(phone_number)
            if not network:
                return None
            
            access_token = self.token_manager.get_token("disbursements")
            if not access_token:
                raise TokenExpiredError("Could not obtain valid token")
            
            reference_id = str(uuid.uuid4())
            
            logger.info(f"Transferring R{amount} to {phone_number} via {network}")
            
            # Simulate successful transfer
            return reference_id
                
        except TokenExpiredError:
            raise
        except Exception as e:
            logger.error(f"Error transferring money: {e}")
            return None
    
    def get_transaction_status(self, reference_id: str, transaction_type: str = "collections") -> Optional[Dict]:
        """Get transaction status"""
        try:
            # Simulate transaction status
            statuses = ["PENDING", "SUCCESSFUL", "FAILED"]
            status = random.choice(statuses)
            
            return {
                "referenceId": reference_id,
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "currency": "ZAR"
            }
        except Exception as e:
            logger.error(f"Error getting transaction status: {e}")
            return None
    
    def cleanup(self):
        """Cleanup resources"""
        if self.token_manager:
            self.token_manager.cleanup()

class SouthAfricaMobileAnalyzer:
    """Analyze South African mobile money transaction patterns"""
    
    def __init__(self):
        self.risk_factors = {
            'transaction_frequency': 0.25,
            'balance_consistency': 0.20,
            'bill_payment_history': 0.25,
            'income_stability': 0.30
        }
        self.payment_client = SouthAfricaPaymentClient()
    
    def fetch_real_transaction_data(self, phone_number: str) -> List[Dict]:
        """Fetch transaction data for South African networks"""
        return self.generate_sa_sample_transactions(phone_number)
    
    def generate_sa_sample_transactions(self, phone_number: str, months: int = 6) -> List[Dict]:
        """Generate realistic sample transaction data for South African users"""
        transactions = []
        network = self.payment_client.config.detect_network(phone_number) or "vodacom"
        
        # Base values based on network (different spending patterns)
        base_values = {
            "vodacom": {"income": 8500, "spending": 7200, "frequency": 22},
            "mtn": {"income": 7800, "spending": 6500, "frequency": 25},
            "cellc": {"income": 6500, "spending": 5800, "frequency": 18},
            "telkom": {"income": 7200, "spending": 6100, "frequency": 20}
        }
        
        base = base_values.get(network, base_values["vodacom"])
        
        # Generate transactions for the past 6 months
        for month in range(months):
            month_date = datetime.now() - timedelta(days=30 * (month + 1))
            
            # Salary deposits (1-3 per month)
            salary_count = random.randint(1, 3)
            for i in range(salary_count):
                salary_amount = base["income"] * random.uniform(0.8, 1.2) / salary_count
                transactions.append({
                    "date": (month_date - timedelta(days=random.randint(0, 7))).strftime("%Y-%m-%d"),
                    "type": "DEPOSIT",
                    "amount": round(salary_amount, 2),
                    "description": "Salary deposit",
                    "balance": round(random.uniform(1000, 5000), 2)
                })
            
            # Regular bills (5-8 per month)
            bill_types = ["Electricity", "Water", "Rent", "DSTV", "Insurance", "Loan repayment"]
            bill_count = random.randint(5, 8)
            for i in range(bill_count):
                bill_amount = random.uniform(150, 800)
                transactions.append({
                    "date": (month_date + timedelta(days=random.randint(8, 28))).strftime("%Y-%m-%d"),
                    "type": "WITHDRAWAL",
                    "amount": round(bill_amount, 2),
                    "description": f"{random.choice(bill_types)} payment",
                    "balance": round(random.uniform(500, 3000), 2)
                })
            
            # Airtime and data purchases (8-15 per month)
            airtime_count = random.randint(8, 15)
            for i in range(airtime_count):
                airtime_amount = random.choice([10, 20, 50, 100, 200])
                transactions.append({
                    "date": (month_date + timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
                    "type": "WITHDRAWAL",
                    "amount": airtime_amount,
                    "description": "Airtime purchase",
                    "balance": round(random.uniform(100, 2000), 2)
                })
            
            # Retail purchases (10-20 per month)
            retail_count = random.randint(10, 20)
            retailers = ["Shoprite", "Pick n Pay", "Checkers", "Woolworths", "SPAR", "OK Foods"]
            for i in range(retail_count):
                retail_amount = random.uniform(50, 500)
                transactions.append({
                    "date": (month_date + timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
                    "type": "WITHDRAWAL",
                    "amount": round(retail_amount, 2),
                    "description": f"Purchase at {random.choice(retailers)}",
                    "balance": round(random.uniform(100, 2500), 2)
                })
        
        # Sort by date
        transactions.sort(key=lambda x: x["date"])
        return transactions
    
    def analyze_transaction_pattern(self, transactions: List[Dict]) -> TransactionPattern:
        """Analyze transaction patterns to determine financial behavior"""
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M')
        
        # Calculate monthly inflows and outflows
        monthly_inflows = df[df['type'] == 'DEPOSIT'].groupby('month')['amount'].sum()
        monthly_outflows = df[df['type'] == 'WITHDRAWAL'].groupby('month')['amount'].sum()
        
        # Calculate frequencies
        airtime_frequency = len(df[df['description'].str.contains('Airtime', case=False)])
        data_frequency = len(df[df['description'].str.contains('Data', case=False)])
        
        # Calculate bill payment consistency
        bill_payments = df[df['description'].str.contains('payment', case=False)]
        bill_consistency = bill_payments.groupby('month').size().std()
        bill_consistency = 1 - min(bill_consistency / 10, 1) if bill_consistency > 0 else 1
        
        # Transaction variety (number of unique descriptors)
        transaction_variety = df['description'].nunique()
        
        # Peak balance
        peak_balance = df['balance'].max()
        
        # Detect network provider from phone number if available
        network_provider = "unknown"
        
        return TransactionPattern(
            avg_monthly_inflow=monthly_inflows.mean() if not monthly_inflows.empty else 0,
            avg_monthly_outflow=monthly_outflows.mean() if not monthly_outflows.empty else 0,
            airtime_frequency=airtime_frequency,
            data_frequency=data_frequency,
            bill_payment_consistency=bill_consistency,
            transaction_variety=transaction_variety,
            peak_balance=peak_balance,
            network_provider=network_provider
        )
    
    def calculate_credit_score(self, pattern: TransactionPattern) -> Tuple[float, str]:
        """Calculate credit score based on transaction patterns"""
        score = 0
        
        # Income stability (30% of score)
        if pattern.avg_monthly_inflow > 0:
            income_stability = min(pattern.avg_monthly_inflow / 10000, 1.5)  # Cap at 1.5 for high incomes
            score += income_stability * 300  # 300 points max
        
        # Spending consistency (25% of score)
        if pattern.avg_monthly_outflow > 0:
            savings_ratio = max(0, (pattern.avg_monthly_inflow - pattern.avg_monthly_outflow) / pattern.avg_monthly_inflow)
            score += savings_ratio * 250  # 250 points max
        
        # Bill payment consistency (25% of score)
        score += pattern.bill_payment_consistency * 250  # 250 points max
        
        # Transaction diversity (20% of score)
        diversity_score = min(pattern.transaction_variety / 20, 1)  # More diverse is better
        score += diversity_score * 200  # 200 points max
        
        # Cap at 850 (common credit score max)
        score = min(score, 850)
        
        # Determine risk level
        if score >= 700:
            risk_level = "Low"
        elif score >= 550:
            risk_level = "Medium"
        else:
            risk_level = "High"
        
        return score, risk_level
    
    def generate_loan_deals(self, credit_score: float, monthly_income: float) -> List[LoanDeal]:
        """Generate personalized loan deals based on credit assessment"""
        deals = []
        
        # Basic Loan (available to most users)
        if credit_score >= 400:
            deals.append(LoanDeal(
                id="basic",
                name="Basic Loan",
                min_amount=500,
                max_amount=min(5000, monthly_income * 0.5),
                interest_rate=0.15,
                term_months=6,
                requirements={"min_score": 400, "min_income": 2000},
                description="Our most accessible loan with competitive rates",
                color="#4CAF50",
                ncr_compliant=True
            ))
        
        # Premium Loan (for good credit)
        if credit_score >= 600:
            deals.append(LoanDeal(
                id="premium",
                name="Premium Loan",
                min_amount=1000,
                max_amount=min(15000, monthly_income * 1.0),
                interest_rate=0.12,
                term_months=12,
                requirements={"min_score": 600, "min_income": 5000},
                description="Lower rates for customers with good financial history",
                color="#2196F3",
                ncr_compliant=True
            ))
        
        # Emergency Loan (small, short-term)
        deals.append(LoanDeal(
            id="emergency",
            name="Emergency Loan",
            min_amount=200,
            max_amount=1000,
            interest_rate=0.20,
            term_months=3,
            requirements={"min_score": 300, "min_income": 1000},
            description="Small, short-term loan for urgent needs",
            color="#FF9800",
            ncr_compliant=True
        ))
        
        # Business Loan (for higher incomes)
        if monthly_income >= 8000 and credit_score >= 550:
            deals.append(LoanDeal(
                id="business",
                name="Business Loan",
                min_amount=5000,
                max_amount=min(30000, monthly_income * 1.5),
                interest_rate=0.10,
                term_months=24,
                requirements={"min_score": 550, "min_income": 8000},
                description="For entrepreneurs and small business owners",
                color="#9C27B0",
                ncr_compliant=True
            ))
        
        return deals

# Streamlit UI Components
def render_sidebar():
    """Render the sidebar with language selection and settings"""
    with st.sidebar:
        st.title("CreditSwift SA")
        st.markdown("### Settings")
        
        # Language selection
        language = st.selectbox(
            "Language",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: LANGUAGES[x],
            key="language_select"
        )
        
        # API configuration (for admin use)
        if st.checkbox("Show API Settings", False):
            st.subheader("API Configuration")
            st.text_input("Collections Key", value="", key="sa_collections_key", type="password")
            st.text_input("Disbursements Key", value="", key="sa_disbursements_key", type="password")
            st.text_input("API User ID", value="", key="sa_api_user")
            st.text_input("API Key", value="", key="sa_api_key", type="password")
        
        # Display token status if configured
        if st.session_state.get("payment_client") and st.session_state.payment_client.is_configured():
            st.subheader("API Status")
            token_status = st.session_state.payment_client.get_token_status()
            for service, status in token_status.items():
                st.write(f"{service.upper()}: {'✅' if status['valid'] else '❌'} "
                         f"({status['expires_in_minutes']:.1f}m remaining)")
        
        st.markdown("---")
        st.markdown("### About")
        st.info("""
        CreditSwift SA provides instant micro-loans based on your mobile money transaction history.
        We're compliant with South Africa's NCR regulations and POPI Act.
        """)

def render_main_content():
    """Render the main content of the application"""
    lang = st.session_state.get("language_select", "en")
    t = TRANSLATIONS[lang]
    
    st.title(t["app_title"])
    st.markdown(f"*{t['tagline']}*")
    
    # Initialize session state variables
    if "payment_client" not in st.session_state:
        st.session_state.payment_client = SouthAfricaPaymentClient()
    
    if "analyzer" not in st.session_state:
        st.session_state.analyzer = SouthAfricaMobileAnalyzer()
    
    if "transactions" not in st.session_state:
        st.session_state.transactions = []
    
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    
    # Phone number input
    st.subheader(t["phone_number"])
    phone_number = st.text_input(
        "Enter your South African mobile number:",
        placeholder="e.g., 0821234567",
        key="phone_input"
    )
    
    # Validate phone number
    if phone_number:
        # Clean the phone number
        clean_phone = re.sub(r'[^0-9]', '', phone_number)
        if len(clean_phone) == 9 and clean_phone.startswith('0'):
            clean_phone = '27' + clean_phone[1:]
        
        # Detect network
        network = st.session_state.payment_client.config.detect_network(clean_phone)
        if network:
            network_name = st.session_state.payment_client.config.SUPPORTED_NETWORKS[network]['name']
            st.success(f"Detected: {network_name}")
            
            # Check balance button
            if st.button("Check Balance"):
                with st.spinner("Checking account balance..."):
                    balance_info = st.session_state.payment_client.get_account_balance(clean_phone)
                    if balance_info:
                        st.info(f"Available Balance: R{float(balance_info['availableBalance']):.2f}")
                    else:
                        st.error("Could not retrieve balance. Please try again.")
            
            # Analyze transactions button
            if st.button(t["analyze_history"]):
                with st.spinner("Analyzing your transaction history..."):
                    # Fetch and analyze transactions
                    st.session_state.transactions = st.session_state.analyzer.fetch_real_transaction_data(clean_phone)
                    st.session_state.transaction_pattern = st.session_state.analyzer.analyze_transaction_pattern(
                        st.session_state.transactions
                    )
                    st.session_state.credit_score, st.session_state.risk_level = st.session_state.analyzer.calculate_credit_score(
                        st.session_state.transaction_pattern
                    )
                    st.session_state.loan_deals = st.session_state.analyzer.generate_loan_deals(
                        st.session_state.credit_score,
                        st.session_state.transaction_pattern.avg_monthly_inflow
                    )
                    st.session_state.analysis_complete = True
                    
                    # Send notification
                    notify_application_received(clean_phone)
        
        else:
            st.error("Please enter a valid South African mobile number")
    
    # Display analysis results if available
    if st.session_state.analysis_complete:
        st.markdown("---")
        st.subheader(t["transaction_history"])
        
        # Create metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(t["credit_score"], f"{st.session_state.credit_score:.0f}")
        with col2:
            st.metric(t["monthly_income"], f"R{st.session_state.transaction_pattern.avg_monthly_inflow:.2f}")
        with col3:
            st.metric(t["monthly_expenses"], f"R{st.session_state.transaction_pattern.avg_monthly_outflow:.2f}")
        with col4:
            st.metric(t["risk_level"], st.session_state.risk_level)
        
        # Display transaction history chart
        if st.session_state.transactions:
            df = pd.DataFrame(st.session_state.transactions)
            df['date'] = pd.to_datetime(df['date'])
            
            # Create a time series chart
            fig = px.line(df, x='date', y='balance', title='Account Balance Over Time')
            st.plotly_chart(fig, use_container_width=True)
            
            # Show transaction table
            if st.checkbox("Show Transaction Details"):
                st.dataframe(df[['date', 'type', 'amount', 'description', 'balance']])
        
        # Display loan deals
        st.subheader(t["deals_for_you"])
        for deal in st.session_state.loan_deals:
            with st.expander(f"{deal.name} - Up to R{deal.max_amount:.2f}"):
                st.markdown(f"**{deal.description}**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Amount:** R{deal.min_amount:.2f} - R{deal.max_amount:.2f}")
                with col2:
                    st.markdown(f"**Interest Rate:** {deal.interest_rate*100:.1f}%")
                with col3:
                    st.markdown(f"**Term:** {deal.term_months} months")
                
                # Calculate example repayment
                example_amount = deal.min_amount + (deal.max_amount - deal.min_amount) / 2
                monthly_repayment = example_amount * (1 + deal.interest_rate) / deal.term_months
                
                st.markdown(f"Example: R{example_amount:.2f} loan = R{monthly_repayment:.2f}/month")
                
                # Apply button
                if st.button(f"Apply for {deal.name}", key=f"apply_{deal.id}"):
                    st.session_state.selected_deal = deal
                    st.session_state.application_step = "deal_selected"
                    notify_loan_processing(clean_phone, example_amount)
        
        # Deal application process
        if st.session_state.get("application_step") == "deal_selected":
            deal = st.session_state.selected_deal
            st.subheader(f"Apply for {deal.name}")
            
            # Loan amount slider
            loan_amount = st.slider(
                t["loan_amount"],
                min_value=float(deal.min_amount),
                max_value=float(deal.max_amount),
                value=float(deal.min_amount + (deal.max_amount - deal.min_amount) / 2),
                step=100.0
            )
            
            # Personal details
            st.markdown("### Personal Information")
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name")
                id_number = st.text_input("South African ID Number")
            with col2:
                last_name = st.text_input("Last Name")
                email = st.text_input("Email Address")
            
            # Terms acceptance
            terms_accepted = st.checkbox("I accept the terms and conditions")
            ncr_disclosure = st.checkbox("I acknowledge the NCR cost of credit disclosure")
            
            # Submit application
            if st.button("Submit Application"):
                if not all([first_name, last_name, id_number, email]):
                    st.error("Please fill in all required fields")
                elif not terms_accepted or not ncr_disclosure:
                    st.error("Please accept all disclosures and terms")
                else:
                    # Process application
                    with st.spinner("Processing your application..."):
                        # Simulate approval process (80% approval rate for demo)
                        approved = random.random() > 0.2
                        
                        if approved:
                            # Disburse funds
                            reference_id = st.session_state.payment_client.transfer_money(
                                loan_amount, clean_phone, f"{deal.name} loan disbursement"
                            )
                            
                            if reference_id:
                                st.success("🎉 Your loan has been approved!")
                                st.info(f"R{loan_amount:.2f} will be disbursed to your account shortly. Reference: {reference_id}")
                                
                                # Send notification
                                notify_loan_approved(clean_phone, loan_amount, reference_id)
                                
                                # Show repayment schedule
                                st.subheader(t["repayment_options"])
                                monthly_rate = deal.interest_rate / 12
                                monthly_payment = loan_amount * monthly_rate * (1 + monthly_rate)**deal.term_months / ((1 + monthly_rate)**deal.term_months - 1)
                                
                                st.write(f"Monthly repayment: R{monthly_payment:.2f} for {deal.term_months} months")
                                
                                # Create repayment table
                                repayment_data = []
                                balance = loan_amount
                                for month in range(1, deal.term_months + 1):
                                    interest = balance * monthly_rate
                                    principal = monthly_payment - interest
                                    balance -= principal
                                    repayment_data.append({
                                        "Month": month,
                                        "Payment": round(monthly_payment, 2),
                                        "Principal": round(principal, 2),
                                        "Interest": round(interest, 2),
                                        "Balance": round(max(0, balance), 2)
                                    })
                                
                                st.dataframe(pd.DataFrame(repayment_data))
                            else:
                                st.error("Failed to process disbursement. Please try again.")
                        else:
                            st.error("❌ Your application was not approved at this time.")
                            decline_reasons = [
                                "Insufficient transaction history",
                                "High debt-to-income ratio",
                                "Inconsistent repayment history"
                            ]
                            st.write(f"Reason: {random.choice(decline_reasons)}")
                            
                            # Send notification
                            notify_loan_declined(clean_phone, "Application did not meet criteria")

def main():
    """Main application function"""
    # Initialize session state first
    initialize_session_state()
    
    # Then render the UI components
    render_sidebar()
    render_main_content()

if __name__ == "__main__":
    main()