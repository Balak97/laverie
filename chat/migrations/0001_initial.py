# Generated for chat app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('participant1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations_as_p1', to=settings.AUTH_USER_MODEL)),
                ('participant2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations_as_p2', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date_creation'],
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contenu', models.TextField(blank=True)),
                ('lu', models.BooleanField(default=False)),
                ('date_envoi', models.DateTimeField(auto_now_add=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chat.conversation')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['date_envoi'],
            },
        ),
    ]
