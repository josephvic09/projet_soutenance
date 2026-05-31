from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Notification


@login_required
def liste_notifications(request):
    notifs = request.user.notifications.all()[:50]
    return render(request, 'notifs/liste.html', {
        'notifications': notifs
    })


@login_required
@require_POST
def marquer_lues(request):
    request.user.notifications.filter(lue=False).update(
        lue=True,
        lue_le=timezone.now()
    )
    return JsonResponse({'status': 'ok'})


@login_required
def compte_non_lues(request):
    count = request.user.notifications.filter(lue=False).count()
    return JsonResponse({'count': count})