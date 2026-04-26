from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'merchants', views.MerchantViewSet, basename='merchant')
router.register(r'payouts', views.PayoutViewSet, basename='payout')

urlpatterns = [
    path('auth/register/', views.register_merchant, name='register'),
] + router.urls
