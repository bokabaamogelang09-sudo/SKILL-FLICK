import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import db_manager
from utils.integration import momo_client

st.set_page_config(
    page_title="Loan Tracking",
    page_icon="📋",
    layout="wide"
)

def main():
    st.title("📋 Loan Tracking Dashboard")
    st.markdown("Monitor your active loans, repayment schedules, and payment history.")
    
    try:
        loans = db_manager.get_loans()
    except Exception as e:
        st.error(f"Error loading loans: {e}")
        loans = []
    
    if not loans:
        st.info("💡 No active loans yet. Apply for a loan to track your repayments here.")
        st.markdown("---")
        
        # Show recent applications status
        try:
            applications = db_manager.get_applications()
        except Exception as e:
            st.error(f"Error loading applications: {e}")
            applications = []
        if applications:
            st.subheader("📝 Your Recent Applications")
            for app in applications[-3:]:  # Show last 3 applications
                with st.expander(f"Application: ${app['loan_amount']:,.0f} - {app.get('decision', 'pending').title()}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Amount:** ${app['loan_amount']:,.2f}")
                        st.write(f"**Purpose:** {app['loan_purpose']}")
                        st.write(f"**Date:** {app['timestamp'][:10]}")
                    with col2:
                        st.write(f"**Status:** {app.get('decision', 'pending').title()}")
                        if app.get('credit_score'):
                            st.write(f"**Credit Score:** {app['credit_score']}")
                        if app.get('risk_level'):
                            st.write(f"**Risk Level:** {app['risk_level']}")
        return
    
    # Loan portfolio overview
    show_loan_portfolio_overview()
    
    st.markdown("---")
    
    # Main tracking interface
    tab1, tab2, tab3 = st.tabs(["💰 Active Loans", "📅 Payment Schedule", "📊 Payment History"])
    
    with tab1:
        show_active_loans()
    
    with tab2:
        show_payment_schedule()
    
    with tab3:
        show_payment_history()

def show_loan_portfolio_overview():
    """Display loan portfolio summary"""
    st.subheader("💼 Your Loan Portfolio")
    
    try:
        loans = db_manager.get_loans()
    except Exception as e:
        st.error(f"Error loading loan portfolio: {e}")
        return
    
    # Calculate portfolio metrics
    total_borrowed = sum([loan.get('amount', 0) for loan in loans])
    active_loans = len([loan for loan in loans if loan.get('status') == 'active'])
    total_remaining = sum([loan.get('amount', 0) * 1.15 for loan in loans if loan.get('status') == 'active'])  # Assume 15% interest
    
    # Next payment calculation (mock)
    next_payment_amount = total_remaining / 12 if active_loans > 0 else 0  # Assume 12 month terms
    next_payment_date = (datetime.now() + timedelta(days=30)).strftime("%B %d, %Y")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Borrowed", f"${total_borrowed:,.2f}")
    with col2:
        st.metric("Active Loans", active_loans)
    with col3:
        st.metric("Total Remaining", f"${total_remaining:,.2f}")
    with col4:
        st.metric("Next Payment", f"${next_payment_amount:,.2f}")
    
    # Loan status chart
    if len(loans) > 1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Loan amounts chart
            loan_data = pd.DataFrame(loans)
            fig = px.pie(
                values=loan_data['amount'],
                names=[f"Loan {i+1}" for i in range(len(loans))],
                title="Loan Distribution by Amount"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Payment progress (mock data)
            progress_data = []
            for i, loan in enumerate(loans):
                paid_percentage = min(100, (datetime.now() - datetime.fromisoformat(loan.get('disbursement_date', datetime.now().isoformat()))).days / 365 * 100)
                progress_data.append({
                    'Loan': f"Loan {i+1}",
                    'Paid': paid_percentage,
                    'Remaining': 100 - paid_percentage
                })
            
            if progress_data:
                progress_df = pd.DataFrame(progress_data)
                fig = px.bar(
                    progress_df,
                    x='Loan',
                    y=['Paid', 'Remaining'],
                    title="Repayment Progress",
                    color_discrete_map={'Paid': '#2E8B57', 'Remaining': '#FF8C00'}
                )
                st.plotly_chart(fig, use_container_width=True)

def show_active_loans():
    """Display active loans with details"""
    st.subheader("💰 Active Loans")
    
    try:
        loans = db_manager.get_loans()
        active_loans = [loan for loan in loans if loan.get('status') == 'active']
    except Exception as e:
        st.error(f"Error loading active loans: {e}")
        return
    
    if not active_loans:
        st.info("No active loans found.")
        return
    
    for i, loan in enumerate(active_loans):
        with st.expander(f"Loan #{i+1}: ${loan.get('amount', 0):,.2f}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Loan Details**")
                st.write(f"Principal: ${loan.get('amount', 0):,.2f}")
                st.write(f"Interest Rate: 15.0%")  # Mock rate
                st.write(f"Term: 12 months")  # Mock term
                st.write(f"Status: {loan.get('status', 'active').title()}")
            
            with col2:
                st.markdown("**Payment Info**")
                disbursement_date = datetime.fromisoformat(loan.get('disbursement_date', datetime.now().isoformat()))
                st.write(f"Disbursed: {disbursement_date.strftime('%B %d, %Y')}")
                
                next_payment = disbursement_date + timedelta(days=30)
                st.write(f"Next Payment: {next_payment.strftime('%B %d, %Y')}")
                
                monthly_payment = loan.get('amount', 0) * 1.15 / 12  # 15% annual interest
                st.write(f"Monthly Payment: ${monthly_payment:,.2f}")
            
            with col3:
                st.markdown("**Progress**")
                # Mock progress calculation
                days_since_disbursement = (datetime.now() - disbursement_date).days
                months_elapsed = max(0, days_since_disbursement / 30)
                progress = min(100, months_elapsed / 12 * 100)
                
                st.progress(progress / 100)
                st.write(f"Progress: {progress:.1f}%")
                
                remaining_amount = loan.get('amount', 0) * 1.15 * (1 - progress/100)
                st.write(f"Remaining: ${remaining_amount:,.2f}")
            
            # Action buttons
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"Make Payment", key=f"pay_{i}"):
                    show_payment_interface(loan, i)
            
            with col2:
                if st.button(f"View Schedule", key=f"schedule_{i}"):
                    show_loan_schedule(loan, i)
            
            with col3:
                if st.button(f"Transaction History", key=f"history_{i}"):
                    show_loan_transactions(loan, i)

