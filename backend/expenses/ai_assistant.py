"""
Why this exists:
This file implements the core Natural Language Processing (NLP) rule engine
for our FairShare offline AI Assistant. It parses queries, queries the database,
and generates smart, accurate conversational responses in English.
"""

import re
from decimal import Decimal
from datetime import datetime
from .models import Group, GroupMember, User, Expense, Settlement, ImportAnomaly
from .calculations import calculate_group_balances, simplify_debts

def process_ai_query(group_id, query_text):
    query_text = query_text.lower().strip()
    
    # 1. Verify group exists
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return "Group not found. Please verify the group ID."

    # Fetch calculation details
    balances_summary = calculate_group_balances(group_id)
    simplified_settlements = simplify_debts(balances_summary)
    
    # Map usernames for checking
    members = group.members.all()
    member_names = [m.user.username.lower() for m in members]
    all_users = User.objects.all()
    system_usernames = [u.username.lower() for u in all_users]

    # Pre-calculated facts
    total_expenses = Expense.objects.filter(group=group).count()
    total_amount_inr = sum(e.normalized_amount_inr for e in Expense.objects.filter(group=group))

    # Helper format currency
    def fmt_curr(val):
        return f"₹{float(val):,.2f}"

    # --------------------------------------------------------------------------
    # CASE 1: Greeting or Help
    # --------------------------------------------------------------------------
    if any(greet in query_text for greet in ['hi', 'hello', 'hey', 'help', 'assist', 'kaise', 'options']):
        reply = (
            f"Hello! I am your FairShare AI Assistant for the **{group.name}** group. 😊\n\n"
            "You can ask me questions about group expenses and balances in natural language. "
            "Try these queries:\n"
            "- *'Who owes whom?'* or *'How to settle?'* (Aisha's Simplified settlements)\n"
            "- *'Explain Rohan's balance'* or *'Rohan outstanding status?'* (Rohan's Traceability)\n"
            "- *'Are there duplicates?'* or *'CSV anomalies?'* (Meera's review cards)\n"
            "- *'When did Meera leave?'* or *'Who joined when?'* (Sam's & Meera's timelines)\n"
            "- *'Total group expenses'* or *'How much did we spend?'*"
        )
        return reply

    # --------------------------------------------------------------------------
    # CASE 2: Settlements ("who owes whom", "settle", "payment", "aisha")
    # --------------------------------------------------------------------------
    if any(k in query_text for k in ['owe', 'settle', 'pay', 'payment', 'hisab', 'kisko', 'aisha', 'simplify']):
        if not simplified_settlements:
            return "Everyone is fully settled! 😄 No outstanding debts."
        
        reply = "Here are the simplified settlements (Aisha's greedy minimizer algorithm): 💸\n\n"
        for idx, s in enumerate(simplified_settlements):
            reply += f"{idx+1}. **{s['from_user']}** pays **{s['to_user']}** -> **{fmt_curr(s['amount'])}**\n"
        reply += "\n*Note: This simplifies all multi-party transfers to prevent redundant payments.*"
        return reply

    # --------------------------------------------------------------------------
    # CASE 3: CSV Anomalies / Duplicates / Review warnings
    # --------------------------------------------------------------------------
    if any(k in query_text for k in ['anomaly', 'anomalies', 'duplicate', 'review', 'warning', 'galti', 'excel', 'csv', 'conflict']):
        # Find pending anomalies
        pending_anomalies = ImportAnomaly.objects.filter(status='pending_review')
        if not pending_anomalies.exists():
            return "There are no duplicate expenses or anomalies pending review! The CSV import data is clean. 👍"
        
        reply = f"Detected **{pending_anomalies.count()}** pending anomalies in the CSV review queue: ⚠️\n\n"
        for a in pending_anomalies:
            row_data = a.row_data
            reply += f"- **Row #{a.row_number}** ({a.severity}): {a.anomaly_type} in '{row_data.get('title', 'Expense')}' by {row_data.get('paid_by', 'Unknown')}. Status is `{a.status}`.\n"
        reply += "\n*Go to 'CSV Import' -> 'Review Screen' to approve or reject them!*"
        return reply

    # --------------------------------------------------------------------------
    # CASE 4: Timeline / Join Date / Leave Date / Sam / Meera
    # --------------------------------------------------------------------------
    if any(k in query_text for k in ['timeline', 'join', 'leave', 'left', 'active', 'date', 'member', 'joined_at']):
        reply = "Here is the group timeline and active periods: 📅\n\n"
        for m in members:
            left_str = m.left_at.strftime('%Y-%m-%d') if m.left_at else "Active indefinitely"
            reply += f"- **{m.user.username}**: Joined `{m.joined_at}` | Left: `{left_str}`\n"
        reply += "\n*Expenses are automatically split only amongst members who were active on the transaction date (satisfies Sam's request!)*"
        return reply

    # --------------------------------------------------------------------------
    # CASE 5: Specific User Balance & Traceability (Rohan's Request)
    # --------------------------------------------------------------------------
    # Let's check if the query mentions a registered user name
    mentioned_user = None
    for name in system_usernames:
        if name in query_text:
            mentioned_user = name
            break
            
    if mentioned_user:
        # Find matching User
        user_obj = User.objects.filter(username__iexact=mentioned_user).first()
        if user_obj:
            user_title = user_obj.username
            # Get their balance info
            info = balances_summary.get(user_title)
            if not info:
                # Registered but not in group
                return f"{user_title} is registered in the system but is not a member of the group '{group.name}'."
            
            net = info['net_balance']
            ledger = info.get('ledger', [])
            
            if abs(net) < 0.05:
                status_str = "is fully settled (balance is zero)."
            elif net > 0:
                status_str = f"is **owed** {fmt_curr(net)} in total."
            else:
                status_str = f"**owes** {fmt_curr(abs(net))} in total."
                
            reply = f"### Balance Audit for **{user_title}** {status_str} 📊\n\n"
            reply += f"- **Total Paid Expenses**: {fmt_curr(info['total_paid_expenses'])}\n"
            reply += f"- **Total Owed Splits**: {fmt_curr(info['total_owed_splits'])}\n\n"
            
            if ledger:
                reply += "**Itemized Transaction Ledger:**\n"
                for item in ledger[:5]: # Show top 5
                    amt_str = f"+{fmt_curr(item['amount'])}" if item['amount'] > 0 else f"-{fmt_curr(abs(item['amount']))}"
                    reply += f"- `{item['date']}` | *{item['title']}* -> **{amt_str}**\n"
                if len(ledger) > 5:
                    reply += f"- *And {len(ledger) - 5} more transactions...*\n"
            else:
                reply += "No transactions logged in this group."
            return reply

    # --------------------------------------------------------------------------
    # CASE 6: Total spent / stats
    # --------------------------------------------------------------------------
    if any(k in query_text for k in ['total', 'spent', 'expense', 'spend', 'kharch', 'stat', 'summary', 'statistics']):
        return (
            f"### Group Financial Summary for **{group.name}** 💳\n\n"
            f"- **Total Active Members**: {members.count()}\n"
            f"- **Total Logged Expenses**: {total_expenses} items\n"
            f"- **Total Spendings**: {fmt_curr(total_amount_inr)}\n"
            f"- **Active Anomalies Pending**: {ImportAnomaly.objects.filter(status='pending_review').count()} warnings"
        )

    # --------------------------------------------------------------------------
    # DEFAULT CASE: Catch-all friendly response
    # --------------------------------------------------------------------------
    return (
        f"I'm not fully sure how to answer '{query_text}'. But I can tell you about balances, settlements, temporal timelines, and CSV anomalies. "
        "Try asking:\n"
        "- *'Who owes whom?'*\n"
        "- *'Explain Rohan's ledger'* \n"
        "- *'When did Meera leave?'*"
    )
