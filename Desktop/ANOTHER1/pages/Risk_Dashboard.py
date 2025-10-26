import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import db_manager

st.set_page_config(
    page_title="Risk Dashboard",
    page_icon="📊",
    layout="wide"
)

def main():
    st.title("📊 Risk Analysis Dashboard")
    st.markdown("Comprehensive risk assessment and portfolio analytics powered by AI insights.")
    
    # Check if there's any data in database
    try:
        applications = db_manager.get_applications()
        if not applications:
            st.info("📝 No applications yet. Submit a loan application to see risk analytics here.")
            return
    except Exception as e:
        st.error(f"Error loading applications: {e}")
        return
    
    # Portfolio overview
    show_portfolio_overview()
    
    st.markdown("---")
    
    # Risk analytics tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Credit Score Analysis", 
        "⚠️ Risk Distribution", 
        "📈 Trends & Patterns",
        "🔍 Individual Assessment"
    ])
    
    with tab1:
        show_credit_score_analysis()
    
    with tab2:
        show_risk_distribution()
    
    with tab3:
        show_trends_analysis()
    
    with tab4:
        show_individual_assessment()

def show_portfolio_overview():
    """Display high-level portfolio metrics"""
    st.subheader("🏦 Portfolio Overview")
    
    try:
        applications = db_manager.get_applications()
        loans = db_manager.get_loans()
    except Exception as e:
        st.error(f"Error loading portfolio data: {e}")
        return
    
    # Calculate metrics
    total_apps = len(applications)
    approved_apps = len([app for app in applications if app.get('decision') == 'approved'])
    rejected_apps = len([app for app in applications if app.get('decision') == 'rejected'])
    pending_apps = len([app for app in applications if app.get('decision') == 'pending'])
    
    total_requested = sum([app.get('loan_amount', 0) for app in applications])
    total_approved = sum([app.get('suggested_loan_amount', 0) for app in applications if app.get('decision') == 'approved'])
    
    avg_credit_score = np.mean([app.get('credit_score', 500) for app in applications if app.get('credit_score')])
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Applications",
            total_apps,
            delta=f"+{len([app for app in applications if (datetime.now() - datetime.fromisoformat(app['timestamp'])).days <= 7])}"
        )
    
    with col2:
        approval_rate = (approved_apps / total_apps * 100) if total_apps > 0 else 0
        st.metric("Approval Rate", f"{approval_rate:.1f}%")
    
    with col3:
        st.metric("Avg Credit Score", f"{avg_credit_score:.0f}")
    
    with col4:
        st.metric("Total Requested", f"${total_requested:,.0f}")
    
    # Status breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        # Application status pie chart
        status_data = {
            'Approved': approved_apps,
            'Rejected': rejected_apps,
            'Pending': pending_apps
        }
        
        fig = px.pie(
            values=list(status_data.values()),
            names=list(status_data.keys()),
            title="Application Status Distribution",
            color_discrete_map={
                'Approved': '#2E8B57',
                'Rejected': '#DC143C',
                'Pending': '#FF8C00'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Risk level distribution
        risk_levels = [app.get('risk_level', 'UNKNOWN') for app in applications if app.get('risk_level')]
        if risk_levels:
            risk_counts = pd.Series(risk_levels).value_counts()
            
            fig = px.bar(
                x=risk_counts.index,
                y=risk_counts.values,
                title="Risk Level Distribution",
                color=risk_counts.index,
                color_discrete_map={
                    'LOW': '#2E8B57',
                    'MEDIUM': '#FF8C00',
                    'HIGH': '#DC143C'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

def show_credit_score_analysis():
    """Detailed credit score analytics"""
    st.subheader("🎯 Credit Score Analysis")
    
    try:
        applications = db_manager.get_applications()
        scored_apps = [app for app in applications if app.get('credit_score')]
    except Exception as e:
        st.error(f"Error loading credit score data: {e}")
        return
    
    if not scored_apps:
        st.info("No credit score data available yet.")
        return
    
    scores_df = pd.DataFrame(scored_apps)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Credit score distribution histogram
        fig = px.histogram(
            scores_df,
            x='credit_score',
            nbins=20,
            title="Credit Score Distribution",
            labels={'credit_score': 'Credit Score', 'count': 'Frequency'}
        )
        fig.add_vline(x=600, line_dash="dash", line_color="orange", annotation_text="Fair Credit")
        fig.add_vline(x=700, line_dash="dash", line_color="green", annotation_text="Good Credit")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Credit score vs loan amount scatter
        fig = px.scatter(
            scores_df,
            x='credit_score',
            y='loan_amount',
            color='risk_level',
            size='suggested_loan_amount',
            title="Credit Score vs Loan Amount",
            color_discrete_map={
                'LOW': '#2E8B57',
                'MEDIUM': '#FF8C00',
                'HIGH': '#DC143C'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Credit score statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Average Score", f"{scores_df['credit_score'].mean():.0f}")
    with col2:
        st.metric("Median Score", f"{scores_df['credit_score'].median():.0f}")
    with col3:
        st.metric("Highest Score", f"{scores_df['credit_score'].max():.0f}")
    with col4:
        st.metric("Lowest Score", f"{scores_df['credit_score'].min():.0f}")

def show_risk_distribution():
    """Risk factor analysis"""
    st.subheader("⚠️ Risk Distribution Analysis")
    
    try:
        applications = db_manager.get_applications()
    except Exception as e:
        st.error(f"Error loading risk data: {e}")
        return
    
    if not applications:
        st.info("No application data available for risk analysis.")
        return
    
    df = pd.DataFrame(applications)
    
    # Risk factors analysis
    col1, col2 = st.columns(2)
    
    with col1:
        # Debt-to-income ratio distribution
        debt_ratios = []
        for app in applications:
            income = app.get('monthly_income', 0)
            expenses = app.get('monthly_expenses', 0)
            debt = app.get('current_debt', 0)
            if income > 0:
                ratio = (expenses + debt/12) / income
                debt_ratios.append(min(ratio, 2))  # Cap at 200%
        
        if debt_ratios:
            fig = px.histogram(
                debt_ratios,
                nbins=15,
                title="Debt-to-Income Ratio Distribution",
                labels={'value': 'Debt-to-Income Ratio', 'count': 'Frequency'}
            )
            fig.add_vline(x=0.3, line_dash="dash", line_color="green", annotation_text="Healthy (<30%)")
            fig.add_vline(x=0.5, line_dash="dash", line_color="orange", annotation_text="Risky (>50%)")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Employment stability
        if 'employment_years' in df.columns:
            fig = px.histogram(
                df,
                x='employment_years',
                title="Employment Years Distribution",
                labels={'employment_years': 'Years of Employment', 'count': 'Frequency'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Risk factors heatmap
    st.subheader("🔥 Risk Factor Analysis")
    
    # Create risk factors matrix
    risk_factors = []
    for app in applications:
        factors = {
            'High Debt Ratio': 1 if (app.get('monthly_expenses', 0) + app.get('current_debt', 0)/12) / max(app.get('monthly_income', 1), 1) > 0.5 else 0,
            'Low Income': 1 if app.get('monthly_income', 0) < 1000 else 0,
            'Short Employment': 1 if app.get('employment_years', 0) < 1 else 0,
            'Poor Credit History': 1 if app.get('credit_history', '').lower() in ['poor', 'no credit history'] else 0,
            'Large Loan Request': 1 if app.get('loan_amount', 0) > app.get('monthly_income', 1) * 6 else 0,
            'High Age': 1 if app.get('age', 0) > 60 else 0,
            'Many Dependents': 1 if app.get('dependents', 0) > 4 else 0
        }
        risk_factors.append(factors)
    
    if risk_factors:
        risk_df = pd.DataFrame(risk_factors)
        risk_summary = risk_df.sum().sort_values(ascending=False)
        
        fig = px.bar(
            x=risk_summary.values,
            y=risk_summary.index,
            orientation='h',
            title="Most Common Risk Factors",
            labels={'x': 'Number of Applicants', 'y': 'Risk Factor'}
        )
        st.plotly_chart(fig, use_container_width=True)

def show_trends_analysis():
    """Time-based trends analysis"""
    st.subheader("📈 Trends & Patterns Analysis")
    
    try:
        applications = db_manager.get_applications()
    except Exception as e:
        st.error(f"Error loading trends data: {e}")
        return
    
    if not applications:
        st.info("No historical data available for trend analysis.")
        return
    
    # Convert to DataFrame with datetime
    df = pd.DataFrame(applications)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Applications over time
        daily_apps = df.groupby('date').size().reset_index()
        daily_apps.columns = ['date', 'count']
        
        fig = px.line(
            daily_apps,
            x='date',
            y='count',
            title="Applications Over Time",
            labels={'date': 'Date', 'count': 'Number of Applications'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Average credit score over time
        if 'credit_score' in df.columns:
            daily_scores = df.groupby('date')['credit_score'].mean().reset_index()
            
            fig = px.line(
                daily_scores,
                x='date',
                y='credit_score',
                title="Average Credit Score Trend",
                labels={'date': 'Date', 'credit_score': 'Average Credit Score'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Loan purpose analysis
    if 'loan_purpose' in df.columns:
        purpose_counts = df['loan_purpose'].value_counts()
        
        fig = px.pie(
            values=purpose_counts.values,
            names=purpose_counts.index,
            title="Loan Purpose Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)

def show_individual_assessment():
    """Individual application assessment viewer"""
    st.subheader("🔍 Individual Assessment Review")
    
    try:
        applications = db_manager.get_applications()
    except Exception as e:
        st.error(f"Error loading assessment data: {e}")
        return
    
    if not applications:
        st.info("No applications available for individual review.")
        return
    
    # Application selector
    app_options = [f"{app['full_name']} - {app['timestamp'][:10]} (${app['loan_amount']:,.0f})" 
                   for app in applications]
    
    selected_app_idx = st.selectbox("Select Application to Review:", range(len(app_options)), 
                                   format_func=lambda x: app_options[x])
    
    if selected_app_idx is not None:
        app = applications[selected_app_idx]
        
        # Application details
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 👤 Applicant Information")
            st.write(f"**Name:** {app['full_name']}")
            st.write(f"**Age:** {app['age']}")
            st.write(f"**Employment:** {app['employment_status']}")
            st.write(f"**Experience:** {app['employment_years']} years")
            st.write(f"**Monthly Income:** ${app['monthly_income']:,.2f}")
            st.write(f"**Monthly Expenses:** ${app['monthly_expenses']:,.2f}")
            st.write(f"**Current Debt:** ${app.get('current_debt', 0):,.2f}")
        
        with col2:
            st.markdown("### 💰 Loan Details")
            st.write(f"**Amount Requested:** ${app['loan_amount']:,.2f}")
            st.write(f"**Purpose:** {app['loan_purpose']}")
            st.write(f"**Repayment Term:** {app['repayment_term']}")
            st.write(f"**Credit History:** {app['credit_history']}")
            
            if app.get('credit_score'):
                st.markdown("### 🎯 AI Assessment")
                st.write(f"**Credit Score:** {app['credit_score']}/850")
                st.write(f"**Risk Level:** {app['risk_level']}")
                st.write(f"**Decision:** {app['decision'].upper()}")
                st.write(f"**Confidence:** {app.get('confidence_score', 0)*100:.1f}%")
        
        # Risk factors
        if app.get('key_factors'):
            st.markdown("### ⚠️ Key Risk Factors")
            for factor in app['key_factors']:
                st.write(f"• {factor}")
        
        # Detailed reasoning
        if app.get('reasoning'):
            st.markdown("### 📋 AI Reasoning")
            st.write(app['reasoning'])
        
        # Financial metrics visualization
        if app.get('credit_score'):
            st.markdown("### 📊 Financial Health Radar")
            
            # Create radar chart
            categories = ['Credit Score', 'Income Level', 'Employment Stability', 
                         'Debt Management', 'Loan Affordability']
            
            # Normalize scores to 0-5 scale
            scores = [
                app['credit_score'] / 170,  # 850 max -> 5 scale
                min(5, app['monthly_income'] / 1000),  # $5000+ -> 5
                min(5, app['employment_years']),  # 5+ years -> 5
                5 - min(5, (app.get('current_debt', 0) + app['monthly_expenses']) / 
                       max(app['monthly_income'], 1) * 5),  # Lower debt ratio -> higher score
                5 - min(5, app['loan_amount'] / max(app['monthly_income'] * 12, 1) * 5)  # Lower loan ratio -> higher score
            ]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=scores,
                theta=categories,
                fill='toself',
                name='Financial Profile'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 5]
                    )),
                showlegend=True,
                title="Financial Health Assessment"
            )
            
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
