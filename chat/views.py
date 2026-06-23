import json
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings

from .models import Conversation, Message, ConversationChatbot, MessageChatbot
from logements.models import Logement


@login_required
def liste_conversations(request):
    convs = (
        Conversation.objects.filter(locataire=request.user) |
        Conversation.objects.filter(bailleur=request.user)
    ).select_related(
        'locataire', 'bailleur', 'logement'
    ).order_by('-modifie_le')
    return render(request, 'chat/conversations.html', {   # ← pluriel
        'conversations': convs
    })


@login_required
def conversation_detail(request, conv_uuid):
    conv = get_object_or_404(Conversation, uuid=conv_uuid)
    if request.user not in [conv.locataire, conv.bailleur]:
        return redirect('chat:conversations')
    Message.objects.filter(
        conversation=conv, non_lu=True
    ).exclude(expediteur=request.user).update(
        non_lu=False, lu_le=timezone.now()
    )
    messages_list = conv.messages.filter(
        supprime=False
    ).select_related('expediteur')
    return render(request, 'chat/conversation.html', {
        'conversation': conv,
        'messages':     messages_list,
    })
# ─── À ajouter dans chat/views.py, par exemple juste après conversation_detail ───

@login_required
def poll_messages(request, conv_uuid):
    """
    Appelée toutes les ~3 secondes en JS depuis la page de conversation.
    Renvoie les 30 derniers messages avec leur statut de lecture,
    et marque comme lus les messages reçus pendant que la page est ouverte.
    """
    conv = get_object_or_404(Conversation, uuid=conv_uuid)
    if request.user not in [conv.locataire, conv.bailleur]:
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    # Marquer comme lus les messages reçus (pas envoyés par moi)
    Message.objects.filter(
        conversation=conv, non_lu=True
    ).exclude(expediteur=request.user).update(
        non_lu=False, lu_le=timezone.now()
    )

    qs = conv.messages.filter(supprime=False).order_by('-cree_le')[:30]
    data = []
    for m in reversed(list(qs)):
        data.append({
            'id':            m.pk,
            'contenu':       m.contenu,
            'expediteur_id': m.expediteur_id,
            'cree_le':       m.cree_le.strftime('%H:%M'),
            'lu':            not m.non_lu,
        })
    return JsonResponse({'messages': data})


@login_required
def demarrer_conversation(request, logement_id):
    logement = get_object_or_404(Logement, pk=logement_id, statut='PUBLIE')
    if request.user == logement.bailleur:
        return redirect('logements:detail', slug=logement.slug)
    conv, _ = Conversation.objects.get_or_create(
        locataire=request.user,
        bailleur=logement.bailleur,
        logement=logement,
    )
    return redirect('chat:detail', conv_uuid=str(conv.uuid))


@login_required
@require_POST
def envoyer_message(request, conv_uuid):
    conv = get_object_or_404(Conversation, uuid=conv_uuid)
    if request.user not in [conv.locataire, conv.bailleur]:
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    data    = json.loads(request.body)
    contenu = data.get('contenu', '').strip()
    if not contenu:
        return JsonResponse({'error': 'Message vide'}, status=400)
    msg = Message.objects.create(
        conversation=conv,
        expediteur=request.user,
        contenu=contenu[:2000],
    )
    conv.save()
    try:
        from notifs.utils import notif_nouveau_message
        notif_nouveau_message(msg)
    except Exception:
        pass
    return JsonResponse({
        'id':         msg.pk,
        'contenu':    msg.contenu,
        'expediteur': request.user.get_full_name(),
        'cree_le':    msg.cree_le.strftime('%H:%M'),
    })


def chatbot(request):
    if not request.session.session_key:
        request.session.create()
    conv = None
    if request.user.is_authenticated:
        conv = ConversationChatbot.objects.filter(
            utilisateur=request.user
        ).order_by('-modifie_le').first()
    return render(request, 'chat/chatbot.html', {
        'conversation': conv
    })


