from django.contrib import admin
from .models import Ticket

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
