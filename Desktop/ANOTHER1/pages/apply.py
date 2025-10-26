import streamlit as st
from datetime import datetime
import sys
import os
import traceback
import re


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.integration import momo_client


# Add error handling for imports
try:
    from utils.credit_score import calculate_ai_credit_score, generate_risk_explanation
    from utils.integration import momo_client
    from utils.database import db_manager

    IMPORTS_SUCCESS = True
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.error("Please ensure all utility modules are properly installed and accessible")
    IMPORTS_SUCCESS = False

st.set_page_config(
    page_title="Apply for Loan",
    page_icon="📝",
    layout="wide"
)


def main():
    if not IMPORTS_SUCCESS:
        st.error("Cannot proceed due to import errors. Please check your dependencies.")
        return

    st.title("📝 Loan Application")
    st.markdown("Complete the form below to apply for a micro-loan with AI-powered instant assessment.")

    # Initialize session state
    initialize_session_state()

    # Multi-step application form
    tab1, tab2, tab3 = st.tabs(["👤 Personal Information", "💰 Financial Details", "📋 Review & Submit"])

    with tab1:
        show_personal_info_form()

    with tab2:
        show_financial_info_form()

    with tab3:
        show_review_and_submit()


def initialize_session_state():
    """Initialize session state variables"""
    if 'application_step' not in st.session_state:
        st.session_state.application_step = 1

    # Initialize form fields with default values
    default_values = {
        'full_name': '',
        'age': 18,
        'phone_number': '',
        'email': '',
        'address': '',
        'gender': 'Male',
        'marital_status': 'Single',
        'education_level': 'Secondary',
        'dependents': 0,
        'employment_status': 'Employed',
        'employer_name': '',
        'employment_years': 0,
        'monthly_income': 0.0,
        'monthly_expenses': 0.0,
        'current_debt': 0.0,
        'savings_amount': 0.0,
        'credit_history': 'No Credit History',
        'loan_amount': 50.0,
        'loan_purpose': 'Business Expansion',
        'repayment_term': '12 months',
        'collateral': '',
        'business_type': '',
        'business_years': 0,
        'business_revenue': 0.0,
        'business_employees': 0
    }

    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value


def show_personal_info_form():
    st.subheader("Personal Information")

    col1, col2 = st.columns(2)

    with col1:
        st.session_state.full_name = st.text_input(
            "Full Name *",
            value=st.session_state.full_name,
            key="full_name_input"
        )
        st.session_state.age = st.number_input(
            "Age *",
            min_value=18,
            max_value=80,
            value=st.session_state.age,
            key="age_input"
        )
        st.session_state.phone_number = st.text_input(
            "Phone Number *",
            value=st.session_state.phone_number,
            help="Mobile Money account number (e.g., +256701234567)",
            key="phone_input"
        )
        st.session_state.email = st.text_input(
            "Email Address",
            value=st.session_state.email,
            key="email_input"
        )

    with col2:
        st.session_state.gender = st.selectbox(
            "Gender",
            ["Male", "Female", "Other"],
            index=["Male", "Female", "Other"].index(st.session_state.gender),
            key="gender_input"
        )
        st.session_state.marital_status = st.selectbox(
            "Marital Status",
            ["Single", "Married", "Divorced", "Widowed"],
            index=["Single", "Married", "Divorced", "Widowed"].index(st.session_state.marital_status),
            key="marital_input"
        )
        education_options = ["Primary", "Secondary", "Certificate", "Diploma", "Degree", "Postgraduate"]
        st.session_state.education_level = st.selectbox(
            "Education Level",
            education_options,
            index=education_options.index(st.session_state.education_level),
            key="education_input"
        )
        st.session_state.dependents = st.number_input(
            "Number of Dependents",
            min_value=0,
            max_value=20,
            value=st.session_state.dependents,
            key="dependents_input"
        )

    st.session_state.address = st.text_area(
        "Physical Address *",
        value=st.session_state.address,
        key="address_input"
    )

    # Validation with better error messages
    if st.button("Continue to Financial Details", type="primary"):
        validation_errors = validate_personal_info()
        if not validation_errors:
            st.session_state.application_step = 2
            st.success("Personal information saved! Continue to financial details.")
            st.rerun()
        else:
            for error in validation_errors:
                st.error(error)


