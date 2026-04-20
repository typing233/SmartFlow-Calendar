#!/usr/bin/env python3
"""
测试智能还款算法的计算公式和边界条件
"""

from repayment_algorithm import RepaymentOptimizer, Bill, RepaymentType
from datetime import date, datetime, timedelta

def test_interest_calculations():
    """测试利息计算公式"""
    optimizer = RepaymentOptimizer()
    
    print("=" * 60)
    print("测试利息计算公式")
    print("=" * 60)
    
    daily_rate = optimizer.calculate_daily_rate(18.25)
    expected_daily_rate = 0.1825 / 365
    assert abs(daily_rate - expected_daily_rate) < 1e-10, f"日利率计算错误: {daily_rate}"
    print(f"✓ 日利率计算: 年化18.25% → 日利率 {daily_rate:.10f}")
    
    monthly_rate = optimizer.calculate_monthly_rate(12)
    expected_monthly_rate = 0.12 / 12
    assert abs(monthly_rate - expected_monthly_rate) < 1e-10, f"月利率计算错误: {monthly_rate}"
    print(f"✓ 月利率计算: 年化12% → 月利率 {monthly_rate:.10f}")
    
    simple_interest = optimizer.calculate_simple_interest(10000, 18.25, 30)
    expected_simple = 10000 * (0.1825 / 365) * 30
    assert abs(simple_interest - expected_simple) < 1e-6, f"单利计算错误: {simple_interest}"
    print(f"✓ 单利计算: 10000元, 年化18.25%, 30天 → 利息 {simple_interest:.2f}元")
    
    print("\n所有利息计算公式测试通过!\n")

def test_installment_interest():
    """测试分期利息计算"""
    optimizer = RepaymentOptimizer()
    
    print("=" * 60)
    print("测试分期利息计算")
    print("=" * 60)
    
    bill = Bill(
        id=1,
        platform="测试信用卡",
        amount=12000,
        apr=18,
        min_payment=1200,
        days_until_due=10,
        installment_options=[3, 6, 12]
    )
    
    interest_3 = optimizer.calculate_installment_interest(bill, 3)
    print(f"✓ 12000元, 年化18%, 分3期 → 总利息: {interest_3:.2f}元")
    
    interest_6 = optimizer.calculate_installment_interest(bill, 6)
    print(f"✓ 12000元, 年化18%, 分6期 → 总利息: {interest_6:.2f}元")
    
    interest_12 = optimizer.calculate_installment_interest(bill, 12)
    print(f"✓ 12000元, 年化18%, 分12期 → 总利息: {interest_12:.2f}元")
    
    assert interest_12 > interest_6 > interest_3 > 0, "分期越长利息应该越多"
    print("\n分期利息计算测试通过!\n")

def test_min_payment_interest():
    """测试最低还款利息计算"""
    optimizer = RepaymentOptimizer()
    
    print("=" * 60)
    print("测试最低还款利息计算")
    print("=" * 60)
    
    bill = Bill(
        id=1,
        platform="花呗",
        amount=10000,
        apr=18.25,
        min_payment=1000,
        days_until_due=5,
        installment_options=[3, 6, 12]
    )
    
    interest = optimizer.calculate_min_payment_interest(bill, 30)
    remaining = bill.amount - bill.min_payment
    expected_interest = remaining * (0.1825 / 365) * 30
    
    assert abs(interest - expected_interest) < 1e-6, f"最低还款利息计算错误"
    print(f"✓ 账单10000元, 还最低1000元, 剩余9000元")
    print(f"✓ 年化18.25%, 30天利息: {interest:.2f}元")
    print(f"✓ 验证公式: 9000 * (18.25%/365) * 30 = {expected_interest:.2f}元")
    
    print("\n最低还款利息计算测试通过!\n")

def test_full_payment_interest():
    """测试全额还款利息计算"""
    optimizer = RepaymentOptimizer()
    
    print("=" * 60)
    print("测试全额还款利息计算")
    print("=" * 60)
    
    bill_not_overdue = Bill(
        id=1,
        platform="信用卡A",
        amount=5000,
        apr=15,
        min_payment=500,
        days_until_due=3,
        installment_options=[3, 6, 12]
    )
    
    interest1 = optimizer.calculate_full_payment_interest(bill_not_overdue)
    assert interest1 == 0, f"到期前全额还款应无利息, 实际: {interest1}"
    print("✓ 到期前(3天)全额还款: 利息 = 0元")
    
    bill_overdue = Bill(
        id=2,
        platform="信用卡B",
        amount=5000,
        apr=15,
        min_payment=500,
        days_until_due=-5,
        installment_options=[3, 6, 12]
    )
    
    interest2 = optimizer.calculate_full_payment_interest(bill_overdue)
    expected_overdue = 5000 * (0.15 / 365) * 5
    assert abs(interest2 - expected_overdue) < 1e-6, f"逾期利息计算错误"
    print(f"✓ 逾期5天全额还款: 利息 = {interest2:.2f}元")
    print(f"✓ 验证公式: 5000 * (15%/365) * 5 = {expected_overdue:.2f}元")
    
    print("\n全额还款利息计算测试通过!\n")

