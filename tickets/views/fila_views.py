
from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.db import transaction
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.utils import timezone

from ..forms import EntrarFilaForm
from ..models import Ticket
from ..permissions import eh_staff
from ..services.fila_service import (
    TicketAtivoError,
    ChaveJaUtilizadaError,
    ValeNaoAutorizadoError,
    buscar_ticket_ativo,
    criar_ticket,
)


@login_required
def inicio(request):
    ticket_ativo = buscar_ticket_ativo(request.user)

    if ticket_ativo:
        return redirect('meu_ticket')

    if request.method == 'POST':
        form = EntrarFilaForm(request.POST)

        if form.is_valid():
            chave = form.cleaned_data['chave_vale']

            try:
                ticket = criar_ticket(
                    usuario=request.user,
                    chave=chave
                )

            except TicketAtivoError:
                messages.warning(
                    request,
                    'Você já possui um ticket ativo.'
                )
                return redirect('meu_ticket')

            except ValeNaoAutorizadoError:
                messages.error(
                    request,
                    'Chave de vale inválida ou não autorizada para sua conta.'
                )

            except ChaveJaUtilizadaError:
                messages.error(
                    request,
                    'Essa chave já foi utilizada '
                    'ou já está na fila.'
                )

            else:
                messages.success(
                    request,
                    f'Ticket #{ticket.pk} criado. '
                    'Você entrou na fila.'
                )
                return redirect('meu_ticket')

    else:
        form = EntrarFilaForm()

    return render(
        request,
        'tickets/inicio.html',
        {'form': form}
    )


@login_required
def meu_ticket(request):
    ticket = buscar_ticket_ativo(request.user)

    if not ticket:
        return redirect('inicio')

    posicao = ticket.posicao_na_fila()

    pessoas_na_frente = (
        max(posicao - 1, 0) if posicao else None
    )

    return render(
        request,
        'tickets/meu_ticket.html',
        {
            'ticket': ticket,
            'posicao': posicao,
            'pessoas_na_frente': pessoas_na_frente,
        }
    )


def fila_publica(request):
    chamado = Ticket.objects.filter(
        status=Ticket.Status.CHAMADO
    ).order_by('chamado_em').first()

    prontos = Ticket.objects.filter(
        status=Ticket.Status.PRONTO
    ).order_by('pronto_em')

    aguardando = Ticket.objects.filter(
        status=Ticket.Status.AGUARDANDO
    ).order_by('criado_em')

    meu_ticket_id = None

    if request.user.is_authenticated:
        meu = buscar_ticket_ativo(request.user)
        meu_ticket_id = meu.id if meu else None

    return render(
        request,
        'tickets/fila_publica.html',
        {
            'chamado': chamado,
            'prontos': prontos,
            'aguardando': aguardando,
            'meu_ticket_id': meu_ticket_id,
        }
    )


@user_passes_test(eh_staff, login_url='login')
def painel_admin(request):
    chamados = Ticket.objects.filter(
        status=Ticket.Status.CHAMADO
    ).order_by('chamado_em')

    prontos = Ticket.objects.filter(
        status=Ticket.Status.PRONTO
    ).order_by('pronto_em')

    aguardando = Ticket.objects.filter(
        status=Ticket.Status.AGUARDANDO
    ).order_by('criado_em')

    return render(
        request,
        'tickets/painel_admin.html',
        {
            'chamados': chamados,
            'prontos': prontos,
            'aguardando': aguardando,
        }
    )


@user_passes_test(eh_staff, login_url='login')
@transaction.atomic
def chamar_proximo(request):
    if request.method != 'POST':
        return redirect('painel_admin')

    ticket = Ticket.objects.select_for_update().filter(
        status=Ticket.Status.AGUARDANDO
    ).order_by('criado_em').first()

    if not ticket:
        messages.warning(
            request,
            'Não há ninguém aguardando na fila.'
        )
        return redirect('painel_admin')

    ticket.status = Ticket.Status.CHAMADO
    ticket.chamado_em = timezone.now()

    ticket.save(
        update_fields=['status', 'chamado_em']
    )

    messages.success(
        request,
        f'Ticket #{ticket.pk} foi chamado.'
    )

    return redirect('painel_admin')


@user_passes_test(eh_staff, login_url='login')
def marcar_pronto(request, ticket_id):
    if request.method != 'POST':
        return redirect('painel_admin')

    ticket = get_object_or_404(
        Ticket,
        pk=ticket_id
    )

    if ticket.status != Ticket.Status.CHAMADO:
        messages.error(
            request,
            'Somente tickets chamados podem '
            'ser marcados como prontos.'
        )
        return redirect('painel_admin')

    ticket.status = Ticket.Status.PRONTO
    ticket.pronto_em = timezone.now()

    ticket.save(
        update_fields=['status', 'pronto_em']
    )

    messages.success(
        request,
        f'Ticket #{ticket.pk} marcado como pronto.'
    )

    return redirect('painel_admin')


@user_passes_test(eh_staff, login_url='login')
def marcar_retirado(request, ticket_id):
    if request.method != 'POST':
        return redirect('painel_admin')

    ticket = get_object_or_404(
        Ticket,
        pk=ticket_id
    )

    atualizados = Ticket.objects.filter(
        pk=ticket.pk,
        status=Ticket.Status.PRONTO,
        qr_validado_em__isnull=False
    ).update(
        status=Ticket.Status.RETIRADO,
        retirado_em=timezone.now()
    )

    if atualizados == 1:
        messages.success(
            request,
            f'Ticket #{ticket.pk} retirado com sucesso.'
        )
    else:
        messages.error(
            request,
            'Não foi possível finalizar o ticket. '
            'Ele precisa estar pronto e ter '
            'o QR Code validado.'
        )

    return redirect('painel_admin')

