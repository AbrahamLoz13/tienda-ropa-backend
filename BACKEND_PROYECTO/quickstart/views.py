from decimal import Decimal

from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import PrendaFilter
from .models import CarritoItem, Categoria, Favorito, Pedido, PedidoItem, Prenda
from .permissions import IsAdminOrReadOnly
from .serializers import (
    CarritoItemSerializer,
    CategoriaSerializer,
    ImagenPrendaSerializer,
    PedidoSerializer,
    PrendaSerializer,
    RegisterSerializer,
)


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ["nombre"]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "No puedes eliminar una categoría que todavía tiene prendas."},
                status=409,
            )


class PrendaViewSet(viewsets.ModelViewSet):
    queryset = Prenda.objects.select_related("categoria").prefetch_related("imagenes")
    serializer_class = PrendaSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filterset_class = PrendaFilter
    ordering_fields = ["precio", "creado", "nombre"]
    search_fields = ["nombre", "descripcion", "marca", "color"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            context["favoritos_ids"] = set(
                Favorito.objects.filter(user=user).values_list("prenda_id", flat=True)
            )
        return context

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def favorito(self, request, pk=None):
        prenda = self.get_object()
        fav, creado = Favorito.objects.get_or_create(user=request.user, prenda=prenda)
        if not creado:
            fav.delete()
        return Response({"es_favorito": creado})

    @action(detail=False, methods=["get"])
    def favoritos(self, request):
        prendas = self.get_queryset().filter(favoritos__user=request.user)
        serializer = self.get_serializer(prendas, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="imagenes",
        parser_classes=[MultiPartParser, FormParser],
    )
    def agregar_imagen(self, request, pk=None):
        prenda = self.get_object()
        serializer = ImagenPrendaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(prenda=prenda)
        return Response(serializer.data, status=201)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"imagenes/(?P<imagen_id>\d+)",
    )
    def eliminar_imagen(self, request, pk=None, imagen_id=None):
        prenda = self.get_object()
        imagen = get_object_or_404(prenda.imagenes, pk=imagen_id)
        imagen.delete()
        return Response(status=204)


class CarritoViewSet(viewsets.ModelViewSet):
    serializer_class = CarritoItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = []
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            CarritoItem.objects.filter(user=self.request.user)
            .select_related("prenda")
            .order_by("id")
        )

    def list(self, request, *args, **kwargs):
        items = self.get_queryset()
        data = self.get_serializer(items, many=True).data
        total = sum((i.prenda.precio * i.cantidad for i in items), Decimal("0"))
        piezas = sum(i.cantidad for i in items)
        return Response(
            {"items": data, "total": str(total), "cantidad_total": piezas}
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prenda = serializer.validated_data["prenda"]
        cantidad = serializer.validated_data.get("cantidad", 1)

        if prenda.stock == 0:
            raise ValidationError({"cantidad": "Esta prenda está agotada."})

        existente = CarritoItem.objects.filter(user=request.user, prenda=prenda).first()
        nueva = (existente.cantidad if existente else 0) + cantidad
        if nueva > prenda.stock:
            raise ValidationError(
                {"cantidad": f"Solo hay {prenda.stock} disponibles."}
            )

        if existente:
            existente.cantidad = nueva
            existente.save()
            item = existente
        else:
            item = CarritoItem.objects.create(
                user=request.user, prenda=prenda, cantidad=cantidad
            )
        return Response(self.get_serializer(item).data, status=201)

    def partial_update(self, request, *args, **kwargs):
        item = self.get_object()
        serializer = self.get_serializer(
            item, data={"cantidad": request.data.get("cantidad")}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        cantidad = serializer.validated_data["cantidad"]
        if cantidad > item.prenda.stock:
            raise ValidationError(
                {"cantidad": f"Solo hay {item.prenda.stock} disponibles."}
            )
        item.cantidad = cantidad
        item.save()
        return Response(self.get_serializer(item).data)

    @action(detail=False, methods=["delete"])
    def vaciar(self, request):
        CarritoItem.objects.filter(user=request.user).delete()
        return Response(status=204)

    @action(detail=False, methods=["post"])
    def comprar(self, request):
        with transaction.atomic():
            items = list(
                CarritoItem.objects.select_for_update()
                .filter(user=request.user)
                .select_related("prenda")
            )
            if not items:
                return Response({"detail": "Tu carrito está vacío."}, status=400)

            prendas = {
                p.pk: p
                for p in Prenda.objects.select_for_update().filter(
                    pk__in=[i.prenda_id for i in items]
                )
            }

            problemas = []
            for it in items:
                prenda = prendas[it.prenda_id]
                if it.cantidad > prenda.stock:
                    problemas.append(
                        {
                            "prenda": prenda.pk,
                            "nombre": prenda.nombre,
                            "disponibles": prenda.stock,
                            "pedidas": it.cantidad,
                        }
                    )
            if problemas:
                return Response(
                    {
                        "detail": "Algunas prendas ya no tienen stock suficiente.",
                        "problemas": problemas,
                    },
                    status=409,
                )

            total = sum(
                (prendas[i.prenda_id].precio * i.cantidad for i in items), Decimal("0")
            )
            pedido = Pedido.objects.create(user=request.user, total=total)
            for it in items:
                prenda = prendas[it.prenda_id]
                PedidoItem.objects.create(
                    pedido=pedido,
                    prenda=prenda,
                    nombre=prenda.nombre,
                    talla=prenda.talla,
                    color=prenda.color,
                    precio_unitario=prenda.precio,
                    cantidad=it.cantidad,
                )
                prenda.stock -= it.cantidad
                prenda.save(update_fields=["stock"])
            CarritoItem.objects.filter(user=request.user).delete()

        return Response(
            PedidoSerializer(pedido, context={"request": request}).data, status=201
        )


class PedidoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = []

    def get_queryset(self):
        return Pedido.objects.filter(user=self.request.user).prefetch_related("items")


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "username": user.username}, status=201)


class MeView(APIView):
    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_staff": user.is_staff,
            }
        )


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=204)
    
class MarcasView(APIView):
    def get(self, request):
        return Response([valor for valor, _ in Prenda.MARCAS])