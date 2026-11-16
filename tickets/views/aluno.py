from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from ..forms import EntrarFilaForm
from ..models import Ticket
from ..services.fila_service import (
    TicketAtivoError,
    ChaveJaUtilizadaError,
    buscar_ticket_ativo,
    criar_ticket,
)


@login_required
def inicio(request):

    # Consulta o serviço para identificar ticket ativo
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
    ticket = Ticket.objects.filter(
        usuario=request.user
    ).exclude(
        status=Ticket.Status.RETIRADO
    ).order_by('-criado_em').first()

    if not ticket:
        return redirect('inicio')

    posicao = ticket.posicao_na_fila()
    pessoas_na_frente = max(posicao - 1, 0) if posicao else None

    return render(request, 'tickets/meu_ticket.html', {
        'ticket': ticket,
        'posicao': posicao,
        'pessoas_na_frente': pessoas_na_frente,
    })



@login_required
def qr_code_ticket(request):
    ticket = Ticket.objects.filter(
        usuario=request.user
    ).exclude(status=Ticket.Status.RETIRADO).order_by('-criado_em').first()

    if not ticket:
        return redirect('inicio')

    validar_url = request.build_absolute_uri(
        reverse('validar_token_qr', args=[ticket.token_qr])
    )

    imagem = qrcode.make(validar_url)
    buffer = BytesIO()
    imagem.save(buffer, format='PNG')

    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response



@login_required
def renovar_qr(request):
    if request.method != 'POST':
        return redirect('meu_ticket')

    ticket = Ticket.objects.filter(
        usuario=request.user
    ).exclude(
        status=Ticket.Status.RETIRADO
    ).order_by('-criado_em').first()

    if not ticket:
        return redirect('inicio')

    # Tenta renovar o QR Code
    renovado = ticket.renovar_qr()

    if renovado:
        messages.success(
            request,
            'QR Code renovado por mais 10 minutos.'
        )
    else:
        messages.error(
            request,
            'Este voucher já foi validado ou retirado. '
            'Não é possível renovar o QR Code.'
        )

    return redirect('meu_ticket')



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
        meu = Ticket.objects.filter(
            usuario=request.user
        ).exclude(status=Ticket.Status.RETIRADO).order_by('-criado_em').first()
        meu_ticket_id = meu.id if meu else None

    return render(request, 'tickets/fila_publica.html', {
        'chamado': chamado,
        'prontos': prontos,
        'aguardando': aguardando,
        'meu_ticket_id': meu_ticket_id,
    })

