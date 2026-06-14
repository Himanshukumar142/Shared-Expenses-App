"""
URL configuration for config project.
This file defines root level routing. It includes endpoints for simple_jwt token 
authentication and includes urls from the expenses app.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Admin Panel route
    path('admin/', admin.site.urls),
    
    # Authentication APIs
    # SimpleJWT's TokenObtainPairView handles credentials checks and returns access & refresh tokens.
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # App-specific APIs (e.g. registration, groups, expenses, settlements)
    path('api/', include('expenses.urls')),
]
