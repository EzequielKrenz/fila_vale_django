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

Crie as migrações:

```bash
python manage.py makemigrations
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

## Observação sobre a chave primária

Neste protótipo, a chave informada pelo aluno é tratada como identificador único
do vale e não pode ser reutilizada.

Em uma implantação real, o ideal é ter uma tabela de vales previamente emitidos
e validar se a chave existe, pertence ao aluno e ainda não foi consumida.
