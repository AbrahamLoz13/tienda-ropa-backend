from django.contrib import admin

from .models import Categoria, Favorito, ImagenPrenda, Prenda


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