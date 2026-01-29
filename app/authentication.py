from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from .models import User

class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication to use app.models.User instead of the default Django User.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_model = User

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token[self.user_id_claim]
        except KeyError:
            raise InvalidToken(('Token contained no recognizable user identification'))

        try:
            user = self.user_model.objects.get(**{self.user_id_field: user_id})
        except self.user_model.DoesNotExist:
            raise AuthenticationFailed(('User not found'), code='user_not_found')

        if not user_id:
             raise AuthenticationFailed(('User not found'), code='user_not_found')
             
        # Optional: check if user is active if you had an is_active field
        # if not user.is_active:
        #    raise AuthenticationFailed(('User is inactive'), code='user_inactive')

        return user
