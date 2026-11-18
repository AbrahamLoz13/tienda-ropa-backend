from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

# (valor guardado, nombre que se muestra, código de color para dibujarlo en la app)
COLORES = [
    ("negro", "Negro", "#1a1a1a"),
    ("blanco", "Blanco", "#ffffff"),
    ("gris", "Gris", "#9e9e9e"),
    ("azul", "Azul", "#1e6fd9"),
    ("rojo", "Rojo", "#d32f2f"),
    ("verde", "Verde", "#2e7d32"),
    ("amarillo", "Amarillo", "#fbc02d"),
    ("naranja", "Naranja", "#ef6c00"),
    ("rosa", "Rosa", "#ec7fa9"),
    ("morado", "Morado", "#7b1fa2"),
    ("cafe", "Café", "#6d4c41"),
    ("beige", "Beige", "#d7c4a3"),
    ("multicolor", "Multicolor", "#888888"),
    ("otro", "Otro", "#bdbdbd"),
]


# --- Tallas ---
# Cada categoría dice qué tipo de talla usa y cada prenda dice si es para
# adulto o infantil. Con esas dos cosas se sabe qué tallas son válidas.
TIPOS_TALLA = [
    ("ropa", "Ropa"),
    ("calzado", "Calzado"),
    ("unitalla", "Unitalla"),
]
PUBLICOS = [
    ("adulto", "Adulto"),
    ("infantil", "Infantil"),
]
UNITALLA = "U"
TALLAS_POR_TIPO = {
    "ropa": {
        "adulto": ["XS", "S", "M", "L", "XL", "XXL"],
        "infantil": ["2", "4", "6", "8", "10", "12", "14", "16"],  # años
    },
    "calzado": {
        "adulto": [str(n) for n in range(22, 32)],    # 22 a 31 MX
        "infantil": [str(n) for n in range(12, 22)],  # 12 a 21 MX
    },
    "unitalla": {
        "adulto": [UNITALLA],
        "infantil": [UNITALLA],
    },
}


def tallas_validas(tipo, publico):
    """Lista de tallas permitidas para un tipo de categoría y un público."""
    return TALLAS_POR_TIPO.get(tipo, {}).get(publico, [])


def nombre_talla(talla, tipo, publico):
    """Cómo se muestra la talla: "M", "26 MX", "8 años" o "Unitalla"."""
    if talla not in tallas_validas(tipo, publico):
        return talla  # talla antigua que todavía no se corrige: se muestra tal cual
    if tipo == "unitalla":
        return "Unitalla"
    if tipo == "calzado":
        return f"{talla} MX"
    if publico == "infantil":
        return f"{talla} años"
    return talla


# Create your models here.
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(upload_to="categorias/", blank=True, null=True)
    tipo_talla = models.CharField(max_length=10, choices=TIPOS_TALLA, default="ropa")
    class Meta:
        verbose_name_plural = "Categorías"
        ordering = ['nombre']
    def __str__(self):
        return self.nombre
    
class Prenda(models.Model):
    TALLAS = [
        ("XS","XS"),
        ("S","S"),
        ("M","M"),
        ("L","L"),
        ("XL","XL"),
        ("XXL","XXL"),
    ]
    MARCAS = [
        ("Nike", "Nike"),
        ("Adidas", "Adidas"),
        ("Puma", "Puma"),
        ("Reebok", "Reebok"),
        ("Under Armour", "Under Armour"),
        ("Vans", "Vans"),
        ("Converse", "Converse"),
        ("Levi's", "Levi's"),
        ("Zara", "Zara"),
        ("H&M", "H&M"),
        ("Tommy Hilfiger", "Tommy Hilfiger"),
        ("Lacoste", "Lacoste"),
        ("Otra", "Otra"),
    ]
    COLOR_CHOICES = [(valor, nombre) for valor, nombre, _ in COLORES]

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(
        max_digits=8,
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))])
    # La lista de tallas válidas depende de la categoría y del público
    # (ver TALLAS_POR_TIPO); la revisa el serializer.
    talla = models.CharField(max_length=3, default="M")
    publico = models.CharField(max_length=10, choices=PUBLICOS, default="adulto")
    color = models.CharField(max_length=50, choices=COLOR_CHOICES)
    marca = models.CharField(max_length=100, choices=MARCAS, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    imagen = models.ImageField(upload_to='prendas/', blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='prendas')
    creado = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-creado"]
    def __str__(self):
        return f"{self.nombre} ({self.talla_nombre})"

    @property
    def talla_nombre(self):
        return nombre_talla(self.talla, self.categoria.tipo_talla, self.publico)

    def clean(self):
        # Misma regla que la API, para el panel de administración de Django.
        if not self.categoria_id:
            return
        tipo = self.categoria.tipo_talla
        if tipo == "unitalla":
            self.talla = UNITALLA
        elif self.talla not in tallas_validas(tipo, self.publico):
            raise ValidationError(
                {"talla": "Válidas: " + ", ".join(tallas_validas(tipo, self.publico))}
            )


class ImagenPrenda(models.Model):
    prenda = models.ForeignKey(Prenda, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='prendas/galeria/')
    descripcion = models.CharField(max_length=150, blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Imágenes de prendas"
            
    def __str__(self):
        return f"Imagen de {self.prenda.nombre} ({self.prenda.talla})"

        
class Favorito (models.Model):
    user = models.ForeignKey(
    settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favoritos"
)
    prenda = models.ForeignKey(
    Prenda, on_delete=models.CASCADE, related_name="favoritos"
)
    creado = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
        models.UniqueConstraint(
            fields=["user", "prenda"], name="favorito_unico_por_usuario"
        )
    ]

    def __str__(self):
        return f"{self.user} ({self.prenda})"
    
class CarritoItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carrito"
    )
    prenda = models.ForeignKey(
        Prenda, on_delete=models.CASCADE, related_name="en_carritos"
    )
    cantidad = models.PositiveIntegerField(default=1)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Items del carrito"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "prenda"], name="carrito_item_unico_por_usuario"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.prenda} x{self.cantidad}"


class Pedido(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pedidos"
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, default="confirmado")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Pedido #{self.pk} de {self.user}"


class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    prenda = models.ForeignKey(
        Prenda, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # copia de los datos al momento de comprar
    nombre = models.CharField(max_length=150)
    # Se guarda ya con su nombre ("26 MX", "8 años") para que el historial
    # diga exactamente qué se compró.
    talla = models.CharField(max_length=20)
    color = models.CharField(max_length=50)
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    cantidad = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.nombre} x{self.cantidad}"