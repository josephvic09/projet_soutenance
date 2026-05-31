from django.urls import path
from . import views

app_name = 'logements'

urlpatterns = [
    # Pages principales
    path('',                                    views.accueil,           name='accueil'),
    path('recherche/',                          views.recherche,         name='recherche'),
    path('logements/<slug:slug>/',              views.detail_logement,   name='detail'),

    # Gestion annonces
    path('logements/creer/',                    views.creer_logement,    name='creer'),
    path('logements/<slug:slug>/modifier/',     views.modifier_logement, name='modifier'),
    path('logements/<slug:slug>/supprimer/',    views.supprimer_logement,name='supprimer'),

    # Actions AJAX
    path('logements/<int:logement_id>/favori/', views.toggle_favori,     name='toggle_favori'),
    path('logements/<int:logement_id>/reserver/', views.faire_reservation, name='reserver'),
    path('logements/<int:logement_id>/signaler/', views.signaler_logement, name='signaler'),

    # API carte
    path('api/logements-carte/',                views.api_logements_carte, name='api_carte'),
    path('carte/', views.carte, name='carte'),
]