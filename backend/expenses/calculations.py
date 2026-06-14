from decimal import Decimal
from collections import defaultdict
from .models import User, Group, GroupMember, Expense, ExpenseSplit, Settlement

# ==============================================================================
# CALCULATE GROUP BALANCES & LEDGER (TRACEABILITY)
# ==============================================================================
def calculate_group_balances(group_id):
    """
    Why this exists:
    Calculates the detailed net balance and ledger items for all members of a group.
    This provides both Aisha's summary and Rohan's detailed traceability breakdown.
    
    Business Logic:
    For each user:
      Net Balance = (Expenses Paid + Settlements Paid) - (Expense Splits Owed + Settlements Received)
    """
    group = Group.objects.get(id=group_id)
    # Fetch all users associated with this group
    members = [gm.user for gm in group.members.all()]
    
    # Dictionaries to store aggregate values
    expenses_paid = defaultdict(Decimal)      # Total amount spent by user as payer
    splits_owed = defaultdict(Decimal)        # Total amount user owes from splits
    settlements_paid = defaultdict(Decimal)   # Settlements user paid to others
    settlements_received = defaultdict(Decimal) # Settlements user received from others
    
    # Ledger will store list of line items for Rohan's traceability request
    # Format: { username: [ { date, title, amount, type }, ... ] }
    ledger = defaultdict(list)

    # 1. Process Expenses
    expenses = group.expenses.all().order_by('expense_date', 'id')
    for expense in expenses:
        # Add to paid amount for the payer
        expenses_paid[expense.paid_by.username] += expense.normalized_amount_inr
        ledger[expense.paid_by.username].append({
            'date': expense.expense_date.strftime('%Y-%m-%d'),
            'title': f"Paid for: {expense.title}",
            'amount': expense.normalized_amount_inr,
            'type': 'payment_made', # Positive impact on balance
            'expense_id': expense.id
        })

        # Add to owed amount for split participants
        for split in expense.splits.all():
            splits_owed[split.user.username] += split.amount_inr
            ledger[split.user.username].append({
                'date': expense.expense_date.strftime('%Y-%m-%d'),
                'title': f"Share of: {expense.title}",
                'amount': -split.amount_inr,
                'type': 'share_owed', # Negative impact on balance
                'expense_id': expense.id
            })

    # 2. Process Settlements
    settlements = group.settlements.all().order_by('settled_at', 'id')
    for settlement in settlements:
        settlements_paid[settlement.payer.username] += settlement.amount
        ledger[settlement.payer.username].append({
            'date': settlement.settled_at.strftime('%Y-%m-%d'),
            'title': f"Settlement paid to {settlement.payee.username}",
            'amount': settlement.amount,
            'type': 'settlement_made', # Positive impact on balance
            'settlement_id': settlement.id
        })

        settlements_received[settlement.payee.username] += settlement.amount
        ledger[settlement.payee.username].append({
            'date': settlement.settled_at.strftime('%Y-%m-%d'),
            'title': f"Settlement received from {settlement.payer.username}",
            'amount': -settlement.amount,
            'type': 'settlement_received', # Negative impact on balance
            'settlement_id': settlement.id
        })

    # 3. Assemble Balances Summary
    balances_summary = {}
    for user in members:
        username = user.username
        paid = expenses_paid[username]
        owed = splits_owed[username]
        set_paid = settlements_paid[username]
        set_recv = settlements_received[username]
        
        # Core Balance Formula
        net_balance = (paid + set_paid) - (owed + set_recv)
        
        # Rounding to 2 decimal places for accuracy
        net_balance = round(net_balance, 2)
        
        balances_summary[username] = {
            'user_id': user.id,
            'total_paid_expenses': round(paid, 2),
            'total_owed_splits': round(owed, 2),
            'total_settlements_paid': round(set_paid, 2),
            'total_settlements_received': round(set_recv, 2),
            'net_balance': float(net_balance),
            'ledger': ledger[username]
        }

    return balances_summary


# ==============================================================================
# DEBT SIMPLIFICATION ALGORITHM (GREEDY MINIMIZATION)
# ==============================================================================
def simplify_debts(balances_summary):
    """
    Why this exists:
    Fulfills Aisha's request: "Who pays whom, how much, done".
    Implements a greedy algorithm to settle debts with the minimum number of transfers.
    
    Algorithm steps:
    1. Separate members into Creditors (net_balance > 0) and Debtors (net_balance < 0).
    2. Sort both lists in descending order of absolute values.
    3. Pair the largest debtor with the largest creditor.
    4. Settle the maximum possible amount: min(abs(debtor_balance), creditor_balance).
    5. Update balances and repeat until all balances are settled.
    """
    creditors = []
    debtors = []

    # Separate into debtors and creditors
    for username, data in balances_summary.items():
        balance = Decimal(str(data['net_balance']))
        # We ignore very small balances due to rounding errors (less than 0.01 INR)
        if balance > Decimal('0.01'):
            creditors.append({'username': username, 'balance': balance})
        elif balance < Decimal('-0.01'):
            debtors.append({'username': username, 'balance': abs(balance)})

    suggested_payments = []

    # Sort to start with the largest balances (greedy matching)
    creditors.sort(key=lambda x: x['balance'], reverse=True)
    debtors.sort(key=lambda x: x['balance'], reverse=True)

    while creditors and debtors:
        creditor = creditors[0]
        debtor = debtors[0]

        # Settle the minimum of the two balances
        settlement_amount = min(debtor['balance'], creditor['balance'])
        
        suggested_payments.append({
            'from_user': debtor['username'],
            'to_user': creditor['username'],
            'amount': float(round(settlement_amount, 2))
        })

        # Update remaining balances
        debtor['balance'] -= settlement_amount
        creditor['balance'] -= settlement_amount

        # Remove settled members or resort if balance remains
        if debtor['balance'] < Decimal('0.01'):
            debtors.pop(0)
        else:
            # Sort again in case the debtor still has balance
            debtors.sort(key=lambda x: x['balance'], reverse=True)

        if creditor['balance'] < Decimal('0.01'):
            creditors.pop(0)
        else:
            # Sort again in case the creditor still has balance
            creditors.sort(key=lambda x: x['balance'], reverse=True)

    return suggested_payments
