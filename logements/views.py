from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Logement, PhotoLogement, Favori, Avis, Ville, Quartier, Reservation, Signalement
from .forms import LogementForm, AvisForm, RechercheForm, ReservationForm


# ─── Accueil ─────────────────────────────────────────────

def accueil(request):
    logements_vedette = Logement.objects.filter(
        statut='PUBLIE', disponible=True, est_vedette=True
    ).select_related('ville', 'quartier').prefetch_related('photos')[:6]

    logements_recents = Logement.objects.filter(
        statut='PUBLIE', disponible=True
    ).select_related('ville', 'quartier').prefetch_related('photos').order_by('-cree_le')[:12]

    villes_populaires = Ville.objects.filter(actif=True).annotate(
        nb=Count('logements', filter=Q(logements__statut='PUBLIE'))
    ).order_by('-nb')[:8]

    context = {
        'logements_vedette': logements_vedette,
        'logements_recents': logements_recents,
        'villes_populaires': villes_populaires,
        'form_recherche':    RechercheForm(),
        'stats': {
            'nb_logements': Logement.objects.filter(statut='PUBLIE').count(),
            'nb_villes':    Ville.objects.filter(actif=True).count(),
        }
    }
    return render(request, 'logements/accueil.html', context)


# ─── Recherche ───────────────────────────────────────────

def recherche(request):
    form = RechercheForm(request.GET)
    qs = Logement.objects.filter(
        statut='PUBLIE', disponible=True
    ).select_related('ville', 'quartier').prefetch_related('photos')

    if form.is_valid():
        data = form.cleaned_data

        if data.get('q'):
            terme = data['q']
            qs = qs.filter(
                Q(titre__icontains=terme) |
                Q(description__icontains=terme) |
                Q(ville__nom__icontains=terme) |
                Q(quartier__nom__icontains=terme) |
                Q(adresse__icontains=terme)
            )
        if data.get('ville'):
            qs = qs.filter(ville__nom__icontains=data['ville'])
        if data.get('quartier'):
            qs = qs.filter(quartier__nom__icontains=data['quartier'])
        if data.get('type_logement'):
            qs = qs.filter(type_logement=data['type_logement'])
        if data.get('type_offre'):
            qs = qs.filter(type_offre=data['type_offre'])
        if data.get('prix_min'):
            qs = qs.filter(prix__gte=data['prix_min'])
        if data.get('prix_max'):
            qs = qs.filter(prix__lte=data['prix_max'])
        if data.get('nb_chambres'):
            qs = qs.filter(nb_chambres__gte=data['nb_chambres'])
        if data.get('standing'):
            qs = qs.filter(standing=data['standing'])
        if data.get('wifi'):
            qs = qs.filter(internet=True)
        if data.get('parking'):
            qs = qs.filter(parking=True)
        if data.get('climatisation'):
            qs = qs.filter(climatisation=True)
        if data.get('gardien'):
            qs = qs.filter(gardien=True)
        if data.get('piscine'):
            qs = qs.filter(piscine=True)
        if data.get('generateur'):
            qs = qs.filter(generateur=True)

    # Tri
    tri = request.GET.get('tri', 'recent')
    TRI_MAP = {
        'recent':    '-cree_le',
        'prix_asc':  'prix',
        'prix_desc': '-prix',
        'populaire': '-nb_vues',
    }
    qs = qs.order_by(TRI_MAP.get(tri, '-cree_le'))

    # Pagination
    paginator = Paginator(qs, 12)
    page      = request.GET.get('page', 1)
    logements = paginator.get_page(page)

    # Logements pour la carte
    logements_carte = list(
        qs.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).values(
            'id', 'titre', 'prix', 'latitude',
            'longitude', 'type_logement', 'nb_chambres'
        )[:100]
    )

    context = {
        'form':            form,
        'logements':       logements,
        'nb_resultats':    qs.count(),
        'logements_carte': logements_carte,
        'tri_actuel':      tri,
        'villes':          Ville.objects.filter(actif=True),
    }
    return render(request, 'logements/recherche.html', context)


# ─── Détail logement ─────────────────────────────────────

def detail_logement(request, slug):
    logement = get_object_or_404(
        Logement.objects.select_related(
            'ville', 'quartier', 'bailleur'
        ).prefetch_related('photos', 'avis'),
        slug=slug,
        statut='PUBLIE'
    )

    # Incrémenter vues (une fois par session)
    vue_key = f'vue_{logement.pk}'
    if not request.session.get(vue_key):
        logement.incrementer_vues()
        request.session[vue_key] = True

    # Logements similaires
    similaires = Logement.objects.filter(
        statut='PUBLIE',
        disponible=True,
        ville=logement.ville,
        type_logement=logement.type_logement,
    ).exclude(pk=logement.pk).prefetch_related('photos')[:4]

    # Est en favori ?
    est_favori = False
    if request.user.is_authenticated:
        est_favori = Favori.objects.filter(
            utilisateur=request.user,
            logement=logement
        ).exists()

    # Formulaire avis
    avis_form = AvisForm()
    if request.method == 'POST' and 'avis' in request.POST:
        if request.user.is_authenticated:
            avis_form = AvisForm(request.POST)
            if avis_form.is_valid():
                avis, cree = Avis.objects.get_or_create(
                    logement=logement,
                    auteur=request.user,
                    defaults={
                        'note':        avis_form.cleaned_data['note'],
                        'commentaire': avis_form.cleaned_data['commentaire'],
                    }
                )
                if cree:
                    messages.success(request, "✅ Avis soumis ! Visible après validation.")
                else:
                    messages.warning(request, "Vous avez déjà donné un avis.")
                return redirect('logements:detail', slug=slug)

    context = {
        'logement':         logement,
        'similaires':       similaires,
        'est_favori':       est_favori,
        'avis_form':        avis_form,
        'avis_list':        logement.avis.filter(approuve=True).select_related('auteur')[:10],
        'note_moy':         logement.note_moyenne,
        'form_reservation': ReservationForm(),
    }
    return render(request, 'logements/detail.html', context)


