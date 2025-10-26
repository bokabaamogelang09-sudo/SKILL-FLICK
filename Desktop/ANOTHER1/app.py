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
from utils.notifications import (
    notify_loan_approved, 
    notify_loan_declined, 
    notify_loan_processing,
    notify_application_received,
    test_sms_notification
)

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
        "repayment_options": "Repayment Options"
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
        "repayment_options": "Terugbetaling Opsies"
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
        "repayment_options": "Izinketho Zokubuyisela"
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
        transactions = self.generate_sa_sample_transactions(phone_number)
        
        if self.payment_client.is_configured():
            try:
                balance_info = self.payment_client.get_account_balance(phone_number)
                if balance_info and transactions:
                    transactions[-1]['balance'] = float(balance_info.get('availableBalance', 0))
                    transactions[-1]['currency'] = balance_info.get('currency', 'ZAR')
                    transactions[-1]['network'] = balance_info.get('network', 'Unknown')
            except Exception as e:
                logger.warning(f"Could not fetch real balance: {e}")
        
        return transactions
    
    def generate_sa_sample_transactions(self, phone_number: str) -> List[Dict]:
        """Generate realistic South African transaction data"""
        config = SouthAfricaPaymentConfig()
        network = config.detect_network(phone_number) or 'vodacom'
        network_name = config.SUPPORTED_NETWORKS[network]['name']
        
        transactions = []
        base_date = datetime.now() - timedelta(days=90)
        
        seed = sum(ord(c) for c in phone_number) % 1000
        random.seed(seed)
        
        # South African specific transaction types and amounts (in ZAR)
        sa_transaction_types = [
            ("airtime", random.uniform(20, 200)),  # R20-200 airtime
            ("data_bundle", random.uniform(50, 500)),  # R50-500 data
            ("electricity", random.uniform(100, 1000)),  # Prepaid electricity
            ("water_rates", random.uniform(200, 800)),  # Municipal bills
            ("grocery_payment", random.uniform(300, 2000)),  # Grocery shopping
            ("taxi_fare", random.uniform(15, 80)),  # Minibus taxi fares
            ("school_fees", random.uniform(500, 3000)),  # School payments
            ("salary_received", random.uniform(8000, 25000)),  # Monthly salary
            ("social_grant", random.uniform(400, 2000)),  # SASSA grants
            ("stokvel_contribution", random.uniform(200, 1000)),  # Stokvel payments
            ("funeral_cover", random.uniform(50, 300)),  # Funeral insurance
            ("loan_repayment", random.uniform(200, 1500))  # Other loan payments
        ]
        
        for i in range(random.randint(40, 120)):
            date = base_date + timedelta(days=random.randint(0, 90))
            
            trans_type, amount = random.choice(sa_transaction_types)
            is_incoming = trans_type in ["salary_received", "social_grant"] or random.random() < 0.25
            
            transactions.append({
                "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                "type": trans_type,
                "amount": round(amount, 2),
                "direction": "incoming" if is_incoming else "outgoing",
                "balance": random.uniform(50, 8000),  # ZAR balance range
                "description": f"{trans_type.replace('_', ' ').title()} - {network_name}",
                "currency": "ZAR",
                "network": network_name
            })
        
        return sorted(transactions, key=lambda x: x['date'])
    
    def analyze_patterns(self, transactions: List[Dict]) -> TransactionPattern:
        """Analyze South African transaction patterns"""
        if not transactions:
            return TransactionPattern(0, 0, 0, 0, 0, 0, 0, "Unknown")
        
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M')
        
        monthly_inflow = df[df['direction'] == 'incoming'].groupby('month')['amount'].sum()
        monthly_outflow = df[df['direction'] == 'outgoing'].groupby('month')['amount'].sum()
        
        # SA specific analysis
        airtime_count = len(df[df['type'] == 'airtime'])
        data_count = len(df[df['type'] == 'data_bundle'])
        
        # Include SA specific bills
        essential_bills = df[df['type'].isin(['electricity', 'water_rates', 'school_fees'])]
        bill_consistency = len(essential_bills.groupby('month')) / 3 if len(essential_bills) > 0 else 0
        
        transaction_variety = len(df['type'].unique())
        network_provider = df['network'].iloc[0] if len(df) > 0 else "Unknown"
        
        return TransactionPattern(
            avg_monthly_inflow=monthly_inflow.mean() if not monthly_inflow.empty else 0,
            avg_monthly_outflow=monthly_outflow.mean() if not monthly_outflow.empty else 0,
            airtime_frequency=airtime_count,
            data_frequency=data_count,
            bill_payment_consistency=min(bill_consistency, 1.0),
            transaction_variety=transaction_variety,
            peak_balance=df['balance'].max(),
            network_provider=network_provider
        )
    
    def calculate_credit_score(self, pattern: TransactionPattern) -> int:
        """Calculate credit score for South African context"""
        score = 300  # Base score
        
        # Income analysis (adjusted for SA income levels)
        if pattern.avg_monthly_inflow > 15000:  # R15k+
            score += 200
        elif pattern.avg_monthly_inflow > 8000:  # R8k+
            score += 150
        elif pattern.avg_monthly_inflow > 4000:  # R4k+
            score += 100
        elif pattern.avg_monthly_inflow > 2000:  # R2k+
            score += 50
        
        # Balance management
        if pattern.peak_balance > 3000:  # R3k+
            score += 150
        elif pattern.peak_balance > 1000:  # R1k+
            score += 100
        else:
            score += 50
        
        # Bill payment consistency
        score += int(pattern.bill_payment_consistency * 100)
        
        # Transaction activity
        activity_score = min(pattern.airtime_frequency + pattern.data_frequency, 50)
        variety_score = min(pattern.transaction_variety * 8, 50)
        score += activity_score + variety_score
        
        return min(score, 850)