def show_payment_interface(loan, loan_index):
    """Show payment interface for a specific loan"""
    st.subheader(f"💳 Make Payment - Loan #{loan_index + 1}")
    
    monthly_payment = loan.get('amount', 0) * 1.15 / 12
    
    col1, col2 = st.columns(2)
    
    with col1:
        payment_amount = st.number_input(
            "Payment Amount (USD)",
            min_value=1.0,
            max_value=float(loan.get('amount', 0) * 1.15),
            value=monthly_payment,
            format="%.2f"
        )
        
        payment_method = st.selectbox(
            "Payment Method",
            ["Mobile Money", "Bank Transfer", "Cash"]
        )
        
        phone_number = st.text_input(
            "Mobile Money Number",
            value="",
            help="Enter your Mobile Money account number"
        )
    
    with col2:
        st.markdown("**Payment Summary**")
        st.write(f"Loan Amount: ${loan.get('amount', 0):,.2f}")
        st.write(f"Suggested Payment: ${monthly_payment:,.2f}")
        st.write(f"Payment Amount: ${payment_amount:,.2f}")
        
        if payment_amount >= monthly_payment:
            st.success("✅ Full monthly payment")
        else:
            st.warning("⚠️ Partial payment")
    
    if st.button("Process Payment", type="primary"):
        process_loan_payment(loan, payment_amount, payment_method, phone_number)

def process_loan_payment(loan, amount, method, phone_number):
    """Process loan payment through Mobile Money"""
    
    with st.spinner("Processing payment..."):
        if method == "Mobile Money":
            # Validate phone number
            is_valid, validation_msg = momo_client.validate_phone_number(phone_number)
            
            if not is_valid:
                st.error(f"Payment failed: {validation_msg}")
                return
            
            # Simulate payment collection
            result = momo_client.collect_repayment(
                phone_number, amount, loan.get('id', 'unknown'), 1
            )
            
            if result["success"]:
                st.success("💰 Payment successful!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Transaction ID:** {result['transaction_id']}")
                    st.info(f"**Amount:** ${result['amount_collected']:,.2f}")
                with col2:
                    st.info(f"**Payment Date:** {result['timestamp'][:10]}")
                    st.info(f"**Status:** {result['status'].title()}")
                
                # Update loan record (in a real app, this would update the database)
                st.balloons()
                
            else:
                st.error(f"Payment failed: {result['error']}")
                
        else:
            # Mock other payment methods
            st.success(f"Payment of ${amount:,.2f} processed via {method}")
            st.info("Payment will be processed within 1-2 business days.")

