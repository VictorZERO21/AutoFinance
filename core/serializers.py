from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Usuario"""
    class Meta:
        model = Usuario
        fields = ('id', 'username', 'email', 'nombre_completo', 'dni', 'rol', 'is_staff')
        read_only_fields = ('id',)


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer para registro de nuevos usuarios"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        min_length=6
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        min_length=6
    )

    class Meta:
        model = Usuario
        fields = ('email', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden'
            })
        return attrs

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este correo ya está registrado')
        return value

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        email = validated_data['email']

        # Usar el email como username
        usuario = Usuario.objects.create_user(
            username=email,
            email=email,
            password=password,
            nombre_completo='',
            dni=None,
            rol='CLIENTE'
        )
        return usuario


class LoginSerializer(serializers.Serializer):
    """Serializer personalizado para login con email y contraseña"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError({'email': 'Email o contraseña incorrectos'})

        # Autenticar con username
        user = authenticate(username=usuario.username, password=password)

        if user is None:
            raise serializers.ValidationError({'password': 'Email o contraseña incorrectos'})

        data['user'] = user
        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personalizado que retorna tokens JWT y datos del usuario"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Agregar información personalizada del usuario
        token['email'] = user.email
        token['nombre_completo'] = user.nombre_completo
        token['rol'] = user.rol
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Agregar información del usuario en la respuesta
        usuario = self.user
        data['usuario'] = {
            'id': usuario.id,
            'username': usuario.username,
            'email': usuario.email,
            'nombre_completo': usuario.nombre_completo,
            'dni': usuario.dni,
            'rol': usuario.rol,
            'is_staff': usuario.is_staff,
        }
        return data


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer para refrescar token"""
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return value
