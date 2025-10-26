import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL=postgresql://neondb_owner:npg_LSlXujRn39MW@ep-flat-morning-adrpwazn-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# Configure engine with proper connection pooling and SSL settings
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,  # Recycle connections every hour
    pool_pre_ping=True,  # Verify connections before use
    connect_args={
        "sslmode": "prefer",  # Handle SSL gracefully
        "application_name": "micro_loans_app"
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False, index=True)
    role = Column(String, default="borrower")  # borrower, admin, agent
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Personal information
    age = Column(Integer)
    gender = Column(String)
    address = Column(Text)
    marital_status = Column(String)
    education_level = Column(String)
    dependents = Column(Integer, default=0)
    
    # Relationships
    applications = relationship("LoanApplication", back_populates="user")
    loans = relationship("Loan", back_populates="borrower")

class LoanApplication(Base):
    __tablename__ = "loan_applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Loan details
    loan_amount = Column(Float, nullable=False)
    loan_purpose = Column(String, nullable=False)
    repayment_term = Column(String, nullable=False)
    collateral = Column(Text)
    
    # Employment and financial info
    employment_status = Column(String, nullable=False)
    employer_name = Column(String)
    employment_years = Column(Integer, nullable=False)
    monthly_income = Column(Float, nullable=False)
    monthly_expenses = Column(Float, nullable=False)
    current_debt = Column(Float, default=0)
    savings_amount = Column(Float, default=0)
    credit_history = Column(String, nullable=False)
    
    # Business information (optional)
    business_type = Column(String)
    business_years = Column(Integer, default=0)
    business_revenue = Column(Float, default=0)
    business_employees = Column(Integer, default=0)
    
    # AI Assessment results
    credit_score = Column(Integer)
    risk_level = Column(String)  # LOW, MEDIUM, HIGH
    approval_recommendation = Column(String)  # APPROVE, REJECT, REVIEW
    confidence_score = Column(Float)
    key_factors = Column(JSON)
    reasoning = Column(Text)
    suggested_loan_amount = Column(Float)
    suggested_interest_rate = Column(Float)
    repayment_capacity = Column(Float)
    debt_to_income_ratio = Column(Float)
    
    # Application status
    status = Column(String, default="pending")  # pending, approved, rejected, under_review
    decision = Column(String)  # approved, rejected, pending
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assessed_at = Column(DateTime)
    approved_at = Column(DateTime)
    rejected_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="applications")
    loan = relationship("Loan", back_populates="application", uselist=False)

class Loan(Base):
    __tablename__ = "loans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id"), nullable=False)
    borrower_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Loan terms
    principal_amount = Column(Float, nullable=False)
    interest_rate = Column(Float, nullable=False)
    term_months = Column(Integer, nullable=False)
    monthly_payment = Column(Float, nullable=False)
    total_repayment = Column(Float, nullable=False)
    
    # Payment tracking
    amount_paid = Column(Float, default=0)
    remaining_balance = Column(Float, nullable=False)
    next_payment_date = Column(DateTime)
    
    # Loan status
    status = Column(String, default="active")  # active, completed, defaulted, written_off
    disbursement_date = Column(DateTime, default=datetime.utcnow)
    completion_date = Column(DateTime)
    
    # Mobile Money transaction info
    disbursement_transaction_id = Column(String)
    momo_phone_number = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    application = relationship("LoanApplication", back_populates="loan")
    borrower = relationship("User", back_populates="loans")
    payments = relationship("Payment", back_populates="loan")
    transactions = relationship("Transaction", back_populates="loan")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id"), nullable=False)
    
    # Payment details
    installment_number = Column(Integer, nullable=False)
    amount_due = Column(Float, nullable=False)
    amount_paid = Column(Float, nullable=False)
    principal_amount = Column(Float, nullable=False)
    interest_amount = Column(Float, nullable=False)
    
    # Payment status
    status = Column(String, default="pending")  # pending, paid, overdue, partial
    due_date = Column(DateTime, nullable=False)
    paid_date = Column(DateTime)
    
    # Payment method
    payment_method = Column(String)  # mobile_money, bank_transfer, cash
    transaction_id = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loan = relationship("Loan", back_populates="payments")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Transaction details
    transaction_type = Column(String, nullable=False)  # disbursement, repayment, fee
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    
    # External transaction references
    external_transaction_id = Column(String, unique=True)
    provider = Column(String)  # mtn_momo, airtel_money, bank
    provider_reference = Column(String)
    
    # Transaction status
    status = Column(String, default="pending")  # pending, completed, failed, cancelled
    
    # Mobile Money specific
    phone_number = Column(String)
    network_operator = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    failed_at = Column(DateTime)
    
    # Additional metadata
    transaction_metadata = Column(JSON)
    error_message = Column(Text)
    
    # Relationships
    loan = relationship("Loan", back_populates="transactions")

