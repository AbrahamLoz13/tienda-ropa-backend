from django.contrib import admin

from .models import Categoria, Prenda, ImagenPrenda,Favorito

# Register your models here.
admin.site.register(Categoria)
admin.site.register(Prenda)
admin.site.register(ImagenPrenda)
admin.site.register(Favorito)