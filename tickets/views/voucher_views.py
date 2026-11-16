from io import BytesIO

import qrcode

from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.http import HttpResponse
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.urls import reverse

from ..forms import ValidarQRForm
from ..models import Ticket
from ..permissions import eh_staff
from ..services.fila_service import buscar_ticket_ativo
from ..services.voucher_service import (
    VoucherError,
    validar_voucher,
)


@login_required
def qr_code_ticket(request):
    ticket = buscar_ticket_ativo(request.user)

    if not ticket:
        return redirect('inicio')

    validar_url = request.build_absolute_uri(
        reverse(
            'validar_token_qr',
            args=[ticket.token_qr]
        )
    )

    imagem = qrcode.make(validar_url)
    buffer = BytesIO()
    imagem.save(buffer, format='PNG')

    response = HttpResponse(
        buffer.getvalue(),
        content_type='image/png'
    )

    response['Cache-Control'] = (
        'no-store, no-cache, '
        'must-revalidate, max-age=0'
    )

    return response


@login_required
def renovar_qr(request):
    if request.method != 'POST':
        return redirect('meu_ticket')

    ticket = buscar_ticket_ativo(request.user)

    if not ticket:
        return redirect('inicio')

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


@user_passes_test(eh_staff, login_url='login')
def validacao_qr(request):
    form = ValidarQRForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        return redirect(
            'validar_token_qr',
            token=form.cleaned_data['token']
        )

    return render(
        request,
        'tickets/validacao_qr.html',
        {'form': form}
    )


@user_passes_test(eh_staff, login_url='login')
def validar_token_qr(request, token):
    ticket = get_object_or_404(
        Ticket,
        token_qr=token
    )

    if request.method == 'POST':
        try:
            validar_voucher(ticket)

        except VoucherError as erro:
            messages.error(
                request,
                str(erro)
            )

        else:
            messages.success(
                request,
                f'Refeição do ticket #{ticket.pk} '
                'validada com sucesso.'
            )

            return redirect('validacao_qr')

    return render(
        request,
        'tickets/confirmar_validacao.html',
        {'ticket': ticket}
    )
