from django.contrib import admin
from .models import Ticket, ValeEmitido

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'usuario',
        'status',
        'criado_em',
        'chamado_em',
        'pronto_em',
        'qr_validado_em',
        'retirado_em',
    )
    list_filter = ('status', 'criado_em', 'qr_validado_em')
    search_fields = ('usuario__username', 'chave_vale')
    readonly_fields = ('token_qr', 'qr_expira_em', 'qr_validado_em')


@admin.register(ValeEmitido)
class ValeEmitidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'aluno', 'chave', 'ativo', 'emitido_em')
    list_filter = ('ativo', 'emitido_em')
    search_fields = ('aluno__username', 'chave')
    readonly_fields = ('chave', 'emitido_em')
    list_select_related = ('aluno',)
