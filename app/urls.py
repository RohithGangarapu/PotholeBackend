"""
URL Configuration for Pothole Detection System API

This module defines all API routes using Django REST Framework routers.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, IOTDeviceViewSet, PotholeViewSet, AlertViewSet, LoginView,
    VideoStreamView, VideoStreamStatusView, FrameProcessingView
)

# Create router and register ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'devices', IOTDeviceViewSet, basename='device')
router.register(r'potholes', PotholeViewSet, basename='pothole')
router.register(r'alerts', AlertViewSet, basename='alert')

# URL patterns
urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    # Video streaming endpoints (status must come before general route)
    path('video-stream/status/', VideoStreamStatusView.as_view(), name='video-stream-status'),
    path('video-stream/', VideoStreamView.as_view(), name='video-stream-post'),
    path('video-stream/<str:stream_id>/', VideoStreamView.as_view(), name='video-stream-delete'),
    # Frame processing endpoints
    path('frame-processing/', FrameProcessingView.as_view(), name='frame-processing-stats'),
    path('frame-processing/<str:task_id>/', FrameProcessingView.as_view(), name='frame-processing-task'),
    # Router URLs
    path('', include(router.urls)),
]
