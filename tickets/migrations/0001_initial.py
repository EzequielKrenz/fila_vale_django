from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chave_vale', models.CharField(max_length=50, unique=True, verbose_name='Chave primária do vale')),
                ('token_qr', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('qr_expira_em', models.DateTimeField(blank=True, null=True)),
                ('qr_validado_em', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('AGUARDANDO', 'Aguardando'), ('CHAMADO', 'Chamado'), ('PRONTO', 'Pronto'), ('RETIRADO', 'Retirado')], default='AGUARDANDO', max_length=15)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('chamado_em', models.DateTimeField(blank=True, null=True)),
                ('pronto_em', models.DateTimeField(blank=True, null=True)),
                ('retirado_em', models.DateTimeField(blank=True, null=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['criado_em']},
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['status', 'criado_em'], name='ticket_status_criado_idx'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['token_qr'], name='ticket_token_qr_idx'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['qr_validado_em'], name='ticket_qr_valid_idx'),
        ),
    ]