def show_payment_schedule():
    """Display payment schedule for all loans"""
    st.subheader("📅 Payment Schedule")
    
    try:
        loans = db_manager.get_loans()
        active_loans = [loan for loan in loans if loan.get('status') == 'active']
    except Exception as e:
        st.error(f"Error loading payment schedule: {e}")
        return
    
    if not active_loans:
        st.info("No active loans with payment schedules.")
        return
    
    # Generate mock payment schedule
    schedule_data = []
    
    for i, loan in enumerate(active_loans):
        disbursement_date = datetime.fromisoformat(loan.get('disbursement_date', datetime.now().isoformat()))
        monthly_payment = loan.get('amount', 0) * 1.15 / 12
        
        for month in range(12):  # 12-month term
            payment_date = disbursement_date + timedelta(days=30 * (month + 1))
            
            # Mock payment status
            if payment_date < datetime.now():
                status = "Paid" if month < 2 else "Overdue"  # Assume first 2 payments made
            elif payment_date <= datetime.now() + timedelta(days=7):
                status = "Due Soon"
            else:
                status = "Pending"
            
            schedule_data.append({
                'Loan': f"Loan #{i+1}",
                'Payment #': month + 1,
                'Due Date': payment_date.strftime('%Y-%m-%d'),
                'Amount': f"${monthly_payment:,.2f}",
                'Status': status,
                'Days Until Due': (payment_date - datetime.now()).days
            })
    
    schedule_df = pd.DataFrame(schedule_data)
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        loan_filter = st.selectbox("Filter by Loan", ["All"] + list(schedule_df['Loan'].unique()))
    
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All"] + list(schedule_df['Status'].unique()))
    
    with col3:
        period_filter = st.selectbox("Period", ["All", "Next 30 Days", "Overdue"])
    
    # Apply filters
    filtered_df = schedule_df.copy()
    
    if loan_filter != "All":
        filtered_df = filtered_df[filtered_df['Loan'] == loan_filter]
    
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
    
    if period_filter == "Next 30 Days":
        filtered_df = filtered_df[filtered_df['Days Until Due'] <= 30]
    elif period_filter == "Overdue":
        filtered_df = filtered_df[filtered_df['Status'] == 'Overdue']
    
    # Display schedule
    st.dataframe(
        filtered_df[['Loan', 'Payment #', 'Due Date', 'Amount', 'Status']],
        use_container_width=True
    )
    
    # Upcoming payments alert
    upcoming = filtered_df[filtered_df['Status'] == 'Due Soon']
    if len(upcoming) > 0:
        st.warning(f"⚠️ You have {len(upcoming)} payments due within 7 days!")
        
        for idx in range(len(upcoming)):
            payment = upcoming.iloc[idx]
            st.write(f"• {payment['Loan']}: {payment['Amount']} due on {payment['Due Date']}")