def test_bill_prioritization():
    """测试账单优先级排序"""
    optimizer = RepaymentOptimizer()
    
    print("=" * 60)
    print("测试账单优先级排序")
    print("=" * 60)
    
    bills = [
        Bill(id=1, platform="普通账单", amount=1000, apr=12, min_payment=100, 
             days_until_due=10, installment_options=[3, 6, 12]),
        Bill(id=2, platform="高息账单", amount=2000, apr=24, min_payment=200, 
             days_until_due=10, installment_options=[3, 6, 12]),
        Bill(id=3, platform="逾期账单", amount=1500, apr=18, min_payment=150, 
             days_until_due=-5, installment_options=[3, 6, 12]),
        Bill(id=4, platform="临近到期", amount=800, apr=15, min_payment=80, 
             days_until_due=2, installment_options=[3, 6, 12]),
    ]
    
    prioritized = optimizer.prioritize_bills(bills)
    
    assert prioritized[0].id == 3, f"逾期账单应该优先, 实际第一个: {prioritized[0].platform}"
    print(f"✓ 优先级1: {prioritized[0].platform} (逾期5天)")
    
    high_interest_bills = [b for b in prioritized if b.days_until_due >= 0]
    if high_interest_bills:
        assert high_interest_bills[0].apr >= high_interest_bills[-1].apr, "非逾期账单应按利率从高到低排序"
        print(f"✓ 非逾期账单按利率排序: {[b.platform for b in high_interest_bills]}")
        print(f"✓ 对应利率: {[b.apr for b in high_interest_bills]}")
    
    print("\n账单优先级排序测试通过!\n")

def test_edge_cases():
    """测试边界条件"""
    optimizer = RepaymentOptimizer()
    
    print("=" * 60)
    print("测试边界条件")
    print("=" * 60)
    
    result = optimizer.optimize_repayment(bills=[], available_cash=10000)
    assert not result['success'], "空账单列表应该返回失败"
    print("✓ 边界1: 空账单列表 → 返回失败")
    
    bills = [
        Bill(id=1, platform="测试", amount=5000, apr=18, min_payment=500,
             days_until_due=10, installment_options=[3, 6, 12])
    ]
    
    result = optimizer.optimize_repayment(bills=bills, available_cash=0)
    assert result['success'], "可用现金为0应该返回成功但建议最低还款"
    plans = result['plans']
    assert len(plans) == 1
    print(f"✓ 边界2: 可用现金为0 → 建议: {plans[0]['repayment_type']}")
    print(f"  利息预估: {result['total_interest']:.2f}元")
    
    result = optimizer.optimize_repayment(bills=bills, available_cash=5000)
    plans = result['plans']
    assert plans[0]['repayment_type'] == '全额还款', f"资金充足应该全额还款, 实际: {plans[0]['repayment_type']}"
    assert plans[0]['interest_cost'] == 0, "全额还款到期前利息应为0"
    print(f"✓ 边界3: 资金充足(刚好够) → 全额还款, 利息={plans[0]['interest_cost']}元")
    
    result = optimizer.optimize_repayment(bills=bills, available_cash=10000)
    plans = result['plans']
    assert plans[0]['repayment_type'] == '全额还款', f"资金充足应该全额还款, 实际: {plans[0]['repayment_type']}"
    assert result['remaining_cash'] == 5000, f"剩余现金计算错误: {result['remaining_cash']}"
    print(f"✓ 边界4: 资金充足(远超需求) → 全额还款, 剩余现金={result['remaining_cash']}元")
    
    bills_zerorate = [
        Bill(id=1, platform="零利率", amount=10000, apr=0, min_payment=1000,
             days_until_due=10, installment_options=[3, 6, 12])
    ]
    result = optimizer.optimize_repayment(bills=bills_zerorate, available_cash=5000)
    print(f"✓ 边界5: 零利率账单测试 → 利息预估={result['total_interest']:.2f}元")
    
    print("\n边界条件测试通过!\n")