# ─── Créer logement ──────────────────────────────────────

@login_required
def creer_logement(request):
    if not request.user.est_bailleur:
        messages.error(request, "Seuls les bailleurs peuvent publier des annonces.")
        return redirect('logements:accueil')

    if request.method == 'POST':
        form   = LogementForm(request.POST)
        photos = request.FILES.getlist('photos')

        if form.is_valid():
            logement          = form.save(commit=False)
            logement.bailleur = request.user
            logement.statut   = 'EN_ATTENTE'
            logement.save()

            for i, photo in enumerate(photos[:10]):
                PhotoLogement.objects.create(
                    logement=logement,
                    image=photo,
                    principale=(i == 0),
                    ordre=i,
                )

            messages.success(
                request,
                "✅ Annonce soumise ! Elle sera publiée après validation."
            )
            return redirect('accounts:dashboard_bailleur')
    else:
        form = LogementForm()

    return render(request, 'logements/creer.html', {
        'form':   form,
        'villes': Ville.objects.filter(actif=True),
    })


# ─── Modifier logement ───────────────────────────────────

@login_required
def modifier_logement(request, slug):
    logement = get_object_or_404(Logement, slug=slug, bailleur=request.user)

    if request.method == 'POST':
        form = LogementForm(request.POST, instance=logement)
        if form.is_valid():
            form.save()
            for i, photo in enumerate(request.FILES.getlist('photos')):
                PhotoLogement.objects.create(
                    logement=logement,
                    image=photo,
                    ordre=100 + i
                )
            messages.success(request, "✅ Annonce mise à jour !")
            return redirect('logements:detail', slug=logement.slug)
    else:
        form = LogementForm(instance=logement)

    return render(request, 'logements/modifier.html', {
        'form':     form,
        'logement': logement,
    })


# ─── Supprimer logement ──────────────────────────────────

@login_required
def supprimer_logement(request, slug):
    logement = get_object_or_404(Logement, slug=slug, bailleur=request.user)
    if request.method == 'POST':
        logement.statut = 'ARCHIVE'
        logement.save()
        messages.success(request, "Annonce archivée.")
    return redirect('accounts:dashboard_bailleur')


# ─── Toggle favori (AJAX) ────────────────────────────────

@login_required
@require_POST
def toggle_favori(request, logement_id):
    logement = get_object_or_404(Logement, pk=logement_id, statut='PUBLIE')
    favori, cree = Favori.objects.get_or_create(
        utilisateur=request.user,
        logement=logement
    )
    if not cree:
        favori.delete()
        Logement.objects.filter(pk=logement_id).update(
            nb_favoris=max(0, logement.nb_favoris - 1)
        )
        return JsonResponse({'status': 'removed'})

    Logement.objects.filter(pk=logement_id).update(
        nb_favoris=logement.nb_favoris + 1
    )
    return JsonResponse({'status': 'added'})


# ─── Réservation ─────────────────────────────────────────

@login_required
@require_POST
def faire_reservation(request, logement_id):
    logement = get_object_or_404(
        Logement, pk=logement_id, statut='PUBLIE', disponible=True
    )
    form = ReservationForm(request.POST)
    if form.is_valid():
        res          = form.save(commit=False)
        res.logement = logement
        res.locataire = request.user
        res.save()
        messages.success(request, "✅ Demande envoyée ! Le bailleur vous contactera.")
    else:
        messages.error(request, "Erreur dans le formulaire.")
    return redirect('logements:detail', slug=logement.slug)


# ─── Signalement (AJAX) ──────────────────────────────────

@login_required
@require_POST
def signaler_logement(request, logement_id):
    logement    = get_object_or_404(Logement, pk=logement_id)
    motif       = request.POST.get('motif', 'AUTRE')
    description = request.POST.get('description', '')
    Signalement.objects.create(
        logement=logement,
        auteur=request.user,
        motif=motif,
        description=description,
    )
    return JsonResponse({'status': 'ok'})


# ─── API Carte ───────────────────────────────────────────

def api_logements_carte(request):
    qs = Logement.objects.filter(
        statut='PUBLIE',
        disponible=True,
        latitude__isnull=False,
        longitude__isnull=False,
    ).select_related('ville').prefetch_related('photos')[:200]

    data = []
    for l in qs:
        photo = l.get_photo_principale()
        data.append({
            'id':           l.pk,
            'titre':        l.titre,
            'prix':         l.prix,
            'prix_formate': l.prix_formate,
            'ville':        l.ville.nom,
            'quartier':     l.quartier.nom if l.quartier else '',
            'type':         l.get_type_logement_display(),
            'chambres':     l.nb_chambres,
            'lat':          float(l.latitude),
            'lng':          float(l.longitude),
            'photo':        photo.image.url if photo else '/static/images/no-image.jpg',
            'url':          f'/logements/{l.slug}/',
        })
    return JsonResponse({'logements': data})