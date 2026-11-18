from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import (
    PUBLICOS,
    TIPOS_TALLA,
    UNITALLA,
    CarritoItem,
    Categoria,
    ImagenPrenda,
    Pedido,
    PedidoItem,
    Prenda,
    tallas_validas,
)


def _rango(tallas):
    """["22", ..., "31"] -> "22 a 31"; ["XS", ..., "XXL"] -> "XS, S, M, L, XL, XXL"."""
    if all(t.isdigit() for t in tallas) and len(tallas) > 3:
        return f"{tallas[0]} a {tallas[-1]}"
    return ", ".join(tallas)


class CategoriaSerializer(serializers.ModelSerializer):
    tipo_talla = serializers.ChoiceField(
        choices=TIPOS_TALLA,
        required=False,
        error_messages={"invalid_choice": "Elige Ropa, Calzado o Unitalla."},
    )

    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion", "imagen", "tipo_talla"]


class ImagenPrendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenPrenda
        fields = ["id", "imagen", "descripcion"]


class PrendaSerializer(serializers.ModelSerializer):
    imagenes = ImagenPrendaSerializer(many=True, read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    color_nombre = serializers.CharField(source="get_color_display", read_only=True)
    # Tipo de talla de la categoría y cómo se muestra la talla ("26 MX", "8 años").
    categoria_tipo_talla = serializers.CharField(source="categoria.tipo_talla", read_only=True)
    talla_nombre = serializers.CharField(read_only=True)
    publico = serializers.ChoiceField(
        choices=PUBLICOS,
        required=False,
        error_messages={"invalid_choice": "Elige Adulto o Infantil."},
    )
    talla = serializers.CharField(
        max_length=3,
        required=False,
        error_messages={"max_length": "Elige una talla de la lista."},
    )
    es_favorito = serializers.SerializerMethodField()
    stock = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=10000,
        error_messages={
            "invalid": "Ingresa un número entero.",
            "min_value": "El stock no puede ser negativo.",
            "max_value": "El stock no puede ser mayor a 10,000 piezas.",
            "max_string_length": "El stock no puede ser mayor a 10,000 piezas.",
        },
    )

    class Meta:
        model = Prenda
        fields = [
            "id", "nombre", "descripcion", "precio", "talla", "talla_nombre",
            "publico", "color", "color_nombre", "marca", "stock", "imagen",
            "categoria", "categoria_nombre", "categoria_tipo_talla",
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
        categoria = data.get("categoria", getattr(self.instance, "categoria", None))
        publico = data.get("publico", getattr(self.instance, "publico", "adulto"))
        talla = data.get("talla", getattr(self.instance, "talla", "M"))
        color = data.get("color", getattr(self.instance, "color", None))

        # La talla se revisa cuando se crea la prenda o cuando cambia la talla,
        # la categoría o el público. Si solo cambia, por ejemplo, el stock,
        # una prenda vieja con talla fuera de lista se puede seguir guardando.
        cambia_talla = self.instance is None or any(
            campo in data for campo in ("talla", "categoria", "publico")
        )
        if categoria is not None and cambia_talla:
            tipo = categoria.tipo_talla
            if tipo == "unitalla":
                talla = UNITALLA
                data["talla"] = UNITALLA
            else:
                validas = tallas_validas(tipo, publico)
                talla = str(talla).strip().upper()
                if talla not in validas:
                    tipo_txt = dict(TIPOS_TALLA)[tipo].lower()
                    publico_txt = dict(PUBLICOS)[publico].lower()
                    unidad = " (MX)" if tipo == "calzado" else " (años)" if publico == "infantil" else ""
                    raise serializers.ValidationError(
                        {"talla": f"Elige una talla de {tipo_txt} {publico_txt}{unidad}: {_rango(validas)}."}
                    )
                data["talla"] = talla

        repetida = Prenda.objects.filter(
            nombre__iexact=nombre, talla=talla, color__iexact=color, publico=publico
        )
        if self.instance:
            repetida = repetida.exclude(pk=self.instance.pk)
        if repetida.exists():
            raise serializers.ValidationError(
                "Ya existe una prenda con ese nombre, talla, color y público."
            )
        return data


class CarritoItemSerializer(serializers.ModelSerializer):
    cantidad = serializers.IntegerField(min_value=1, default=1)
    prenda_nombre = serializers.CharField(source="prenda.nombre", read_only=True)
    precio = serializers.DecimalField(
        source="prenda.precio", max_digits=8, decimal_places=2, read_only=True
    )
    talla = serializers.CharField(source="prenda.talla", read_only=True)
    talla_nombre = serializers.CharField(source="prenda.talla_nombre", read_only=True)
    publico = serializers.CharField(source="prenda.publico", read_only=True)
    color = serializers.CharField(source="prenda.get_color_display", read_only=True)
    stock = serializers.IntegerField(source="prenda.stock", read_only=True)
    imagen = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CarritoItem
        fields = [
            "id", "prenda", "prenda_nombre", "precio", "talla", "talla_nombre",
            "publico", "color", "stock", "imagen", "cantidad", "subtotal",
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
    # Foto de la prenda para el historial. Si la prenda ya se eliminó de la
    # tienda, llega null (el nombre, talla, color y precio se guardaron al comprar).
    imagen = serializers.SerializerMethodField()

    class Meta:
        model = PedidoItem
        fields = [
            "id", "prenda", "nombre", "talla", "color",
            "precio_unitario", "cantidad", "subtotal", "imagen",
        ]

    def get_subtotal(self, obj):
        return str(obj.precio_unitario * obj.cantidad)

    def get_imagen(self, obj):
        if not obj.prenda or not obj.prenda.imagen:
            return None
        request = self.context.get("request")
        url = obj.prenda.imagen.url
        return request.build_absolute_uri(url) if request else url


class PedidoSerializer(serializers.ModelSerializer):
    items = PedidoItemSerializer(many=True, read_only=True)
    # Total de piezas del pedido (suma de cantidades).
    piezas = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = ["id", "total", "estado", "creado", "piezas", "items"]

    def get_piezas(self, obj):
        return sum(item.cantidad for item in obj.items.all())


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        # Solo cambia el largo permitido; se conservan las reglas de Django
        # (caracteres válidos y usuario repetido).
        extra_kwargs = {
            "username": {
                "min_length": 3,
                "max_length": 20,
                "error_messages": {
                    "min_length": "El usuario debe tener al menos 3 caracteres.",
                    "max_length": "El usuario no puede tener más de 20 caracteres.",
                },
            },
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este correo ya está registrado.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)