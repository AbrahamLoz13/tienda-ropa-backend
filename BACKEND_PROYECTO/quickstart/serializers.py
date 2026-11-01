from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Categoria, ImagenPrenda, Prenda


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion"]


class ImagenPrendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenPrenda
        fields = ["id", "imagen", "descripcion"]


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

    def validate_nombre(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("El nombre debe tener al menos 2 caracteres.")
        return value

    def validate_imagen(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("La imagen no debe pesar más de 5 MB.")
        return value

    def validate(self, data):
        nombre = data.get("nombre", getattr(self.instance, "nombre", None))
        talla = data.get("talla", getattr(self.instance, "talla", "M"))
        color = data.get("color", getattr(self.instance, "color", None))
        repetida = Prenda.objects.filter(
            nombre__iexact=nombre, talla=talla, color__iexact=color
        )
        if self.instance:
            repetida = repetida.exclude(pk=self.instance.pk)
        if repetida.exists():
            raise serializers.ValidationError(
                "Ya existe una prenda con ese nombre, talla y color."
            )
        return data


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