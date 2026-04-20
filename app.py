from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import traceback
from repayment_algorithm import RepaymentOptimizer, Bill

app = Flask(__name__, static_folder='frontend/static', static_url_path='')
CORS(app)

class FinancialDataStore:
    def __init__(self):
        self.incomes = []
        self.expenses = []
        self.bills = []
        self.current_month = date.today().replace(day=1)

    def get_calendar_data(self):
        year = self.current_month.year
        month = self.current_month.month
        _, num_days = calendar.monthrange(year, month)
        
        calendar_data = {
            'year': year,
            'month': month,
            'days': []
        }
        
        for day in range(1, num_days + 1):
            current_date = date(year, month, day)
            day_data = {
                'date': current_date.isoformat(),
                'day': day,
                'weekday': current_date.weekday(),
                'is_income': False,
                'is_expense': False,
                'is_bill_due': False,
                'income_amount': 0,
                'expense_amount': 0,
                'bills_due': []
            }
            
            for income in self.incomes:
                try:
                    income_date = datetime.fromisoformat(income['date']).date()
                    if income_date == current_date:
                        day_data['is_income'] = True
                        day_data['income_amount'] += income['amount']
                except (ValueError, TypeError):
                    continue
            
            for expense in self.expenses:
                try:
                    if expense['day_of_month'] == day:
                        day_data['is_expense'] = True
                        day_data['expense_amount'] += expense['amount']
                except (ValueError, TypeError):
                    continue
            
            for bill in self.bills:
                try:
                    due_date = datetime.fromisoformat(bill['due_date']).date()
                    if due_date == current_date:
                        day_data['is_bill_due'] = True
                        day_data['bills_due'].append({
                            'id': bill['id'],
                            'platform': bill['platform'],
                            'amount': bill['amount'],
                            'apr': bill['apr'],
                            'min_payment': bill.get('min_payment', bill['amount'] * 0.1)
                        })
                except (ValueError, TypeError):
                    continue
            
            calendar_data['days'].append(day_data)
        
        return calendar_data

store = FinancialDataStore()
optimizer = RepaymentOptimizer()

def validate_date(date_str):
    if not date_str:
        return False, "日期不能为空"
    try:
        datetime.fromisoformat(date_str)
        return True, None
    except ValueError:
        return False, f"日期格式无效: {date_str}"

def validate_amount(amount, min_value=0, max_value=1000000000, field_name="金额"):
    if amount is None:
        return False, f"{field_name}不能为空"
    try:
        amount = float(amount)
        if amount < min_value:
            return False, f"{field_name}不能小于{min_value}"
        if amount > max_value:
            return False, f"{field_name}不能超过{max_value}"
        return True, None
    except (TypeError, ValueError):
        return False, f"{field_name}格式无效"

def validate_apr(apr):
    if apr is None:
        return False, "利率不能为空"
    try:
        apr = float(apr)
        if apr < 0:
            return False, "利率不能为负数"
        if apr > 1000:
            return False, "利率过高，请检查输入（合理范围0-100%）"
        return True, None
    except (TypeError, ValueError):
        return False, "利率格式无效"

def validate_day_of_month(day):
    if day is None:
        return False, "日期不能为空"
    try:
        day = int(day)
        if day < 1 or day > 31:
            return False, "日期必须在1-31之间"
        return True, None
    except (TypeError, ValueError):
        return False, "日期格式无效"

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    app.logger.error(traceback.format_exc())
    return jsonify({
        'success': False,
        'message': '服务器内部错误，请稍后重试',
        'error': str(e) if app.debug else '内部错误'
    }), 500

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/incomes', methods=['GET', 'POST'])
def handle_incomes():
    if request.method == 'GET':
        return jsonify(store.incomes)
    
    elif request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else {}
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': '请求数据为空'
                }), 400
            
            date_str = data.get('date')
            valid, error = validate_date(date_str)
            if not valid:
                return jsonify({
                    'success': False,
                    'message': error
                }), 400
            
            amount = data.get('amount')
            valid, error = validate_amount(amount, min_value=0.01, field_name="收入金额")
            if not valid:
                return jsonify({
                    'success': False,
                    'message': error
                }), 400
            
            description = data.get('description', '收入')
            if description and len(description) > 100:
                description = description[:100]
            
            income = {
                'id': len(store.incomes) + 1,
                'date': str(date_str),
                'amount': float(amount),
                'description': str(description) if description else '收入'
            }
            store.incomes.append(income)
            
            return jsonify({
                'success': True,
                'data': income
            }), 201
            
        except Exception as e:
            app.logger.error(f"Error adding income: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'添加收入失败: {str(e)}'
            }), 500

