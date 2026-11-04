import django_filters

from .models import Prenda


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class PrendaFilter(django_filters.FilterSet):
    precio_min = django_filters.NumberFilter(field_name="precio", lookup_expr="gte")
    precio_max = django_filters.NumberFilter(field_name="precio", lookup_expr="lte")
    talla = CharInFilter(field_name="talla", lookup_expr="in")
    color = django_filters.CharFilter(field_name="color", lookup_expr="iexact")

    class Meta:
        model = Prenda
        fields = ["categoria", "marca"]