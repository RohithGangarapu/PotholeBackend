"""
Django REST Framework ViewSets for Pothole Detection System

These ViewSets provide API endpoints for managing users, devices, potholes, and alerts
using standard Django models and PostgreSQL.
"""

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from datetime import datetime

from .models import User, IOTDevice, Pothole, Alert
from .serializers import (
    UserSerializer, IOTDeviceSerializer, PotholeSerializer, 
    AlertSerializer, QuickPotholeUploadSerializer, LoginSerializer
)
from .utils.detector import PotholeDetector
from .utils.video_processor import start_video_stream, stop_video_stream, get_stream_status, get_all_streams_status
from .utils.frame_queue import add_frame_processing_task, get_task_status, get_queue_stats

# Initialize detector
detector = PotholeDetector()


@extend_schema_view(
    list=extend_schema(description="List all users", tags=['Users']),
    create=extend_schema(description="Create a new user", tags=['Users']),
    retrieve=extend_schema(description="Get user details by ID", tags=['Users']),
    update=extend_schema(description="Update user (full)", tags=['Users']),
    partial_update=extend_schema(description="Update user (partial)", tags=['Users']),
    destroy=extend_schema(description="Delete user", tags=['Users']),
)
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.
    Provides CRUD operations for user management.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer


@extend_schema_view(
    list=extend_schema(description="List all IOT devices", tags=['IOT Devices']),
    create=extend_schema(description="Register a new IOT device", tags=['IOT Devices']),
    retrieve=extend_schema(description="Get device details by ID", tags=['IOT Devices']),
    update=extend_schema(description="Update device (full)", tags=['IOT Devices']),
    partial_update=extend_schema(description="Update device (partial)", tags=['IOT Devices']),
    destroy=extend_schema(description="Delete device", tags=['IOT Devices']),
)
class IOTDeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing IOT devices.
    Provides CRUD operations and device-specific actions.
    """
    queryset = IOTDevice.objects.all()
    serializer_class = IOTDeviceSerializer
    
    @extend_schema(
        description="Update device status",
        tags=['IOT Devices'],
        request={'application/json': {'type': 'object', 'properties': {'status': {'type': 'string', 'enum': ['active', 'inactive', 'blocked']}}}},
    )
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update device status"""
        device = self.get_object()
        new_status = request.data.get('status')
        if not new_status:
            return Response({
                "status": "error",
                "message": "Status is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status not in ['active', 'inactive', 'blocked']:
            return Response({
                "status": "error",
                "message": "Invalid status. Must be: active, inactive, or blocked"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        device.status = new_status
        device.save()
        serializer = self.get_serializer(device)
        return Response({
            "status": "success",
            "data": serializer.data
        })
    
    @extend_schema(
        description="Get all devices for a specific user",
        tags=['IOT Devices'],
        parameters=[OpenApiParameter(name='user_id', location=OpenApiParameter.PATH, type=int)],
    )
    @action(detail=False, methods=['get'], url_path='by-user/(?P<user_id>[^/.]+)')
    def by_user(self, request, user_id=None):
        """Get devices by user ID"""
        devices = self.queryset.filter(owner_id=user_id)
        serializer = self.get_serializer(devices, many=True)
        return Response({
            "status": "success",
            "data": serializer.data
        })


@extend_schema_view(
    list=extend_schema(description="List all potholes", tags=['Potholes']),
    create=extend_schema(description="Create a new pothole record", tags=['Potholes']),
    retrieve=extend_schema(description="Get pothole details by ID", tags=['Potholes']),
    update=extend_schema(description="Update pothole (full)", tags=['Potholes']),
    partial_update=extend_schema(description="Update pothole (partial)", tags=['Potholes']),
    destroy=extend_schema(description="Delete pothole", tags=['Potholes']),
)
class PotholeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing potholes.
    Provides CRUD operations, filtering, and image upload.
    """
    queryset = Pothole.objects.all()
    serializer_class = PotholeSerializer
    
    @extend_schema(
        description="Filter potholes by severity level",
        tags=['Potholes'],
        parameters=[OpenApiParameter(name='severity', location=OpenApiParameter.PATH, type=str, enum=['low', 'medium', 'high'])],
    )
    @action(detail=False, methods=['get'], url_path='by-severity/(?P<severity>[^/.]+)')
    def by_severity(self, request, severity=None):
        """Get potholes by severity"""
        if severity not in ['low', 'medium', 'high']:
            return Response({
                "status": "error",
                "message": "Invalid severity. Must be: low, medium, or high"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        potholes = self.queryset.filter(severity=severity)
        serializer = self.get_serializer(potholes, many=True)
        return Response({
            "status": "success",
            "data": serializer.data
        })
    
    @extend_schema(
        description="Filter potholes by status",
        tags=['Potholes'],
        parameters=[OpenApiParameter(name='status', location=OpenApiParameter.PATH, type=str, enum=['unresolved', 'fixed', 'ignored'])],
    )
    @action(detail=False, methods=['get'], url_path='by-status/(?P<status_param>[^/.]+)')
    def by_status(self, request, status_param=None):
        """Get potholes by status"""
        if status_param not in ['unresolved', 'fixed', 'ignored']:
            return Response({
                "status": "error",
                "message": "Invalid status. Must be: unresolved, fixed, or ignored"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        potholes = self.queryset.filter(status=status_param)
        serializer = self.get_serializer(potholes, many=True)
        return Response({
            "status": "success",
            "data": serializer.data
        })
    
    @extend_schema(
        description="Get all potholes detected by a specific device",
        tags=['Potholes'],
        parameters=[OpenApiParameter(name='device_id', location=OpenApiParameter.PATH, type=int)],
    )
    @action(detail=False, methods=['get'], url_path='by-device/(?P<device_id>[^/.]+)')
    def by_device(self, request, device_id=None):
        """Get potholes by device ID"""
        potholes = self.queryset.filter(device_id=device_id)
        serializer = self.get_serializer(potholes, many=True)
        return Response({
            "status": "success",
            "data": serializer.data
        })
    


    @extend_schema(
        description="Upload image for pothole detection (contains optional latitude, longitude as query params and photo as payload).",
        tags=['Potholes'],
        parameters=[
            OpenApiParameter(name='latitude', location=OpenApiParameter.QUERY, type=float, description='Latitude of the pothole'),
            OpenApiParameter(name='longitude', location=OpenApiParameter.QUERY, type=float, description='Longitude of the pothole'),
        ],
        request={'multipart/form-data': QuickPotholeUploadSerializer},
    )
    @action(detail=False, methods=['post'], url_path='upload-image')
    def upload_image(self, request):
        """Upload image and directly create Pothole records if detected"""
        data = request.data.copy()
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        
        if latitude: data['latitude'] = latitude
        if longitude: data['longitude'] = longitude
            
        serializer = QuickPotholeUploadSerializer(data=data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            photo = validated_data['photo']
            
            try:
                # --- YOLO Pothole Detection Logic ---
                # Save photo temporarily for detector to read
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile
                import os
                import uuid

                temp_filename = f"temp_{uuid.uuid4()}.jpg"
                temp_path = default_storage.save(f"tmp/{temp_filename}", ContentFile(photo.read()))
                full_temp_path = default_storage.path(temp_path)
                
                # Run detection
                try:
                    detections, annotated_image_bytes = detector.detect(full_temp_path)
                finally:
                    # Always clean up temp file
                    if os.path.exists(full_temp_path):
                        os.remove(full_temp_path)
                
                pothole_records = []
                if detections:
                    # If userId is missing but deviceId is present, infer user from device owner
                    device_obj = validated_data.get('deviceId')
                    user_obj = validated_data.get('userId')
                    if user_obj is None and device_obj is not None:
                        try:
                            user_obj = device_obj.owner
                        except Exception:
                            user_obj = None

                    # If we still don't have required FKs, don't attempt DB writes (avoid 500)
                    if device_obj is None or user_obj is None:
                        return Response({
                            "status": "success",
                            "message": (
                                f"Detection complete. {len(detections)} pothole(s) found, but not recorded "
                                "because deviceId/userId is missing."
                            ),
                            "detection_count": len(detections),
                            "potholes": []
                        }, status=status.HTTP_200_OK)

                    # Store detections
                    for det in detections:
                        # Prepare the annotated image for saving
                        pothole_image = photo
                        if annotated_image_bytes:
                            pothole_image = ContentFile(annotated_image_bytes, name=photo.name)
                        
                        pothole = Pothole.objects.create(
                            device=device_obj,
                            user=user_obj,
                            depth=det['depth'],
                            severity=det['severity'],
                            image=pothole_image, # Store the annotated image
                            latitude=validated_data.get('latitude', 0.0),
                            longitude=validated_data.get('longitude', 0.0),
                            status='unresolved'
                        )
                        pothole_records.append(PotholeSerializer(pothole).data)
                    
                    return Response({
                        "status": "success",
                        "message": f"Detection complete. {len(detections)} pothole(s) found and recorded.",
                        "detection_count": len(detections),
                        "potholes": pothole_records
                    }, status=status.HTTP_201_CREATED)
                
                return Response({
                    "status": "success",
                    "message": "Detection complete. No potholes found. No record created.",
                    "detection_count": 0,
                    "potholes": []
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "status": "error",
                    "message": f"Detection process failed: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "status": "error",
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(description="List all alerts", tags=['Alerts']),
    create=extend_schema(description="Create a new alert", tags=['Alerts']),
    retrieve=extend_schema(description="Get alert details by ID", tags=['Alerts']),
    update=extend_schema(description="Update alert (full)", tags=['Alerts']),
    partial_update=extend_schema(description="Update alert (partial)", tags=['Alerts']),
    destroy=extend_schema(description="Delete alert", tags=['Alerts']),
)
class AlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing alerts.
    Provides CRUD operations and filtering by user, pothole, and type.
    """
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    
    @extend_schema(
        description="Get all alerts for a specific user",
        tags=['Alerts'],
        parameters=[OpenApiParameter(name='user_id', location=OpenApiParameter.PATH, type=int)],
    )
    @action(detail=False, methods=['get'], url_path='by-user/(?P<user_id>[^/.]+)')
    def by_user(self, request, user_id=None):
        """Get alerts by user ID"""
        alerts = self.queryset.filter(user_id=user_id)
        serializer = self.get_serializer(alerts, many=True)
        return Response({
            "status": "success",
            "data": serializer.data
        })
    
    @extend_schema(
        description="Get all alerts for a specific pothole",
        tags=['Alerts'],
        parameters=[OpenApiParameter(name='pothole_id', location=OpenApiParameter.PATH, type=int)],
    )
    @action(detail=False, methods=['get'], url_path='by-pothole/(?P<pothole_id>[^/.]+)')
    def by_pothole(self, request, pothole_id=None):
        """Get alerts by pothole ID"""
        alerts = self.queryset.filter(pothole_id=pothole_id)
        serializer = self.get_serializer(alerts, many=True)
        return Response({
            "status": "success",
            "data": serializer.data
        })
    
    @extend_schema(
        description="Filter alerts by type",
        tags=['Alerts'],
        parameters=[OpenApiParameter(name='type', location=OpenApiParameter.PATH, type=str, enum=['warning', 'info', 'emergency'])],
    )
    @action(detail=False, methods=['get'], url_path='by-type/(?P<type_param>[^/.]+)')
    def by_type(self, request, type_param=None):
        """Get alerts by type"""
        if type_param not in ['warning', 'info', 'emergency']:
            return Response({
                "status": "error",
                "message": "Invalid type. Must be: warning, info, or emergency"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        alerts = self.queryset.filter(alert_type=type_param)
        serializer = self.get_serializer(alerts, many=True)
        return Response({
            "status": "success",
            "data": serializer.data
        })

class LoginView(APIView):
    """
    API View for user login.
    """
    @extend_schema(
        description="Authenticate user with email and password",
        tags=['Authentication'],
        request=LoginSerializer,
        responses={
            200: {"type": "object", "properties": {"status": {"type": "string"}, "message": {"type": "string"}, "user": {"$ref": "#/components/schemas/User"}}},
            401: {"type": "object", "properties": {"status": {"type": "string"}, "message": {"type": "string"}}},
            404: {"type": "object", "properties": {"status": {"type": "string"}, "message": {"type": "string"}}},
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({
                    "status": "error",
                    "message": "User with this email does not exist"
                }, status=status.HTTP_404_NOT_FOUND)
            
            if check_password(password, user.password):
                user_serializer = UserSerializer(user)
                return Response({
                    "status": "success",
                    "message": "Login successful",
                    "user": user_serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "error",
                    "message": "Invalid password"
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
            "status": "error",
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class VideoStreamView(APIView):
    """
    API View for managing video streaming and frame capture
    """
    
    @extend_schema(
        description="Start video streaming from a URL",
        tags=['Video Streaming'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'stream_id': {'type': 'string', 'description': 'Unique identifier for the stream'},
                    'video_url': {'type': 'string', 'description': 'RTSP or HTTP video stream URL'},
                    'device_id': {'type': 'integer', 'description': 'Optional device ID for tracking'},
                    'frame_interval': {'type': 'integer', 'default': 30, 'description': 'Seconds between frame captures'}
                },
                'required': ['stream_id', 'video_url']
            }
        },
        responses={
            200: {'type': 'object', 'properties': {'status': {'type': 'string'}, 'message': {'type': 'string'}, 'stream_id': {'type': 'string'}}},
            400: {'type': 'object', 'properties': {'status': {'type': 'string'}, 'message': {'type': 'string'}}},
        }
    )
    def post(self, request):
        """Start video streaming"""
        stream_id = request.data.get('stream_id')
        video_url = request.data.get('video_url')
        device_id = request.data.get('device_id')
        frame_interval = request.data.get('frame_interval', 30)
        
        if not stream_id or not video_url:
            return Response({
                "status": "error",
                "message": "stream_id and video_url are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate frame_interval
        if not isinstance(frame_interval, int) or frame_interval < 1:
            return Response({
                "status": "error",
                "message": "frame_interval must be a positive integer"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            detection_api_url = request.build_absolute_uri('/api/v1/potholes/upload-image/')
            success = start_video_stream(stream_id, video_url, detection_api_url, frame_interval, device_id)
            if success:
                return Response({
                    "status": "success",
                    "message": f"Video streaming started for stream {stream_id}",
                    "stream_id": stream_id
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "error",
                    "message": f"Stream {stream_id} is already running or failed to start"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Error starting video stream: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        description="Stop video streaming",
        tags=['Video Streaming'],
        parameters=[OpenApiParameter(name='stream_id', location=OpenApiParameter.PATH, type=str, description='Stream ID to stop')],
        responses={
            200: {'type': 'object', 'properties': {'status': {'type': 'string'}, 'message': {'type': 'string'}}},
            404: {'type': 'object', 'properties': {'status': {'type': 'string'}, 'message': {'type': 'string'}}},
        }
    )
    def delete(self, request, stream_id=None):
        """Stop video streaming"""
        if not stream_id:
            return Response({
                "status": "error",
                "message": "stream_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            success = stop_video_stream(stream_id)
            if success:
                return Response({
                    "status": "success",
                    "message": f"Video streaming stopped for stream {stream_id}"
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "error",
                    "message": f"Stream {stream_id} is not active"
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Error stopping video stream: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VideoStreamStatusView(APIView):
    """
    API View for getting video streaming status
    """
    
    @extend_schema(
        description="Get status of all video streams",
        tags=['Video Streaming']
    )
    def get(self, request):
        """Get status of all streams or specific stream"""
        stream_id = request.query_params.get('stream_id')
        
        try:
            if stream_id:
                stream_status = get_stream_status(stream_id)
                if stream_status:
                    return Response({
                        "status": "success",
                        "data": stream_status
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "status": "error",
                        "message": f"Stream {stream_id} not found"
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                all_status = get_all_streams_status()
                return Response({
                    "status": "success",
                    "data": all_status
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Error getting stream status: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FrameProcessingView(APIView):
    """
    API View for frame processing queue management
    """
    
    @extend_schema(
        description="Get frame processing queue statistics",
        tags=['Frame Processing'],
        responses={
            200: {'type': 'object', 'properties': {
                'status': {'type': 'string'},
                'data': {'type': 'object'}
            }}
        }
    )
    def get(self, request, task_id=None):
        """Get queue statistics or task status"""
        if task_id:
            # Get specific task status
            try:
                task_status = get_task_status(task_id)
                if task_status:
                    return Response({
                        "status": "success",
                        "data": task_status
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "status": "error",
                        "message": f"Task {task_id} not found"
                    }, status=status.HTTP_404_NOT_FOUND)
                        
            except Exception as e:
                return Response({
                    "status": "error",
                    "message": f"Error getting task status: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Get queue statistics
            try:
                queue_stats = get_queue_stats()
                return Response({
                    "status": "success",
                    "data": queue_stats
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "status": "error",
                    "message": f"Error getting queue stats: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
