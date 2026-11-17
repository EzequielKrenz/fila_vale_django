from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import tickets.models


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0002_ticket_ticket_unico_ativo_usuario'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ValeEmitido',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'chave',
                    models.CharField(
                        default=tickets.models.gerar_chave_vale,
                        editable=False,
                        max_length=50,
                        unique=True,
                    ),
                ),
                ('ativo', models.BooleanField(default=True)),
                ('emitido_em', models.DateTimeField(auto_now_add=True)),
                (
                    'aluno',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='vales_emitidos',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={'ordering': ['-emitido_em']},
        ),
    ]
