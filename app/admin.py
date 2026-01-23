"""
Django Admin Configuration for Pothole Detection System

This module configures the Django admin interface for managing
users, devices, potholes, and alerts.
"""

from django.contrib import admin
from .models import User, IOTDevice, Pothole, Alert


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Admin configuration for User model.
    """
    list_display = ['id', 'username', 'email', 'phone', 'created_at']
    list_filter = ['created_at']
    search_fields = ['username', 'email', 'phone']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('username', 'email', 'phone', 'password')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # Hash password if it's not already hashed (very basic check)
        if obj.password and not obj.password.startswith('pbkdf2_sha256$'):
            from django.contrib.auth.hashers import make_password
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


@admin.register(IOTDevice)
class IOTDeviceAdmin(admin.ModelAdmin):
    """
    Admin configuration for IOT Device model.
    """
    list_display = ['id', 'device_type', 'mac_id', 'status', 'owner', 'registered_at']
    list_filter = ['status', 'device_type', 'registered_at']
    search_fields = ['id', 'mac_id', 'device_type']
    readonly_fields = ['id', 'registered_at']
    
    fieldsets = (
        ('Device Information', {
            'fields': ('device_type', 'mac_id', 'status')
        }),
        ('User Association', {
            'fields': ('owner', 'registered_by')
        }),
        ('Timestamps', {
            'fields': ('registered_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Pothole)
class PotholeAdmin(admin.ModelAdmin):
    """
    Admin configuration for Pothole model.
    """
    list_display = ['id', 'severity', 'status', 'depth', 'device', 'user', 'detected_at']
    list_filter = ['severity', 'status', 'detected_at']
    search_fields = ['id', 'address']
    readonly_fields = ['id', 'detected_at']
    
    fieldsets = (
        ('Pothole Information', {
            'fields': ('depth', 'severity', 'status', 'image')
        }),
        ('Device & User', {
            'fields': ('device', 'user')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'address')
        }),
        ('Timestamps', {
            'fields': ('detected_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """
    Admin configuration for Alert model.
    """
    list_display = ['id', 'alert_type', 'user', 'pothole', 'distance', 'alert_time']
    list_filter = ['alert_type', 'alert_time']
    search_fields = ['id', 'alert_text']
    readonly_fields = ['id', 'alert_time']
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('alert_type', 'alert_text', 'distance')
        }),
        ('Associations', {
            'fields': ('user', 'pothole')
        }),
        ('Timestamps', {
            'fields': ('alert_time',),
            'classes': ('collapse',)
        }),
    )
