from django.urls import path
from . import views

app_name = 'notifs'

urlpatterns = [
    path('',              views.liste_notifications, name='liste'),
    path('marquer-lues/', views.marquer_lues,        name='marquer_lues'),
    path('count/',        views.compte_non_lues,     name='count'),
]