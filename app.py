from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from repayment_algorithm import RepaymentOptimizer

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
                income_date = datetime.fromisoformat(income['date']).date()
                if income_date == current_date:
                    day_data['is_income'] = True
                    day_data['income_amount'] += income['amount']
            
            for expense in self.expenses:
                if expense['day_of_month'] == day:
                    day_data['is_expense'] = True
                    day_data['expense_amount'] += expense['amount']
            
            for bill in self.bills:
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
            
            calendar_data['days'].append(day_data)
        
        return calendar_data

store = FinancialDataStore()
optimizer = RepaymentOptimizer()

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/incomes', methods=['GET', 'POST'])
def handle_incomes():
    if request.method == 'GET':
        return jsonify(store.incomes)
    elif request.method == 'POST':
        data = request.json
        income = {
            'id': len(store.incomes) + 1,
            'date': data['date'],
            'amount': data['amount'],
            'description': data.get('description', '收入')
        }
        store.incomes.append(income)
        return jsonify(income), 201

@app.route('/api/incomes/<int:income_id>', methods=['DELETE'])
def delete_income(income_id):
    store.incomes = [i for i in store.incomes if i['id'] != income_id]
    return jsonify({'success': True})

@app.route('/api/expenses', methods=['GET', 'POST'])
def handle_expenses():
    if request.method == 'GET':
        return jsonify(store.expenses)
    elif request.method == 'POST':
        data = request.json
        expense = {
            'id': len(store.expenses) + 1,
            'day_of_month': data['day_of_month'],
            'amount': data['amount'],
            'description': data.get('description', '日常开支')
        }
        store.expenses.append(expense)
        return jsonify(expense), 201

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    store.expenses = [e for e in store.expenses if e['id'] != expense_id]
    return jsonify({'success': True})

@app.route('/api/bills', methods=['GET', 'POST'])
def handle_bills():
    if request.method == 'GET':
        return jsonify(store.bills)
    elif request.method == 'POST':
        data = request.json
        bill = {
            'id': len(store.bills) + 1,
            'platform': data['platform'],
            'amount': data['amount'],
            'due_date': data['due_date'],
            'apr': data['apr'],
            'min_payment': data.get('min_payment', data['amount'] * 0.1),
            'installment_options': data.get('installment_options', [3, 6, 12])
        }
        store.bills.append(bill)
        return jsonify(bill), 201

@app.route('/api/bills/<int:bill_id>', methods=['DELETE'])
def delete_bill(bill_id):
    store.bills = [b for b in store.bills if b['id'] != bill_id]
    return jsonify({'success': True})

@app.route('/api/calendar', methods=['GET'])
def get_calendar():
    year = request.args.get('year', default=None, type=int)
    month = request.args.get('month', default=None, type=int)
    
    if year and month:
        store.current_month = date(year, month, 1)
    
    return jsonify(store.get_calendar_data())

@app.route('/api/calculate-repayment', methods=['POST'])
def calculate_repayment():
    data = request.json
    available_cash = data.get('available_cash', 0)
    
    bills_for_calc = []
    for bill in store.bills:
        due_date = datetime.fromisoformat(bill['due_date']).date()
        today = date.today()
        days_until_due = (due_date - today).days
        
        bills_for_calc.append({
            'id': bill['id'],
            'platform': bill['platform'],
            'amount': bill['amount'],
            'apr': bill['apr'],
            'min_payment': bill.get('min_payment', bill['amount'] * 0.1),
            'days_until_due': days_until_due,
            'installment_options': bill.get('installment_options', [3, 6, 12])
        })
    
    result = optimizer.optimize_repayment(
        bills=bills_for_calc,
        available_cash=available_cash
    )
    
    return jsonify(result)

@app.route('/api/month/<direction>', methods=['POST'])
def change_month(direction):
    if direction == 'prev':
        store.current_month = store.current_month - relativedelta(months=1)
    elif direction == 'next':
        store.current_month = store.current_month + relativedelta(months=1)
    
    return jsonify(store.get_calendar_data())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
