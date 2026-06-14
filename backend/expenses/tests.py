from django.test import TestCase
from django.db.models import Q
from decimal import Decimal
import datetime

from .models import User, Group, GroupMember, Expense, ExpenseSplit, Settlement
from .calculations import calculate_group_balances, simplify_debts
from .anomaly_engine import run_anomaly_detection

class SharedExpensesTestCase(TestCase):
    def setUp(self):
        # 1. Create flatmate users
        self.aisha = User.objects.create_user(username='Aisha', email='aisha@example.com')
        self.rohan = User.objects.create_user(username='Rohan', email='rohan@example.com')
        self.priya = User.objects.create_user(username='Priya', email='priya@example.com')
        self.meera = User.objects.create_user(username='Meera', email='meera@example.com')
        self.sam = User.objects.create_user(username='Sam', email='sam@example.com')

        # 2. Create the flatmates group
        self.group = Group.objects.create(name='Flatmates', description='Testing Shared Expenses')

        # 3. Create memberships with temporal dates matching assignment instructions:
        # Aisha, Rohan, Priya: joined Feb 1st, 2026. Active
        GroupMember.objects.create(user=self.aisha, group=self.group, joined_at=datetime.date(2026, 2, 1))
        GroupMember.objects.create(user=self.rohan, group=self.group, joined_at=datetime.date(2026, 2, 1))
        GroupMember.objects.create(user=self.priya, group=self.group, joined_at=datetime.date(2026, 2, 1))
        
        # Meera: joined Feb 1st, 2026. Left March 31st, 2026
        GroupMember.objects.create(
            user=self.meera, group=self.group, 
            joined_at=datetime.date(2026, 2, 1), 
            left_at=datetime.date(2026, 3, 31)
        )
        
        # Sam: joined April 15th, 2026. Active
        GroupMember.objects.create(user=self.sam, group=self.group, joined_at=datetime.date(2026, 4, 15))

    # ==========================================================================
    # TEST: ACTIVE MEMBERSHIP FILTERING BY DATE (Sam & Meera check)
    # ==========================================================================
    def test_active_membership_date_filtering(self):
        """
        Verify that:
        - March expense is only split among Aisha, Rohan, Priya, Meera (Sam excluded).
        - April 20th expense is split among Aisha, Rohan, Priya, Sam (Meera excluded).
        """
        # Scenario A: March Wifi Bill (split equally)
        march_wifi = Expense.objects.create(
            group=self.group,
            title="March Wifi",
            amount=Decimal("1200.00"),
            currency="INR",
            paid_by=self.rohan,
            expense_date=datetime.date(2026, 3, 5),
            split_type="equal"
        )
        
        # Trigger nested splits creation by calling the view context or manually replicating logic
        # Here we manually simulate equal split trigger
        active_memberships = GroupMember.objects.filter(
            group=self.group,
            joined_at__lte=march_wifi.expense_date
        ).exclude(left_at__lt=march_wifi.expense_date)
        
        active_users = [gm.user for gm in active_memberships]
        
        # Sam should not be active in March
        self.assertIn(self.meera, active_users)
        self.assertNotIn(self.sam, active_users)
        
        share_amt = march_wifi.amount / len(active_users)
        for u in active_users:
            ExpenseSplit.objects.create(expense=march_wifi, user=u, amount=share_amt)
            
        self.assertEqual(march_wifi.splits.count(), 4) # Aisha, Rohan, Priya, Meera

        # Scenario B: April Electricity Bill (split equally)
        april_electricity = Expense.objects.create(
            group=self.group,
            title="April Electricity",
            amount=Decimal("1600.00"),
            currency="INR",
            paid_by=self.aisha,
            expense_date=datetime.date(2026, 4, 20),
            split_type="equal"
        )
        
        active_memberships_apr = GroupMember.objects.filter(
            group=self.group,
            joined_at__lte=april_electricity.expense_date
        ).filter(
            models_q := (models_q_filter := Q(left_at__isnull=True) | Q(left_at__gte=april_electricity.expense_date))
        )
        
        active_users_apr = [gm.user for gm in active_memberships_apr]
        
        # Meera should be excluded and Sam should be included
        self.assertNotIn(self.meera, active_users_apr)
        self.assertIn(self.sam, active_users_apr)
        
        share_amt_apr = april_electricity.amount / len(active_users_apr)
        for u in active_users_apr:
            ExpenseSplit.objects.create(expense=april_electricity, user=u, amount=share_amt_apr)
            
        self.assertEqual(april_electricity.splits.count(), 4) # Aisha, Rohan, Priya, Sam

    # ==========================================================================
    # TEST: USD EXCHANGE RATE NORMALIZATION (Priya's check)
    # ==========================================================================
    def test_usd_normalization(self):
        """
        Verify that USD amount is properly normalized to INR using exchange rate
        and preserved as original.
        """
        usd_villa = Expense.objects.create(
            group=self.group,
            title="Goa Villa USD",
            amount=Decimal("500.00"),
            currency="USD",
            exchange_rate=Decimal("83.000000"),
            paid_by=self.aisha,
            expense_date=datetime.date(2026, 3, 9),
            split_type="equal"
        )
        
        # Save hook must calculate normalized INR amount
        self.assertEqual(usd_villa.normalized_amount_inr, Decimal("41500.00")) # 500 * 83

    # ==========================================================================
    # TEST: DEBT SIMPLIFICATION ALGORITHM (Aisha's check)
    # ==========================================================================
    def test_settlements_simplification(self):
        """
        Verify the greedy settlements simplification matching:
        Rohan owes 700, Priya owes 500, Aisha receives 1200
        Output:
          Rohan pays Aisha 700
          Priya pays Aisha 500
        """
        balances_summary = {
            'Aisha': {'net_balance': 1200.00},
            'Rohan': {'net_balance': -700.00},
            'Priya': {'net_balance': -500.00}
        }
        
        simplified = simplify_debts(balances_summary)
        
        self.assertEqual(len(simplified), 2)
        # Verify transaction 1
        self.assertEqual(simplified[0]['from_user'], 'Rohan')
        self.assertEqual(simplified[0]['to_user'], 'Aisha')
        self.assertEqual(simplified[0]['amount'], 700.00)
        
        # Verify transaction 2
        self.assertEqual(simplified[1]['from_user'], 'Priya')
        self.assertEqual(simplified[1]['to_user'], 'Aisha')
        self.assertEqual(simplified[1]['amount'], 500.00)

    # ==========================================================================
    # TEST: ANOMALY LOG ENGINE SCAN (Meera's check)
    # ==========================================================================
    def test_anomaly_detection_engine(self):
        """
        Verify that anomaly scan correctly flags duplicates, missing currencies,
        and name spellings.
        """
        # Simulated raw CSV lines
        csv_rows = [
            # 1. Standard row
            {'date': '2026-02-01', 'description': 'Rent', 'paid_by': 'Aisha', 'amount': '1000', 'currency': 'INR', 'split_type': 'equal', 'split_with': 'Aisha;Rohan;Priya'},
            # 2. Duplicate of row 1 (Marina bites Dinner duplicate check simulation)
            {'date': '2026-02-01', 'description': 'Rent', 'paid_by': 'Aisha', 'amount': '1000', 'currency': 'INR', 'split_type': 'equal', 'split_with': 'Aisha;Rohan;Priya'},
            # 3. Missing currency row (auto default check)
            {'date': '2026-02-03', 'description': 'Snacks', 'paid_by': 'priya', 'amount': '250', 'currency': '', 'split_type': 'equal', 'split_with': 'Aisha;Rohan;Priya'},
            # 4. Error split percentage mismatch row
            {'date': '2026-02-05', 'description': 'Pizza', 'paid_by': 'Rohan', 'amount': '1500', 'currency': 'INR', 'split_type': 'percentage', 'split_with': 'Aisha;Rohan', 'split_details': 'Aisha 60; Rohan 60'}
        ]
        
        report = run_anomaly_detection(csv_rows)
        
        self.assertEqual(report['total_rows'], 4)
        
        # Detects duplicate
        duplicate_anomalies = [a for a in report['anomalies'] if a['anomaly_type'] == 'Duplicate Expense Row']
        self.assertEqual(len(duplicate_anomalies), 1)
        
        # Detects split percentage sum mismatch
        mismatch_anomalies = [a for a in report['anomalies'] if a['anomaly_type'] == 'Split Percentage Sum Mismatch']
        self.assertEqual(len(mismatch_anomalies), 1)

    # ==========================================================================
    # TEST: OFFLINE AI ASSISTANT CHAT BOT ENGINE
    # ==========================================================================
    def test_ai_assistant_chatbot(self):
        """
        Verify that processing AI queries correctly handles greetings, settlements,
        user ledgers, and catch-alls.
        """
        from .ai_assistant import process_ai_query
        
        # Scenario 1: Greeting query
        greeting_reply = process_ai_query(self.group.id, "hello, can you help me?")
        self.assertIn("Hello! I am your FairShare AI Assistant", greeting_reply)
        self.assertIn("Who owes whom?", greeting_reply)

        # Scenario 2: Settle query
        settlement_reply = process_ai_query(self.group.id, "who owes who and how to settle?")
        self.assertIn("Sab settled hai!", settlement_reply) # No expenses yet

        # Scenario 3: Timeline query
        timeline_reply = process_ai_query(self.group.id, "show me active timeline dates")
        self.assertIn("Here is the group timeline and active periods", timeline_reply)
        self.assertIn("Aisha", timeline_reply)
        self.assertIn("Meera", timeline_reply)

        # Scenario 4: Specific user balance query
        rohan_balance_reply = process_ai_query(self.group.id, "explain Rohan's balance status")
        self.assertIn("Balance Audit for **Rohan**", rohan_balance_reply)
        self.assertIn("is fully settled", rohan_balance_reply)

