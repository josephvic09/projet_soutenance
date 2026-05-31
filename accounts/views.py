import secrets
import hashlib
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm

from .models import Utilisateur, LogActivite
from .forms import (
    InscriptionForm, ConnexionForm, ProfilForm,
    ResetPasswordDemandeForm, ResetPasswordConfirmForm
)


# ─── Utilitaires ─────────────────────────────────────────

def get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def log_activite(user, action, request, description=''):
    LogActivite.objects.create(
        utilisateur=user,
        action=action,
        description=description,
        ip_address=get_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )


def get_redirect_url(user):
    if user.est_admin:
        return '/accounts/tableau-de-bord/admin/'
    elif user.role == 'BAILLEUR':
        return '/accounts/tableau-de-bord/bailleur/'
    return '/accounts/tableau-de-bord/locataire/'


# ─── Inscription ─────────────────────────────────────────

def inscription(request):
    if request.user.is_authenticated:
        return redirect('logements:accueil')

    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # ✅ Activation directe sans email
            user.is_active = True
            user.email_verified = True
            user.save()

            login(request, user)
            log_activite(user, 'INSCRIPTION', request)
            messages.success(
                request,
                f"🎉 Bienvenue {user.prenom} ! Votre compte a été créé avec succès."
            )
            return redirect(get_redirect_url(user))
        else:
            messages.error(request, "Veuillez corriger les erreurs.")
    else:
        form = InscriptionForm()

    return render(request, 'accounts/inscription.html', {'form': form})


# ─── Vérification email ───────────────────────────────────

