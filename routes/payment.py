from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from extensions import db
from models import Payment
import qrcode
import io
import base64
from bson.objectid import ObjectId
import math

def calculate_renewal_payment(plan_cost, last_payment_date, current_date, plan_duration):
    """
    Calculate the renewal payment amount based on elapsed time since last payment.
    
    Args:
        plan_cost (float): Cost of the plan
        last_payment_date (datetime): Date of last successful payment
        current_date (datetime): Current date
        plan_duration (int): Duration of plan in days
        
    Returns:
        float: Amount to be paid for renewal
    """
    elapsed_days = (current_date - last_payment_date).days
    
    if elapsed_days <= 0:
        return 0.0
        
    # Calculate number of full periods elapsed
    periods = math.ceil(elapsed_days / plan_duration)
    
    # Calculate total payment amount
    payment_amount = periods * plan_cost
    
    # Round up to nearest whole number
    return math.ceil(payment_amount)

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/make-payment', methods=['GET', 'POST'])
@login_required
def make_payment():
    # Get all unpaid plans for the user
    unpaid_plans = []
    if current_user.plan_ids:
        plans = list(db.plans.find({'_id': {'$in': current_user.plan_ids}}))
        for plan in plans:
            payment = db.payments.find_one({
                'user_id': current_user.id,
                'plan_id': plan['_id'],
                'status': 'paid'
            })
            if not payment:
                unpaid_plans.append(plan)
    
    # Calculate total amount
    amount = sum(plan['price'] for plan in unpaid_plans)
    
    if request.method == 'POST':
        # Calculate renewal payment if this is a renewal
        if 'renewal' in request.form:
            last_payment = db.payments.find_one({
                'user_id': current_user.id,
                'plan_id': unpaid_plans[0]['_id'],
                'status': 'paid'
            }, sort=[('paid_at', -1)])
            
            if last_payment:
                amount = calculate_renewal_payment(
                    plan_cost=unpaid_plans[0]['price'],
                    last_payment_date=last_payment['paid_at'],
                    current_date=datetime.utcnow(),
                    plan_duration=unpaid_plans[0]['renewal_period']
                )
            else:
                amount = unpaid_plans[0]['price']
        else:
            amount = float(request.form.get('amount'))
            
        due_date = datetime.utcnow() + timedelta(days=30)
        
        # Create a payment record for each unpaid plan
        for plan in unpaid_plans:
            payment_data = {
                'user_id': current_user.id,
                'plan_id': plan['_id'],
                'amount': plan['price'],
                'status': 'pending',
                'due_date': due_date,
                'created_at': datetime.utcnow()
            }
            result = db.payments.insert_one(payment_data)
            print(f"Created payment with ID: {result.inserted_id}")  # Debug logging
        
        flash('Payment initiated successfully', 'success')
        return redirect(url_for('payment.payment_status'))
    
    return render_template('payment/make_payment.html', 
                         amount=amount)

from datetime import datetime

@payment_bp.route('/payment-status')
@login_required
def payment_status():
    payments = db.payments.find({'user_id': current_user.id})
    return render_template('payment/payment_status.html', 
                         payments=payments,
                         now=datetime.utcnow())

@payment_bp.route('/pay-now/<string:payment_id>', methods=['GET', 'POST'])
@login_required
def pay_now(payment_id):
    payment = db.payments.find_one({'_id': ObjectId(payment_id)})
    
    if payment and payment['user_id'] == current_user.id:
        # Generate UPI QR code
        upi_id = 'mohnishkumar7777777@okaxis'
        amount = str(payment['amount'])
        note = f'Payment for {current_user.username}'
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f'upi://pay?pa={upi_id}&pn=YourBusinessName&am={amount}&tn={note}')
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Calculate expiration time (15 minutes from now)
        expiration_time = datetime.utcnow() + timedelta(minutes=15)
        
        # Handle payment completion
        if request.method == 'POST':
            db.payments.update_one(
                {'_id': ObjectId(payment_id)},
                {'$set': {'status': 'in progress'}}
            )
            flash('Payment is now in progress', 'info')
            return redirect(url_for('payment.payment_status'))
        
        return render_template('payment/pay_now.html', 
                             qr_code=img_str, 
                             upi_id=upi_id,
                             payment=payment,
                             expiration_time=expiration_time)
    
    flash('Invalid payment request', 'danger')
    return redirect(url_for('payment.payment_status'))

@payment_bp.route('/confirm-payment/<payment_id>')
@login_required
def confirm_payment(payment_id):
    payment = db.payments.find_one({'_id': ObjectId(payment_id)})
    
    if payment and payment['user_id'] == current_user.id:
        # Generate bill URL
        bill_url = url_for('user.view_bill', transaction_id=payment_id, _external=True)
        
        # Update payment status and add bill URL
        db.payments.update_one(
            {'_id': ObjectId(payment_id)},
            {'$set': {
                'status': 'paid',
                'bill_url': bill_url,
                'paid_at': datetime.utcnow()
            }}
        )
        flash('Payment completed successfully', 'success')
    else:
        flash('Invalid payment request', 'danger')
    
    return redirect(url_for('payment.payment_status'))

@payment_bp.route('/admin/mark-paid/<payment_id>')
@login_required
def admin_mark_paid(payment_id):
    if not current_user.is_admin:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    payment = db.payments.find_one({'_id': ObjectId(payment_id)})
    
    if payment:
        # Generate bill URL
        bill_url = url_for('user.view_bill', transaction_id=payment_id, _external=True)
        
        # Calculate next billing date (30 days from now)
        next_billing_date = datetime.utcnow() + timedelta(days=30)
        
        # Update payment status and add bill URL
        db.payments.update_one(
            {'_id': ObjectId(payment_id)},
            {'$set': {
                'status': 'paid',
                'bill_url': bill_url,
                'paid_at': datetime.utcnow(),
                'marked_by_admin': True,
                'next_billing_date': next_billing_date
            }}
        )
        
        # Create a new pending payment for the next billing cycle
        new_payment = {
            'user_id': payment['user_id'],
            'plan_id': payment['plan_id'],
            'amount': payment['amount'],
            'status': 'pending',
            'due_date': next_billing_date,
            'created_at': datetime.utcnow()
        }
        db.payments.insert_one(new_payment)
        
        flash('Payment marked as paid. Next billing cycle created.', 'success')
    else:
        flash('Payment not found', 'danger')
    
    return redirect(url_for('admin.manage_payments'))

@payment_bp.route('/check-payment-status/<payment_id>')
@login_required
def check_payment_status(payment_id):
    payment = db.payments.find_one({
        '_id': ObjectId(payment_id),
        'user_id': current_user.id
    })
    
    if not payment:
        return jsonify({'status': 'not_found'}), 404
    
    return jsonify({
        'status': payment['status'],
        'amount': payment['amount']
    })
