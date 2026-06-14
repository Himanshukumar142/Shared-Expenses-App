from rest_framework import serializers
from django.db import transaction
from django.db.models import Q
from decimal import Decimal
from .models import User, Group, GroupMember, Expense, ExpenseSplit, Settlement, ImportJob, ImportAnomaly

# ==============================================================================
# USER & REGISTRATION SERIALIZERS
# ==============================================================================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        # Using Django's secure user creation method which hashes the password automatically
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user


# ==============================================================================
# GROUP & MEMBERSHIP SERIALIZERS
# ==============================================================================
class GroupMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id')

    class Meta:
        model = GroupMember
        fields = ('id', 'user_id', 'username', 'joined_at', 'left_at')

    def validate(self, attrs):
        # Check that left_at is after joined_at if both present
        joined_at = attrs.get('joined_at')
        left_at = attrs.get('left_at')
        if joined_at and left_at and left_at < joined_at:
            raise serializers.ValidationError("Left date cannot be before joined date.")
        return attrs


class GroupSerializer(serializers.ModelSerializer):
    members = GroupMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ('id', 'name', 'description', 'created_at', 'members')


# ==============================================================================
# EXPENSE SPLIT SERIALIZERS
# ==============================================================================
class ExpenseSplitSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id')

    class Meta:
        model = ExpenseSplit
        fields = ('id', 'user_id', 'username', 'amount', 'amount_inr', 'percentage', 'share')
        read_only_fields = ('id', 'amount_inr')


# ==============================================================================
# EXPENSE SERIALIZER (NESTED CREATION SUPPORT)
# ==============================================================================
class ExpenseSerializer(serializers.ModelSerializer):
    splits = ExpenseSplitSerializer(many=True, required=False)
    paid_by_name = serializers.CharField(source='paid_by.username', read_only=True)
    paid_by_id = serializers.IntegerField(source='paid_by.id')

    class Meta:
        model = Expense
        fields = (
            'id', 'group', 'title', 'description', 'amount', 'currency', 
            'exchange_rate', 'normalized_amount_inr', 'paid_by_id', 'paid_by_name', 
            'expense_date', 'split_type', 'created_at', 'splits'
        )
        read_only_fields = ('id', 'normalized_amount_inr', 'created_at')

    def create(self, validated_data):
        # We process splits nested in transaction to avoid partial database writes
        splits_data = self.context.get('request').data.get('splits', [])
        paid_by_id = validated_data.pop('paid_by_id')
        
        # Resolve paid_by user
        paid_by = User.objects.get(id=paid_by_id)
        validated_data['paid_by'] = paid_by
        
        group = validated_data['group']
        expense_date = validated_data['expense_date']
        split_type = validated_data.get('split_type', 'equal')
        amount = validated_data['amount']

        with transaction.atomic():
            # Create the Expense instance (its save hook calculates normalized_amount_inr)
            expense = Expense.objects.create(**validated_data)

            # Query the database to find group members active on this specific date
            # This directly satisfies Sam's active membership filtering request
            active_memberships = GroupMember.objects.filter(
                group=group,
                joined_at__lte=expense_date
            ).filter(
                Q(left_at__isnull=True) | Q(left_at__gte=expense_date)
            )
            
            active_users = [membership.user for membership in active_memberships]

            if not active_users:
                raise serializers.ValidationError(
                    f"No active members exist in this group on date {expense_date}."
                )

            # Case A: Equal split (default or if no explicit splits passed)
            if split_type == 'equal' or not splits_data:
                share_amount = amount / Decimal(len(active_users))
                for user in active_users:
                    ExpenseSplit.objects.create(
                        expense=expense,
                        user=user,
                        amount=share_amount
                    )

            # Case B: Manual Splits (EXACT/Percentage/Share) provided by client / CSV importer
            else:
                parsed_sum = Decimal('0.00')
                total_percentage = Decimal('0.00')
                total_shares = Decimal('0.00')
                
                # First pass: parse tokens and check active membership
                for split_item in splits_data:
                    user_id = split_item.get('user_id')
                    try:
                        user = User.objects.get(id=user_id)
                    except User.DoesNotExist:
                        raise serializers.ValidationError(f"User with ID {user_id} does not exist.")
                        
                    # Verify user is active on date
                    if user not in active_users:
                        raise serializers.ValidationError(
                            f"Member {user.username} is not active in this group on date {expense_date}."
                        )

                    split_amount = Decimal(str(split_item.get('amount', '0.00')))
                    percentage = split_item.get('percentage', None)
                    share = split_item.get('share', None)
                    
                    if percentage is not None:
                        total_percentage += Decimal(str(percentage))
                    if share is not None:
                        total_shares += Decimal(str(share))
                        
                    parsed_sum += split_amount

                    # Save split
                    ExpenseSplit.objects.create(
                        expense=expense,
                        user=user,
                        amount=split_amount,
                        percentage=percentage,
                        share=share
                    )

                # Split verification checks
                if split_type == 'exact' and abs(parsed_sum - amount) > Decimal('0.05'):
                    raise serializers.ValidationError(
                        f"Exact splits sum ({parsed_sum}) must equal total amount ({amount})."
                    )
                elif split_type == 'percentage' and abs(total_percentage - Decimal('100.00')) > Decimal('0.05'):
                    raise serializers.ValidationError(
                        f"Percentage splits sum ({total_percentage}%) must equal 100%."
                    )

            return expense


# ==============================================================================
# SETTLEMENT SERIALIZER
# ==============================================================================
class SettlementSerializer(serializers.ModelSerializer):
    payer_name = serializers.CharField(source='payer.username', read_only=True)
    payee_name = serializers.CharField(source='payee.username', read_only=True)
    payer_id = serializers.IntegerField(source='payer.id')
    payee_id = serializers.IntegerField(source='payee.id')

    class Meta:
        model = Settlement
        fields = (
            'id', 'group', 'payer_id', 'payer_name', 'payee_id', 'payee_name', 
            'amount', 'currency', 'settled_at', 'created_at'
        )
        read_only_fields = ('id', 'created_at')

    def create(self, validated_data):
        payer_id = validated_data.pop('payer_id')
        payee_id = validated_data.pop('payee_id')
        
        # Verify users exist
        payer = User.objects.get(id=payer_id)
        payee = User.objects.get(id=payee_id)
        
        validated_data['payer'] = payer
        validated_data['payee'] = payee
        
        return Settlement.objects.create(**validated_data)


# ==============================================================================
# IMPORT JOB & ANOMALY SERIALIZERS
# ==============================================================================
class ImportAnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportAnomaly
        fields = ('id', 'import_job', 'row_number', 'anomaly_type', 'severity', 'action_taken', 'status', 'row_data')


class ImportJobSerializer(serializers.ModelSerializer):
    anomalies = ImportAnomalySerializer(many=True, read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = ImportJob
        fields = ('id', 'uploaded_by_name', 'status', 'file_name', 'created_at', 'anomalies')
