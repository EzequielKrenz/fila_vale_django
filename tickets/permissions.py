def eh_staff(user):
    """Verifica se o usuário é um funcionário autenticado."""
    return user.is_authenticated and user.is_staff
