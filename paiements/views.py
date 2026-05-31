from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Paiement
from logements.models import Reservation


@login_required
def initier_paiement(request, reservation_id):
    reservation = get_object_or_404(
        Reservation, pk=reservation_id, locataire=request.user
    )

    if request.method == 'POST':
        methode   = request.POST.get('methode', 'MTN_MOMO')
        telephone = request.POST.get('telephone', '')

        paiement = Paiement.objects.create(
            utilisateur=request.user,
            type_paiement='RESERVATION',
            methode=methode,
            montant=reservation.logement.prix,
            reservation=reservation,
            telephone=telephone,
        )

        # Simuler paiement réussi (intégrer API réelle ici)
        paiement.statut    = 'REUSSI'
        paiement.traite_le = timezone.now()
        paiement.save()

        reservation.paye = True
        reservation.save()

        messages.success(
            request,
            f"✅ Paiement réussi ! Référence : {paiement.reference}"
        )
        return redirect('accounts:dashboard_locataire')

    return render(request, 'paiements/paiement.html', {
        'reservation': reservation
    })


@login_required
def historique_paiements(request):
    paiements = request.user.paiements.order_by('-cree_le')[:20]
    return render(request, 'paiements/historique.html', {
        'paiements': paiements
    })