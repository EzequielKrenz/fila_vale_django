from django.urls import path

from .views import (
    usuario_views,
    fila_views,
    voucher_views,
    relatorio_views,
)


urlpatterns = [
    # Aluno
    path(
        '',
        fila_views.inicio,
        name='inicio'
    ),

    path(
        'meu-ticket/',
        fila_views.meu_ticket,
        name='meu_ticket'
    ),

    path(
        'meu-ticket/qr/',
        voucher_views.qr_code_ticket,
        name='qr_code_ticket'
    ),

    path(
        'meu-ticket/renovar-qr/',
        voucher_views.renovar_qr,
        name='renovar_qr'
    ),

    # Fila pública
    path(
        'fila/',
        fila_views.fila_publica,
        name='fila_publica'
    ),

    # Administração
    path(
        'painel/usuarios/criar/',
        usuario_views.criar_usuario,
        name='criar_usuario'
    ),

    path(
        'painel/',
        fila_views.painel_admin,
        name='painel_admin'
    ),

    path(
        'painel/chamar-proximo/',
        fila_views.chamar_proximo,
        name='chamar_proximo'
    ),

    path(
        'painel/pronto/<int:ticket_id>/',
        fila_views.marcar_pronto,
        name='marcar_pronto'
    ),

    path(
        'painel/retirado/<int:ticket_id>/',
        fila_views.marcar_retirado,
        name='marcar_retirado'
    ),

    # Validação de QR Code
    path(
        'validacao/',
        voucher_views.validacao_qr,
        name='validacao_qr'
    ),

    path(
        'validar/<uuid:token>/',
        voucher_views.validar_token_qr,
        name='validar_token_qr'
    ),

    # Relatórios
    path(
        'relatorios/',
        relatorio_views.relatorios,
        name='relatorios'
    ),
]
