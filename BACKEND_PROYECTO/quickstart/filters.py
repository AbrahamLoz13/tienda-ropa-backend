import django_filters
from django.db.models import Q
from rest_framework.filters import SearchFilter

from .models import PUBLICOS, Prenda


class BusquedaLiteral(SearchFilter):
    """Busca el texto tal cual lo escribe el usuario.

    El SearchFilter normal trata las comillas como delimitadores de frase:
    una comilla suelta (') se vuelve una frase vacía y la búsqueda devuelve
    todas las prendas. Aquí cada palabra separada por espacios se busca
    literalmente, comillas incluidas (por ejemplo "Levi's").
    """

    def get_search_terms(self, request):
        texto = request.query_params.get(self.search_param, "")
        texto = texto.replace("\x00", "")  # caracteres nulos, igual que DRF
        return texto.split()


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class PrendaFilter(django_filters.FilterSet):
    precio_min = django_filters.NumberFilter(field_name="precio", lookup_expr="gte")
    precio_max = django_filters.NumberFilter(field_name="precio", lookup_expr="lte")
    # Acepta "M,L" o, para no confundir "12 años" con "12 MX", "ropa:12,calzado:26".
    talla = CharInFilter(method="filtrar_talla")
    color = CharInFilter(field_name="color", lookup_expr="in")
    publico = django_filters.ChoiceFilter(choices=PUBLICOS)

    class Meta:
        model = Prenda
        fields = ["categoria", "marca"]

    def filtrar_talla(self, queryset, name, valores):
        condicion = Q()
        for valor in valores:
            valor = valor.strip()
            if not valor:
                continue
            if ":" in valor:
                tipo, talla = valor.split(":", 1)
                condicion |= Q(categoria__tipo_talla=tipo, talla=talla)
            else:
                condicion |= Q(talla=valor)
        return queryset.filter(condicion) if condicion else queryset