def show_payment_history():
    """Display payment history and analytics"""
    st.subheader("📊 Payment History & Analytics")
    
    try:
        loans = db_manager.get_loans()
    except Exception as e:
        st.error(f"Error loading payment history: {e}")
        return
    
    if not loans:
        st.info("No payment history available.")
        return
    
    # Mock payment history data
    payment_history = []
    
    for i, loan in enumerate(loans):
        disbursement_date = datetime.fromisoformat(loan.get('disbursement_date', datetime.now().isoformat()))
        monthly_payment = loan.get('amount', 0) * 1.15 / 12
        
        # Generate 2-3 mock payments
        for payment_num in range(min(3, int((datetime.now() - disbursement_date).days / 30) + 1)):
            payment_date = disbursement_date + timedelta(days=30 * payment_num + 5)  # 5 days after due
            
            payment_history.append({
                'Loan': f"Loan #{i+1}",
                'Date': payment_date.strftime('%Y-%m-%d'),
                'Amount': monthly_payment,
                'Method': 'Mobile Money',
                'Status': 'Completed',
                'Transaction ID': f"PAY_{payment_date.strftime('%Y%m%d')}_{i}_{payment_num}"
            })
    
    if not payment_history:
        st.info("No payments recorded yet.")
        return
    
    # Payment history table
    history_df = pd.DataFrame(payment_history)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Payment summary metrics
        total_paid = history_df['Amount'].sum()
        avg_payment = history_df['Amount'].mean()
        payment_count = len(history_df)
        
        st.metric("Total Paid", f"${total_paid:,.2f}")
        st.metric("Average Payment", f"${avg_payment:,.2f}")
        st.metric("Payments Made", payment_count)
    
    with col2:
        # Payment methods chart
        method_counts = history_df['Method'].value_counts()
        
        fig = px.pie(
            values=method_counts.values,
            names=method_counts.index,
            title="Payment Methods Used"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Payment timeline
    history_df['Date'] = pd.to_datetime(history_df['Date'])
    
    fig = px.scatter(
        history_df,
        x='Date',
        y='Amount',
        color='Loan',
        size='Amount',
        title="Payment Timeline",
        labels={'Date': 'Payment Date', 'Amount': 'Payment Amount ($)'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Payment history table
    st.markdown("### Payment Records")
    st.dataframe(
        history_df[['Date', 'Loan', 'Amount', 'Method', 'Status', 'Transaction ID']],
        use_container_width=True
    )
    
    # Download option
    if st.button("📄 Download Payment History"):
        csv = history_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"payment_history_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def show_loan_schedule(loan, loan_index):
    """Show detailed schedule for a specific loan"""
    st.subheader(f"📋 Repayment Schedule - Loan #{loan_index + 1}")
    
    # Generate detailed schedule
    disbursement_date = datetime.fromisoformat(loan.get('disbursement_date', datetime.now().isoformat()))
    principal = loan.get('amount', 0)
    annual_rate = 0.15  # 15% annual interest
    monthly_rate = annual_rate / 12
    months = 12
    
    # Calculate monthly payment
    monthly_payment = principal * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
    
    schedule = []
    remaining_balance = principal
    
    for month in range(months):
        payment_date = disbursement_date + timedelta(days=30 * (month + 1))
        
        interest_payment = remaining_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        remaining_balance -= principal_payment
        
        schedule.append({
            'Payment #': month + 1,
            'Due Date': payment_date.strftime('%Y-%m-%d'),
            'Payment Amount': f"${monthly_payment:,.2f}",
            'Principal': f"${principal_payment:,.2f}",
            'Interest': f"${interest_payment:,.2f}",
            'Remaining Balance': f"${max(0, remaining_balance):,.2f}",
            'Status': 'Paid' if month < 2 else ('Overdue' if payment_date < datetime.now() else 'Pending')
        })
    
    schedule_df = pd.DataFrame(schedule)
    st.dataframe(schedule_df, use_container_width=True)
    
    # Summary
    total_interest = monthly_payment * months - principal
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Principal Amount", f"${principal:,.2f}")
    with col2:
        st.metric("Total Interest", f"${total_interest:,.2f}")
    with col3:
        st.metric("Total Repayment", f"${monthly_payment * months:,.2f}")

def show_loan_transactions(loan, loan_index):
    """Show transaction history for a specific loan"""
    st.subheader(f"💳 Transaction History - Loan #{loan_index + 1}")
    
    # Get transactions from MoMo client
    transaction_history = momo_client.get_transaction_history(loan_id=loan.get('id'))
    
    if transaction_history["success"] and transaction_history["transactions"]:
        transactions_df = pd.DataFrame(transaction_history["transactions"])
        
        st.dataframe(
            transactions_df[['timestamp', 'type', 'amount_disbursed', 'status', 'transaction_id']],
            use_container_width=True
        )
    else:
        st.info("No transaction history found for this loan.")
        
        # Show mock transaction
        st.markdown("### Disbursement Record")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Transaction ID:** {loan.get('transaction_id', 'N/A')}")
            st.write(f"**Amount:** ${loan.get('amount', 0):,.2f}")
            st.write(f"**Type:** Disbursement")
        
        with col2:
            st.write(f"**Date:** {loan.get('disbursement_date', 'N/A')[:10]}")
            st.write(f"**Status:** Completed")
            st.write(f"**Method:** Mobile Money")

if __name__ == "__main__":
    main()
