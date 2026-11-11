from io import BytesIO
from datetime import timedelta

import qrcode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from .forms import CriarUsuarioForm, EntrarFilaForm, ValidarQRForm
from .models import Ticket


def eh_staff(user):
    return user.is_authenticated and user.is_staff


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


@login_required
def inicio(request):
    # Verifica se o aluno já possui um ticket ativo
    ticket_ativo = Ticket.objects.filter(
        usuario=request.user
    ).exclude(
        status=Ticket.Status.RETIRADO
    ).order_by('-criado_em').first()

    if ticket_ativo:
        return redirect('meu_ticket')

    if request.method == 'POST':
        form = EntrarFilaForm(request.POST)

        if form.is_valid():
            chave = form.cleaned_data['chave_vale'].strip()

            # Verificação antecipada para melhorar
            # a experiência do usuário
            if Ticket.objects.filter(
                chave_vale=chave
            ).exists():
                messages.error(
                    request,
                    'Essa chave já foi utilizada ou já está na fila.'
                )
            else:
                try:
                    with transaction.atomic():
                        ticket = Ticket.objects.create(
                            usuario=request.user,
                            chave_vale=chave
                        )

                except IntegrityError:
                    # Outra requisição pode ter criado
                    # um ticket para este aluno
                    possui_ativo = Ticket.objects.filter(
                        usuario=request.user
                    ).exclude(
                        status=Ticket.Status.RETIRADO
                    ).exists()

                    if possui_ativo:
                        messages.warning(
                            request,
                            'Você já possui um ticket ativo.'
                        )
                        return redirect('meu_ticket')

                    # A chave pode ter sido usada
                    # por outra requisição
                    if Ticket.objects.filter(
                        chave_vale=chave
                    ).exists():
                        messages.error(
                            request,
                            'Essa chave já foi utilizada '
                            'ou já está na fila.'
                        )
                    else:
                        # Não esconder outros erros do banco
                        raise

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
        agora = timezone.now()

        # Só valida se todas as condições forem atendidas
        atualizados = Ticket.objects.filter(
            pk=ticket.pk,
            token_qr=token,
            qr_validado_em__isnull=True,
            qr_expira_em__gte=agora,
            status__in=[
                Ticket.Status.CHAMADO,
                Ticket.Status.PRONTO
            ]
        ).update(
            qr_validado_em=agora
        )

        if atualizados == 1:
            messages.success(
                request,
                f'Refeição do ticket #{ticket.pk} '
                'validada com sucesso.'
            )
            return redirect('validacao_qr')

        # Busca novamente o estado real do banco
        ticket.refresh_from_db()

        if ticket.token_qr != token:
            messages.error(
                request,
                'Este QR Code foi substituído por outro.'
            )
        elif ticket.qr_validado_em is not None:
            messages.error(
                request,
                'Este QR Code já foi validado.'
            )
        elif (
            ticket.qr_expira_em is None
            or ticket.qr_expira_em < agora
        ):
            messages.error(
                request,
                'QR Code expirado. O aluno deve renová-lo.'
            )
        else:
            messages.error(
                request,
                'O ticket precisa estar chamado ou pronto '
                'para permitir a validação.'
            )

    return render(
        request,
        'tickets/confirmar_validacao.html',
        {'ticket': ticket}
    )


@user_passes_test(eh_staff, login_url='login')
def relatorios(request):
    agora = timezone.now()
    inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_semana = inicio_dia - timedelta(days=inicio_dia.weekday())
    inicio_mes = inicio_dia.replace(day=1)

    consumos = Ticket.objects.filter(qr_validado_em__isnull=False)

    diario = consumos.filter(qr_validado_em__gte=inicio_dia).count()
    semanal = consumos.filter(qr_validado_em__gte=inicio_semana).count()
    mensal = consumos.filter(qr_validado_em__gte=inicio_mes).count()

    ultimos_7 = []
    for dias in range(6, -1, -1):
        dia = inicio_dia - timedelta(days=dias)
        proximo = dia + timedelta(days=1)
        qtd = consumos.filter(
            qr_validado_em__gte=dia,
            qr_validado_em__lt=proximo
        ).count()
        ultimos_7.append({
            'dia': dia.strftime('%d/%m'),
            'total': qtd
        })

    return render(request, 'tickets/relatorios.html', {
        'diario': diario,
        'semanal': semanal,
        'mensal': mensal,
        'ultimos_7': ultimos_7,
    })
