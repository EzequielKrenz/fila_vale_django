from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404

from ..forms import ValidarQRForm
from ..models import Ticket
from ..permissions import eh_staff
from ..services.voucher_service import VoucherError, validar_voucher


@user_passes_test(eh_staff, login_url='login')
def validacao_qr(request):
    form = ValidarQRForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        return redirect('validar_token_qr', token=form.cleaned_data['token'])

    return render(request, 'tickets/validacao_qr.html', {'form': form})



@user_passes_test(eh_staff, login_url='login')
def validar_token_qr(request, token):

    ticket = get_object_or_404(
        Ticket,
        token_qr=token
    )

    if request.method == 'POST':
        try:
            # Serviço aplica as regras de negócio
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

