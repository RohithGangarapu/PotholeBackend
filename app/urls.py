"""
URL Configuration for Pothole Detection System API

This module defines all API routes using Django REST Framework routers.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, IOTDeviceViewSet, PotholeViewSet, AlertViewSet

# Create router and register ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'devices', IOTDeviceViewSet, basename='device')
router.register(r'potholes', PotholeViewSet, basename='pothole')
router.register(r'alerts', AlertViewSet, basename='alert')

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
]
