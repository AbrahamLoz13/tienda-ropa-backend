from rest_framework import generics, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import PrendaFilter
from .models import Categoria, Favorito, Prenda
from .permissions import IsAdminOrReadOnly
from .serializers import (
    CategoriaSerializer,
    ImagenPrendaSerializer,
    PrendaSerializer,
    RegisterSerializer,
)


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ["nombre"]


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