@app.route('/api/incomes/<int:income_id>', methods=['DELETE'])
def delete_income(income_id):
    try:
        original_length = len(store.incomes)
        store.incomes = [i for i in store.incomes if i.get('id') != income_id]
        
        if len(store.incomes) == original_length:
            return jsonify({
                'success': False,
                'message': f'未找到ID为{income_id}的收入记录'
            }), 404
        
        return jsonify({
            'success': True,
            'message': '删除成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500

@app.route('/api/expenses', methods=['GET', 'POST'])
def handle_expenses():
    if request.method == 'GET':
        return jsonify(store.expenses)
    
    elif request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else {}
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': '请求数据为空'
                }), 400
            
            day_of_month = data.get('day_of_month')
            valid, error = validate_day_of_month(day_of_month)
            if not valid:
                return jsonify({
                    'success': False,
                    'message': error
                }), 400
            
            amount = data.get('amount')
            valid, error = validate_amount(amount, min_value=0.01, field_name="开支金额")
            if not valid:
                return jsonify({
                    'success': False,
                    'message': error
                }), 400
            
            description = data.get('description', '日常开支')
            if description and len(description) > 100:
                description = description[:100]
            
            expense = {
                'id': len(store.expenses) + 1,
                'day_of_month': int(day_of_month),
                'amount': float(amount),
                'description': str(description) if description else '日常开支'
            }
            store.expenses.append(expense)
            
            return jsonify({
                'success': True,
                'data': expense
            }), 201
            
        except Exception as e:
            app.logger.error(f"Error adding expense: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'添加开支失败: {str(e)}'
            }), 500

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    try:
        original_length = len(store.expenses)
        store.expenses = [e for e in store.expenses if e.get('id') != expense_id]
        
        if len(store.expenses) == original_length:
            return jsonify({
                'success': False,
                'message': f'未找到ID为{expense_id}的开支记录'
            }), 404
        
        return jsonify({
            'success': True,
            'message': '删除成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500

@app.route('/api/bills', methods=['GET', 'POST'])
def handle_bills():
    if request.method == 'GET':
        return jsonify(store.bills)
    
    elif request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else {}
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': '请求数据为空'
                }), 400
            
            platform = data.get('platform', '').strip()
            if not platform:
                return jsonify({
                    'success': False,
                    'message': '平台名称不能为空'
                }), 400
            if len(platform) > 50:
                platform = platform[:50]
            
            amount = data.get('amount')
            valid, error = validate_amount(amount, min_value=0.01, field_name="账单金额")
            if not valid:
                return jsonify({
                    'success': False,
                    'message': error
                }), 400
            
            due_date = data.get('due_date')
            valid, error = validate_date(due_date)
            if not valid:
                return jsonify({
                    'success': False,
                    'message': error
                }), 400
            
            apr = data.get('apr')
            valid, error = validate_apr(apr)
            if not valid:
                return jsonify({
                    'success': False,
                    'message': error
                }), 400
            
            amount_float = float(amount)
            min_payment = data.get('min_payment')
            if min_payment is None or min_payment == '':
                min_payment = amount_float * 0.1
            else:
                valid, error = validate_amount(min_payment, min_value=0, field_name="最低还款额")
                if not valid:
                    min_payment = amount_float * 0.1
                else:
                    min_payment = float(min_payment)
                    if min_payment > amount_float:
                        min_payment = amount_float
            
            installment_options = data.get('installment_options', [3, 6, 12])
            if not isinstance(installment_options, list):
                installment_options = [3, 6, 12]
            
            installment_options = [int(m) for m in installment_options if isinstance(m, (int, float)) and m > 0]
            if not installment_options:
                installment_options = [3, 6, 12]
            
            bill = {
                'id': len(store.bills) + 1,
                'platform': platform,
                'amount': amount_float,
                'due_date': str(due_date),
                'apr': float(apr),
                'min_payment': min_payment,
                'installment_options': installment_options
            }
            store.bills.append(bill)
            
            return jsonify({
                'success': True,
                'data': bill
            }), 201
            
        except Exception as e:
            app.logger.error(f"Error adding bill: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'添加账单失败: {str(e)}'
            }), 500

