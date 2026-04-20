from datetime import datetime, date
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class RepaymentType(Enum):
    FULL = "全额还款"
    MINIMUM = "最低还款"
    INSTALLMENT = "分期还款"

@dataclass
class Bill:
    id: int
    platform: str
    amount: float
    apr: float
    min_payment: float
    days_until_due: int
    installment_options: List[int]

@dataclass
class RepaymentPlan:
    bill_id: int
    platform: str
    original_amount: float
    repayment_type: RepaymentType
    payment_amount: float
    installment_months: Optional[int] = None
    interest_cost: float = 0.0
    monthly_payment: float = 0.0

class RepaymentOptimizer:
    def __init__(self):
        pass
    
    def calculate_daily_rate(self, apr: float) -> float:
        return apr / 100 / 365
    
    def calculate_monthly_rate(self, apr: float) -> float:
        return apr / 100 / 12
    
    def calculate_simple_interest(self, principal: float, apr: float, days: int) -> float:
        daily_rate = self.calculate_daily_rate(apr)
        return principal * daily_rate * days
    
    def calculate_min_payment_interest(self, bill: Bill, days_after_due: int = 30) -> float:
        remaining = bill.amount - bill.min_payment
        return self.calculate_simple_interest(remaining, bill.apr, days_after_due)
    
    def calculate_installment_interest(self, bill: Bill, months: int) -> float:
        monthly_rate = self.calculate_monthly_rate(bill.apr)
        if monthly_rate == 0:
            return 0
        
        monthly_payment = (bill.amount * monthly_rate * (1 + monthly_rate) ** months) / \
                         ((1 + monthly_rate) ** months - 1)
        
        total_payment = monthly_payment * months
        total_interest = total_payment - bill.amount
        
        return max(total_interest, 0)
    
    def calculate_full_payment_interest(self, bill: Bill) -> float:
        if bill.days_until_due >= 0:
            return 0
        else:
            overdue_days = abs(bill.days_until_due)
            return self.calculate_simple_interest(bill.amount, bill.apr, overdue_days)
    
    def prioritize_bills(self, bills: List[Bill]) -> List[Bill]:
        def priority_key(bill: Bill) -> tuple:
            is_overdue = bill.days_until_due < 0
            urgency_score = -bill.days_until_due if is_overdue else 0
            
            return (
                -is_overdue,
                urgency_score,
                -bill.apr,
                bill.amount
            )
        
        return sorted(bills, key=priority_key)
    
    def optimize_repayment(
        self, 
        bills: List[Bill], 
        available_cash: float
    ) -> Dict[str, Any]:
        if not bills:
            return {
                'success': False,
                'message': '没有账单需要处理',
                'plans': [],
                'total_interest': 0,
                'total_payment': 0,
                'remaining_cash': available_cash
            }
        
        prioritized_bills = self.prioritize_bills(bills)
        plans: List[RepaymentPlan] = []
        remaining_cash = available_cash
        total_interest = 0.0
        total_payment = 0.0
        
        for bill in prioritized_bills:
            if remaining_cash <= 0:
                if bill.days_until_due < 0:
                    interest = self.calculate_simple_interest(bill.amount, bill.apr, 30)
                else:
                    interest = self.calculate_simple_interest(bill.amount, bill.apr, bill.days_until_due + 30)
                
                plans.append(RepaymentPlan(
                    bill_id=bill.id,
                    platform=bill.platform,
                    original_amount=bill.amount,
                    repayment_type=RepaymentType.MINIMUM,
                    payment_amount=0,
                    interest_cost=interest,
                    monthly_payment=0
                ))
                total_interest += interest
                continue
            
            if remaining_cash >= bill.amount:
                interest = self.calculate_full_payment_interest(bill)
                plans.append(RepaymentPlan(
                    bill_id=bill.id,
                    platform=bill.platform,
                    original_amount=bill.amount,
                    repayment_type=RepaymentType.FULL,
                    payment_amount=bill.amount,
                    interest_cost=interest,
                    monthly_payment=bill.amount
                ))
                remaining_cash -= bill.amount
                total_payment += bill.amount
                total_interest += interest
                continue
            
            if remaining_cash >= bill.min_payment:
                best_option = None
                min_interest = float('inf')
                
                min_interest_cost = self.calculate_min_payment_interest(bill)
                best_option = {
                    'type': RepaymentType.MINIMUM,
                    'payment': bill.min_payment,
                    'interest': min_interest_cost,
                    'installment_months': None
                }
                min_interest = min_interest_cost
                
                for months in bill.installment_options:
                    if months <= 0:
                        continue
                    installment_interest = self.calculate_installment_interest(bill, months)
                    monthly_rate = self.calculate_monthly_rate(bill.apr)
                    
                    if monthly_rate > 0:
                        monthly_payment = (bill.amount * monthly_rate * (1 + monthly_rate) ** months) / \
                                        ((1 + monthly_rate) ** months - 1)
                    else:
                        monthly_payment = bill.amount / months
                    
                    first_payment = min(monthly_payment, remaining_cash)
                    
                    if installment_interest < min_interest:
                        min_interest = installment_interest
                        best_option = {
                            'type': RepaymentType.INSTALLMENT,
                            'payment': monthly_payment,
                            'interest': installment_interest,
                            'installment_months': months,
                            'monthly_payment': monthly_payment
                        }
                
                if best_option:
                    actual_payment = min(best_option['payment'], remaining_cash)
                    plans.append(RepaymentPlan(
                        bill_id=bill.id,
                        platform=bill.platform,
                        original_amount=bill.amount,
                        repayment_type=best_option['type'],
                        payment_amount=actual_payment,
                        installment_months=best_option.get('installment_months'),
                        interest_cost=best_option['interest'],
                        monthly_payment=best_option.get('monthly_payment', actual_payment)
                    ))
                    remaining_cash -= actual_payment
                    total_payment += actual_payment
                    total_interest += best_option['interest']
                continue
            
            if bill.days_until_due < 0:
                interest = self.calculate_simple_interest(bill.amount, bill.apr, 30)
            else:
                interest = self.calculate_simple_interest(bill.amount, bill.apr, bill.days_until_due + 30)
            
            plans.append(RepaymentPlan(
                bill_id=bill.id,
                platform=bill.platform,
                original_amount=bill.amount,
                repayment_type=RepaymentType.MINIMUM,
                payment_amount=0,
                interest_cost=interest,
                monthly_payment=0
            ))
            total_interest += interest
        
        result = {
            'success': True,
            'message': '还款方案已生成',
            'plans': [],
            'total_interest': round(total_interest, 2),
            'total_payment': round(total_payment, 2),
            'remaining_cash': round(remaining_cash, 2)
        }
        
        for plan in plans:
            plan_dict = {
                'bill_id': plan.bill_id,
                'platform': plan.platform,
                'original_amount': round(plan.original_amount, 2),
                'repayment_type': plan.repayment_type.value,
                'payment_amount': round(plan.payment_amount, 2),
                'interest_cost': round(plan.interest_cost, 2),
                'monthly_payment': round(plan.monthly_payment, 2)
            }
            
            if plan.installment_months:
                plan_dict['installment_months'] = plan.installment_months
            
            result['plans'].append(plan_dict)
        
        result['recommendation_text'] = self._generate_recommendation_text(result['plans'])
        
        return result
    
    def _generate_recommendation_text(self, plans: List[Dict]) -> str:
        recommendations = []
        
        for plan in plans:
            platform = plan['platform']
            repayment_type = plan['repayment_type']
            amount = plan['original_amount']
            payment = plan['payment_amount']
            
            if repayment_type == '全额还款':
                recommendations.append(f"【{platform}】全额还款 ¥{amount:,.2f}")
            elif repayment_type == '最低还款':
                if payment > 0:
                    recommendations.append(f"【{platform}】还最低 ¥{payment:,.2f}（剩余 ¥{amount - payment:,.2f} 将产生利息）")
                else:
                    recommendations.append(f"【{platform}】资金不足，建议先还最低 ¥{amount * 0.1:,.2f}")
            elif repayment_type == '分期还款':
                months = plan.get('installment_months', 3)
                monthly_payment = plan.get('monthly_payment', payment)
                recommendations.append(f"【{platform}】分{months}期，每期 ¥{monthly_payment:,.2f}")
        
        if not recommendations:
            return "暂无还款建议"
        
        return "\n".join(recommendations)
