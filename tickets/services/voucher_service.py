from django.utils import timezone

from tickets.models import Ticket


# Exceções específicas do domínio
class VoucherError(Exception):
    """Erro relacionado à validação de vouchers."""
    pass


class VoucherJaValidadoError(VoucherError):
    """O voucher já foi utilizado."""
    pass


class VoucherExpiradoError(VoucherError):
    """O prazo do QR Code terminou."""
    pass


class VoucherNaoAutorizadoError(VoucherError):
    """O status do ticket não permite validação."""
    pass


class VoucherAlteradoError(VoucherError):
    """O token foi substituído durante a operação."""
    pass


def validar_voucher(ticket):
    """
    Valida o voucher de maneira condicional no banco.

    Retorna True quando a validação é concluída.
    Lança uma exceção específica quando não é permitida.
    """

    agora = timezone.now()
    token_original = ticket.token_qr

    # A verificação e a gravação são feitas
    # em uma única operação no banco
    atualizados = Ticket.objects.filter(
        pk=ticket.pk,
        token_qr=token_original,
        qr_validado_em__isnull=True,
        qr_expira_em__gte=agora,
        status__in=[
            Ticket.Status.CHAMADO,
            Ticket.Status.PRONTO,
        ]
    ).update(qr_validado_em=agora)

    if atualizados == 1:
        ticket.qr_validado_em = agora
        return True

    # Consulta o estado mais recente para
    # identificar por que a validação falhou
    ticket.refresh_from_db()

    if ticket.token_qr != token_original:
        raise VoucherAlteradoError(
            'O QR Code foi substituído por outro.'
        )

    if ticket.qr_validado_em is not None:
        raise VoucherJaValidadoError(
            'Este QR Code já foi validado.'
        )

    if (
        ticket.qr_expira_em is None
        or ticket.qr_expira_em < agora
    ):
        raise VoucherExpiradoError(
            'QR Code expirado. O aluno deve renová-lo.'
        )

    if ticket.status not in [
        Ticket.Status.CHAMADO,
        Ticket.Status.PRONTO,
    ]:
        raise VoucherNaoAutorizadoError(
            'O ticket precisa estar chamado ou pronto '
            'para permitir a validação.'
        )

    raise VoucherError(
        'Não foi possível validar o voucher. '
        'Tente novamente.'
    )
