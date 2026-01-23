"""
Django Models for Pothole Detection System

These models are now managed by Django and stored in PostgreSQL.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class User(models.Model):
    """
    User model for authentication and profile management.
    """
    username = models.CharField(max_length=150, help_text="User's display name")
    email = models.EmailField(unique=True, help_text="User's email address")
    phone = models.CharField(max_length=20, help_text="User's phone number")
    password = models.CharField(max_length=128, help_text="Hashed password")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Account creation timestamp")
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.email})"


class IOTDevice(models.Model):
    """
    IOT Device model for device registration and management.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blocked', 'Blocked'),
    ]
    
    device_type = models.CharField(max_length=100, help_text="Type of IOT device")
    mac_id = models.CharField(max_length=100, unique=True, help_text="Device MAC address")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', help_text="Device status")
    registered_at = models.DateTimeField(auto_now_add=True, help_text="Device registration timestamp")
    registered_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registered_devices', help_text="Admin/owner who registered device")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_devices', help_text="User ID of device owner")
    
    class Meta:
        db_table = 'iot_devices'
        verbose_name = 'IOT Device'
        verbose_name_plural = 'IOT Devices'
        ordering = ['-registered_at']
    
    def __str__(self):
        return f"{self.device_type} - {self.mac_id}"


class Pothole(models.Model):
    """
    Pothole model for pothole detection and tracking.
    """
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('unresolved', 'Unresolved'),
        ('fixed', 'Fixed'),
        ('ignored', 'Ignored'),
    ]
    
    device = models.ForeignKey(IOTDevice, on_delete=models.CASCADE, related_name='detected_potholes', help_text="Device that detected the pothole")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_potholes', help_text="User associated with detection")
    depth = models.FloatField(validators=[MinValueValidator(0.0)], help_text="Pothole depth in cm")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, help_text="Severity level")
    image = models.ImageField(upload_to='potholes/', blank=True, null=True, help_text="Pothole image")
    detected_at = models.DateTimeField(auto_now_add=True, help_text="Detection timestamp")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unresolved', help_text="Resolution status")
    
    # Location fields
    latitude = models.FloatField(validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)], help_text="Latitude coordinate")
    longitude = models.FloatField(validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)], help_text="Longitude coordinate")
    address = models.CharField(max_length=500, blank=True, null=True, help_text="Human-readable address")
    
    class Meta:
        db_table = 'potholes'
        verbose_name = 'Pothole'
        verbose_name_plural = 'Potholes'
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"Pothole {self.id} - {self.severity} severity"


class Alert(models.Model):
    """
    Alert model for notification system.
    """
    ALERT_TYPE_CHOICES = [
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('emergency', 'Emergency'),
    ]
    
    alert_text = models.TextField(help_text="Alert message content")
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES, help_text="Type of alert")
    alert_time = models.DateTimeField(auto_now_add=True, help_text="Alert creation timestamp")
    distance = models.FloatField(validators=[MinValueValidator(0.0)], help_text="Distance to pothole in meters")
    pothole = models.ForeignKey(Pothole, on_delete=models.CASCADE, related_name='pothole_alerts', help_text="Associated pothole")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_alerts', help_text="User receiving the alert")
    
    class Meta:
        db_table = 'alerts'
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        ordering = ['-alert_time']
    
    def __str__(self):
        return f"{self.alert_type.upper()} Alert for User {self.user_id}"

    def __str__(self):
        return f"{self.alert_type.upper()} Alert for User {self.user_id}"
