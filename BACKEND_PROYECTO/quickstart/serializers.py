from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import (
    CarritoItem,
    Categoria,
    ImagenPrenda,
    Pedido,
    PedidoItem,
    Prenda,
)


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion", "imagen"]


class ImagenPrendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenPrenda
        fields = ["id", "imagen", "descripcion"]


class PrendaSerializer(serializers.ModelSerializer):
    imagenes = ImagenPrendaSerializer(many=True, read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    color_nombre = serializers.CharField(source="get_color_display", read_only=True)
    es_favorito = serializers.SerializerMethodField()

    class Meta:
        model = Prenda
        fields = [
            "id", "nombre", "descripcion", "precio", "talla", "color", "color_nombre",
            "marca", "stock", "imagen", "categoria", "categoria_nombre",
            "imagenes", "es_favorito", "creado",
        ]

    def get_es_favorito(self, obj):
        return obj.id in self.context.get("favoritos_ids", set())

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


class CarritoItemSerializer(serializers.ModelSerializer):
    cantidad = serializers.IntegerField(min_value=1, default=1)
    prenda_nombre = serializers.CharField(source="prenda.nombre", read_only=True)
    precio = serializers.DecimalField(
        source="prenda.precio", max_digits=8, decimal_places=2, read_only=True
    )
    talla = serializers.CharField(source="prenda.talla", read_only=True)
    color = serializers.CharField(source="prenda.get_color_display", read_only=True)
    stock = serializers.IntegerField(source="prenda.stock", read_only=True)
    imagen = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CarritoItem
        fields = [
            "id", "prenda", "prenda_nombre", "precio", "talla", "color",
            "stock", "imagen", "cantidad", "subtotal",
        ]

    def get_imagen(self, obj):
        img = obj.prenda.imagen
        if not img:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(img.url) if request else img.url

    def get_subtotal(self, obj):
        return str(obj.prenda.precio * obj.cantidad)


class PedidoItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = PedidoItem
        fields = [
            "id", "prenda", "nombre", "talla", "color",
            "precio_unitario", "cantidad", "subtotal",
        ]

    def get_subtotal(self, obj):
        return str(obj.precio_unitario * obj.cantidad)


class PedidoSerializer(serializers.ModelSerializer):
    items = PedidoItemSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = ["id", "total", "estado", "creado", "items"]


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