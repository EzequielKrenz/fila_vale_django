from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Ticket


class TicketWorkflowTests(TestCase):
    def setUp(self):
        self.aluno = User.objects.create_user(
            username='aluno',
            password='senha-de-teste'
        )
        self.gestor = User.objects.create_user(
            username='gestor',
            password='senha-de-teste',
            is_staff=True
        )

    def test_ticket_and_qr_validation_workflow(self):
        self.client.login(username='aluno', password='senha-de-teste')

        response = self.client.get(reverse('inicio'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('inicio'),
            {'chave_vale': 'vale-teste-001'}
        )
        self.assertRedirects(response, reverse('meu_ticket'))

        ticket = Ticket.objects.get(chave_vale='vale-teste-001')
        response = self.client.get(reverse('qr_code_ticket'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertIn('no-store', response['Cache-Control'])

        self.client.logout()
        self.client.login(username='gestor', password='senha-de-teste')

        self.client.post(reverse('chamar_proximo'))
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.CHAMADO)

        self.client.post(
            reverse('marcar_pronto', args=[ticket.pk])
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.PRONTO)

        validar_url = reverse(
            'validar_token_qr',
            args=[ticket.token_qr]
        )
        response = self.client.get(validar_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(validar_url)
        self.assertRedirects(response, reverse('validacao_qr'))
        ticket.refresh_from_db()
        primeira_validacao = ticket.qr_validado_em
        self.assertIsNotNone(primeira_validacao)

        response = self.client.post(validar_url)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.qr_validado_em, primeira_validacao)

        response = self.client.get(reverse('relatorios'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['diario'], 1)


    def test_qr_validado_nao_pode_ser_renovado(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-seguranca-001',
            status=Ticket.Status.CHAMADO
        )

        token_original = ticket.token_qr

        # Funcionário valida o voucher
        self.client.force_login(self.gestor)

        resposta = self.client.post(
            reverse('validar_token_qr', args=[token_original])
        )
        self.assertEqual(resposta.status_code, 302)

        ticket.refresh_from_db()
        data_validacao = ticket.qr_validado_em
        self.assertIsNotNone(data_validacao)

        # Aluno tenta renovar o QR já utilizado
        self.client.force_login(self.aluno)

        resposta = self.client.post(reverse('renovar_qr'))
        self.assertRedirects(resposta, reverse('meu_ticket'))

        ticket.refresh_from_db()

        # Não pode alterar nem o token nem a validação
        self.assertEqual(ticket.token_qr, token_original)
        self.assertEqual(ticket.qr_validado_em, data_validacao)


    def test_qr_antigo_nao_funciona_apos_renovacao(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-seguranca-002',
            status=Ticket.Status.CHAMADO
        )

        token_antigo = ticket.token_qr

        # Aluno renova o voucher ainda não utilizado
        self.client.force_login(self.aluno)

        resposta = self.client.post(reverse('renovar_qr'))
        self.assertRedirects(resposta, reverse('meu_ticket'))

        ticket.refresh_from_db()
        self.assertNotEqual(ticket.token_qr, token_antigo)

        # Funcionário tenta usar o QR anterior
        self.client.force_login(self.gestor)

        resposta = self.client.post(
            reverse('validar_token_qr', args=[token_antigo])
        )

        # Token antigo não existe mais
        self.assertEqual(resposta.status_code, 404)

        ticket.refresh_from_db()
        self.assertIsNone(ticket.qr_validado_em)

        # O novo QR continua funcionando
        resposta = self.client.post(
            reverse('validar_token_qr', args=[ticket.token_qr])
        )

        self.assertRedirects(resposta, reverse('validacao_qr'))

        ticket.refresh_from_db()
        self.assertIsNotNone(ticket.qr_validado_em)


    def test_nao_retirar_sem_validacao(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-retirada-001',
            status=Ticket.Status.PRONTO
        )

        self.client.force_login(self.gestor)

        self.client.post(
            reverse('marcar_retirado', args=[ticket.pk])
        )

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.status,
            Ticket.Status.PRONTO
        )
        self.assertIsNone(ticket.retirado_em)


    def test_retirar_apos_validacao(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-retirada-002',
            status=Ticket.Status.PRONTO
        )

        self.client.force_login(self.gestor)

        # Valida o QR Code
        self.client.post(
            reverse('validar_token_qr', args=[ticket.token_qr])
        )

        # Registra a retirada
        self.client.post(
            reverse('marcar_retirado', args=[ticket.pk])
        )

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.status,
            Ticket.Status.RETIRADO
        )
        self.assertIsNotNone(ticket.retirado_em)

        # Tenta retirar novamente
        primeira_retirada = ticket.retirado_em

        self.client.post(
            reverse('marcar_retirado', args=[ticket.pk])
        )

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.retirado_em,
            primeira_retirada
        )


class CriarUsuarioTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='senha-de-teste',
            is_staff=True
        )

    def test_staff_can_create_regular_user(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse('criar_usuario'), {
            'username': 'novo-aluno',
            'password1': 'Senha-forte-987!',
            'password2': 'Senha-forte-987!',
        })

        self.assertRedirects(response, reverse('criar_usuario'))
        usuario = User.objects.get(username='novo-aluno')
        self.assertFalse(usuario.is_staff)
        self.assertTrue(usuario.check_password('Senha-forte-987!'))

    def test_non_staff_cannot_create_users(self):
        aluno = User.objects.create_user(
            username='aluno',
            password='senha-de-teste'
        )
        self.client.force_login(aluno)

        response = self.client.get(reverse('criar_usuario'))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('criar_usuario')}"
        )
        self.assertFalse(User.objects.filter(username='novo-aluno').exists())

    def test_login_page_explains_account_creation(self):
        response = self.client.get(reverse('login'))

        self.assertContains(
            response,
            'Solicite a criação ao administrador do sistema.'
        )
