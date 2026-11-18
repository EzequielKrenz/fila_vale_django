from django.db import IntegrityError, transaction
from django.utils import timezone

from tickets.models import Ticket


class TicketAtivoError(Exception):
    """O usuário já possui um ticket ativo."""
    pass


class ChaveJaUtilizadaError(Exception):
    """A chave do vale já foi utilizada."""
    pass


def buscar_ticket_ativo(usuario):
    """Busca o ticket ativo de um usuário."""

    return (
        Ticket.objects
        .filter(usuario=usuario)
        .exclude(status=Ticket.Status.RETIRADO)
        .order_by('-criado_em')
        .first()
    )


def criar_ticket(usuario, chave):
    """Cria um ticket respeitando as regras da fila."""

    chave = chave.strip()

    if not chave:
        raise ValueError('A chave do vale é obrigatória.')

    # Regra 1: um ticket ativo por usuário
    if buscar_ticket_ativo(usuario) is not None:
        raise TicketAtivoError(
            'O usuário já possui um ticket ativo.'
        )

    # Regra 2: a chave do vale deve ser única
    if Ticket.objects.filter(chave_vale=chave).exists():
        raise ChaveJaUtilizadaError(
            'Esta chave já foi utilizada.'
        )

    try:
        with transaction.atomic():
            ticket = Ticket.objects.create(
                usuario=usuario,
                chave_vale=chave
            )

    except IntegrityError:
        # Trata duplicidades que ocorreram entre
        # a consulta e a gravação no banco.
        if buscar_ticket_ativo(usuario) is not None:
            raise TicketAtivoError(
                'O usuário já possui um ticket ativo.'
            ) from None

        if Ticket.objects.filter(chave_vale=chave).exists():
            raise ChaveJaUtilizadaError(
                'Esta chave já foi utilizada.'
            ) from None

        raise

    return ticket


class FilaAtualizadaError(Exception):
    """O próximo ticket mudou antes de ser chamado."""


def chamar_ticket_aguardando(ticket_id):
    """Troca AGUARDANDO por CHAMADO uma única vez."""
    atualizados = Ticket.objects.filter(
        pk=ticket_id,
        status=Ticket.Status.AGUARDANDO,
    ).update(
        status=Ticket.Status.CHAMADO,
        chamado_em=timezone.now(),
    )
    return atualizados == 1


def chamar_proximo_ticket():
    """
    Chama o primeiro ticket aguardando.

    Retorna o ID ou None se a fila estiver vazia.
    Se outro funcionário alterou o ticket, solicita nova tentativa.
    """
    proximo = Ticket.objects.filter(
        status=Ticket.Status.AGUARDANDO
    ).order_by('criado_em', 'pk').first()

    if proximo is None:
        return None

    if not chamar_ticket_aguardando(proximo.pk):
        raise FilaAtualizadaError(
            'A fila foi atualizada por outro funcionário.'
        )

    return proximo.pk


def marcar_ticket_pronto(ticket_id):
    """Troca CHAMADO por PRONTO uma única vez."""
    atualizados = Ticket.objects.filter(
        pk=ticket_id,
        status=Ticket.Status.CHAMADO,
    ).update(
        status=Ticket.Status.PRONTO,
        pronto_em=timezone.now(),
    )
    return atualizados == 1