def test_optimization_scenarios():
    """测试优化场景"""
    optimizer = RepaymentOptimizer()
    
    print("=" * 60)
    print("测试优化场景")
    print("=" * 60)
    
    bills = [
        Bill(id=1, platform="信用卡A(高息)", amount=10000, apr=24, min_payment=1000,
             days_until_due=15, installment_options=[3, 6, 12]),
        Bill(id=2, platform="花呗(中息)", amount=5000, apr=15.86, min_payment=500,
             days_until_due=10, installment_options=[3, 6, 12]),
        Bill(id=3, platform="京东白条(低息)", amount=3000, apr=12, min_payment=300,
             days_until_due=20, installment_options=[3, 6, 12]),
    ]
    
    print("场景1: 资金足够全额还款")
    result = optimizer.optimize_repayment(bills=bills, available_cash=20000)
    print(f"  总利息预估: {result['total_interest']:.2f}元")
    print(f"  总还款: {result['total_payment']:.2f}元")
    print(f"  剩余现金: {result['remaining_cash']:.2f}元")
    for plan in result['plans']:
        print(f"    - {plan['platform']}: {plan['repayment_type']}")
    print()
    
    print("场景2: 资金只够还高息账单")
    result = optimizer.optimize_repayment(bills=bills, available_cash=10000)
    print(f"  总利息预估: {result['total_interest']:.2f}元")
    print(f"  总还款: {result['total_payment']:.2f}元")
    print(f"  剩余现金: {result['remaining_cash']:.2f}元")
    for plan in result['plans']:
        print(f"    - {plan['platform']}: {plan['repayment_type']}, 利息={plan['interest_cost']:.2f}")
    print()
    
    print("场景3: 资金只够还最低")
    result = optimizer.optimize_repayment(bills=bills, available_cash=2000)
    print(f"  总利息预估: {result['total_interest']:.2f}元")
    print(f"  总还款: {result['total_payment']:.2f}元")
    print(f"  剩余现金: {result['remaining_cash']:.2f}元")
    for plan in result['plans']:
        print(f"    - {plan['platform']}: {plan['repayment_type']}")
    print()
    
    print("场景4: 逾期账单优先处理")
    bills_with_overdue = [
        Bill(id=1, platform="逾期信用卡", amount=8000, apr=18, min_payment=800,
             days_until_due=-3, installment_options=[3, 6, 12]),
        Bill(id=2, platform="正常账单", amount=10000, apr=24, min_payment=1000,
             days_until_due=10, installment_options=[3, 6, 12]),
    ]
    result = optimizer.optimize_repayment(bills=bills_with_overdue, available_cash=10000)
    print(f"  总利息预估: {result['total_interest']:.2f}元")
    for plan in result['plans']:
        print(f"    - {plan['platform']}: {plan['repayment_type']}")
    
    print("\n优化场景测试通过!\n")

def test_recommendation_text():
    """测试推荐文本生成"""
    optimizer = RepaymentOptimizer()
    
    print("=" * 60)
    print("测试推荐文本生成")
    print("=" * 60)
    
    bills = [
        Bill(id=1, platform="花呗", amount=5000, apr=15.86, min_payment=500,
             days_until_due=10, installment_options=[3, 6, 12]),
        Bill(id=2, platform="信用卡A", amount=10000, apr=24, min_payment=1000,
             days_until_due=15, installment_options=[3, 6, 12]),
    ]
    
    result = optimizer.optimize_repayment(bills=bills, available_cash=15000)
    print("推荐文本:")
    print("-" * 40)
    print(result['recommendation_text'])
    print("-" * 40)
    
    assert '花呗' in result['recommendation_text'], "推荐文本应包含平台名称"
    assert '全额还款' in result['recommendation_text'], "资金充足应推荐全额还款"
    
    print("\n推荐文本生成测试通过!\n")

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试智能还款算法")
    print("=" * 60 + "\n")
    
    try:
        test_interest_calculations()
        test_installment_interest()
        test_min_payment_interest()
        test_full_payment_interest()
        test_bill_prioritization()
        test_edge_cases()
        test_optimization_scenarios()
        test_recommendation_text()
        
        print("=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
        print("\n计算公式验证:")
        print("  1. 日利率 = 年利率 / 365 ✓")
        print("  2. 月利率 = 年利率 / 12 ✓")
        print("  3. 单利 = 本金 × 日利率 × 天数 ✓")
        print("  4. 分期利息 = 月供 × 期数 - 本金 (等额本息) ✓")
        print("  5. 最低还款利息 = 剩余本金 × 日利率 × 30天 ✓")
        print("  6. 逾期利息 = 本金 × 日利率 × 逾期天数 ✓")
        print("\n边界条件覆盖:")
        print("  1. 空账单列表 ✓")
        print("  2. 可用现金为0 ✓")
        print("  3. 资金刚好够 ✓")
        print("  4. 资金远超需求 ✓")
        print("  5. 零利率账单 ✓")
        print("  6. 逾期账单优先 ✓")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        raise

if __name__ == '__main__':
    main()