def verifier_email(request, token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    try:
        user = Utilisateur.objects.get(
            email_verify_token=token_hash,
            is_active=False
        )
        user.is_active = True
        user.email_verified = True
        user.email_verify_token = ''
        user.save()
        messages.success(request, "✅ Email vérifié ! Vous pouvez vous connecter.")
        return redirect('accounts:connexion')
    except Utilisateur.DoesNotExist:
        messages.error(request, "Lien invalide ou expiré.")
        return redirect('accounts:inscription')


def verification_email_envoyee(request):
    return render(request, 'accounts/verification_email_envoyee.html')


# ─── Connexion ────────────────────────────────────────────

def connexion(request):
    if request.user.is_authenticated:
        return redirect(get_redirect_url(request.user))

    if request.method == 'POST':
        form = ConnexionForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            if not form.cleaned_data.get('se_souvenir'):
                request.session.set_expiry(0)
            login(request, user)
            Utilisateur.objects.filter(pk=user.pk).update(
                nb_connexions=user.nb_connexions + 1,
                derniere_connexion_ip=get_ip(request)
            )
            log_activite(user, 'CONNEXION', request)
            messages.success(request, f"Bienvenue {user.prenom} !")
            next_url = request.GET.get('next', get_redirect_url(user))
            return redirect(next_url)
        else:
            messages.error(request, "Email ou mot de passe incorrect.")
    else:
        form = ConnexionForm()

    return render(request, 'accounts/connexion.html', {'form': form})


# ─── Déconnexion ──────────────────────────────────────────

def deconnexion(request):
    if request.user.is_authenticated:
        log_activite(request.user, 'DECONNEXION', request)
        logout(request)
    messages.info(request, "Vous avez été déconnecté(e).")
    return redirect('accounts:connexion')


# ─── Reset mot de passe ───────────────────────────────────

def reset_password_demande(request):
    if request.method == 'POST':
        form = ResetPasswordDemandeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user  = Utilisateur.objects.get(email=email)
            token = secrets.token_urlsafe(32)
            user.reset_password_token   = hashlib.sha256(token.encode()).hexdigest()
            user.reset_password_expires = timezone.now() + timedelta(hours=2)
            user.save()

            lien = request.build_absolute_uri(
                f'/accounts/reset-password/{token}/'
            )
            send_mail(
                subject='🔑 Réinitialisation mot de passe — LogementCM',
                message=f'Bonjour {user.prenom},\n\nCliquez ici :\n{lien}\n\nLien valable 2h.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            messages.success(request, "Lien de réinitialisation envoyé à votre email.")
            return redirect('accounts:connexion')
    else:
        form = ResetPasswordDemandeForm()

    return render(request, 'accounts/reset_password_demande.html', {'form': form})


def reset_password_confirmer(request, token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    try:
        user = Utilisateur.objects.get(
            reset_password_token=token_hash,
            reset_password_expires__gt=timezone.now()
        )
    except Utilisateur.DoesNotExist:
        messages.error(request, "Lien invalide ou expiré.")
        return redirect('accounts:reset_password_demande')

    if request.method == 'POST':
        form = ResetPasswordConfirmForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password1'])
            user.reset_password_token   = ''
            user.reset_password_expires = None
            user.save()
            messages.success(request, "Mot de passe réinitialisé ! Connectez-vous.")
            return redirect('accounts:connexion')
    else:
        form = ResetPasswordConfirmForm()

    return render(request, 'accounts/reset_password_confirmer.html', {'form': form})


# ─── Profil ───────────────────────────────────────────────

@login_required
def profil(request):
    if request.method == 'POST':
        form = ProfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            log_activite(request.user, 'MODIF_PROFIL', request)
            messages.success(request, "Profil mis à jour !")
            return redirect('accounts:profil')
    else:
        form = ProfilForm(instance=request.user)

    return render(request, 'accounts/profil.html', {'form': form})


@login_required
def changer_mot_de_passe(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            log_activite(user, 'MODIF_MDP', request)
            messages.success(request, "Mot de passe changé !")
            return redirect('accounts:profil')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'accounts/changer_mdp.html', {'form': form})


# ─── Tableaux de bord ─────────────────────────────────────

@login_required
def tableau_de_bord(request):
    if request.user.est_admin:
        return redirect('accounts:dashboard_admin')
    elif request.user.role == 'BAILLEUR':
        return redirect('accounts:dashboard_bailleur')
    return redirect('accounts:dashboard_locataire')


@login_required
def dashboard_locataire(request):
    from logements.models import Favori, Reservation, RechercheHistorique
    from chat.models import Conversation

    favoris = Favori.objects.filter(
        utilisateur=request.user
    ).select_related('logement__ville', 'logement__quartier').prefetch_related(
        'logement__photos'
    ).order_by('-cree_le')[:6]

    reservations = Reservation.objects.filter(
        locataire=request.user
    ).select_related('logement__ville').order_by('-cree_le')[:5]

    nb_messages = (
        Conversation.objects.filter(locataire=request.user) |
        Conversation.objects.filter(bailleur=request.user)
    ).count()

    context = {
        'favoris':      favoris,
        'reservations': reservations,
        'nb_favoris':   Favori.objects.filter(utilisateur=request.user).count(),
        'nb_reservations': Reservation.objects.filter(locataire=request.user).count(),
        'nb_messages':  nb_messages,
    }
    return render(request, 'accounts/dashboard_locataire.html', context)

@login_required
def dashboard_bailleur(request):
    if not request.user.est_bailleur:
        messages.error(request, "Accès refusé.")
        return redirect('accounts:dashboard_locataire')
    return render(request, 'accounts/dashboard_bailleur.html')


@login_required
def dashboard_admin(request):
    if not request.user.est_admin:
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('accounts:tableau_de_bord')
    return render(request, 'accounts/dashboard_admin.html')
@login_required
def mes_favoris(request):
    from logements.models import Favori
    favoris = Favori.objects.filter(
        utilisateur=request.user
    ).select_related(
        'logement__ville', 'logement__quartier'
    ).prefetch_related('logement__photos').order_by('-cree_le')

    return render(request, 'accounts/mes_favoris.html', {
        'favoris': favoris,
        'nb_favoris': favoris.count(),
    })


@login_required
def mes_reservations(request):
    from logements.models import Reservation
    reservations = Reservation.objects.filter(
        locataire=request.user
    ).select_related('logement__ville', 'logement__quartier').order_by('-cree_le')

    return render(request, 'accounts/mes_reservations.html', {
        'reservations': reservations,
    })


@login_required
def comparer_logements(request):
    from logements.models import Logement
    ids = request.GET.getlist('ids')
    logements = []
    if ids:
        logements = Logement.objects.filter(
            pk__in=ids[:4], statut='PUBLIE'
        ).select_related('ville', 'quartier').prefetch_related('photos')

    return render(request, 'accounts/comparer.html', {
        'logements': logements,
    })