@app.route('/api/bills/<int:bill_id>', methods=['DELETE'])
def delete_bill(bill_id):
    try:
        original_length = len(store.bills)
        store.bills = [b for b in store.bills if b.get('id') != bill_id]
        
        if len(store.bills) == original_length:
            return jsonify({
                'success': False,
                'message': f'未找到ID为{bill_id}的账单记录'
            }), 404
        
        return jsonify({
            'success': True,
            'message': '删除成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500

@app.route('/api/calendar', methods=['GET'])
def get_calendar():
    try:
        year = request.args.get('year', default=None, type=int)
        month = request.args.get('month', default=None, type=int)
        
        if year and month:
            if year < 1900 or year > 2100:
                return jsonify({
                    'success': False,
                    'message': '年份范围无效（1900-2100）'
                }), 400
            if month < 1 or month > 12:
                return jsonify({
                    'success': False,
                    'message': '月份范围无效（1-12）'
                }), 400
            store.current_month = date(year, month, 1)
        
        return jsonify({
            'success': True,
            'data': store.get_calendar_data()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取日历数据失败: {str(e)}'
        }), 500

@app.route('/api/calculate-repayment', methods=['POST'])
def calculate_repayment():
    try:
        data = request.get_json() if request.is_json else {}
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据为空'
            }), 400
        
        available_cash = data.get('available_cash', 0)
        
        try:
            available_cash = float(available_cash)
            if available_cash < 0:
                available_cash = 0
        except (TypeError, ValueError):
            available_cash = 0
        
        if not store.bills:
            return jsonify({
                'success': False,
                'message': '没有账单需要处理',
                'plans': [],
                'total_interest': 0,
                'total_payment': 0,
                'remaining_cash': available_cash
            })
        
        bills_for_calc = []
        today = date.today()
        
        for bill in store.bills:
            try:
                bill_id = bill.get('id', 0)
                platform = str(bill.get('platform', '未知平台'))
                amount = float(bill.get('amount', 0))
                apr = float(bill.get('apr', 0))
                min_payment = float(bill.get('min_payment', amount * 0.1))
                installment_options = bill.get('installment_options', [3, 6, 12])
                
                if amount <= 0:
                    continue
                
                try:
                    due_date = datetime.fromisoformat(bill.get('due_date', '')).date()
                    days_until_due = (due_date - today).days
                except (ValueError, TypeError):
                    days_until_due = 30
                
                if min_payment <= 0:
                    min_payment = amount * 0.1
                if min_payment > amount:
                    min_payment = amount
                
                if not isinstance(installment_options, list):
                    installment_options = [3, 6, 12]
                installment_options = [int(m) for m in installment_options if isinstance(m, (int, float)) and m > 0]
                if not installment_options:
                    installment_options = [3, 6, 12]
                
                bills_for_calc.append(Bill(
                    id=bill_id,
                    platform=platform,
                    amount=amount,
                    apr=apr,
                    min_payment=min_payment,
                    days_until_due=days_until_due,
                    installment_options=installment_options
                ))
                
            except Exception as e:
                app.logger.warning(f"Skipping invalid bill: {str(e)}")
                continue
        
        if not bills_for_calc:
            return jsonify({
                'success': False,
                'message': '没有有效的账单数据',
                'plans': [],
                'total_interest': 0,
                'total_payment': 0,
                'remaining_cash': available_cash
            })
        
        result = optimizer.optimize_repayment(
            bills=bills_for_calc,
            available_cash=available_cash
        )
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error calculating repayment: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'计算还款方案失败: {str(e)}',
            'plans': [],
            'total_interest': 0,
            'total_payment': 0,
            'remaining_cash': data.get('available_cash', 0) if data else 0
        }), 500

@app.route('/api/month/<direction>', methods=['POST'])
def change_month(direction):
    try:
        if direction == 'prev':
            store.current_month = store.current_month - relativedelta(months=1)
        elif direction == 'next':
            store.current_month = store.current_month + relativedelta(months=1)
        else:
            return jsonify({
                'success': False,
                'message': '无效的方向参数'
            }), 400
        
        return jsonify({
            'success': True,
            'data': store.get_calendar_data()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'切换月份失败: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
