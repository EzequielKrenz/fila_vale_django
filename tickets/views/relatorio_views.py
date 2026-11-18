from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render

from ..permissions import eh_staff
from ..services.relatorio_service import calcular_resumo_consumo


@user_passes_test(eh_staff, login_url='login')
def relatorios(request):
    contexto = calcular_resumo_consumo()
    return render(request, 'tickets/relatorios.html', contexto)