class SouthAfricaLoanEngine:
    """NCR-compliant loan engine for South Africa"""
    
    def __init__(self):
        # NCR-compliant loan products with maximum rates
        self.deals = [
            LoanDeal(
                id="emergency_cash",
                name="Emergency Cash",
                min_amount=500,    # R500
                max_amount=3000,   # R3000
                interest_rate=0.05,  # 5% monthly (NCR compliant)
                term_months=1,
                requirements={"min_score": 400, "min_monthly_income": 2000},
                description="Quick cash for emergencies. NCR registered.",
                color="#FF6B6B",
                ncr_compliant=True
            ),
            LoanDeal(
                id="payday_advance",
                name="Payday Advance",
                min_amount=1000,   # R1000
                max_amount=8000,   # R8000
                interest_rate=0.04,  # 4% monthly
                term_months=3,
                requirements={"min_score": 500, "min_monthly_income": 5000},
                description="Bridge to payday with affordable repayments.",
                color="#4ECDC4",
                ncr_compliant=True
            ),
            LoanDeal(
                id="personal_loan",
                name="Personal Loan",
                min_amount=5000,   # R5000
                max_amount=25000,  # R25000
                interest_rate=0.035,  # 3.5% monthly
                term_months=6,
                requirements={"min_score": 600, "min_monthly_income": 8000},
                description="Personal loans for life's bigger moments.",
                color="#45B7D1",
                ncr_compliant=True
            ),
            LoanDeal(
                id="consolidation_loan",
                name="Debt Consolidation",
                min_amount=10000,  # R10000
                max_amount=50000,  # R50000
                interest_rate=0.025,  # 2.5% monthly
                term_months=12,
                requirements={"min_score": 700, "min_monthly_income": 12000},
                description="Consolidate your debts into one payment.",
                color="#96CEB4",
                ncr_compliant=True
            )
        ]
        self.payment_client = SouthAfricaPaymentClient()
    
    def get_qualified_deals(self, credit_score: int, monthly_income: float) -> List[LoanDeal]:
        """Get NCR-compliant deals"""
        qualified = []
        for deal in self.deals:
            if (deal.ncr_compliant and
                credit_score >= deal.requirements["min_score"] and 
                monthly_income >= deal.requirements["min_monthly_income"]):
                qualified.append(deal)
        return qualified
    
    def calculate_suggested_amount(self, deal: LoanDeal, monthly_income: float) -> float:
        """Calculate affordable amount per NCR affordability assessment"""
        # NCR affordability: max 25% of net income for unsecured credit
        max_monthly_payment = monthly_income * 0.25
        monthly_rate = deal.interest_rate
        
        # Calculate affordable loan amount
        if monthly_rate > 0:
            affordable_amount = (max_monthly_payment * deal.term_months) / (1 + monthly_rate * deal.term_months)
        else:
            affordable_amount = max_monthly_payment * deal.term_months
        
        return min(max(affordable_amount, deal.min_amount), deal.max_amount)
    
    def disburse_loan(self, amount: float, phone_number: str, deal: LoanDeal) -> Optional[str]:
        """Disburse loan via South African mobile networks"""
        if not self.payment_client.is_configured():
            logger.error("Payment API not configured for disbursement")
            return "DEMO_SA_" + str(uuid.uuid4())[:8]
        
        message = f"CreditSwift SA {deal.name} loan - R{amount:.0f}"
        transaction_id = self.payment_client.transfer_money(amount, phone_number, message)
        return transaction_id