def show_financial_info_form():
    st.subheader("Financial Information")

    col1, col2 = st.columns(2)

    with col1:
        employment_options = ["Employed", "Self-Employed", "Business Owner", "Farmer", "Student", "Unemployed"]
        st.session_state.employment_status = st.selectbox(
            "Employment Status *",
            employment_options,
            index=employment_options.index(st.session_state.employment_status),
            key="employment_input"
        )
        st.session_state.employer_name = st.text_input(
            "Employer/Business Name",
            value=st.session_state.employer_name,
            key="employer_input"
        )
        st.session_state.employment_years = st.number_input(
            "Years in Current Employment/Business *",
            min_value=0,
            max_value=50,
            value=st.session_state.employment_years,
            key="emp_years_input"
        )
        st.session_state.monthly_income = st.number_input(
            "Monthly Income (USD) *",
            min_value=0.0,
            format="%.2f",
            value=st.session_state.monthly_income,
            key="income_input"
        )

    with col2:
        st.session_state.monthly_expenses = st.number_input(
            "Monthly Expenses (USD) *",
            min_value=0.0,
            format="%.2f",
            value=st.session_state.monthly_expenses,
            key="expenses_input"
        )
        st.session_state.current_debt = st.number_input(
            "Current Debt (USD)",
            min_value=0.0,
            format="%.2f",
            value=st.session_state.current_debt,
            key="debt_input"
        )
        st.session_state.savings_amount = st.number_input(
            "Savings (USD)",
            min_value=0.0,
            format="%.2f",
            value=st.session_state.savings_amount,
            key="savings_input"
        )
        credit_options = ["Excellent", "Good", "Fair", "Poor", "No Credit History"]
        st.session_state.credit_history = st.selectbox(
            "Credit History",
            credit_options,
            index=credit_options.index(st.session_state.credit_history),
            key="credit_input"
        )

    # Loan details
    st.subheader("Loan Requirements")
    col1, col2 = st.columns(2)

    with col1:
        st.session_state.loan_amount = st.number_input(
            "Loan Amount Requested (USD) *",
            min_value=50.0,
            max_value=50000.0,
            format="%.2f",
            value=st.session_state.loan_amount,
            key="loan_amount_input"
        )
        purpose_options = ["Business Expansion", "Equipment Purchase", "Working Capital",
                           "Agriculture", "Education", "Emergency", "Home Improvement", "Other"]
        st.session_state.loan_purpose = st.selectbox(
            "Loan Purpose *",
            purpose_options,
            index=purpose_options.index(st.session_state.loan_purpose),
            key="purpose_input"
        )

    with col2:
        term_options = ["3 months", "6 months", "12 months", "18 months", "24 months"]
        st.session_state.repayment_term = st.selectbox(
            "Preferred Repayment Term",
            term_options,
            index=term_options.index(st.session_state.repayment_term),
            key="term_input"
        )
        st.session_state.collateral = st.text_area(
            "Collateral (if any)",
            value=st.session_state.collateral,
            help="Describe any assets you can offer as security",
            key="collateral_input"
        )

    # Business information (if self-employed/business owner)
    if st.session_state.employment_status in ["Self-Employed", "Business Owner"]:
        st.subheader("Business Information")
        col1, col2 = st.columns(2)

        with col1:
            st.session_state.business_type = st.text_input(
                "Type of Business",
                value=st.session_state.business_type,
                key="bus_type_input"
            )
            st.session_state.business_years = st.number_input(
                "Years in Business",
                min_value=0,
                max_value=50,
                value=st.session_state.business_years,
                key="bus_years_input"
            )

        with col2:
            st.session_state.business_revenue = st.number_input(
                "Monthly Business Revenue (USD)",
                min_value=0.0,
                format="%.2f",
                value=st.session_state.business_revenue,
                key="revenue_input"
            )
            st.session_state.business_employees = st.number_input(
                "Number of Employees",
                min_value=0,
                value=st.session_state.business_employees,
                key="employees_input"
            )

    if st.button("Continue to Review", type="primary"):
        validation_errors = validate_financial_info()
        if not validation_errors:
            st.session_state.application_step = 3
            st.success("Financial information saved! Review your application.")
            st.rerun()
        else:
            for error in validation_errors:
                st.error(error)


