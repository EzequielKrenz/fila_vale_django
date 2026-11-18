"""Cálculos dos relatórios conforme o fuso horário do projeto."""

from datetime import datetime, time, timedelta

from django.utils import timezone

from ..models import Ticket


def _inicio_do_dia(data, fuso):
    """Retorna a meia-noite local como datetime com fuso."""
    return timezone.make_aware(
        datetime.combine(data, time.min),
        fuso,
    )


def calcular_resumo_consumo(agora=None):
    """
    Conta refeições validadas até 'agora', considerando o dia,
    a semana (segunda a domingo), o mês e os últimos sete
    dias no fuso horário configurado no Django.
    """
    if agora is None:
        agora = timezone.now()

    fuso = timezone.get_default_timezone()
    hoje = timezone.localtime(agora, fuso).date()
    inicio_semana_data = hoje - timedelta(days=hoje.weekday())
    inicio_mes_data = hoje.replace(day=1)

    # Garante que validações futuras não entrem nos indicadores.
    consumos = Ticket.objects.filter(
        qr_validado_em__isnull=False,
        qr_validado_em__lte=agora,
    )

    diario = consumos.filter(
        qr_validado_em__gte=_inicio_do_dia(hoje, fuso),
    ).count()

    semanal = consumos.filter(
        qr_validado_em__gte=_inicio_do_dia(inicio_semana_data, fuso),
    ).count()

    mensal = consumos.filter(
        qr_validado_em__gte=_inicio_do_dia(inicio_mes_data, fuso),
    ).count()

    ultimos_7 = []
    for dias in range(6, -1, -1):
        dia = hoje - timedelta(days=dias)
        proximo_dia = dia + timedelta(days=1)

        total = consumos.filter(
            qr_validado_em__gte=_inicio_do_dia(dia, fuso),
            qr_validado_em__lt=_inicio_do_dia(proximo_dia, fuso),
        ).count()

        ultimos_7.append({
            'dia': dia.strftime('%d/%m'),
            'total': total,
        })

    return {
        'diario': diario,
        'semanal': semanal,
        'mensal': mensal,
        'ultimos_7': ultimos_7,
    }
