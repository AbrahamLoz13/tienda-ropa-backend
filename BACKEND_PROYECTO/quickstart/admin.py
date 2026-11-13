from django.contrib import admin

from .models import (
    CarritoItem,
    Categoria,
    Favorito,
    ImagenPrenda,
    Pedido,
    PedidoItem,
    Prenda,
)


class ImagenPrendaInline(admin.TabularInline):
    model = ImagenPrenda
    extra = 1


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "descripcion"]
    search_fields = ["nombre"]


@admin.register(Prenda)
class PrendaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "categoria", "talla", "color", "precio", "stock", "creado"]
    list_filter = ["categoria", "talla", "color"]
    search_fields = ["nombre", "marca", "color"]
    list_editable = ["precio", "stock"]
    inlines = [ImagenPrendaInline]


@admin.register(ImagenPrenda)
class ImagenPrendaAdmin(admin.ModelAdmin):
    list_display = ["prenda", "descripcion"]


@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ["user", "prenda", "creado"]
    list_filter = ["user"]


@admin.register(CarritoItem)
class CarritoItemAdmin(admin.ModelAdmin):
    list_display = ["user", "prenda", "cantidad", "creado"]
    list_filter = ["user"]


class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 0
    can_delete = False
    readonly_fields = [
        "prenda",
        "nombre",
        "talla",
        "color",
        "precio_unitario",
        "cantidad",
    ]


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "total", "estado", "creado"]
    list_filter = ["estado", "user"]
    inlines = [PedidoItemInline]