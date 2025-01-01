from datetime import datetime
from flask_login import UserMixin
from bson.objectid import ObjectId

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.password = user_data['password']
        self.role = user_data.get('role', 'user')
        self.plan_ids = user_data.get('plan_ids', [])
        self.created_at = user_data.get('created_at', datetime.utcnow())

class Payment:
    def __init__(self, payment_data):
        self.id = str(payment_data['_id'])
        self.user_id = payment_data['user_id']
        self.plan_id = payment_data['plan_id']
        self.amount = payment_data['amount']
        self.status = payment_data.get('status', 'pending')
        self.due_date = payment_data['due_date']
        self.created_at = payment_data.get('created_at', datetime.utcnow())
        self.renewal_cycle = payment_data.get('renewal_cycle', 1)
        self.next_renewal = payment_data.get('next_renewal', 
            self.due_date + timedelta(days=payment_data.get('renewal_period', 30)))

class Ticket:
    def __init__(self, ticket_data):
        self.id = str(ticket_data['_id'])
        self.user_id = ticket_data['user_id']
        self.subject = ticket_data['subject']
        self.description = ticket_data['description']
        self.status = ticket_data.get('status', 'open')
        self.created_at = ticket_data.get('created_at', datetime.utcnow())
        self.replies = ticket_data.get('replies', [])
        
    def add_reply(self, user_id, message, is_admin=False):
        reply = {
            'user_id': user_id,
            'message': message,
            'is_admin': is_admin,
            'created_at': datetime.utcnow()
        }
        self.replies.append(reply)
        
    def update_status(self, status):
        if status in ['open', 'waiting', 'closed']:
            self.status = status

class Coupon:
    def __init__(self, coupon_data):
        self.id = str(coupon_data['_id'])
        self.code = coupon_data['code']
        self.discount = coupon_data['discount']
        self.usage_limit = coupon_data['usage_limit']
        self.used_count = coupon_data.get('used_count', 0)
        self.created_at = coupon_data.get('created_at', datetime.utcnow())

class Plan:
    def __init__(self, plan_data):
        self.id = str(plan_data['_id'])
        self.name = plan_data['name']
        self.price = plan_data['price']
        self.description = plan_data['description']
        self.renewal_period = plan_data['renewal_period']  # in days
        self.created_at = plan_data.get('created_at', datetime.utcnow())
