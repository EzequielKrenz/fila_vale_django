from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import uuid


class Ticket(models.Model):
    class Status(models.TextChoices):
        AGUARDANDO = 'AGUARDANDO', 'Aguardando'
        CHAMADO = 'CHAMADO', 'Chamado'
        PRONTO = 'PRONTO', 'Pronto'
        RETIRADO = 'RETIRADO', 'Retirado'

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tickets'
    )

    chave_vale = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Chave primária do vale'
    )

    token_qr = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    qr_expira_em = models.DateTimeField(
        null=True,
        blank=True
    )

    qr_validado_em = models.DateTimeField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.AGUARDANDO
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    chamado_em = models.DateTimeField(null=True, blank=True)
    pronto_em = models.DateTimeField(null=True, blank=True)
    retirado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['criado_em']
        indexes = [
            models.Index(
                fields=['status', 'criado_em'],
                name='ticket_status_criado_idx'
            ),
            models.Index(fields=['token_qr'], name='ticket_token_qr_idx'),
            models.Index(
                fields=['qr_validado_em'],
                name='ticket_qr_valid_idx'
            ),
        ]

    def __str__(self):
        return f'Ticket #{self.pk} - {self.status}'

    def save(self, *args, **kwargs):
        if self.qr_expira_em is None:
            self.qr_expira_em = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def posicao_na_fila(self):
        if self.status != self.Status.AGUARDANDO:
            return None

        return Ticket.objects.filter(
            status=self.Status.AGUARDANDO,
            criado_em__lt=self.criado_em
        ).count() + 1

    @property
    def qr_valido(self):
        return (
            self.qr_validado_em is None
            and self.qr_expira_em is not None
            and timezone.now() <= self.qr_expira_em
        )

    def renovar_qr(self):
        # Gera os novos valores
        novo_token = uuid.uuid4()
        nova_expiracao = timezone.now() + timedelta(minutes=10)

        # Atualiza somente tickets que ainda não foram
        # validados nem retirados
        atualizados = Ticket.objects.filter(
            pk=self.pk,
            qr_validado_em__isnull=True
        ).exclude(
            status=self.Status.RETIRADO
        ).update(
            token_qr=novo_token,
            qr_expira_em=nova_expiracao
        )

        # Se nenhuma linha foi atualizada, a renovação
        # não estava autorizada
        if atualizados == 0:
            return False

        # Sincroniza o objeto em memória
        self.token_qr = novo_token
        self.qr_expira_em = nova_expiracao

        return True