def show_review_and_submit():
    st.subheader("Review Your Application")

    # Display application summary
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Personal Information")
        st.write(f"**Name:** {st.session_state.full_name}")
        st.write(f"**Age:** {st.session_state.age}")
        st.write(f"**Phone:** {st.session_state.phone_number}")
        st.write(f"**Email:** {st.session_state.email or 'Not provided'}")
        st.write(f"**Address:** {st.session_state.address}")

        st.markdown("### Employment")
        st.write(f"**Status:** {st.session_state.employment_status}")
        st.write(f"**Experience:** {st.session_state.employment_years} years")
        st.write(f"**Monthly Income:** ${st.session_state.monthly_income:,.2f}")

    with col2:
        st.markdown("### Loan Details")
        st.write(f"**Amount:** ${st.session_state.loan_amount:,.2f}")
        st.write(f"**Purpose:** {st.session_state.loan_purpose}")
        st.write(f"**Term:** {st.session_state.repayment_term}")

        st.markdown("### Financial Summary")
        st.write(f"**Monthly Expenses:** ${st.session_state.monthly_expenses:,.2f}")
        st.write(f"**Current Debt:** ${st.session_state.current_debt:,.2f}")
        st.write(f"**Credit History:** {st.session_state.credit_history}")

    # Calculate debt-to-income ratio
    if st.session_state.monthly_income > 0:
        dti_ratio = (
                                st.session_state.monthly_expenses + st.session_state.current_debt) / st.session_state.monthly_income
        st.metric("Debt-to-Income Ratio", f"{dti_ratio:.1%}")

        if dti_ratio > 0.5:
            st.warning("⚠️ High debt-to-income ratio may affect approval")

    # Terms and conditions
    st.markdown("---")
    terms_accepted = st.checkbox("I accept the terms and conditions and consent to credit assessment")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("← Back to Edit"):
            st.session_state.application_step = 2
            st.rerun()

    with col3:
        if st.button("Submit Application 🚀", type="primary", disabled=not terms_accepted):
            submit_application()


def submit_application():
    """Process and submit the loan application"""

    try:
        with st.spinner("Processing your application with AI assessment..."):
            # Collect all application data
            application_data = collect_application_data()

            # Validate application data before processing
            if not validate_application_data(application_data):
                st.error("Invalid application data. Please review your inputs.")
                return

            # Save application to database
            application_id = db_manager.save_application(application_data)

            if not application_id:
                st.error("Failed to save application. Please try again.")
                return

            # Perform AI credit scoring
            credit_analysis = calculate_ai_credit_score(application_data)

            # Update application with credit analysis
            decision = credit_analysis['approval_recommendation'].lower()
            db_manager.update_application_assessment(application_id, credit_analysis, decision)

            # Display results
            display_credit_results(credit_analysis, application_id)

            # Clear form after successful submission
            clear_application_form()

    except Exception as e:
        st.error(f"Error processing application: {str(e)}")
        st.error("Your application has been saved and will be processed manually.")
        if st.checkbox("Show detailed error (for debugging)"):
            st.code(traceback.format_exc())


def collect_application_data():
    """Collect all application data from session state"""
    return {
        "full_name": st.session_state.full_name,
        "age": st.session_state.age,
        "phone_number": st.session_state.phone_number,
        "email": st.session_state.email,
        "address": st.session_state.address,
        "gender": st.session_state.gender,
        "marital_status": st.session_state.marital_status,
        "education_level": st.session_state.education_level,
        "dependents": st.session_state.dependents,
        "employment_status": st.session_state.employment_status,
        "employer_name": st.session_state.employer_name,
        "employment_years": st.session_state.employment_years,
        "monthly_income": st.session_state.monthly_income,
        "monthly_expenses": st.session_state.monthly_expenses,
        "current_debt": st.session_state.current_debt,
        "savings_amount": st.session_state.savings_amount,
        "credit_history": st.session_state.credit_history,
        "loan_amount": st.session_state.loan_amount,
        "loan_purpose": st.session_state.loan_purpose,
        "repayment_term": st.session_state.repayment_term,
        "collateral": st.session_state.collateral,
        "business_type": st.session_state.business_type,
        "business_years": st.session_state.business_years,
        "business_revenue": st.session_state.business_revenue,
        "business_employees": st.session_state.business_employees,
        "application_date": datetime.now().isoformat()
    }


def display_credit_results(credit_analysis, application_id):
    """Display credit assessment results"""
    st.success("🎉 Application submitted successfully!")
    st.info(f"**Application ID:** {application_id}")

    # Show credit assessment results
    st.markdown("## 🤖 AI Credit Assessment Results")

    # Risk level indicator
    risk_color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}
    risk_level = credit_analysis.get('risk_level', 'UNKNOWN')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Credit Score", f"{credit_analysis.get('credit_score', 0)}/850")
    with col2:
        if risk_level in risk_color:
            st.markdown(f"**Risk Level:** :{risk_color[risk_level]}[{risk_level}]")
        else:
            st.markdown(f"**Risk Level:** {risk_level}")
    with col3:
        confidence = credit_analysis.get('confidence_score', 0)
        st.metric("Confidence", f"{confidence * 100:.1f}%")

    # Decision
    decision = credit_analysis.get('approval_recommendation', '').lower()
    if decision == "approved":
        suggested_amount = credit_analysis.get('suggested_loan_amount', st.session_state.loan_amount)
        st.success(f"✅ **LOAN APPROVED** - ${suggested_amount:,.2f}")

        # Initiate disbursement if approved
        if st.button("Proceed with Disbursement 💰"):
            initiate_disbursement(application_id, suggested_amount)

    elif decision == "rejected":
        st.error("❌ **LOAN REJECTED**")
    else:
        st.warning("⏳ **UNDER REVIEW** - Manual review required")

    # Show detailed explanation
    with st.expander("📊 Detailed Assessment Report"):
        explanation = generate_risk_explanation(credit_analysis)
        st.markdown(explanation)


