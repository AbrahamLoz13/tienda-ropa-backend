from rest_framework import viewsets, generics
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.views import APIView
from .models import Categoria, Prenda, Favorito
from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import IsAdminOrReadOnly
from .serializers import CategoriaSerializer, PrendaSerializer,  RegisterSerializer


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ["nombre"]
    
class PrendaViewSet(viewsets.ModelViewSet):
    queryset = Prenda.objects.all()
    serializer_class = PrendaSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ["categoria", "talla", "color", "marca"]
    ordering_fields = ["precio", "creado", "nombre"]
    search_fields = ["nombre","descripcion","marca","color"]
    
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
        return Response({"id": user.id, "username": user.username, "email": user.email})


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=204)