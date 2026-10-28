from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('meu-ticket/', views.meu_ticket, name='meu_ticket'),
    path('meu-ticket/qr/', views.qr_code_ticket, name='qr_code_ticket'),
    path('meu-ticket/renovar-qr/', views.renovar_qr, name='renovar_qr'),

    path('fila/', views.fila_publica, name='fila_publica'),

    path('painel/usuarios/criar/', views.criar_usuario, name='criar_usuario'),
    path('painel/', views.painel_admin, name='painel_admin'),
    path('painel/chamar-proximo/', views.chamar_proximo, name='chamar_proximo'),
    path('painel/pronto/<int:ticket_id>/', views.marcar_pronto, name='marcar_pronto'),
    path('painel/retirado/<int:ticket_id>/', views.marcar_retirado, name='marcar_retirado'),

    path('validacao/', views.validacao_qr, name='validacao_qr'),
    path('validar/<uuid:token>/', views.validar_token_qr, name='validar_token_qr'),

    path('relatorios/', views.relatorios, name='relatorios'),
]