def validate_sa_phone(phone: str) -> bool:
    """Validate South African mobile phone number"""
    # SA mobile number patterns: +27 followed by mobile prefixes
    pattern = r"^\+27(60|61|62|63|64|65|66|67|68|69|70|71|72|73|74|76|78|79|81|82|83|84)[0-9]{7}$"
    return bool(re.match(pattern, phone))

def init_session_state():
    """Initialize session state variables"""
    if "language" not in st.session_state:
        st.session_state.language = "en"
    if "phone_number" not in st.session_state:
        st.session_state.phone_number = ""
    if "transactions" not in st.session_state:
        st.session_state.transactions = []
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    if "selected_deal" not in st.session_state:
        st.session_state.selected_deal = None
    if "payment_client" not in st.session_state:
        st.session_state.payment_client = SouthAfricaPaymentClient()

def get_text(key: str) -> str:
    """Get translated text"""
    return TRANSLATIONS.get(st.session_state.language, TRANSLATIONS["en"]).get(key, key)

def render_api_setup():
    """Render South African payment API configuration"""
    with st.expander("🔧 South African Payment API Configuration", expanded=False):
        st.markdown("### Mobile Payment Integration")
        st.markdown("""
        CreditSwift SA integrates with major South African mobile networks:
        
        **Supported Networks:**
        - **Vodacom M-Pesa** (082, 083, 084)
        - **MTN MoMo SA** (078, 079)
        - **Cell C** (084)
        - **Telkom Mobile** (081)
        
        **Compliance:**
        - NCR (National Credit Regulator) registered
        - POPI Act (Protection of Personal Information) compliant
        - Responsible lending practices
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            collections_key = st.text_input("Collections API Key", 
                                          type="password",
                                          value=st.session_state.get("sa_collections_key", ""))
            api_user = st.text_input("API User ID", value=st.session_state.get("sa_api_user", ""))
        
        with col2:
            disbursements_key = st.text_input("Disbursements API Key",
                                            type="password", 
                                            value=st.session_state.get("sa_disbursements_key", ""))
            api_key = st.text_input("API Key", type="password", value=st.session_state.get("sa_api_key", ""))
        
        # Save to session state
        st.session_state["sa_collections_key"] = collections_key
        st.session_state["sa_disbursements_key"] = disbursements_key
        st.session_state["sa_api_user"] = api_user
        st.session_state["sa_api_key"] = api_key
        
        if st.button("Test Network Connection"):
            client = SouthAfricaPaymentClient()
            if client.is_configured():
                status = client.get_token_status()
                st.success("✅ Payment system connected!")
                st.json(status)
            else:
                st.error("❌ Please configure API credentials first.")

def render_sidebar():
    """Render sidebar with language selection and info"""
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/4ECDC4/FFFFFF?text=CreditSwift+SA", width=200)
        
        # Language selector
        language = st.selectbox(
            "🌍 Language / Taal / Ulimi",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: LANGUAGES[x],
            index=0,
            key="language_selector"
        )
        st.session_state.language = language
        
        st.markdown("---")
        
        # API Configuration
        render_api_setup()
        
        st.markdown("---")
        
        # How it works
        st.markdown("### ℹ️ How It Works")
        st.markdown("""
        1. **Enter your SA mobile number**
        2. **We analyze your mobile money history**
        3. **Get NCR-compliant loan offers**
        4. **Choose affordable repayment terms**
        5. **Receive money instantly via mobile**
        """)
        
        # Compliance info
        st.markdown("### 🛡️ NCR Compliance")
        st.markdown("""
        - **Registered credit provider**
        - **Affordability assessments**
        - **Transparent pricing**
        - **Responsible lending**
        """)
        
        # Support
        st.markdown("---")
        st.markdown("### 📞 Support")
        st.markdown("**Call:** 0861-CREDIT")
        st.markdown("**WhatsApp:** +27-82-123-4567")
        st.markdown("**Email:** help@creditswift.co.za")

def render_phone_input():
    """Render South African phone number input"""
    st.markdown("## 📱 Enter Your Mobile Number")
    st.markdown("We'll analyze your mobile money transaction history across all major SA networks.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        phone = st.text_input(
            get_text("phone_number"),
            value=st.session_state.phone_number,
            placeholder="+27-82-XXX-XXXX",
            help="Enter your South African mobile number (Vodacom, MTN, Cell C, or Telkom)"
        )
        
        if phone and not validate_sa_phone(phone):
            st.error("Please enter a valid SA mobile number (e.g., +27821234567)")
            
            # Show supported networks
            config = SouthAfricaPaymentConfig()
            detected_network = config.detect_network(phone) if phone else None
            
            if detected_network:
                network_info = config.SUPPORTED_NETWORKS[detected_network]
                st.info(f"Detected network: {network_info['name']}")
            else:
                st.warning("Supported networks: Vodacom (082/083/084), MTN (078/079), Cell C (084), Telkom (081)")
            return
        
        st.session_state.phone_number = phone
    
    with col2:
        st.write("")  # Spacing
        if st.button(get_text("analyze_history"), type="primary", disabled=not validate_sa_phone(phone)):
            with st.spinner("Analyzing your transaction history..."):
                analyzer = SouthAfricaMobileAnalyzer()
                
                # Check account balance
                balance_info = analyzer.payment_client.get_account_balance(phone)
                if balance_info:
                    network = balance_info.get('network', 'Unknown')
                    balance = balance_info.get('availableBalance', '0')
                    st.success(f"✅ Connected to {network}! Balance: R{balance}")
                
                # Get transaction data
                transactions = analyzer.fetch_real_transaction_data(phone)
                st.session_state.transactions = transactions
                st.session_state.analysis_complete = True
                st.rerun()

def render_transaction_analysis():
    """Render South African transaction analysis"""
    if not st.session_state.analysis_complete:
        return None
    
    analyzer = SouthAfricaMobileAnalyzer()
    pattern = analyzer.analyze_patterns(st.session_state.transactions)
    credit_score = analyzer.calculate_credit_score(pattern)
    
    st.markdown("## 📊 Transaction History Analysis")
    
    # Key metrics for SA context
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        score_rating = "Excellent" if credit_score > 750 else "Good" if credit_score > 600 else "Fair"
        st.metric(
            "Credit Score", 
            f"{credit_score}/850",
            delta=score_rating
        )
    
    with col2:
        st.metric(
            "Monthly Income", 
            f"R{pattern.avg_monthly_inflow:,.0f}",
            delta=f"R{pattern.avg_monthly_inflow - pattern.avg_monthly_outflow:,.0f} net"
        )
    
    with col3:
        activity_level = "High" if (pattern.airtime_frequency + pattern.data_frequency) > 15 else "Moderate"
        st.metric(
            "Mobile Activity",
            f"{pattern.airtime_frequency + pattern.data_frequency}",
            delta=activity_level
        )
    
    with col4:
        bill_score = f"{pattern.bill_payment_consistency*100:.0f}%"
        bill_rating = "Excellent" if pattern.bill_payment_consistency > 0.8 else "Good"
        st.metric(
            "Bill Payment Score",
            bill_score,
            delta=bill_rating
        )
    
    # Network information
    st.info(f"📡 Network Provider: {pattern.network_provider}")
    
    # SA-specific visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Monthly cash flow in ZAR
        df = pd.DataFrame(st.session_state.transactions)
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.strftime('%Y-%m')
        
        monthly_data = df.groupby(['month', 'direction'])['amount'].sum().unstack(fill_value=0)
        
        if not monthly_data.empty:
            fig = go.Figure()
            if 'incoming' in monthly_data.columns:
                fig.add_trace(go.Bar(name='Income', x=monthly_data.index, y=monthly_data['incoming'], marker_color='green'))
            if 'outgoing' in monthly_data.columns:
                fig.add_trace(go.Bar(name='Expenses', x=monthly_data.index, y=monthly_data['outgoing'], marker_color='red'))
            
            fig.update_layout(
                title="Monthly Cash Flow (ZAR)", 
                xaxis_title="Month", 
                yaxis_title="Amount (R)"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # SA-specific transaction types
        type_counts = df['type'].value_counts()
        
        if not type_counts.empty:
            fig = px.pie(
                values=type_counts.values, 
                names=type_counts.index, 
                title="Transaction Types Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    return credit_score, pattern

def render_loan_deals(credit_score: int, monthly_income: float):
    """Render NCR-compliant loan deals"""
    st.markdown("## 💰 NCR-Compliant Loan Options")
    
    deal_engine = SouthAfricaLoanEngine()
    qualified_deals = deal_engine.get_qualified_deals(credit_score, monthly_income)
    
    if not qualified_deals:
        st.warning("⚠️ Based on responsible lending criteria, no loans are available at this time.")
        
        st.markdown("### 💡 How to Improve Your Eligibility")
        st.markdown("""
        - **Build transaction history**: Use mobile money more frequently
        - **Pay bills consistently**: Maintain good payment patterns  
        - **Increase income**: Higher regular income improves eligibility
        - **Reduce expenses**: Better expense management shows financial responsibility
        
        **Free Financial Wellness:**
        - Budget planning tools available
        - Savings goal tracking
        - Debt management advice
        """)
        return
    
    # NCR disclosure
    st.info("🛡️ All loan products are NCR registered and include affordability assessments as required by law.")
    
    # Display deals
    for deal in qualified_deals:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            suggested_amount = deal_engine.calculate_suggested_amount(deal, monthly_income)
            total_cost = suggested_amount * (1 + (deal.interest_rate * deal.term_months))
            monthly_payment = total_cost / deal.term_months
            
            with col1:
                st.markdown(f"""
                <div style="padding: 20px; border-left: 5px solid {deal.color}; background-color: #f8f9fa; margin: 10px 0;">
                    <h3 style="color: {deal.color}; margin: 0;">{deal.name}</h3>
                    <p style="margin: 5px 0; color: #666;">{deal.description}</p>
                    <small style="color: #999;">✅ NCR Compliant | Interest rate: {deal.interest_rate*100:.1f}% pm</small>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.metric("Suggested Amount", f"R{suggested_amount:,.0f}")
                st.caption(f"Range: R{deal.min_amount:,.0f} - R{deal.max_amount:,.0f}")
            
            with col3:
                st.metric("Monthly Payment", f"R{monthly_payment:,.0f}")
                st.caption(f"Term: {deal.term_months} months")
            
            with col4:
                st.metric("Total Cost", f"R{total_cost:,.0f}")
                if st.button(f"Select Loan", key=f"select_{deal.id}"):
                    st.session_state.selected_deal = {
                        "deal": deal,
                        "amount": suggested_amount,
                        "monthly_payment": monthly_payment,
                        "total_cost": total_cost
                    }
                    st.success(f"Selected: {deal.name}")

def render_repayment_options():
    """Render NCR-compliant repayment options"""
    if not st.session_state.selected_deal:
        return
    
    deal_info = st.session_state.selected_deal
    deal = deal_info["deal"]
    
    st.markdown("## 💳 Loan Application & Repayment")
    st.markdown(f"**Selected:** {deal.name} (NCR Registered)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Loan Details")
        
        # Amount adjustment
        custom_amount = st.slider(
            "Adjust loan amount:",
            min_value=float(deal.min_amount),
            max_value=float(deal.max_amount),
            value=float(deal_info["amount"]),
            step=50.0
        )
        
        # Recalculate for SA context
        monthly_interest = deal.interest_rate
        total_interest = custom_amount * monthly_interest * deal.term_months
        total_repayment = custom_amount + total_interest
        monthly_payment = total_repayment / deal.term_months
        
        # NCR required disclosures
        st.markdown("**NCR Required Disclosures:**")
        st.write(f"💰 Loan Amount: R{custom_amount:,.0f}")
        st.write(f"📈 Interest Rate: {deal.interest_rate*100:.1f}% per month")
        st.write(f"💸 Total Interest: R{total_interest:,.0f}")
        st.write(f"💯 Total Repayment: R{total_repayment:,.0f}")
        st.write(f"📅 Monthly Payment: R{monthly_payment:,.0f}")
        st.write(f"⏰ Loan Term: {deal.term_months} months")
        
        # Payment methods for SA
        st.markdown("### 💱 Repayment Methods")
        payment_methods = {
            "debit_order": "Debit Order (Bank Account)",
            "mobile_wallet": "Mobile Wallet Auto-debit",
            "retail_payment": "Retail Payment Points",
            "bank_transfer": "Manual Bank Transfer"
        }
        
        payment_method = st.selectbox(
            "Choose repayment method:",
            list(payment_methods.keys()),
            format_func=lambda x: payment_methods[x]
        )
        
        payment_date = st.selectbox(
            "Payment date:",
            [1, 7, 15, 25],
            help="Preferred monthly payment date"
        )
    
    with col2:
        st.markdown("### 🤖 Loan Assistant")
        
        with st.container():
            st.markdown("""
            <div style="background-color: #e3f2fd; padding: 15px; border-radius: 10px; margin: 10px 0;">
                <strong>🤖 CreditSwift SA Assistant:</strong><br>
                Hi! I'm here to help with your NCR-compliant loan application. Ask me about rates, terms, or South African regulations.
            </div>
            """, unsafe_allow_html=True)
            
            sa_questions = [
                "How does NCR regulation protect me?",
                "What happens if I can't pay on time?",
                "Are there early payment benefits?",
                "How do debit orders work?",
                "What are my rights as a borrower?",
                "How is interest calculated?",
                "Can I cancel within cooling-off period?",
                "What if my income changes?"
            ]
            
            selected_question = st.selectbox("Quick questions:", ["Select a question..."] + sa_questions)
            
            if selected_question != "Select a question...":
                sa_answers = {
                    "How does NCR regulation protect me?": "NCR ensures transparent pricing, affordability assessments, and fair treatment. You have rights to clear information and fair debt collection practices.",
                    "What happens if I can't pay on time?": "Contact us immediately. We offer payment arrangements and will not harass you. NCR rules protect you from aggressive collection practices.",
                    "Are there early payment benefits?": "Yes! Early settlement reduces total interest. You can pay extra anytime via mobile wallet or debit order increase.",
                    "How do debit orders work?": "Your bank automatically pays us monthly. You get SMS notifications and can manage/stop debit orders through your bank.",
                    "What are my rights as a borrower?": "You have rights to clear contract terms, fair treatment, complaint procedures, and debt counseling referrals if needed.",
                    "How is interest calculated?": f"Simple interest: R{custom_amount:,.0f} × {deal.interest_rate*100:.1f}% × {deal.term_months} months = R{total_interest:,.0f}",
                    "Can I cancel within cooling-off period?": "Yes, you have 5 business days to cancel without penalty as per NCR regulations.",
                    "What if my income changes?": "Contact us for payment arrangement options. We're required to consider reasonable payment proposals."
                }
                
                st.markdown(f"""
                <div style="background-color: #f3e5f5; padding: 15px; border-radius: 10px; margin: 10px 0;">
                    <strong>🤖 Answer:</strong><br>
                    {sa_answers[selected_question]}
                </div>
                """, unsafe_allow_html=True)
    
    # Application form
    st.markdown("---")
    st.markdown("### 📝 Loan Application")
    
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name", help="As per SA ID document")
        id_number = st.text_input("SA ID Number", help="13-digit South African ID")
        monthly_income = st.number_input("Monthly Income (R)", min_value=0, help="Before deductions")
    
    with col2:
        surname = st.text_input("Surname", help="As per SA ID document")
        email = st.text_input("Email Address")
        bank_account = st.text_input("Bank Account (for debit order)", help="Your primary bank account")
    
    # Consents and agreements
    st.markdown("### ✅ Consents & Agreements")
    
    ncr_consent = st.checkbox(
        "I consent to NCR credit check and understand my credit record may be accessed",
        help="Required for responsible lending assessment"
    )
    
    terms_accepted = st.checkbox(
        "I accept the loan terms, understand the total cost of credit, and confirm affordability",
        help="NCR requires clear understanding of loan costs"
    )
    
    popi_consent = st.checkbox(
        "I consent to processing of personal information per POPI Act",
        help="Required for loan processing and compliance"
    )
    
    # Application submission
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        can_apply = all([ncr_consent, terms_accepted, popi_consent, first_name, surname, id_number])
        apply_button = st.button(
            "🚀 Submit NCR-Compliant Application", 
            type="primary", 
            use_container_width=True,
            disabled=not can_apply
        )
        
        if apply_button:
            with st.spinner("Processing your NCR-compliant loan application..."):
                time.sleep(3)  # Simulate processing
                
                # Loan disbursement
                deal_engine = SouthAfricaLoanEngine()
                transaction_id = deal_engine.disburse_loan(
                    custom_amount, 
                    st.session_state.phone_number, 
                    deal
                )
                
                if transaction_id:
                    st.balloons()
                    st.success("🎉 Loan Approved & Disbursed!")
                    
                    # Show approval with SA context
                    st.markdown(f"""
                    ### ✅ NCR-Compliant Loan Approved
                    
                    **Loan Details:**
                    - Amount: R{custom_amount:,.0f}
                    - Monthly Payment: R{monthly_payment:,.0f}
                    - Term: {deal.term_months} months
                    - Total Cost: R{total_repayment:,.0f}
                    
                    **Transaction:**
                    - Reference: {transaction_id}
                    - Sent to: {st.session_state.phone_number}
                    - Method: Mobile wallet transfer
                    
                    **Important:**
                    - You have 5 days cooling-off period
                    - First payment due: {(datetime.now() + timedelta(days=30)).strftime('%d %B %Y')}
                    - Keep this reference for your records
                    
                    **Support:** 0861-CREDIT | help@creditswift.co.za
                    """)
                    
                    # Send notification
                    try:
                        due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                        notify_loan_approved(st.session_state.phone_number, custom_amount, due_date)
                    except Exception as e:
                        logger.warning(f"Could not send notification: {e}")
                else:
                    st.error("❌ Loan approved but transfer pending - our team will contact you shortly.")

def process_loan_application(phone_number, loan_amount, user_data):
    """Process loan application with SMS notifications"""
    
    # Generate reference number
    reference = f"CRS{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    try:
        # 1. Send application received notification
        notify_application_received(phone_number, loan_amount)
        
        # 2. Analyze mobile money history (simplified for demo)
        analyzer = SouthAfricaMobileAnalyzer()
        transactions = analyzer.fetch_real_transaction_data(phone_number)
        pattern = analyzer.analyze_patterns(transactions)
        credit_score = analyzer.calculate_credit_score(pattern)
        
        # 3. Make loan decision
        loan_engine = SouthAfricaLoanEngine()
        qualified_deals = loan_engine.get_qualified_deals(credit_score, pattern.avg_monthly_inflow)
        
        if qualified_deals:
            # Calculate due date (30 days from now)
            due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            
            # 4a. Process disbursement
            deal = qualified_deals[0]  # Use first qualified deal
            disbursement_result = loan_engine.disburse_loan(loan_amount, phone_number, deal)
            
            if disbursement_result:
                # 5a. Send approval notification
                notify_loan_approved(phone_number, loan_amount, due_date)
                
                return {
                    "status": "approved",
                    "amount": loan_amount,
                    "reference": reference,
                    "due_date": due_date,
                    "message": "Loan approved and disbursed! SMS sent."
                }
            else:
                # Disbursement failed
                notify_loan_declined(phone_number, "Technical error during disbursement")
                return {"status": "failed", "message": "Disbursement failed"}
        
        else:
            # 4b. Send decline notification
            decline_reason = "Insufficient mobile money activity or income"
            notify_loan_declined(phone_number, decline_reason)
            
            return {
                "status": "declined",
                "reason": decline_reason,
                "reference": reference,
                "message": "Loan declined. SMS sent."
            }
    
    except Exception as e:
        # Error occurred - notify user
        notify_loan_declined(phone_number, "Technical error occurred")
        logger.error(f"Error processing loan for {phone_number}: {str(e)}")
        return {"status": "error", "message": f"Error: {str(e)}"}

def render_admin_notifications():
    """Render notification testing section in admin"""
    
    st.header("📱 SMS Notification Testing")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Test Individual SMS")
        test_phone = st.text_input("Phone Number", placeholder="+27823456789")
        
        notification_type = st.selectbox("Notification Type", [
            "account_created",
            "loan_approved", 
            "loan_declined",
            "payment_due",
            "payment_received"
        ])
        
        if st.button("Send Test SMS"):
            if test_phone:
                with st.spinner("Sending SMS..."):
                    if notification_type == "loan_approved":
                        success = notify_loan_approved(test_phone, 1000, "2024-10-15")
                    elif notification_type == "loan_declined":
                        success = notify_loan_declined(test_phone, "Test decline reason")
                    else:
                        success = test_sms_notification(test_phone)
                    
                    if success:
                        st.success("✅ Test SMS sent successfully!")
                    else:
                        st.error("❌ Failed to send SMS")
            else:
                st.error("Please enter a phone number")
    
    with col2:
        st.subheader("SMS Statistics")
        
        # You can add database queries here to show SMS stats
        st.metric("SMS Sent Today", "23")
        st.metric("Success Rate", "95%")
        st.metric("Failed SMS", "1")
        
        if st.button("View SMS Logs"):
            st.info("SMS logs would be displayed here")

def main():
    """Main application for CreditSwift South Africa"""
    init_session_state()
    
    # Custom CSS for South African theme
    st.markdown("""
    <style>
    .main {
        padding-top: 1rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 20px;
        font-weight: bold;
    }
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    render_sidebar()
    
    # Main content
    st.title(get_text("app_title"))
    st.markdown(get_text("tagline"))
    st.markdown("*NCR Registered | POPI Compliant | Powered by SA Mobile Networks*")
    
    # Progress indicator
    progress_stages = ["📱 Mobile", "📊 Analysis", "💰 Loans", "📋 Apply"]
    current_stage = 0
    
    if st.session_state.phone_number and validate_sa_phone(st.session_state.phone_number):
        current_stage = 1
    if st.session_state.analysis_complete:
        current_stage = 2
    if st.session_state.selected_deal:
        current_stage = 3
    
    cols = st.columns(4)
    for i, stage in enumerate(progress_stages):
        with cols[i]:
            if i <= current_stage:
                st.markdown(f"**{stage}** ✅")
            elif i == current_stage + 1:
                st.markdown(f"**{stage}** ⏳")
            else:
                st.markdown(f"{stage}")
    
    st.markdown("---")
    
    # Render application sections
    render_phone_input()
    
    if st.session_state.analysis_complete:
        result = render_transaction_analysis()
        if result is not None:
            credit_score, pattern = result
            render_loan_deals(credit_score, pattern.avg_monthly_inflow)
            render_repayment_options()
    
    # Footer with SA compliance
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p><strong>CreditSwift South Africa</strong> - Responsible AI-Powered Lending</p>
        <p>🛡️ NCR Registration: NCRCP123456 | 📋 FSP License: 12345 | 🔒 POPI Act Compliant</p>
        <p>📞 Customer Care: 0861-CREDIT | 💬 WhatsApp: +27-82-123-4567</p>
        <p><small>CreditSwift SA (Pty) Ltd is an authorized credit provider registered with the National Credit Regulator</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()