# Database utility functions
def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

def get_db_session() -> Session:
    """Get database session with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            session = SessionLocal()
            # Test the connection with proper SQLAlchemy syntax
            session.execute(text("SELECT 1"))
            return session
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}. Retrying...")
                if session:
                    session.close()
                continue
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                raise

def close_db_session(db: Session):
    """Close database session"""
    if db:
        try:
            db.close()
        except Exception as e:
            logger.warning(f"Error closing database session: {e}")

# Data Access Layer
class DatabaseManager:
    def __init__(self):
        self.engine = engine
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user and return user ID"""
        db = get_db_session()
        try:
            user = User(
                email=user_data.get('email'),
                full_name=user_data.get('full_name'),
                phone_number=user_data.get('phone_number'),
                age=user_data.get('age'),
                gender=user_data.get('gender'),
                address=user_data.get('address'),
                marital_status=user_data.get('marital_status'),
                education_level=user_data.get('education_level'),
                dependents=user_data.get('dependents', 0)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return str(user.id)
        finally:
            close_db_session(db)
    
    def save_application(self, application_data: Dict[str, Any], user_id: Optional[str] = None) -> str:
        """Save loan application to database with improved error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            db = None
            try:
                db = get_db_session()
                
                # Create user if doesn't exist
                if not user_id:
                    user = User(
                        full_name=application_data.get('full_name'),
                        phone_number=application_data.get('phone_number'),
                        email=application_data.get('email', ''),
                        age=application_data.get('age'),
                        gender=application_data.get('gender'),
                        address=application_data.get('address'),
                        marital_status=application_data.get('marital_status'),
                        education_level=application_data.get('education_level'),
                        dependents=application_data.get('dependents', 0)
                    )
                    db.add(user)
                    db.flush()  # Get the ID without committing
                    user_id = str(user.id)
                
                # Create loan application
                application = LoanApplication(
                    user_id=user_id,
                    loan_amount=application_data.get('loan_amount'),
                    loan_purpose=application_data.get('loan_purpose'),
                    repayment_term=application_data.get('repayment_term'),
                    collateral=application_data.get('collateral', ''),
                    employment_status=application_data.get('employment_status'),
                    employer_name=application_data.get('employer_name', ''),
                    employment_years=application_data.get('employment_years'),
                    monthly_income=application_data.get('monthly_income'),
                    monthly_expenses=application_data.get('monthly_expenses'),
                    current_debt=application_data.get('current_debt', 0),
                    savings_amount=application_data.get('savings_amount', 0),
                    credit_history=application_data.get('credit_history'),
                    business_type=application_data.get('business_type', ''),
                    business_years=application_data.get('business_years', 0),
                    business_revenue=application_data.get('business_revenue', 0),
                    business_employees=application_data.get('business_employees', 0)
                )
                db.add(application)
                db.commit()
                db.refresh(application)
                logger.info(f"Successfully saved application with ID: {application.id}")
                return str(application.id)
                
            except Exception as e:
                if db:
                    try:
                        db.rollback()
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {rollback_error}")
                
                if attempt < max_retries - 1:
                    logger.warning(f"Save application attempt {attempt + 1} failed: {e}. Retrying...")
                    continue
                else:
                    logger.error(f"Failed to save application after {max_retries} attempts: {e}")
                    raise
                    
            finally:
                if db:
                    close_db_session(db)
    
    def update_application_assessment(self, application_id: str, credit_analysis: Dict[str, Any], decision: str):
        """Update application with AI assessment results"""
        db = get_db_session()
        try:
            application = db.query(LoanApplication).filter(
                LoanApplication.id == application_id
            ).first()
            
            if application:
                application.credit_score = credit_analysis.get('credit_score')
                application.risk_level = credit_analysis.get('risk_level')
                application.approval_recommendation = credit_analysis.get('approval_recommendation')
                application.confidence_score = credit_analysis.get('confidence_score')
                application.key_factors = credit_analysis.get('key_factors')
                application.reasoning = credit_analysis.get('reasoning')
                application.suggested_loan_amount = credit_analysis.get('suggested_loan_amount')
                application.suggested_interest_rate = credit_analysis.get('suggested_interest_rate')
                application.repayment_capacity = credit_analysis.get('repayment_capacity')
                application.debt_to_income_ratio = credit_analysis.get('debt_to_income_ratio')
                application.decision = decision
                application.status = decision
                application.assessed_at = datetime.utcnow()
                
                if decision == 'approved':
                    application.approved_at = datetime.utcnow()
                elif decision == 'rejected':
                    application.rejected_at = datetime.utcnow()
                
                db.commit()
                return True
            return False
        finally:
            close_db_session(db)
    
    def create_loan(self, application_id: str, approved_amount: float, interest_rate: float, term_months: int) -> Optional[str]:
        """Create loan from approved application"""
        db = get_db_session()
        try:
            # Get application
            application = db.query(LoanApplication).filter(
                LoanApplication.id == application_id
            ).first()
            
            if not application or application.status != 'approved':
                return None
            
            # Calculate loan terms
            monthly_payment = self._calculate_monthly_payment(approved_amount, interest_rate, term_months)
            total_repayment = monthly_payment * term_months
            
            # Create loan
            loan = Loan(
                application_id=application_id,
                borrower_id=application.user_id,
                principal_amount=approved_amount,
                interest_rate=interest_rate,
                term_months=term_months,
                monthly_payment=monthly_payment,
                total_repayment=total_repayment,
                remaining_balance=total_repayment,
                next_payment_date=datetime.utcnow() + timedelta(days=30),
                momo_phone_number=application.user.phone_number
            )
            
            db.add(loan)
            db.commit()
            db.refresh(loan)
            
            # Generate payment schedule
            self._generate_payment_schedule(db, str(loan.id), approved_amount, monthly_payment, term_months)
            
            return str(loan.id)
        finally:
            close_db_session(db)
    
    def _calculate_monthly_payment(self, principal: float, annual_rate: float, months: int) -> float:
        """Calculate monthly payment using standard loan formula"""
        if annual_rate == 0:
            return principal / months
        
        monthly_rate = annual_rate / 12
        payment = principal * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
        return round(payment, 2)
    
    def _generate_payment_schedule(self, db: Session, loan_id: str, principal: float, monthly_payment: float, months: int):
        """Generate payment schedule for loan"""
        remaining_balance = principal
        payment_date = datetime.utcnow()
        
        for i in range(months):
            payment_date += timedelta(days=30)  # Monthly payments
            
            # Calculate principal and interest
            interest_payment = remaining_balance * (0.15 / 12)  # Assuming 15% annual rate
            principal_payment = monthly_payment - interest_payment
            remaining_balance -= principal_payment
            
            payment = Payment(
                loan_id=loan_id,
                installment_number=i + 1,
                amount_due=monthly_payment,
                amount_paid=0,
                principal_amount=round(principal_payment, 2),
                interest_amount=round(interest_payment, 2),
                due_date=payment_date,
                status="pending"
            )
            db.add(payment)
        
        db.commit()
    
    def get_applications(self, user_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        """Get applications with optional filters"""
        db = get_db_session()
        try:
            query = db.query(LoanApplication).join(User)
            
            if user_id:
                query = query.filter(LoanApplication.user_id == user_id)
            if status:
                query = query.filter(LoanApplication.status == status)
            
            applications = query.all()
            
            result = []
            for app in applications:
                app_dict = {
                    'id': str(app.id),
                    'full_name': app.user.full_name,
                    'phone_number': app.user.phone_number,
                    'email': app.user.email,
                    'age': app.user.age,
                    'address': app.user.address,
                    'gender': app.user.gender,
                    'marital_status': app.user.marital_status,
                    'education_level': app.user.education_level,
                    'dependents': app.user.dependents,
                    'loan_amount': app.loan_amount,
                    'loan_purpose': app.loan_purpose,
                    'repayment_term': app.repayment_term,
                    'employment_status': app.employment_status,
                    'employer_name': app.employer_name,
                    'employment_years': app.employment_years,
                    'monthly_income': app.monthly_income,
                    'monthly_expenses': app.monthly_expenses,
                    'current_debt': app.current_debt,
                    'savings_amount': app.savings_amount,
                    'credit_history': app.credit_history,
                    'credit_score': app.credit_score,
                    'risk_level': app.risk_level,
                    'approval_recommendation': app.approval_recommendation,
                    'confidence_score': app.confidence_score,
                    'key_factors': app.key_factors,
                    'reasoning': app.reasoning,
                    'suggested_loan_amount': app.suggested_loan_amount,
                    'suggested_interest_rate': app.suggested_interest_rate,
                    'decision': app.decision,
                    'status': app.status,
                    'timestamp': app.created_at.isoformat() if app.created_at else None,
                    'assessed_at': app.assessed_at.isoformat() if app.assessed_at else None,
                }
                result.append(app_dict)
            
            return result
        finally:
            close_db_session(db)
    
    def get_loans(self, user_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        """Get loans with optional filters"""
        db = get_db_session()
        try:
            query = db.query(Loan).join(User)
            
            if user_id:
                query = query.filter(Loan.borrower_id == user_id)
            if status:
                query = query.filter(Loan.status == status)
            
            loans = query.all()
            
            result = []
            for loan in loans:
                loan_dict = {
                    'id': str(loan.id),
                    'amount': loan.principal_amount,
                    'status': loan.status,
                    'disbursement_date': loan.disbursement_date.isoformat() if loan.disbursement_date else None,
                    'transaction_id': loan.disbursement_transaction_id,
                    'monthly_payment': loan.monthly_payment,
                    'remaining_balance': loan.remaining_balance,
                    'next_payment_date': loan.next_payment_date.isoformat() if loan.next_payment_date else None,
                    'borrower_name': loan.borrower.full_name,
                    'borrower_phone': loan.borrower.phone_number,
                }
                result.append(loan_dict)
            
            return result
        finally:
            close_db_session(db)
    
    def record_transaction(self, transaction_data: Dict[str, Any]) -> str:
        """Record a transaction"""
        db = get_db_session()
        try:
            transaction = Transaction(
                loan_id=transaction_data.get('loan_id'),
                user_id=transaction_data.get('user_id'),
                transaction_type=transaction_data.get('transaction_type'),
                amount=transaction_data.get('amount'),
                currency=transaction_data.get('currency', 'USD'),
                external_transaction_id=transaction_data.get('external_transaction_id'),
                provider=transaction_data.get('provider'),
                status=transaction_data.get('status', 'pending'),
                phone_number=transaction_data.get('phone_number'),
                transaction_metadata=transaction_data.get('metadata', {})
            )
            
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            
            return str(transaction.id)
        finally:
            close_db_session(db)

# Global database manager instance
db_manager = DatabaseManager()

# Initialize database
def init_database():
    """Initialize database tables"""
    try:
        create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise