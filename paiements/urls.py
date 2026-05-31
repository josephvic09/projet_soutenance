from django.urls import path
from . import views

app_name = 'paiements'

urlpatterns = [
    path('payer/<int:reservation_id>/', views.initier_paiement,    name='payer'),
    path('historique/',                  views.historique_paiements, name='historique'),
]