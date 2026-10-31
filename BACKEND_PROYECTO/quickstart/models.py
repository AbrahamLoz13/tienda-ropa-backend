from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

# Create your models here.
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    
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
    
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(
        max_digits=8,
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))])
    talla = models.CharField(max_length=3, choices=TALLAS, default="M")
    color = models.CharField(max_length=50)
    marca = models.CharField(max_length=100, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    imagen = models.ImageField(upload_to='prendas/', blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='prendas')
    creado = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-creado"]
    def __str__(self):
        return f"{self.nombre} ({self.talla})"
    
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