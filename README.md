# ValeFila IFC - Django

Sistema de fila para vale-alimentação com autenticação, voucher temporário em QR Code,
validação da refeição, acompanhamento da fila e relatórios gerenciais.

## Requisitos implementados

### RF01 - Autenticação e Perfil
- Login com autenticação nativa do Django.
- Usuários comuns representam alunos.
- Usuários com `is_staff=True` representam gestores/cantina.
- Rotas administrativas são protegidas.

### RF02 - Geração de Voucher
- Após informar a chave primária do vale, o sistema cria um ticket.
- O ticket recebe um token UUID aleatório.
- O sistema gera um QR Code contendo uma URL segura de validação.
- O QR Code expira em 10 minutos e pode ser renovado.

### RF03 - Validação de Refeição
- A cantina pode escanear o QR Code com a câmera normal do celular.
- O QR abre a tela de validação do sistema.
- Somente usuário `staff` pode confirmar o consumo.
- O QR precisa estar válido e o ticket precisa estar CHAMADO ou PRONTO.
- O horário da validação é gravado em `qr_validado_em`.
- O mesmo voucher não pode ser validado duas vezes.

### RF04 - Relatórios Gerenciais
- Painel com consumo:
  - diário;
  - semanal;
  - mensal;
  - últimos 7 dias.
- Os relatórios exibem apenas totais agregados.

## Requisitos não funcionais considerados

### RNF01 - Segurança e Privacidade / LGPD
Implementado no código:
- autenticação Django;
- proteção CSRF em formulários;
- rotas administrativas restritas a `is_staff`;
- QR Code com UUID aleatório;
- QR com expiração;
- validação única;
- tela pública sem nome do aluno;
- relatórios agregados, sem nome ou chave do vale;
- cabeçalho `Cache-Control: no-store` na imagem do QR.

Observação:
Conformidade legal integral com LGPD também depende de políticas organizacionais,
base legal, retenção, consentimento quando aplicável, controle de acesso, HTTPS,
logs, backups e processo de atendimento aos titulares.

### RNF02 - Desempenho
O modelo usa índices nos campos mais consultados (`status`, `token_qr`,
`qr_validado_em`) e a validação é simples e transacional.

O requisito "inferior a 2 segundos" deve ser confirmado por teste de carga no
ambiente de produção. O projeto local, por si só, não pode garantir esse SLA.

### RNF03 - Disponibilidade
A aplicação foi estruturada para funcionar com Django, mas 99,9% de disponibilidade
não pode ser garantido por código local.

Em produção, recomenda-se:
- Gunicorn/Uvicorn;
- Nginx;
- PostgreSQL;
- HTTPS;
- múltiplas instâncias;
- health checks;
- monitoramento;
- backup;
- serviço de nuvem com redundância.

### RNF04 - Usabilidade
- Layout responsivo.
- Meta viewport para celulares.
- Botões grandes.
- Estados visuais simples.
- `alt` no QR Code.
- Funciona em navegadores Android e iOS.

## Fluxo do sistema

Aluno:
1. Faz login.
2. Informa a chave primária do vale.
3. Recebe um ticket.
4. Entra na fila.
5. Visualiza sua posição.
6. Possui um QR Code temporário.
7. Aguarda o sistema chamar.
8. Apresenta o QR Code na cantina.
9. Cantina valida o consumo.
10. Pedido é marcado como pronto e depois retirado.

Gestor/Cantina:
1. Acessa `/painel/`.
2. Visualiza a fila.
3. Clica em "Chamar próximo".
4. Pode marcar ticket como "Pronto".
5. Acessa `/validacao/` para validar QR.
6. Marca como "Retirado" após entrega.
7. Acessa `/relatorios/`.

## Instalação

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

Instale:

```bash
pip install -r requirements.txt
```

Aplique as migrações existentes:

```bash
python manage.py migrate
```

Crie o administrador:

```bash
python manage.py createsuperuser
```

Execute:

```bash
python manage.py runserver
```

## Endereços

- Login: http://127.0.0.1:8000/login/
- Área do aluno: http://127.0.0.1:8000/
- Fila pública: http://127.0.0.1:8000/fila/
- Painel da cantina: http://127.0.0.1:8000/painel/
- Validação QR: http://127.0.0.1:8000/validacao/
- Relatórios: http://127.0.0.1:8000/relatorios/
- Django Admin: http://127.0.0.1:8000/admin/

## Criando alunos e gestores

Um gestor autenticado pode criar contas comuns pelo link **Criar usuário** no menu
do sistema. A tela de login não permite cadastro público.

Para criar gestores ou administrar qualquer conta, use o `/admin/`:

- aluno: usuário comum;
- gestor/cantina: marque `Staff status`.

## Configuração obrigatória do ambiente

Crie `.env` na raiz (usando `.env.example` como referência) e defina
`DJANGO_SECRET_KEY`, `DJANGO_DEBUG` e `DJANGO_ALLOWED_HOSTS`.
Não envie o arquivo `.env` ao GitHub.

Aplique as migrações existentes com `python manage.py migrate`.

## Emissão e validação das chaves de vale

Um administrador precisa **emitir o vale antes de o aluno entrar na fila**:

1. Crie a conta do aluno no Django.
2. Acesse `/admin/` como superusuário.
3. Entre em **Vales emitidos**, clique em adicionar e selecione o aluno.
4. Salve o registro. O sistema gerará uma chave aleatória automaticamente.
5. Entregue a chave ao aluno por um canal apropriado.

O aluno só pode criar um ticket se a chave foi emitida para sua conta,
está ativa e não foi usada antes. Desativar um vale impede novas entradas
com ele; não cancela tickets já emitidos.

**Compatibilidade:** tickets antigos não são apagados nem alterados por
essa migração. Entretanto, chaves antigas ainda não utilizadas precisam
ser cadastradas no sistema de emissão antes de serem aceitas.

Esta é uma emissão local pelo Django Admin, **sem integração automática**
com o sistema externo de vale-alimentação. Para uso institucional, será
necessário alinhar a origem e a importação dos vales reais.