def initiate_disbursement(application_id, approved_amount):
    """Initiate Mobile Money disbursement"""

    try:
        phone_number = st.session_state.phone_number

        with st.spinner("Processing disbursement..."):
            # Validate phone number with MoMo provider
            is_valid, validation_msg = momo_client.validate_phone_number(phone_number)

            if not is_valid:
                st.error(f"Disbursement failed: {validation_msg}")
                return

            # Create loan record
            term_months = int(st.session_state.repayment_term.split()[0])
            loan_id = db_manager.create_loan(application_id, approved_amount, 0.15, term_months)

            if not loan_id:
                st.error("Failed to create loan record")
                return

            # Initiate MoMo disbursement
            disbursement_result = momo_client.initiate_disbursement(
                phone_number, approved_amount, loan_id
            )

            if disbursement_result.get("success"):
                display_disbursement_success(disbursement_result, loan_id, phone_number)
            else:
                st.error(f"Disbursement failed: {disbursement_result.get('error', 'Unknown error')}")

    except Exception as e:
        st.error(f"Error during disbursement: {str(e)}")


def display_disbursement_success(result, loan_id, phone_number):
    """Display successful disbursement information"""
    st.success("💰 Disbursement successful!")

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Transaction ID:** {result.get('transaction_id', 'N/A')}")
        st.info(f"**Amount:** ${result.get('amount_disbursed', 0):,.2f}")
    with col2:
        st.info(f"**Fee:** ${result.get('fee', 0):,.2f}")
        st.info(f"**Net Amount:** ${result.get('net_amount', 0):,.2f}")

    # Record disbursement transaction in database
    try:
        transaction_data = {
            'loan_id': loan_id,
            'transaction_type': 'disbursement',
            'amount': result.get('amount_disbursed', 0),
            'external_transaction_id': result.get('transaction_id'),
            'provider': 'momo',
            'status': 'completed',
            'phone_number': phone_number,
            'metadata': result
        }
        db_manager.record_transaction(transaction_data)
        st.success("💾 Transaction recorded in database")
    except Exception as e:
        st.warning(f"Transaction recorded but database update failed: {str(e)}")


def validate_personal_info():
    """Validate personal information fields"""
    errors = []

    if not st.session_state.full_name.strip():
        errors.append("Full name is required")

    if st.session_state.age < 18:
        errors.append("Must be at least 18 years old")

    if not st.session_state.phone_number.strip():
        errors.append("Phone number is required")
    elif not validate_phone_format(st.session_state.phone_number):
        errors.append("Invalid phone number format (should include country code, e.g., +256701234567)")

    if not st.session_state.address.strip():
        errors.append("Physical address is required")

    return errors


def validate_financial_info():
    """Validate financial information fields"""
    errors = []

    if st.session_state.monthly_income <= 0:
        errors.append("Monthly income must be greater than 0")

    if st.session_state.loan_amount <= 0:
        errors.append("Loan amount must be greater than 0")

    if st.session_state.monthly_expenses > st.session_state.monthly_income:
        errors.append("Monthly expenses cannot exceed monthly income")

    if st.session_state.employment_status in ["Self-Employed", "Business Owner"]:
        if not st.session_state.business_type.strip():
            errors.append("Business type is required for self-employed/business owners")

    return errors


def validate_application_data(data):
    """Validate complete application data"""
    required_fields = ['full_name', 'phone_number', 'address', 'monthly_income', 'loan_amount']

    for field in required_fields:
        if not data.get(field):
            return False

    return True


def validate_phone_format(phone_number):
    """Validate phone number format"""
    # Basic validation for international format
    pattern = r'^\+\d{1,3}\d{9,15}$'
    return re.match(pattern, phone_number.replace(' ', '').replace('-', ''))


def clear_application_form():
    """Clear all application form fields"""
    form_fields = [
        'full_name', 'age', 'phone_number', 'email', 'address', 'gender',
        'marital_status', 'education_level', 'dependents', 'employment_status',
        'employer_name', 'employment_years', 'monthly_income', 'monthly_expenses',
        'current_debt', 'savings_amount', 'credit_history', 'loan_amount',
        'loan_purpose', 'repayment_term', 'collateral', 'business_type',
        'business_years', 'business_revenue', 'business_employees'
    ]

    for field in form_fields:
        if field in st.session_state:
            del st.session_state[field]

    st.session_state.application_step = 1
    st.success("Form cleared! You can start a new application.")


if __name__ == "__main__":
    main()