@require_POST
def chatbot_message(request):
    try:
        data         = json.loads(request.body)
        message_user = data.get('message', '').strip()
        conv_id      = data.get('conv_id')
        if not message_user:
            return JsonResponse({'error': 'Message vide'}, status=400)
        session_id = request.session.session_key or 'anonymous'
        if conv_id:
            try:
                conv = ConversationChatbot.objects.get(pk=conv_id)
            except ConversationChatbot.DoesNotExist:
                conv = _creer_conv(request, session_id)
        else:
            conv = _creer_conv(request, session_id)
        MessageChatbot.objects.create(
            conversation=conv,
            role='USER',
            contenu=message_user
        )
        reponse, logements = _generer_reponse(message_user, conv)
        msg_bot = MessageChatbot.objects.create(
            conversation=conv,
            role='ASSISTANT',
            contenu=reponse
        )
        if logements:
            msg_bot.logements_sugeres.set(logements)
        logements_data = []
        for l in logements[:4]:
            photo = l.get_photo_principale()
            logements_data.append({
                'id':       l.pk,
                'titre':    l.titre,
                'prix':     l.prix_formate,
                'ville':    l.ville.nom,
                'quartier': l.quartier.nom if l.quartier else '',
                'chambres': l.nb_chambres,
                'type':     l.get_type_logement_display(),
                'photo':    photo.image.url if photo else '/static/images/no-image.jpg',
                'url':      f'/logements/{l.slug}/',
            })
        return JsonResponse({
            'reponse':   reponse,
            'conv_id':   conv.pk,
            'logements': logements_data,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _creer_conv(request, session_id):
    return ConversationChatbot.objects.create(
        utilisateur=request.user if request.user.is_authenticated else None,
        session_id=session_id,
        titre='Nouvelle recherche',
    )


def _generer_reponse(message, conv):
    criteres  = _extraire_criteres(message)
    logements = _chercher_logements(criteres)
    historique = list(
        conv.messages.order_by('cree_le').values('role', 'contenu')[:10]
    )
    contexte = ''
    if logements.exists():
        contexte = '\n\nLogements disponibles :\n'
        for l in logements[:5]:
            contexte += (
                f"- {l.titre} à {l.ville.nom}"
                f"{' (' + l.quartier.nom + ')' if l.quartier else ''}"
                f" : {l.prix_formate}/mois"
                f", {l.nb_chambres} chambre(s)\n"
            )
    system_prompt = (
        "Tu es l'assistant IA de LogementCM, une plateforme de logements au Cameroun. "
        "Tu aides les utilisateurs à trouver le logement idéal à Yaoundé, Douala et autres villes. "
        "Tu communiques en français, de manière professionnelle et chaleureuse. "
        "Les prix sont en FCFA." + contexte
    )
    messages_api = []
    for m in historique[-8:]:
        messages_api.append({
            'role':    'user' if m['role'] == 'USER' else 'assistant',
            'content': m['contenu']
        })
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=800,
            system=system_prompt,
            messages=messages_api or [{'role': 'user', 'content': message}],
        )
        reponse_texte = response.content[0].text
    except Exception:
        reponse_texte = _reponse_fallback(logements, criteres)
    return reponse_texte, list(logements[:4])


def _extraire_criteres(message):
    msg      = message.lower()
    criteres = {}
    for ville in ['yaoundé', 'yaounde', 'douala', 'bafoussam', 'garoua', 'bamenda']:
        if ville in msg:
            criteres['ville'] = 'Yaoundé' if 'yaounde' in ville else ville.title()
            break
    quartiers = [
        'bastos', 'nlongkak', 'mvog-ada', 'nsam', 'biyem-assi',
        'melen', 'essos', 'omnisport', 'akwa', 'bonanjo', 'bonapriso'
    ]
    for q in quartiers:
        if q in msg:
            criteres['quartier'] = q
            break
    prix_matches = re.findall(r'(\d[\d\s]*)\s*(?:fcfa|francs?|f\b)?', msg)
    montants = []
    for p in prix_matches[:2]:
        try:
            montants.append(int(p.replace(' ', '')))
        except ValueError:
            pass
    if len(montants) >= 2:
        montants.sort()
        criteres['prix_min'] = montants[0]
        criteres['prix_max'] = montants[1]
    elif len(montants) == 1:
        criteres['prix_max'] = montants[0]
    types = {
        'studio':      'STUDIO',
        'appartement': 'APPARTEMENT',
        'villa':       'VILLA',
        'maison':      'MAISON',
        'chambre':     'CHAMBRE',
        'duplex':      'DUPLEX',
    }
    for k, v in types.items():
        if k in msg:
            criteres['type_logement'] = v
            break
    ch = re.search(r'(\d+)\s*chambre', msg)
    if ch:
        criteres['nb_chambres'] = int(ch.group(1))
    return criteres


def _chercher_logements(criteres):
    from django.db.models import Q
    qs = Logement.objects.filter(
        statut='PUBLIE', disponible=True
    ).select_related('ville', 'quartier').prefetch_related('photos')
    if criteres.get('ville'):
        qs = qs.filter(ville__nom__icontains=criteres['ville'])
    if criteres.get('quartier'):
        qs = qs.filter(quartier__nom__icontains=criteres['quartier'])
    if criteres.get('type_logement'):
        qs = qs.filter(type_logement=criteres['type_logement'])
    if criteres.get('prix_min'):
        qs = qs.filter(prix__gte=criteres['prix_min'])
    if criteres.get('prix_max'):
        qs = qs.filter(prix__lte=criteres['prix_max'])
    if criteres.get('nb_chambres'):
        qs = qs.filter(nb_chambres__gte=criteres['nb_chambres'])
    return qs.order_by('-est_booste', '-cree_le')[:5]


def _reponse_fallback(logements, criteres):
    if logements.exists():
        nb = logements.count()
        return (
            f"J'ai trouvé **{nb} logement(s)** correspondant à votre recherche ! "
            f"Voici les meilleures options disponibles."
        )
    elif criteres:
        return (
            "Je n'ai pas trouvé de logements pour ces critères. "
            "Voulez-vous élargir la recherche ?"
        )
    return (
        "Bonjour ! Je suis l'assistant LogementCM. 🏠\n\n"
        "Dites-moi ce que vous cherchez, par exemple :\n\n"
        "« Studio meublé à Bastos Yaoundé entre 80 000 et 120 000 FCFA »"
    )