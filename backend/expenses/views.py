import csv
import io
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import User, Group, GroupMember, Expense, ExpenseSplit, Settlement, ImportJob, ImportAnomaly
from .serializers import (
    RegisterSerializer, UserSerializer, GroupSerializer, 
    ExpenseSerializer, SettlementSerializer, ImportJobSerializer, 
    ImportAnomalySerializer
)
from .calculations import calculate_group_balances, simplify_debts
from .anomaly_engine import run_anomaly_detection, clean_username, parse_dirty_date, FIXED_USD_TO_INR_RATE, VALID_USERS

# ==============================================================================
# AUTHENTICATION: REGISTER VIEW
# ==============================================================================
class RegisterView(APIView):
    """
    Why this exists:
    Endpoint: POST /api/auth/register/
    Allows prospective flatmates to register a new user in the database.
    """
    permission_classes = [permissions.AllowAny] # Anyone can sign up

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Registration successful!", "user": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# GROUPS MANAGEMENT
# ==============================================================================
class GroupViewSet(viewsets.ModelViewSet):
    """
    Why this exists:
    Endpoints: GET /api/groups/, POST /api/groups/, GET /api/groups/{id}/
    Provides CRUD operations for managing shared expense groups.
    """
    queryset = Group.objects.all().order_by('-created_at')
    serializer_class = GroupSerializer

    @action(detail=True, methods=['post'], url_path='members')
    def add_member(self, request, pk=None):
        """
        Endpoint: POST /api/groups/{id}/members/
        Adds a user to a group with specific membership active dates (joined_at, left_at).
        Fulfills Sam's & Meera's membership temporal requests.
        """
        group = self.get_object()
        user_id = request.data.get('user_id')
        joined_at_str = request.data.get('joined_at')
        left_at_str = request.data.get('left_at', None)

        if not user_id or not joined_at_str:
            return Response(
                {"error": "user_id and joined_at are required fields."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
            joined_at = datetime.strptime(joined_at_str, '%Y-%m-%d').date()
            left_at = datetime.strptime(left_at_str, '%Y-%m-%d').date() if left_at_str else None
            
            # Create or update member details
            member, created = GroupMember.objects.update_or_create(
                user=user,
                group=group,
                joined_at=joined_at,
                defaults={'left_at': left_at}
            )
            
            return Response(
                {"message": f"Member {user.username} successfully linked to group.", "created": created},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# EXPENSES MANAGEMENT
# ==============================================================================
class ExpenseViewSet(viewsets.ModelViewSet):
    """
    Why this exists:
    Endpoints: GET /api/expenses/, POST /api/expenses/
    Manages creation and list retrieval of group expense items.
    """
    queryset = Expense.objects.all().order_by('-expense_date', '-id')
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        # Allow filtering by group
        group_id = self.request.query_params.get('group_id', None)
        if group_id:
            return self.queryset.filter(group_id=group_id)
        return self.queryset


# ==============================================================================
# BALANCES & SETTLEMENTS CALCULATIONS
# ==============================================================================
class GroupBalancesView(APIView):
    """
    Why this exists:
    Endpoint: GET /api/groups/{id}/balances/
    Retrieves the complete balance summary of all members, detailed audit ledgers
    for individual transparency, and a simplified list of payments to clear debts.
    """
    def get(self, request, pk=None):
        try:
            # 1. Compute net balances & ledger logs
            balances_summary = calculate_group_balances(pk)
            
            # 2. Run greedy algorithm to simplify payments (Aisha's request)
            simplified_payments = simplify_debts(balances_summary)
            
            return Response({
                "group_id": pk,
                "balances": balances_summary,
                "simplified_settlements": simplified_payments
            }, status=status.HTTP_200_OK)
        except Group.DoesNotExist:
            return Response({"error": "Group not found."}, status=status.HTTP_44_NOT_FOUND)


class SettlementViewSet(viewsets.ModelViewSet):
    """
    Why this exists:
    Endpoint: POST /api/settlements/
    Logs a direct payment between members within a group to settle accounts.
    """
    queryset = Settlement.objects.all().order_by('-settled_at')
    serializer_class = SettlementSerializer


# ==============================================================================
# CSV PARSING & ANOMALY LOG IMPORT
# ==============================================================================
class CSVImportView(APIView):
    """
    Why this exists:
    Endpoint: POST /api/import/
    Ingests the expenses spreadsheet export. Triggers anomaly detection engine,
    performs auto-cleaning, imports safe rows, and logs discrepancies for approval.
    """
    def post(self, request):
        file_obj = request.FILES.get('file', None)
        group_id = request.data.get('group_id', None)
        
        if not file_obj:
            return Response({"error": "No CSV file provided."}, status=status.HTTP_400_BAD_REQUEST)
        if not group_id:
            return Response({"error": "Target group_id is required to import expenses."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({"error": "Group does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Parse CSV rows using default dict reader
        csv_rows = []
        try:
            # Read decoded byte-stream
            decoded_file = file_obj.read().decode('utf-8-sig').splitlines()
            reader = csv.DictReader(decoded_file)
            for row in reader:
                csv_rows.append(dict(row))
        except Exception as e:
            return Response({"error": f"Failed to parse CSV file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Execute the Anomaly Detection Engine
        report = run_anomaly_detection(csv_rows)

        # 3. Save import job details
        with transaction.atomic():
            import_job = ImportJob.objects.create(
                uploaded_by=request.user,
                status='pending',
                file_name=file_obj.name
            )

            imported_count = 0
            flagged_count = 0
            rejected_count = 0
            settlements_detected = 0

            # Step 3A: Auto-Import Approved Rows
            for clean_row in report['valid_records']:
                # Decides if it is a settlement or expense
                if clean_row['is_settlement']:
                    settlements_detected += 1
                    recipient_name = clean_row['split_with'][0]
                    payee = User.objects.get(username=recipient_name)
                    payer = User.objects.get(username=clean_row['paid_by'])
                    
                    Settlement.objects.create(
                        group=group,
                        payer=payer,
                        payee=payee,
                        amount=clean_row['amount'],
                        currency=clean_row['currency'],
                        settled_at=clean_row['date']
                    )
                else:
                    # Create regular Expense
                    payer = User.objects.get(username=clean_row['paid_by'])
                    expense = Expense.objects.create(
                        group=group,
                        title=clean_row['description'],
                        amount=clean_row['amount'],
                        currency=clean_row['currency'],
                        exchange_rate=clean_row['exchange_rate'],
                        paid_by=payer,
                        expense_date=clean_row['date'],
                        split_type=clean_row['split_type'],
                        description=clean_row['original_notes']
                    )
                    
                    # Create its nested splits
                    for member, share_amt in clean_row['split_details'].items():
                        member_user = User.objects.get(username=member)
                        # Estimate percentage/share for split if applicable
                        pct = None
                        if clean_row['split_type'] == 'percentage':
                            # Read original percentage string token
                            pct = Decimal('100') / len(clean_row['split_with']) # approximation or parse
                        
                        ExpenseSplit.objects.create(
                            expense=expense,
                            user=member_user,
                            amount=share_amt
                        )
                imported_count += 1

            # Step 3B: Log Warning & Critical Anomalies for approval (Fulfills Meera's request)
            for anomaly in report['anomalies']:
                ImportAnomaly.objects.create(
                    import_job=import_job,
                    row_number=anomaly['row_number'],
                    anomaly_type=anomaly['anomaly_type'],
                    severity=anomaly['severity'],
                    action_taken=anomaly['action_taken'],
                    status=anomaly['status'],
                    row_data=anomaly['row_data']
                )
                if anomaly['status'] == 'pending_review':
                    flagged_count += 1
                else:
                    rejected_count += 1

            # Update final job status if no reviews pending
            if flagged_count == 0:
                import_job.status = 'processed'
                import_job.save()

        # Assemble counts summary
        summary = {
            "job_id": import_job.id,
            "total_rows": report['total_rows'],
            "imported_rows": imported_count,
            "flagged_rows": flagged_count,
            "rejected_rows": rejected_count,
            "settlements_detected": settlements_detected
        }

        return Response({
            "message": "CSV processing complete.",
            "report_summary": summary,
            "anomalies": ImportAnomalySerializer(import_job.anomalies.all(), many=True).data
        }, status=status.HTTP_200_OK)


class ImportReportDetailView(APIView):
    """
    Why this exists:
    Endpoint: GET /api/import-report/{id}/
    Loads summary report counts and specific anomalies list for a specific ImportJob.
    """
    def get(self, request, id):
        try:
            job = ImportJob.objects.get(id=id)
            anomalies = job.anomalies.all().order_by('row_number')
            
            # Recompute counts
            total = len(anomalies) + Expense.objects.filter(splits__isnull=False).distinct().count() # approx
            flagged = anomalies.filter(status='pending_review').count()
            rejected = anomalies.filter(status='rejected').count()
            
            return Response({
                "job_id": job.id,
                "file_name": job.file_name,
                "uploaded_by": job.uploaded_by.username,
                "status": job.status,
                "created_at": job.created_at,
                "stats": {
                    "flagged_count": flagged,
                    "rejected_count": rejected,
                },
                "anomalies": ImportAnomalySerializer(anomalies, many=True).data
            }, status=status.HTTP_200_OK)
        except ImportJob.DoesNotExist:
            return Response({"error": "Import job report not found."}, status=status.HTTP_404_NOT_FOUND)


class ApproveAnomalyView(APIView):
    """
    Why this exists:
    Endpoint: POST /api/import-report/anomalies/{id}/approve/
    Fulfills Meera's request. Overrides a flagged duplicate/warning anomaly,
    re-processes the record and adds it directly to the active ledger balances.
    """
    def post(self, request, id):
        action = request.data.get('action', 'approve') # 'approve' or 'reject'
        try:
            anomaly = ImportAnomaly.objects.get(id=id)
            if anomaly.status != 'pending_review':
                return Response({"error": "This anomaly has already been reviewed."}, status=status.HTTP_400_BAD_REQUEST)
                
            group_id = request.data.get('group_id')
            if not group_id:
                return Response({"error": "group_id is required to resolve review items."}, status=status.HTTP_400_BAD_REQUEST)
                
            group = Group.objects.get(id=group_id)

            if action == 'reject':
                anomaly.status = 'rejected'
                anomaly.action_taken = "Rejected manually by user."
                anomaly.save()
                return Response({"message": "Anomaly rejected successfully."}, status=status.HTTP_200_OK)

            # Re-process and Save
            row = anomaly.row_data
            
            # Re-run parser heuristics
            parsed_date = parse_dirty_date(row.get('date'))
            payer_name = clean_username(row.get('paid_by'))
            amount_str = str(row.get('amount', '0')).replace('"', '').replace(',', '')
            amount_val = Decimal(amount_str)
            currency = row.get('currency', 'INR').strip().upper()
            if not currency:
                currency = 'INR'
            
            exchange_rate = Decimal('1.00')
            if currency == 'USD':
                exchange_rate = FIXED_USD_TO_INR_RATE

            desc = row.get('description', 'Manually Approved Expense').strip()
            split_type = row.get('split_type', 'equal').strip().lower()
            if split_type == 'unequal' or not split_type:
                split_type = 'equal'

            # Parse split participants
            raw_split_with = row.get('split_with', '').replace('"', '')
            raw_list = [m.strip() for m in raw_split_with.split(';') if m.strip()]
            split_members = [clean_username(m) for m in raw_list if clean_username(m) in VALID_USERS]

            with transaction.atomic():
                payer = User.objects.get(username=payer_name)
                
                # Check if it was a settlement
                is_settlement = 'paid back' in desc.lower() or 'deposit share' in desc.lower() or not row.get('split_type')
                
                if is_settlement and split_members:
                    payee = User.objects.get(username=split_members[0])
                    Settlement.objects.create(
                        group=group,
                        payer=payer,
                        payee=payee,
                        amount=amount_val,
                        currency=currency,
                        settled_at=parsed_date or datetime.today().date()
                    )
                else:
                    # Save manual approved expense
                    expense = Expense.objects.create(
                        group=group,
                        title=desc,
                        amount=amount_val,
                        currency=currency,
                        exchange_rate=exchange_rate,
                        paid_by=payer,
                        expense_date=parsed_date or datetime.today().date(),
                        split_type=split_type
                    )
                    
                    # Split equally among active users
                    share_amount = amount_val / len(split_members) if split_members else amount_val
                    for member in split_members:
                        member_user = User.objects.get(username=member)
                        ExpenseSplit.objects.create(
                            expense=expense,
                            user=member_user,
                            amount=share_amount
                        )

                anomaly.status = 'approved'
                anomaly.action_taken = "Approved manually by user during review."
                anomaly.save()

                # Check if all other anomalies for this job are reviewed
                job = anomaly.import_job
                if job.anomalies.filter(status='pending_review').count() == 0:
                    job.status = 'processed'
                    job.save()

            return Response({"message": f"Anomaly row #{anomaly.row_number} successfully approved and imported!"}, status=status.HTTP_200_OK)
        except ImportAnomaly.DoesNotExist:
            return Response({"error": "Anomaly not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Failed to approve anomaly: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# SEEDING: BOOTSTRAP ENVIRONMENT VIEW
# ==============================================================================
class SetupDefaultEnvironmentView(APIView):
    """
    Why this exists:
    Endpoint: POST /api/setup/
    A utility endpoint to create default users and active memberships
    covering Meera's & Sam's specific dates to start testing immediately.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        with transaction.atomic():
            # 1. Create Default Users (Aisha, Rohan, Priya, Meera, Sam, Dev)
            seeded_users = {}
            for username in VALID_USERS:
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': f"{username.lower()}@example.com",
                        'is_active': True
                    }
                )
                if created or user.password == '':
                    user.set_password('Password123')
                    user.save()
                seeded_users[username] = user

            # 2. Create Default Group
            group, created = Group.objects.get_or_create(
                name="Flatmates",
                defaults={'description': "Shared expenses for Aisha, Rohan, Priya, Meera, Sam & Dev"}
            )

            # 3. Create Group Members with required Joined/Left Dates
            # Aisha: joined Feb 1, 2026. Left: Active
            GroupMember.objects.update_or_create(
                user=seeded_users['Aisha'], group=group,
                defaults={'joined_at': datetime(2026, 2, 1).date(), 'left_at': None}
            )
            # Rohan: joined Feb 1, 2026. Left: Active
            GroupMember.objects.update_or_create(
                user=seeded_users['Rohan'], group=group,
                defaults={'joined_at': datetime(2026, 2, 1).date(), 'left_at': None}
            )
            # Priya: joined Feb 1, 2026. Left: Active
            GroupMember.objects.update_or_create(
                user=seeded_users['Priya'], group=group,
                defaults={'joined_at': datetime(2026, 2, 1).date(), 'left_at': None}
            )
            # Meera: joined Feb 1, 2026. Left: March 31, 2026
            GroupMember.objects.update_or_create(
                user=seeded_users['Meera'], group=group,
                defaults={'joined_at': datetime(2026, 2, 1).date(), 'left_at': datetime(2026, 3, 31).date()}
            )
            # Sam: joined April 15, 2026. Left: Active
            GroupMember.objects.update_or_create(
                user=seeded_users['Sam'], group=group,
                defaults={'joined_at': datetime(2026, 4, 15).date(), 'left_at': None}
            )
            # Dev: joined Feb 1, 2026. Left: March 31, 2026 (Goa visit timeline)
            GroupMember.objects.update_or_create(
                user=seeded_users['Dev'], group=group,
                defaults={'joined_at': datetime(2026, 2, 1).date(), 'left_at': datetime(2026, 3, 31).date()}
            )

        return Response({
            "message": "Default environment successfully created!",
            "users": list(seeded_users.keys()),
            "default_password": "Password123",
            "group": group.name,
            "group_id": group.id
        }, status=status.HTTP_200_OK)


# ==============================================================================
# USER VIEWSET
# ==============================================================================
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Why this exists:
    Endpoints: GET /api/users/
    Provides a read-only list of all registered users in the system.
    Useful for selecting users in dropdown menus.
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

