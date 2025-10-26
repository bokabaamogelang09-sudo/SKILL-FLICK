import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def calculate_ai_credit_score(application_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate AI-based credit score using application data
    
    Returns a comprehensive credit analysis including:
    - Credit score (300-850)
    - Risk level (LOW, MEDIUM, HIGH)
    - Approval recommendation
    - Suggested loan amount
    - Confidence score
    """
    
    try:
        # Extract key financial metrics
        monthly_income = float(application_data.get('monthly_income', 0))
        monthly_expenses = float(application_data.get('monthly_expenses', 0))
        current_debt = float(application_data.get('current_debt', 0))
        requested_amount = float(application_data.get('amount', 0))
        employment_years = int(application_data.get('employment_years', 0))
        age = int(application_data.get('age', 25))
        savings_amount = float(application_data.get('savings_amount', 0))
        dependents = int(application_data.get('dependents', 0))
        
        # Calculate derived metrics
        net_income = monthly_income - monthly_expenses
        debt_to_income_ratio = current_debt / (monthly_income * 12) if monthly_income > 0 else 1.0
        
        # Initialize base score
        credit_score = 500  # Start with neutral score
        
        # 1. Income Analysis (25% weight)
        if monthly_income >= 2000:
            credit_score += 80
        elif monthly_income >= 1000:
            credit_score += 60
        elif monthly_income >= 500:
            credit_score += 40
        elif monthly_income >= 250:
            credit_score += 20
        else:
            credit_score -= 20
        
        # 2. Debt-to-Income Ratio (20% weight)
        if debt_to_income_ratio < 0.2:
            credit_score += 70
        elif debt_to_income_ratio < 0.4:
            credit_score += 40
        elif debt_to_income_ratio < 0.6:
            credit_score += 10
        else:
            credit_score -= 50
        
        # 3. Employment Stability (15% weight)
        if employment_years >= 5:
            credit_score += 60
        elif employment_years >= 3:
            credit_score += 40
        elif employment_years >= 1:
            credit_score += 20
        else:
            credit_score -= 10
        
        # 4. Age Factor (10% weight)
        if 25 <= age <= 45:
            credit_score += 30
        elif 18 <= age <= 65:
            credit_score += 20
        else:
            credit_score += 5
        
        # 5. Savings Capacity (10% weight)
        savings_ratio = savings_amount / (monthly_income * 12) if monthly_income > 0 else 0
        if savings_ratio >= 0.2:
            credit_score += 40
        elif savings_ratio >= 0.1:
            credit_score += 25
        elif savings_ratio >= 0.05:
            credit_score += 15
        
        # 6. Credit History (10% weight)
        credit_history = application_data.get('credit_history', 'No Credit History')
        credit_history_scores = {
            'Excellent': 50,
            'Good': 35,
            'Fair': 15,
            'Poor': -20,
            'No Credit History': 0
        }
        credit_score += credit_history_scores.get(credit_history, 0)
        
        # 7. Employment Status (5% weight)
        employment_status = application_data.get('employment_status', '')
        employment_scores = {
            'Employed': 20,
            'Business Owner': 15,
            'Self-Employed': 10,
            'Farmer': 10,
            'Student': 5,
            'Unemployed': -30
        }
        credit_score += employment_scores.get(employment_status, 0)
        
        # 8. Dependents Factor (5% weight)
        if dependents == 0:
            credit_score += 15
        elif dependents <= 2:
            credit_score += 5
        else:
            credit_score -= 10
        
        # Ensure score is within bounds
        credit_score = max(300, min(850, credit_score))
        
        # Determine risk level
        if credit_score >= 700:
            risk_level = "LOW"
        elif credit_score >= 600:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"
        
        # Calculate loan affordability
        max_affordable_payment = net_income * 0.3  # 30% of net income
        max_loan_amount = calculate_max_loan_amount(max_affordable_payment, 0.15, 12)  # 15% annual rate, 12 months
        
        # Determine approval and suggested amount
        if credit_score >= 650 and debt_to_income_ratio < 0.5 and net_income > 0:
            approval_recommendation = "APPROVED"
            suggested_amount = min(requested_amount, max_loan_amount)
        elif credit_score >= 550 and debt_to_income_ratio < 0.7:
            approval_recommendation = "CONDITIONAL"
            suggested_amount = min(requested_amount * 0.7, max_loan_amount)
        else:
            approval_recommendation = "REJECTED"
            suggested_amount = 0
        
        # Calculate confidence score based on data completeness and consistency
        confidence_factors = []
        
        # Data completeness
        required_fields = ['monthly_income', 'monthly_expenses', 'employment_years', 'age']
        completeness = sum(1 for field in required_fields if application_data.get(field, 0) > 0) / len(required_fields)
        confidence_factors.append(completeness)
        
        # Data consistency
        if monthly_income > monthly_expenses:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.5)
        
        # Reasonable loan amount
        if 0 < requested_amount <= monthly_income * 6:  # Max 6 months of income
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.7)
        
        confidence_score = sum(confidence_factors) / len(confidence_factors)
        
        return {
            'credit_score': credit_score,
            'risk_level': risk_level,
            'approval_recommendation': approval_recommendation,
            'suggested_loan_amount': round(suggested_amount, 2),
            'max_affordable_amount': round(max_loan_amount, 2),
            'confidence_score': round(confidence_score, 2),
            'debt_to_income_ratio': round(debt_to_income_ratio, 3),
            'monthly_affordability': round(max_affordable_payment, 2),
            'assessment_date': datetime.utcnow().isoformat(),
            'key_factors': {
                'income_score': monthly_income,
                'stability_years': employment_years,
                'debt_ratio': debt_to_income_ratio,
                'savings_ratio': savings_ratio,
                'net_income': net_income
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating credit score: {str(e)}")
        
        # Return conservative default assessment
        return {
            'credit_score': 400,
            'risk_level': "HIGH",
            'approval_recommendation': "REJECTED",
            'suggested_loan_amount': 0,
            'max_affordable_amount': 0,
            'confidence_score': 0.1,
            'debt_to_income_ratio': 1.0,
            'monthly_affordability': 0,
            'assessment_date': datetime.utcnow().isoformat(),
            'error': str(e)
        }

def calculate_max_loan_amount(monthly_payment: float, annual_rate: float, term_months: int) -> float:
    """Calculate maximum loan amount based on monthly payment capacity"""
    if monthly_payment <= 0 or annual_rate <= 0 or term_months <= 0:
        return 0
    
    monthly_rate = annual_rate / 12
    
    if monthly_rate == 0:
        return monthly_payment * term_months
    
    # Present value of annuity formula
    pv = monthly_payment * ((1 - (1 + monthly_rate) ** -term_months) / monthly_rate)
    return max(0, pv)

def generate_risk_explanation(credit_analysis: Dict[str, Any]) -> str:
    """Generate human-readable explanation of the credit assessment"""
    
    score = credit_analysis.get('credit_score', 400)
    risk_level = credit_analysis.get('risk_level', 'HIGH')
    approval = credit_analysis.get('approval_recommendation', 'REJECTED')
    suggested_amount = credit_analysis.get('suggested_loan_amount', 0)
    key_factors = credit_analysis.get('key_factors', {})
    
    explanation = f"""
## Credit Assessment Summary

**Credit Score: {score}/850** | **Risk Level: {risk_level}** | **Decision: {approval}**

### Key Assessment Factors:

"""
    
    # Income Analysis
    income = key_factors.get('income_score', 0)
    if income >= 2000:
        explanation += "✅ **Strong Income**: Monthly income of ${:,.2f} demonstrates good earning capacity.\n".format(income)
    elif income >= 500:
        explanation += "⚠️ **Moderate Income**: Monthly income of ${:,.2f} is acceptable but limits loan capacity.\n".format(income)
    else:
        explanation += "❌ **Low Income**: Monthly income of ${:,.2f} is below recommended minimum.\n".format(income)
    
    # Debt Analysis
    debt_ratio = credit_analysis.get('debt_to_income_ratio', 1.0)
    if debt_ratio < 0.3:
        explanation += "✅ **Low Debt Burden**: Debt-to-income ratio of {:.1%} is excellent.\n".format(debt_ratio)
    elif debt_ratio < 0.5:
        explanation += "⚠️ **Moderate Debt**: Debt-to-income ratio of {:.1%} is manageable.\n".format(debt_ratio)
    else:
        explanation += "❌ **High Debt Burden**: Debt-to-income ratio of {:.1%} is concerning.\n".format(debt_ratio)
    
    # Employment Stability
    employment_years = key_factors.get('stability_years', 0)
    if employment_years >= 3:
        explanation += "✅ **Stable Employment**: {} years of employment history shows stability.\n".format(employment_years)
    elif employment_years >= 1:
        explanation += "⚠️ **Moderate Stability**: {} years of employment is acceptable.\n".format(employment_years)
    else:
        explanation += "❌ **Limited Employment History**: Less than 1 year employment increases risk.\n"
    
    # Affordability
    affordability = credit_analysis.get('monthly_affordability', 0)
    if affordability > 0:
        explanation += f"\n**Monthly Affordability**: ${affordability:.2f} available for loan payments.\n"
    
    # Decision Explanation
    explanation += f"\n### Decision Rationale:\n\n"
    
    if approval == "APPROVED":
        explanation += f"""
**LOAN APPROVED** for ${suggested_amount:,.2f}

Your application demonstrates:
- Sufficient income to support repayments
- Manageable debt levels
- Stable employment history
- Low risk profile

**Next Steps**: Proceed with loan disbursement and setup repayment schedule.
"""
    elif approval == "CONDITIONAL":
        explanation += f"""
**CONDITIONAL APPROVAL** for ${suggested_amount:,.2f}

Your application shows potential but with some concerns:
- May require additional documentation
- Reduced loan amount for risk management
- Close monitoring of repayment performance

**Next Steps**: Review terms and provide any requested additional information.
"""
    else:
        explanation += f"""
**LOAN REJECTED**

Your application does not currently meet our lending criteria:
- Income may be insufficient for requested amount
- Debt burden is too high relative to income
- Employment history needs strengthening
- High risk of repayment difficulties

**Next Steps**: Consider improving your financial profile and reapply in 3-6 months.
"""
    
    # Add confidence note
    confidence = credit_analysis.get('confidence_score', 0)
    if confidence >= 0.8:
        explanation += f"\n*Assessment Confidence: High ({confidence*100:.0f}%) - Based on complete and consistent data.*"
    elif confidence >= 0.6:
        explanation += f"\n*Assessment Confidence: Medium ({confidence*100:.0f}%) - Some data gaps or inconsistencies noted.*"
    else:
        explanation += f"\n*Assessment Confidence: Low ({confidence*100:.0f}%) - Limited or inconsistent data affects reliability.*"
    
    return explanation

def get_risk_factors(application_data: Dict[str, Any]) -> Dict[str, str]:
    """Identify specific risk factors in the application"""
    
    risk_factors = {}
    
    monthly_income = float(application_data.get('monthly_income', 0))
    monthly_expenses = float(application_data.get('monthly_expenses', 0))
    current_debt = float(application_data.get('current_debt', 0))
    employment_years = int(application_data.get('employment_years', 0))
    requested_amount = float(application_data.get('amount', 0))
    
    # Income risks
    if monthly_income < 300:
        risk_factors['income'] = "Very low monthly income increases default risk"
    
    # Cash flow risks
    net_income = monthly_income - monthly_expenses
    if net_income <= 0:
        risk_factors['cashflow'] = "Expenses exceed income - negative cash flow"
    elif net_income < requested_amount * 0.1:
        risk_factors['cashflow'] = "Very tight cash flow for loan repayment"
    
    # Debt risks
    if current_debt > monthly_income * 6:
        risk_factors['debt'] = "High existing debt burden"
    
    # Employment risks
    if employment_years < 1:
        risk_factors['employment'] = "Limited employment history"
    
    # Loan size risks
    if requested_amount > monthly_income * 3:
        risk_factors['loan_size'] = "Requested amount is high relative to income"
    
    return risk_factors

def calculate_repayment_schedule(loan_amount: float, annual_rate: float, term_months: int) -> list:
    """Calculate loan repayment schedule"""
    
    if loan_amount <= 0 or annual_rate <= 0 or term_months <= 0:
        return []
    
    monthly_rate = annual_rate / 12
    
    # Calculate monthly payment using loan formula
    if monthly_rate == 0:
        monthly_payment = loan_amount / term_months
    else:
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
    
    schedule = []
    remaining_balance = loan_amount
    
    for month in range(1, term_months + 1):
        interest_payment = remaining_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        remaining_balance -= principal_payment
        
        schedule.append({
            'month': month,
            'payment': round(monthly_payment, 2),
            'principal': round(principal_payment, 2),
            'interest': round(interest_payment, 2),
            'balance': round(max(0, remaining_balance), 2)
        })
    
    return schedule