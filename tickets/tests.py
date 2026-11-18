from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Ticket
from .services.fila_service import (
    TicketAtivoError,
    ChaveJaUtilizadaError,
    criar_ticket,
    FilaAtualizadaError,
    chamar_ticket_aguardando,
    chamar_proximo_ticket,
    marcar_ticket_pronto,
)
from .services.voucher_service import (
    VoucherJaValidadoError,
    VoucherExpiradoError,
    VoucherNaoAutorizadoError,
    VoucherAlteradoError,
    validar_voucher,
)


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


    def test_impede_dois_tickets_ativos(self):
        Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-ativo-001'
        )

        # Tenta criar um segundo ticket ativo
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Ticket.objects.create(
                    usuario=self.aluno,
                    chave_vale='vale-ativo-002'
                )

        self.assertEqual(
            Ticket.objects.filter(
                usuario=self.aluno
            ).count(),
            1
        )


    def test_permite_novo_ticket_apos_retirada(self):
        # Ticket anterior já finalizado
        Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-antigo-001',
            status=Ticket.Status.RETIRADO
        )

        # Aluno entra novamente na fila
        Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-novo-001'
        )

        self.assertEqual(
            Ticket.objects.filter(
                usuario=self.aluno
            ).count(),
            2
        )

        self.assertEqual(
            Ticket.objects.filter(
                usuario=self.aluno
            ).exclude(
                status=Ticket.Status.RETIRADO
            ).count(),
            1
        )


    def test_usuario_nao_entra_duas_vezes_na_fila(self):
        self.client.force_login(self.aluno)

        Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-ativo-003'
        )

        resposta = self.client.post(
            reverse('inicio'),
            {'chave_vale': 'vale-ativo-004'}
        )

        self.assertRedirects(
            resposta,
            reverse('meu_ticket')
        )

        self.assertEqual(
            Ticket.objects.filter(
                usuario=self.aluno
            ).count(),
            1
        )


    def test_servico_cria_ticket(self):
        ticket = criar_ticket(
            usuario=self.aluno,
            chave=' vale-servico-001 '
        )

        self.assertEqual(
            ticket.chave_vale,
            'vale-servico-001'
        )

        self.assertEqual(
            ticket.status,
            Ticket.Status.AGUARDANDO
        )

        self.assertEqual(
            Ticket.objects.filter(
                usuario=self.aluno
            ).count(),
            1
        )


    def test_servico_impede_ticket_ativo(self):
        criar_ticket(
            usuario=self.aluno,
            chave='vale-servico-002'
        )

        with self.assertRaises(TicketAtivoError):
            criar_ticket(
                usuario=self.aluno,
                chave='vale-servico-003'
            )

        self.assertEqual(
            Ticket.objects.filter(
                usuario=self.aluno
            ).count(),
            1
        )


    def test_servico_impede_chave_reutilizada(self):
        outro_aluno = User.objects.create_user(
            username='outro-aluno',
            password='senha-de-teste'
        )

        criar_ticket(
            usuario=self.aluno,
            chave='vale-servico-004'
        )

        with self.assertRaises(ChaveJaUtilizadaError):
            criar_ticket(
                usuario=outro_aluno,
                chave='vale-servico-004'
            )

        self.assertEqual(
            Ticket.objects.filter(
                chave_vale='vale-servico-004'
            ).count(),
            1
        )


    def test_servico_valida_voucher(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-voucher-001',
            status=Ticket.Status.CHAMADO
        )

        resultado = validar_voucher(ticket)

        self.assertTrue(resultado)

        ticket.refresh_from_db()
        self.assertIsNotNone(ticket.qr_validado_em)


    def test_servico_impede_validacao_duplicada(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-voucher-002',
            status=Ticket.Status.PRONTO
        )

        validar_voucher(ticket)
        primeira_validacao = ticket.qr_validado_em

        with self.assertRaises(VoucherJaValidadoError):
            validar_voucher(ticket)

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.qr_validado_em,
            primeira_validacao
        )


    def test_servico_rejeita_voucher_expirado(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-voucher-003',
            status=Ticket.Status.CHAMADO
        )

        Ticket.objects.filter(pk=ticket.pk).update(
            qr_expira_em=timezone.now() - timedelta(minutes=1)
        )

        ticket.refresh_from_db()

        with self.assertRaises(VoucherExpiradoError):
            validar_voucher(ticket)

        ticket.refresh_from_db()
        self.assertIsNone(ticket.qr_validado_em)


    def test_servico_rejeita_ticket_aguardando(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-voucher-004',
            status=Ticket.Status.AGUARDANDO
        )

        with self.assertRaises(VoucherNaoAutorizadoError):
            validar_voucher(ticket)

        ticket.refresh_from_db()
        self.assertIsNone(ticket.qr_validado_em)


    def test_servico_rejeita_token_renovado(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-voucher-005',
            status=Ticket.Status.CHAMADO
        )

        # Outra instância renova o QR no banco
        outro_ticket = Ticket.objects.get(pk=ticket.pk)
        self.assertTrue(outro_ticket.renovar_qr())

        # A instância original mantém o token antigo
        with self.assertRaises(VoucherAlteradoError):
            validar_voucher(ticket)

        ticket.refresh_from_db()
        self.assertIsNone(ticket.qr_validado_em)


    def test_servico_chama_por_ordem_de_chegada(self):
        outro_aluno = User.objects.create_user(
            username='aluno-dois',
            password='senha-de-teste'
        )
        primeiro = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-fila-001'
        )
        segundo = Ticket.objects.create(
            usuario=outro_aluno,
            chave_vale='vale-fila-002'
        )

        self.assertEqual(chamar_proximo_ticket(), primeiro.pk)
        self.assertEqual(chamar_proximo_ticket(), segundo.pk)
        self.assertIsNone(chamar_proximo_ticket())

        primeiro.refresh_from_db()
        segundo.refresh_from_db()
        self.assertEqual(primeiro.status, Ticket.Status.CHAMADO)
        self.assertEqual(segundo.status, Ticket.Status.CHAMADO)
        self.assertIsNotNone(primeiro.chamado_em)
        self.assertIsNotNone(segundo.chamado_em)

    def test_chamada_de_ticket_e_idempotente(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-fila-003'
        )

        self.assertTrue(chamar_ticket_aguardando(ticket.pk))
        ticket.refresh_from_db()
        primeiro_horario = ticket.chamado_em

        self.assertFalse(chamar_ticket_aguardando(ticket.pk))
        ticket.refresh_from_db()
        self.assertEqual(ticket.chamado_em, primeiro_horario)

    def test_marcar_pronto_e_idempotente(self):
        ticket = Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-fila-004',
            status=Ticket.Status.CHAMADO
        )

        self.assertTrue(marcar_ticket_pronto(ticket.pk))
        ticket.refresh_from_db()
        primeiro_horario = ticket.pronto_em

        self.assertFalse(marcar_ticket_pronto(ticket.pk))
        ticket.refresh_from_db()
        self.assertEqual(ticket.pronto_em, primeiro_horario)

    def test_chamada_detecta_fila_alterada(self):
        Ticket.objects.create(
            usuario=self.aluno,
            chave_vale='vale-fila-005'
        )

        with patch(
            'tickets.services.fila_service.chamar_ticket_aguardando',
            return_value=False,
        ):
            with self.assertRaises(FilaAtualizadaError):
                chamar_proximo_ticket()


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

def test_senha_curta_e_rejeitada(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse('criar_usuario'), {
            'username': 'aluno-curta',
            'password1': 'Ab1!',
            'password2': 'Ab1!',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('password2', resposta.context['form'].errors)
        self.assertFalse(User.objects.filter(username='aluno-curta').exists())

    def test_senha_numerica_e_rejeitada(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse('criar_usuario'), {
            'username': 'aluno-numerico',
            'password1': '1234567890',
            'password2': '1234567890',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('password2', resposta.context['form'].errors)
        self.assertFalse(User.objects.filter(username='aluno-numerico').exists())

    def test_senha_comum_e_rejeitada(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse('criar_usuario'), {
            'username': 'aluno-comum',
            'password1': 'password',
            'password2': 'password',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('password2', resposta.context['form'].errors)
        self.assertFalse(User.objects.filter(username='aluno-comum').exists())

    def test_senha_igual_ao_usuario_e_rejeitada(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse('criar_usuario'), {
            'username': 'alunoteste',
            'password1': 'alunoteste',
            'password2': 'alunoteste',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('password2', resposta.context['form'].errors)
        self.assertFalse(User.objects.filter(username='alunoteste').exists())

