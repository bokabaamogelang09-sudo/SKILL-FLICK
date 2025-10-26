import pandas as pd
import json
from datetime import datetime, timedelta
import uuid

class DataManager:
    """
    Manages all application data including loans, applications, and user data
    """
    
    def __init__(self):
        self.applications = []
        self.loans = []
        self.users = []
        self.transactions = []
    
    def save_application(self, application_data):
        """
        Save loan application with timestamp and unique ID
        """
        application_id = str(uuid.uuid4())
        application = {
            "id": application_id,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            **application_data
        }
        self.applications.append(application)
        return application_id
    
    def update_application_status(self, application_id, status, credit_analysis=None):
        """
        Update application status and add credit analysis results
        """
        for app in self.applications:
            if app["id"] == application_id:
                app["status"] = status
                app["last_updated"] = datetime.now().isoformat()
                if credit_analysis:
                    app.update(credit_analysis)
                return True
        return False
    
    def create_loan(self, application_id, approved_amount, interest_rate, term_months):
        """
        Create a new loan record from approved application
        """
        # Find the application
        application = next((app for app in self.applications if app["id"] == application_id), None)
        if not application:
            return None
        
        loan_id = str(uuid.uuid4())
        
        # Calculate repayment schedule
        monthly_payment = self.calculate_monthly_payment(approved_amount, interest_rate, term_months)
        total_repayment = monthly_payment * term_months
        
        loan = {
            "id": loan_id,
            "application_id": application_id,
            "borrower_name": application["full_name"],
            "borrower_phone": application["phone_number"],
            "borrower_email": application.get("email", ""),
            "principal_amount": approved_amount,
            "interest_rate": interest_rate,
            "term_months": term_months,
            "monthly_payment": monthly_payment,
            "total_repayment": total_repayment,
            "amount_paid": 0,
            "remaining_balance": total_repayment,
            "status": "active",
            "disbursement_date": datetime.now().isoformat(),
            "next_payment_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "repayment_schedule": self.generate_repayment_schedule(
                approved_amount, monthly_payment, term_months
            ),
            "created_at": datetime.now().isoformat()
        }
        
        self.loans.append(loan)
        return loan_id
    
    def calculate_monthly_payment(self, principal, annual_rate, months):
        """
        Calculate monthly payment using standard loan formula
        """
        if annual_rate == 0:
            return principal / months
        
        monthly_rate = annual_rate / 12
        payment = principal * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
        return round(payment, 2)
    
    def generate_repayment_schedule(self, principal, monthly_payment, months):
        """
        Generate detailed repayment schedule
        """
        schedule = []
        remaining_balance = principal
        payment_date = datetime.now()
        
        for i in range(months):
            payment_date += timedelta(days=30)  # Monthly payments
            
            # For simplicity, assume equal principal payments
            principal_payment = principal / months
            interest_payment = monthly_payment - principal_payment
            remaining_balance -= principal_payment
            
            schedule.append({
                "installment": i + 1,
                "payment_date": payment_date.strftime("%Y-%m-%d"),
                "amount_due": monthly_payment,
                "principal": round(principal_payment, 2),
                "interest": round(interest_payment, 2),
                "remaining_balance": max(0, round(remaining_balance, 2)),
                "status": "pending",
                "paid_date": None,
                "amount_paid": 0
            })
        
        return schedule
    
    def record_payment(self, loan_id, installment_number, amount_paid, payment_date=None):
        """
        Record a loan payment
        """
        loan = next((loan for loan in self.loans if loan["id"] == loan_id), None)
        if not loan:
            return False
        
        # Find the installment
        schedule = loan["repayment_schedule"]
        if installment_number > len(schedule):
            return False
        
        installment = schedule[installment_number - 1]
        installment["amount_paid"] = amount_paid
        installment["paid_date"] = payment_date or datetime.now().strftime("%Y-%m-%d")
        installment["status"] = "paid" if amount_paid >= installment["amount_due"] else "partial"
        
        # Update loan totals
        loan["amount_paid"] += amount_paid
        loan["remaining_balance"] = max(0, loan["total_repayment"] - loan["amount_paid"])
        
        # Check if loan is fully paid
        if loan["remaining_balance"] <= 0:
            loan["status"] = "completed"
        
        # Update next payment date
        next_unpaid = next((inst for inst in schedule if inst["status"] == "pending"), None)
        if next_unpaid:
            loan["next_payment_date"] = next_unpaid["payment_date"]
        
        loan["last_updated"] = datetime.now().isoformat()
        return True
    
    def get_applications_df(self):
        """
        Get applications as pandas DataFrame for analysis
        """
        if not self.applications:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.applications)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    def get_loans_df(self):
        """
        Get loans as pandas DataFrame for analysis
        """
        if not self.loans:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.loans)
        df['disbursement_date'] = pd.to_datetime(df['disbursement_date'])
        return df
    
    def get_loan_portfolio_stats(self):
        """
        Get portfolio statistics for admin dashboard
        """
        if not self.loans:
            return {
                "total_loans": 0,
                "total_disbursed": 0,
                "total_collected": 0,
                "active_loans": 0,
                "default_rate": 0,
                "avg_loan_amount": 0
            }
        
        loans_df = self.get_loans_df()
        
        return {
            "total_loans": len(self.loans),
            "total_disbursed": loans_df["principal_amount"].sum(),
            "total_collected": loans_df["amount_paid"].sum(),
            "active_loans": len(loans_df[loans_df["status"] == "active"]),
            "completed_loans": len(loans_df[loans_df["status"] == "completed"]),
            "default_rate": len(loans_df[loans_df["status"] == "defaulted"]) / len(self.loans) * 100,
            "avg_loan_amount": loans_df["principal_amount"].mean(),
            "avg_term_months": loans_df["term_months"].mean()
        }
    
    def get_application_stats(self):
        """
        Get application statistics
        """
        if not self.applications:
            return {
                "total_applications": 0,
                "pending_applications": 0,
                "approved_applications": 0,
                "rejected_applications": 0,
                "approval_rate": 0
            }
        
        apps_df = self.get_applications_df()
        
        total = len(self.applications)
        pending = len(apps_df[apps_df.get("decision", "pending") == "pending"])
        approved = len(apps_df[apps_df.get("decision", "") == "approved"])
        rejected = len(apps_df[apps_df.get("decision", "") == "rejected"])
        
        return {
            "total_applications": total,
            "pending_applications": pending,
            "approved_applications": approved,
            "rejected_applications": rejected,
            "approval_rate": (approved / total * 100) if total > 0 else 0
        }

# Global instance for the application
data_manager = DataManager()
