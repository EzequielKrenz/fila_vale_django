from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect

from ..forms import CriarUsuarioForm
from ..permissions import eh_staff


@user_passes_test(eh_staff, login_url='login')
def criar_usuario(request):
    if request.method == 'POST':
        form = CriarUsuarioForm(request.POST)

        if form.is_valid():
            usuario = form.save()

            messages.success(
                request,
                f'A conta de {usuario.username} '
                'foi criada com sucesso.'
            )

            return redirect('criar_usuario')

    else:
        form = CriarUsuarioForm()

    return render(
        request,
        'registration/criar_usuario.html',
        {'form': form}
    )
