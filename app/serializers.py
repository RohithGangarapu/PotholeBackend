"""
Django REST Framework Serializers for Pothole Detection System

These serializers handle validation and serialization of data
using standard Django models.
"""

from rest_framework import serializers
from .models import User, IOTDevice, Pothole, Alert


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    """
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'password', 'createdAt']
        read_only_fields = ['id', 'createdAt']
    
    def create(self, validated_data):
        from django.contrib.auth.hashers import make_password
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        from django.contrib.auth.hashers import make_password
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)
    
    def validate_email(self, value):
        """Validate email format"""
        if not value or '@' not in value:
            raise serializers.ValidationError("Invalid email format")
        return value.lower()
    
    def validate_phone(self, value):
        """Validate phone number"""
        # Remove spaces and dashes
        cleaned = value.replace(' ', '').replace('-', '')
        if not cleaned.isdigit() or len(cleaned) < 10:
            raise serializers.ValidationError("Invalid phone number format")
        return value


class IOTDeviceSerializer(serializers.ModelSerializer):
    """
    Serializer for IOT Device model.
    """
    deviceType = serializers.CharField(source='device_type')
    macId = serializers.CharField(source='mac_id')
    registeredAt = serializers.DateTimeField(source='registered_at', read_only=True)
    registeredBy = serializers.PrimaryKeyRelatedField(source='registered_by', queryset=User.objects.all())
    ownerId = serializers.PrimaryKeyRelatedField(source='owner', queryset=User.objects.all())
    
    class Meta:
        model = IOTDevice
        fields = [
            'id', 'deviceType', 'macId', 'status',
            'registeredAt', 'registeredBy', 'ownerId'
        ]
        read_only_fields = ['id', 'registeredAt']
    
    def validate_status(self, value):
        """Validate device status"""
        valid_statuses = ['active', 'inactive', 'blocked']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value
    
    def validate_mac_id(self, value):
        """Validate MAC ID format"""
        cleaned = value.replace(':', '').replace('-', '').replace('.', '')
        if not cleaned.isalnum() or len(cleaned) != 12:
            raise serializers.ValidationError("Invalid MAC address format")
        return value.upper()


class LocationSerializer(serializers.Serializer):
    """
    Nested serializer for location data.
    """
    latitude = serializers.FloatField(min_value=-90.0, max_value=90.0)
    longitude = serializers.FloatField(min_value=-180.0, max_value=180.0)
    address = serializers.CharField(max_length=500, required=False, allow_blank=True)


class PotholeSerializer(serializers.ModelSerializer):
    """
    Serializer for Pothole model.
    """
    deviceId = serializers.PrimaryKeyRelatedField(source='device', queryset=IOTDevice.objects.all())
    userId = serializers.PrimaryKeyRelatedField(source='user', queryset=User.objects.all())
    detectedAt = serializers.DateTimeField(source='detected_at', read_only=True)
    # image field will automatically be handled by ImageField in ModelSerializer
    
    # Location as nested object for better API structure
    location = LocationSerializer(write_only=True, required=False)
    
    class Meta:
        model = Pothole
        fields = [
            'id', 'deviceId', 'userId', 'depth', 'severity',
            'image', 'detectedAt', 'status',
            'latitude', 'longitude', 'address', 'location'
        ]
        read_only_fields = ['id', 'detectedAt']
    
    def validate_severity(self, value):
        """Validate severity level"""
        valid_severities = ['low', 'medium', 'high']
        if value not in valid_severities:
            raise serializers.ValidationError(
                f"Severity must be one of: {', '.join(valid_severities)}"
            )
        return value
    
    def validate_status(self, value):
        """Validate pothole status"""
        valid_statuses = ['unresolved', 'fixed', 'ignored']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value
    
    def validate_depth(self, value):
        """Validate depth is positive"""
        if value < 0:
            raise serializers.ValidationError("Depth must be a positive number")
        return value
    
    def create(self, validated_data):
        """Handle location nested object during creation"""
        location_data = validated_data.pop('location', None)
        if location_data:
            validated_data['latitude'] = location_data['latitude']
            validated_data['longitude'] = location_data['longitude']
            validated_data['address'] = location_data.get('address', '')
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Handle location nested object during update"""
        location_data = validated_data.pop('location', None)
        if location_data:
            validated_data['latitude'] = location_data['latitude']
            validated_data['longitude'] = location_data['longitude']
            validated_data['address'] = location_data.get('address', '')
        return super().update(instance, validated_data)
    
    def to_representation(self, instance):
        """Include location as nested object in response"""
        representation = super().to_representation(instance)
        
        # Add location object to response
        representation['location'] = {
            'latitude': representation.get('latitude'),
            'longitude': representation.get('longitude'),
            'address': representation.get('address', '')
        }
        
        return representation


class AlertSerializer(serializers.ModelSerializer):
    """
    Serializer for Alert model.
    """
    alertText = serializers.CharField(source='alert_text')
    alertType = serializers.CharField(source='alert_type')
    alertTime = serializers.DateTimeField(source='alert_time', read_only=True)
    pothole = PotholeSerializer(read_only=True)
    potholeId = serializers.PrimaryKeyRelatedField(source='pothole', queryset=Pothole.objects.all(), write_only=True)
    userId = serializers.PrimaryKeyRelatedField(source='user', queryset=User.objects.all())
    
    class Meta:
        model = Alert
        fields = [
            'id', 'alertText', 'alertType', 'alertTime',
            'distance', 'pothole', 'potholeId', 'userId'
        ]
        read_only_fields = ['id', 'alertTime']
    
    def validate_alert_type(self, value):
        """Validate alert type"""
        valid_types = ['warning', 'info', 'emergency']
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Alert type must be one of: {', '.join(valid_types)}"
            )
        return value
    
    def validate_distance(self, value):
        """Validate distance is positive"""
        if value < 0:
            raise serializers.ValidationError("Distance must be a positive number")
        return value
        return value


class QuickPotholeUploadSerializer(serializers.Serializer):
    """
    Serializer for quick pothole upload with photo and coordinates.
    """
    latitude = serializers.FloatField(min_value=-90.0, max_value=90.0, required=False)
    longitude = serializers.FloatField(min_value=-180.0, max_value=180.0, required=False)
    photo = serializers.ImageField(required=True)
    deviceId = serializers.PrimaryKeyRelatedField(queryset=IOTDevice.objects.all(), required=False)
    userId = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    depth = serializers.FloatField(min_value=0.0, required=False, default=0.0)
    severity = serializers.ChoiceField(choices=['low', 'medium', 'high'], required=False, default='low')

    def validate_photo(self, value):
        """Validate image file"""
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image file size must be less than 5MB")
        
        # Check file type
        valid_types = ['image/jpeg', 'image/jpg', 'image/png']
        if value.content_type not in valid_types:
            raise serializers.ValidationError("Only JPEG and PNG images are allowed")
        
        return value


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})
