from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from bson.objectid import ObjectId
from extensions import db
from models import Ticket

ticket_bp = Blueprint('ticket', __name__)

@ticket_bp.route('/create-ticket', methods=['GET', 'POST'])
@login_required
def create_ticket():
    if request.method == 'POST':
        subject = request.form.get('subject')
        description = request.form.get('description')
        
        ticket_data = {
            'user_id': current_user.id,
            'subject': subject,
            'description': description,
            'status': 'open',
            'created_at': datetime.utcnow()
        }
        
        db.tickets.insert_one(ticket_data)
        flash('Ticket created successfully', 'success')
        return redirect(url_for('ticket.ticket_status'))
    
    return render_template('ticket/create_ticket.html')

@ticket_bp.route('/ticket-status')
@login_required
def ticket_status():
    tickets = db.tickets.find({'user_id': current_user.id})
    return render_template('ticket/ticket_status.html', tickets=tickets)

@ticket_bp.route('/ticket/<ticket_id>')
@login_required
def view_ticket(ticket_id):
    ticket = db.tickets.find_one({'_id': ObjectId(ticket_id)})
    
    if ticket and ticket['user_id'] == current_user.id:
        return render_template('ticket/view_ticket.html', ticket=ticket)
    
    flash('Ticket not found', 'danger')
    return redirect(url_for('ticket.ticket_status'))
