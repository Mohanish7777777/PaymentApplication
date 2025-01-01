from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash
from datetime import datetime
from flask_login import login_required, current_user
from bson.objectid import ObjectId
from extensions import db
from models import User, Payment, Ticket, Coupon

admin_bp = Blueprint('admin', __name__)

# @admin_bp.route('/test-route')
# def test_route():
#     print("Test route accessed")  # Debug logging
#     return "Test route is working"

# @admin_bp.route('/test-route-2')
# def test_route_2():
#     return "Test route 2 is working"

@admin_bp.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.user_dashboard'))
    
    # Get statistics
    total_users = db.users.count_documents({})
    total_payments = db.payments.count_documents({})
    total_tickets = db.tickets.count_documents({})
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_payments=total_payments,
                         total_tickets=total_tickets)

@admin_bp.route('/manage-users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    users = list(db.users.find())
    # Add plan information to each user
    for user in users:
        if user.get('plan_ids'):
            user['plans'] = list(db.plans.find({'_id': {'$in': user['plan_ids']}}))
        else:
            user['plans'] = []
    print(f"Users found: {users}")  # Debug logging
    return render_template('admin/manage_users.html', users=users)

from datetime import datetime

@admin_bp.route('/manage-payments')
@login_required
def manage_payments():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.user_dashboard'))
    
    try:
        # Show all in progress payments sorted by creation date
        pending_payments = list(db.payments.find({
            'status': 'in progress'
        }).sort('created_at', -1))
        
        if not pending_payments:
            print("No in progress payments found")  # Debug logging
    except Exception as e:
        print(f"Error fetching payments: {str(e)}")  # Debug logging
        flash('Error loading payments', 'danger')
        pending_payments = []
    
    print(f"Found {len(pending_payments)} pending payments")  # Debug logging
    for payment in pending_payments:
        print(f"Payment ID: {payment['_id']}, User ID: {payment['user_id']}, Amount: {payment['amount']}")
    
    # Show transaction history of marked payments
    transaction_history = list(db.payments.find({
        'status': 'paid',
        'marked_by_admin': True
    }).sort('paid_at', -1))
    
    return render_template('admin/manage_payments.html', 
                         pending_payments=pending_payments,
                         transaction_history=transaction_history,
                         now=datetime.utcnow())

@admin_bp.route('/delete-payment/<payment_id>', methods=['POST'])
@login_required
def delete_payment(payment_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    payment = db.payments.find_one({'_id': ObjectId(payment_id)})
    
    if payment and payment['status'] == 'pending':
        db.payments.delete_one({'_id': ObjectId(payment_id)})
        flash('Payment entry deleted successfully', 'success')
    else:
        flash('Payment not found or cannot be deleted', 'danger')
    
    return redirect(url_for('admin.manage_payments'))

@admin_bp.route('/update-payment-status/<payment_id>/<status>')
@login_required
def update_payment_status(payment_id, status):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.user_dashboard'))
    
    if status not in ['paid', 'pending', 'cancelled']:
        flash('Invalid status', 'danger')
        return redirect(url_for('admin.manage_payments'))
    
    payment = db.payments.find_one({'_id': ObjectId(payment_id)})
    
    if status == 'paid':
        # Add to transaction history
        db.transactions.insert_one({
            'user_id': payment['user_id'],
            'payment_id': payment['_id'],
            'amount': payment['amount'],
            'type': 'payment',
            'status': 'completed',
            'created_at': datetime.utcnow()
        })
        db.payments.update_one(
            {'_id': ObjectId(payment_id)},
            {'$set': {'status': status}}
        )
    elif status == 'cancelled':
        # Move to cancelled payments
        payment['status'] = 'cancelled'
        payment['cancelled_at'] = datetime.utcnow()
        db.cancelled_payments.insert_one(payment)
        db.payments.delete_one({'_id': ObjectId(payment_id)})
    else:
        db.payments.update_one(
            {'_id': ObjectId(payment_id)},
            {'$set': {'status': status}}
        )
    
    flash(f'Payment marked as {status}', 'success')
    return redirect(url_for('admin.manage_payments'))

@admin_bp.route('/manage-tickets', methods=['GET', 'POST'])
@login_required
def manage_tickets():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        ticket_id = request.form.get('ticket_id')
        action = request.form.get('action')
        
        if action == 'reply':
            message = request.form.get('message')
            if message:
                db.tickets.update_one(
                    {'_id': ObjectId(ticket_id)},
                    {'$push': {'replies': {
                        'user_id': current_user.id,
                        'message': message,
                        'is_admin': True,
                        'created_at': datetime.utcnow()
                    }}}
                )
                flash('Reply added successfully', 'success')
            else:
                flash('Reply message cannot be empty', 'danger')
        
        elif action == 'update_status':
            status = request.form.get('status')
            if status in ['open', 'waiting', 'closed']:
                db.tickets.update_one(
                    {'_id': ObjectId(ticket_id)},
                    {'$set': {'status': status}}
                )
                flash(f'Ticket status updated to {status}', 'success')
            else:
                flash('Invalid status', 'danger')
        
        return redirect(url_for('admin.manage_tickets'))
    
    tickets = list(db.tickets.find())
    return render_template('admin/manage_tickets.html', tickets=tickets)

@admin_bp.route('/manage-coupons')
@login_required
def manage_coupons():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    coupons = db.coupons.find()
    return render_template('admin/manage_coupons.html', coupons=coupons)

@admin_bp.route('/create-user', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        existing_user = db.users.find_one({'username': username})
        if existing_user:
            flash('Username already exists', 'danger')
            return redirect(url_for('admin.create_user'))
            
        hashed_password = generate_password_hash(password)
        user_data = {
            'username': username,
            'password': hashed_password,
            'role': role
        }
        db.users.insert_one(user_data)
        flash('User created successfully', 'success')
        return redirect(url_for('admin.manage_users'))
        
    return render_template('admin/create_user.html')

@admin_bp.route('/create-coupon', methods=['GET', 'POST'])
@login_required
def create_coupon():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        code = request.form.get('code')
        discount = float(request.form.get('discount'))
        usage_limit = int(request.form.get('usage_limit'))
        
        coupon_data = {
            'code': code,
            'discount': discount,
            'usage_limit': usage_limit,
            'used_count': 0,
            'created_at': datetime.utcnow()
        }
        db.coupons.insert_one(coupon_data)
        flash('Coupon created successfully', 'success')
        return redirect(url_for('admin.manage_coupons'))
        
    return render_template('admin/create_coupon.html')

@admin_bp.route('/edit-user/<user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    user = db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        role = request.form.get('role')
        
        update_data = {
            'username': username,
            'role': role
        }
        
        # Update password if provided
        if request.form.get('password'):
            update_data['password'] = generate_password_hash(request.form.get('password'))
        
        db.users.update_one({'_id': ObjectId(user_id)}, {'$set': update_data})
        flash('User updated successfully', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/delete-user/<user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    db.users.delete_one({'_id': ObjectId(user_id)})
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/manage-plans')
@login_required
def manage_plans():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    plans = list(db.plans.find())
    print(f"Plans found: {plans}")  # Debug logging
    return render_template('admin/manage_plans.html', plans=plans)

@admin_bp.route('/create-plan', methods=['GET', 'POST'])
@login_required
def create_plan():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        description = request.form.get('description')
        renewal_period = int(request.form.get('renewal_period'))
        
        plan_data = {
            'name': name,
            'price': price,
            'description': description,
            'renewal_period': renewal_period,
            'created_at': datetime.utcnow()
        }
        db.plans.insert_one(plan_data)
        flash('Plan created successfully', 'success')
        return redirect(url_for('admin.manage_plans'))
    
    return render_template('admin/create_plan.html')

@admin_bp.route('/delete-plan/<plan_id>')
@login_required
def delete_plan(plan_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    db.plans.delete_one({'_id': ObjectId(plan_id)})
    flash('Plan deleted successfully', 'success')
    return redirect(url_for('admin.manage_plans'))

@admin_bp.route('/assign-plan/<user_id>', methods=['GET', 'POST'])
@login_required
def assign_plan(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    print(f"Received user_id: {str(user_id)}")  # Debug logging
    user = db.users.find_one({'_id': ObjectId(user_id)})
    print(f"Found user: {user}")  # Debug logging
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    if request.method == 'POST':
        plan_id = request.form.get('plan_id')
        if not plan_id:
            flash('Please select a plan to assign', 'warning')
            return redirect(url_for('admin.assign_plan', user_id=user_id))
            
        try:
            db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$addToSet': {'plan_ids': ObjectId(plan_id)}}
            )
            flash('Plan assigned successfully', 'success')
        except:
            flash('Invalid plan selected', 'danger')
            
        return redirect(url_for('admin.manage_users'))
    
    plans = db.plans.find()
    return render_template('admin/assign_plan.html', user=user, plans=plans)
