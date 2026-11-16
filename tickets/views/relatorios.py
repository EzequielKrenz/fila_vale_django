from datetime import timedelta

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.utils import timezone

from ..models import Ticket
from ..permissions import eh_staff


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

