from django.db import models
from accounts.models import Utilisateur


class Notification(models.Model):

    TYPE_CHOICES = [
        ('MESSAGE',    'Message'),
        ('RESERVATION','Réservation'),
        ('VALIDATION', 'Validation annonce'),
        ('AVIS',       'Avis'),
        ('PAIEMENT',   'Paiement'),
        ('SYSTEME',    'Système'),
    ]

    destinataire = models.ForeignKey(
        Utilisateur, on_delete=models.CASCADE,
        related_name='notifications'
    )
    type_notif   = models.CharField(max_length=20, choices=TYPE_CHOICES)
    titre        = models.CharField(max_length=200)
    message      = models.TextField()
    lien         = models.CharField(max_length=300, blank=True)
    lue          = models.BooleanField(default=False)
    lue_le       = models.DateTimeField(null=True, blank=True)
    cree_le      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        ordering = ['-cree_le']

    def __str__(self):
        return f"{self.destinataire} — {self.titre}"