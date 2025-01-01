from flask import Blueprint, render_template, redirect, url_for, flash, request
from bson.objectid import ObjectId
from flask_login import login_required, current_user
from extensions import db
from models import Payment

user_bp = Blueprint('user', __name__)

from datetime import datetime

@user_bp.route('/user-dashboard')
@login_required
def user_dashboard():
    # Get user's plans and payment status
    user_plans = []
    if current_user.plan_ids:
        plans = list(db.plans.find({'_id': {'$in': current_user.plan_ids}}))
        for plan in plans:
            # Check if payment is due
            payment = db.payments.find_one({
                'user_id': current_user.id,
                'plan_id': plan['_id'],
                'status': 'paid'
            })
            user_plans.append({
                'plan': plan,
                'paid': payment is not None
            })
    
    # Get all payments for totals
    payments = list(db.payments.find({'user_id': current_user.id}))
    total_paid = sum(p['amount'] for p in payments if p['status'] == 'paid')
    total_pending = sum(p['amount'] for p in payments if p['status'] == 'pending')
    
    # Get next billing date from the latest paid payment
    next_billing_date = None
    latest_payment = db.payments.find_one({
        'user_id': current_user.id,
        'status': 'paid'
    }, sort=[('paid_at', -1)])
    
    if latest_payment and 'next_billing_date' in latest_payment:
        next_billing_date = latest_payment['next_billing_date']
    
    return render_template('user/dashboard.html',
                         user_plans=user_plans,
                         total_paid=total_paid,
                         total_pending=total_pending,
                         next_billing_date=next_billing_date,
                         now=datetime.utcnow())

@user_bp.route('/billing')
@login_required
def billing():
    payments = db.payments.find({'user_id': current_user.id})
    return render_template('user/billing.html', payments=payments)

@user_bp.route('/transactions')
@login_required
def transactions():
    transactions = db.payments.find({
        'user_id': current_user.id,
        'status': 'paid'
    }).sort('paid_at', -1)
    
    return render_template('user/transactions.html', 
                         transactions=list(transactions))

@user_bp.route('/bill/<transaction_id>')
@login_required
def view_bill(transaction_id):
    from bson.objectid import ObjectId
    try:
        transaction = db.payments.find_one({
            '_id': ObjectId(transaction_id),
            'user_id': current_user.id
        })
        
        if not transaction:
            flash('Transaction not found', 'danger')
            return redirect(url_for('user.transactions'))
            
        # Fetch plan details
        plan = db.plans.find_one({'_id': transaction['plan_id']})
        transaction['plan_name'] = plan['name'] if plan else 'Unknown Plan'
        
        # Convert ObjectId to string for template
        transaction['_id'] = str(transaction['_id'])
        transaction['plan_id'] = str(transaction['plan_id'])
        
        return render_template('user/bill.html', 
                            transaction=transaction,
                            current_user=current_user)
    except Exception as e:
        flash('Error loading bill details', 'danger')
        return redirect(url_for('user.transactions'))

@user_bp.route('/profile')
@login_required
def profile():
    return render_template('user/profile.html')

@user_bp.route('/ticket-status', methods=['GET', 'POST'])
@login_required
def ticket_status():
    if request.method == 'POST':
        ticket_id = request.form.get('ticket_id')
        message = request.form.get('message')
        
        if message:
            db.tickets.update_one(
                {'_id': ObjectId(ticket_id), 'user_id': current_user.id},
                {'$push': {'replies': {
                    'user_id': current_user.id,
                    'message': message,
                    'is_admin': False,
                    'created_at': datetime.utcnow()
                }}}
            )
            flash('Reply added successfully', 'success')
        else:
            flash('Reply message cannot be empty', 'danger')
        
        return redirect(url_for('user.ticket_status'))
    
    tickets = list(db.tickets.find({'user_id': current_user.id}))
    return render_template('ticket/ticket_status.html', tickets=tickets)
