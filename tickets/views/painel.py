from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from ..forms import CriarUsuarioForm
from ..models import Ticket
from ..permissions import eh_staff


@user_passes_test(eh_staff, login_url='login')
def criar_usuario(request):
    if request.method == 'POST':
        form = CriarUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(
                request,
                f'A conta de {usuario.username} foi criada com sucesso.'
            )
            return redirect('criar_usuario')
    else:
        form = CriarUsuarioForm()

    return render(request, 'registration/criar_usuario.html', {'form': form})



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

    return render(request, 'tickets/painel_admin.html', {
        'chamados': chamados,
        'prontos': prontos,
        'aguardando': aguardando,
    })



@user_passes_test(eh_staff, login_url='login')
@transaction.atomic
def chamar_proximo(request):
    if request.method != 'POST':
        return redirect('painel_admin')

    ticket = Ticket.objects.select_for_update().filter(
        status=Ticket.Status.AGUARDANDO
    ).order_by('criado_em').first()

    if not ticket:
        messages.warning(request, 'Não há ninguém aguardando na fila.')
        return redirect('painel_admin')

    ticket.status = Ticket.Status.CHAMADO
    ticket.chamado_em = timezone.now()
    ticket.save(update_fields=['status', 'chamado_em'])

    messages.success(request, f'Ticket #{ticket.pk} foi chamado.')
    return redirect('painel_admin')



@user_passes_test(eh_staff, login_url='login')
def marcar_pronto(request, ticket_id):
    if request.method != 'POST':
        return redirect('painel_admin')

    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.status != Ticket.Status.CHAMADO:
        messages.error(
            request,
            'Somente tickets chamados podem ser marcados como prontos.'
        )
        return redirect('painel_admin')

    ticket.status = Ticket.Status.PRONTO
    ticket.pronto_em = timezone.now()
    ticket.save(update_fields=['status', 'pronto_em'])

    messages.success(request, f'Ticket #{ticket.pk} marcado como pronto.')
    return redirect('painel_admin')



@user_passes_test(eh_staff, login_url='login')
def marcar_retirado(request, ticket_id):
    if request.method != 'POST':
        return redirect('painel_admin')

    ticket = get_object_or_404(Ticket, pk=ticket_id)

    # Confirma que o ticket está pronto e validado
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
            'Ele precisa estar pronto e ter o QR Code validado.'
        )

    return redirect('painel_admin')

