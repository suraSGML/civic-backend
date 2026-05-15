"""
Views for user account management.
"""
import secrets
from datetime import timedelta

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from core.permissions import IsAdminOrSuperAdmin, IsSuperAdmin
from .models import User, UserRole, PasswordResetToken, EmailVerificationToken
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    AdminUserSerializer,
    WorkerListSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Register a new citizen account."""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger('civic_system')
        logger.warning(f"Register request data: {request.data}")
        logger.warning(f"Request content type: {request.content_type}")
        logger.warning(f"Request method: {request.method}")
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.save()

        # Send verification email
        self._send_verification_email(user)

        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Registration successful. Please verify your email.',
            'user': UserProfileSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)

    def _send_verification_email(self, user):
        token = secrets.token_urlsafe(32)
        EmailVerificationToken.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        send_mail(
            subject='Verify your Civic System account',
            message=f'Hello {user.first_name},\n\nClick to verify: {verify_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )


class LoginView(APIView):
    """Login and receive JWT tokens."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        import logging
        logger = logging.getLogger('civic_system')
        
        logger.info("=== LOGIN START ===")
        
        try:
            logger.info("Step 1: Getting email and password")
            email = request.data.get('email')
            password = request.data.get('password')
            logger.info(f"Step 2: Email={email}, Password length={len(password) if password else 0}")
            
            if not email or not password:
                logger.info("Step 3: Missing credentials")
                return Response({'error': 'Email and password required'}, status=400)
            
            logger.info("Step 4: About to query database")
            # Try to get user
            user = User.objects.filter(email=email).first()
            logger.info(f"Step 5: Query complete, user={user}")
            
            if not user:
                logger.info("Step 6: User not found")
                return Response({'error': 'Invalid credentials'}, status=401)
            
            logger.info("Step 7: Checking password")
            if not user.check_password(password):
                logger.info("Step 8: Password invalid")
                return Response({'error': 'Invalid credentials'}, status=401)
            
            logger.info("Step 9: About to generate tokens")
            refresh = RefreshToken.for_user(user)
            logger.info("Step 10: Tokens generated")
            
            logger.info("Step 11: Returning response")
            return Response({
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': f"{user.first_name} {user.last_name}",
                    'role': user.role,
                    'city': user.city,
                    'region': user.region,
                    'is_verified': user.is_verified,
                },
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
            
        except Exception as e:
            logger.error(f"ERROR: {type(e).__name__}: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=500)


class LogoutView(APIView):
    """Blacklist the refresh token on logout."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully.'})
        except Exception:
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get and update the authenticated user's profile."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserProfileSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class ChangePasswordView(APIView):
    """Change authenticated user's password."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'message': 'Password changed successfully.'})


class VerifyEmailView(APIView):
    """Verify user email with token."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')
        try:
            verification = EmailVerificationToken.objects.get(token=token)
            if not verification.is_valid():
                return Response({'error': 'Token expired or already used.'}, status=400)
            verification.user.is_verified = True
            verification.user.save()
            verification.is_used = True
            verification.save()
            return Response({'message': 'Email verified successfully.'})
        except EmailVerificationToken.DoesNotExist:
            return Response({'error': 'Invalid token.'}, status=400)


class ForgotPasswordView(APIView):
    """Send password reset email."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            token = secrets.token_urlsafe(32)
            PasswordResetToken.objects.create(
                user=user,
                token=token,
                expires_at=timezone.now() + timedelta(hours=2),
            )
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
            send_mail(
                subject='Reset your Civic System password',
                message=f'Hello {user.first_name},\n\nReset your password: {reset_url}\n\nExpires in 2 hours.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        return Response({'message': 'If the email exists, a reset link has been sent.'})


class ResetPasswordView(APIView):
    """Reset password using token."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            if not reset_token.is_valid():
                return Response({'error': 'Token expired or already used.'}, status=400)
            reset_token.user.set_password(new_password)
            reset_token.user.save()
            reset_token.is_used = True
            reset_token.save()
            return Response({'message': 'Password reset successfully.'})
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid token.'}, status=400)


# Admin views
class AdminUserListView(generics.ListCreateAPIView):
    """Admin: list and create users."""
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    filterset_fields = ['role', 'is_active', 'is_verified', 'is_banned']
    search_fields = ['email', 'first_name', 'last_name', 'phone']

    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')

    def perform_create(self, serializer):
        user = serializer.save()
        if 'password' in self.request.data:
            user.set_password(self.request.data['password'])
            user.save()


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: manage individual users."""
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = User.objects.all()


class BanUserView(APIView):
    """Admin: ban or unban a user."""
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            action = request.data.get('action')  # 'ban' or 'unban'
            if action == 'ban':
                user.is_banned = True
                user.ban_reason = request.data.get('reason', '')
                user.save()
                return Response({'message': f'User {user.email} has been banned.'})
            elif action == 'unban':
                user.is_banned = False
                user.ban_reason = ''
                user.save()
                return Response({'message': f'User {user.email} has been unbanned.'})
            return Response({'error': 'Invalid action.'}, status=400)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=404)


class WorkerListView(generics.ListAPIView):
    """List available field workers for assignment."""
    serializer_class = WorkerListSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        return User.objects.filter(
            role=UserRole.FIELD_WORKER,
            is_active=True,
            is_banned=False,
        ).order_by('first_name')
