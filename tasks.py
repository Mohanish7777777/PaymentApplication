from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from database import db
from models import Payment

scheduler = BackgroundScheduler()

def check_renewals():
    now = datetime.utcnow()
    # Find payments that are due for renewal
    due_payments = db.payments.find({
        'next_renewal': {'$lte': now},
        'status': 'paid'
    })
    
    for payment in due_payments:
        # Create new payment record
        plan = db.plans.find_one({'_id': payment['plan_id']})
        new_payment = {
            'user_id': payment['user_id'],
            'plan_id': payment['plan_id'],
            'amount': plan['price'],
            'status': 'pending',
            'due_date': payment['next_renewal'],
            'renewal_cycle': payment['renewal_cycle'] + 1,
            'next_renewal': payment['next_renewal'] + timedelta(days=plan['renewal_period'])
        }
        db.payments.insert_one(new_payment)
        
        # Update existing payment
        db.payments.update_one(
            {'_id': payment['_id']},
            {'$set': {'next_renewal': new_payment['next_renewal']}}
        )

# Schedule the task to run daily
scheduler.add_job(check_renewals, 'interval', days=1)
scheduler.start()
