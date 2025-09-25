from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from expense import Expense
from expense_tracker import plot_expenses_by_category, summarize_expenses
import pandas as pd
import os
import json
import base64
import io
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt

app = Flask(__name__) 
app.secret_key = 'Gyk1V8fZ'

EXPENSE_FILE = 'expenses.csv'
BUDGET = 2000  # Default budget

def get_expense_data():
    """Helper function to get expense data and statistics"""
    if not os.path.exists(EXPENSE_FILE):
        return [], {}, 0, BUDGET, 0, 0
    
    expenses_df = pd.read_csv(EXPENSE_FILE, header=None, names=['name', 'amount', 'category'])
    expenses_df['amount'] = pd.to_numeric(expenses_df['amount'], errors='coerce')
    expenses_df = expenses_df.dropna()
    
    # Calculate statistics
    total_spent = expenses_df['amount'].sum()
    remaining_budget = BUDGET - total_spent
    total_expenses = len(expenses_df)
    
    # Calculate daily budget (remaining days in month)
    import datetime
    import calendar
    now = datetime.datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    remaining_days = max(1, days_in_month - now.day)  # Avoid division by zero
    daily_budget = remaining_budget / remaining_days if remaining_budget > 0 else 0
    
    # Group by category
    category_totals = expenses_df.groupby('category')['amount'].sum().to_dict()
    
    # Convert to list of dictionaries for template
    expenses_list = expenses_df.to_dict('records')
    
    return expenses_list, category_totals, total_spent, remaining_budget, daily_budget, total_expenses

@app.route('/')
def index():
    expenses, category_totals, total_spent, remaining_budget, daily_budget, total_expenses = get_expense_data()
    
    return render_template('index.html', 
                         expenses=expenses,
                         category_totals=category_totals,
                         total_spent=total_spent,
                         remaining_budget=remaining_budget,
                         daily_budget=daily_budget,
                         total_expenses=total_expenses,
                         budget=BUDGET)

@app.route('/add', methods=['POST'])
def add_expense():
    name = request.form['name']
    amount = request.form['amount']
    category = request.form['category']
    
    try:
        # Create expense object with correct parameter order
        new_expense = Expense(name=name, category=category, amount=float(amount))
        
        # Create file with headers if it doesn't exist
        if not os.path.exists(EXPENSE_FILE):
            with open(EXPENSE_FILE, 'w') as f:
                pass  # Create empty file
        
        # Append to CSV
        with open(EXPENSE_FILE, 'a') as f:
            f.write(f"{new_expense.name},{new_expense.amount},{new_expense.category}\n")
        
        flash(f'Expense "{name}" of ${float(amount):.2f} added successfully!', 'success')
    except ValueError:
        flash('Please enter a valid amount!', 'error')
    except Exception as e:
        flash(f'Error adding expense: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/generate_chart')
def generate_chart():
    """Generate chart and return as base64 encoded image"""
    try:
        if not os.path.exists(EXPENSE_FILE):
            return jsonify({'error': 'No expenses found'}), 404
        
        # Read expenses
        df = pd.read_csv(EXPENSE_FILE, header=None, names=["name", "amount", "category"])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.dropna(subset=["amount", "category"])
        
        if df.empty:
            return jsonify({'error': 'No valid expenses found'}), 404
        
        # Group by category
        agg = df.groupby("category")["amount"].sum().sort_values(ascending=False)
        
        # Create plot
        plt.figure(figsize=(10, 6))
        ax = agg.plot(kind="bar", color=['#667eea', '#764ba2', '#48bb78', '#ed8936', '#9f7aea'])
        ax.set_title("Expenses by Category", fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel("Category", fontsize=12)
        ax.set_ylabel("Total Expense ($)", fontsize=12)
        plt.xticks(rotation=45, ha="right")
        
        # Add value labels on bars
        for p in ax.patches:
            ax.text(p.get_x() + p.get_width()/2, p.get_height() + 1, 
                   f"${p.get_height():.2f}",
                   ha="center", va="bottom", fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        
        # Convert plot to base64 string
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return jsonify({'chart': img_base64})
        
    except Exception as e:
        return jsonify({'error': f'Error generating chart: {str(e)}'}), 500

@app.route('/export_data')
def export_data():
    """Export expenses data as CSV"""
    try:
        if not os.path.exists(EXPENSE_FILE):
            flash('No expenses to export!', 'warning')
            return redirect(url_for('index'))
        
        expenses, category_totals, total_spent, remaining_budget, daily_budget, total_expenses = get_expense_data()
        
        # For now, just flash a message. In a real app, you'd return the file
        flash(f'Data exported! Total: {total_expenses} expenses, Amount: ${total_spent:.2f}', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error exporting data: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/clear_all', methods=['POST'])
def clear_all():
    """Clear all expenses"""
    try:
        if os.path.exists(EXPENSE_FILE):
            os.remove(EXPENSE_FILE)
            flash('All expenses cleared successfully!', 'success')
        else:
            flash('No expenses to clear!', 'warning')
    except Exception as e:
        flash(f'Error clearing expenses: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/summary')
def get_summary():
    """Get expense summary as JSON"""
    try:
        expenses, category_totals, total_spent, remaining_budget, daily_budget, total_expenses = get_expense_data()
        
        return jsonify({
            'total_spent': total_spent,
            'remaining_budget': remaining_budget,
            'daily_budget': daily_budget,
            'total_expenses': total_expenses,
            'category_totals': category_totals
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)