from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('',                             views.liste_conversations, name='conversations'),
    path('<uuid:conv_uuid>/',            views.conversation_detail, name='detail'),
    path('<uuid:conv_uuid>/envoyer/',    views.envoyer_message,     name='envoyer'),
    path('demarrer/<int:logement_id>/',  views.demarrer_conversation, name='demarrer'),
    path('chatbot/',                     views.chatbot,             name='chatbot'),
    path('chatbot/message/',             views.chatbot_message,     name='chatbot_message'),
]