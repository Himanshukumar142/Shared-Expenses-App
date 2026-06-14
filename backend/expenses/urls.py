"""
URL configuration for the expenses app.
This file maps API paths directly to backend views and registers REST ViewSets
using Django REST Framework's DefaultRouter.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, GroupViewSet, ExpenseViewSet, SettlementViewSet,
    GroupBalancesView, CSVImportView, ImportReportDetailView, 
    ApproveAnomalyView, SetupDefaultEnvironmentView
)

# Using DefaultRouter for standard REST ViewSets (Groups, Expenses, Settlements)
router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'settlements', SettlementViewSet, basename='settlement')

urlpatterns = [
    # Router inclusion (provides /api/groups/, /api/expenses/, /api/settlements/)
    path('', include(router.urls)),
    
    # Registration endpoint
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    
    # Custom Calculation and Traceability endpoint
    path('groups/<int:pk>/balances/', GroupBalancesView.as_view(), name='group_balances'),
    
    # CSV Import Parser endpoint
    path('import/', CSVImportView.as_view(), name='csv_import'),
    
    # Anomaly Reports detail and resolution actions endpoints
    path('import-report/<int:id>/', ImportReportDetailView.as_view(), name='import_report_detail'),
    path('import-report/anomalies/<int:id>/approve/', ApproveAnomalyView.as_view(), name='approve_anomaly'),
    
    # Bootstrap setup endpoint to seed default users and groups in one click
    path('setup/', SetupDefaultEnvironmentView.as_view(), name='setup_environment'),
]
