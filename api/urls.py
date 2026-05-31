from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('logements/',  views.LogementsAPIView.as_view(), name='logements'),
    path('quartiers/',  views.quartiers_api,               name='quartiers'),
    path('villes/',     views.villes_api,                  name='villes'),
    path('stats/',      views.stats_api,                   name='stats'),
]