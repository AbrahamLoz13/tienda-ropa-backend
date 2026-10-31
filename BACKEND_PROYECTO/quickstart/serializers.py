from rest_framework import serializers
from .models import Categoria, ImagenPrenda, Prenda
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion"]
        
class ImagenPrendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenPrenda
        fields = ["id","imagen","descripcion"]

class PrendaSerializer(serializers.ModelSerializer):
    imagenes = ImagenPrendaSerializer(many=True, read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)

    class Meta:
        model = Prenda
        fields = [
            "id", "nombre", "descripcion", "precio", "talla", "color",
            "marca", "stock", "imagen", "categoria", "categoria_nombre",
            "imagenes", "creado",
        ]
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este correo ya está registrado.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)