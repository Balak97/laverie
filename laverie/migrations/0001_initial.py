# Generated manually for laverie app

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
            name='Machine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(help_text="Ex: Machine 1, Lave-linge A", max_length=100)),
                ('ordre', models.PositiveSmallIntegerField(default=0, help_text="Ordre d'affichage")),
                ('active', models.BooleanField(default=True)),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['ordre', 'nom'],
            },
        ),
        migrations.CreateModel(
            name='FonctionMachine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(help_text='Ex: Coton, Jeans, Délicat', max_length=80)),
                ('duree_minutes', models.PositiveIntegerField(help_text='Durée du cycle en minutes')),
                ('ordre', models.PositiveSmallIntegerField(default=0)),
                ('active', models.BooleanField(default=True)),
                ('machine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fonctions', to='laverie.machine')),
            ],
            options={
                'ordering': ['machine', 'ordre', 'nom'],
                'unique_together': {('machine', 'nom')},
            },
        ),
        migrations.CreateModel(
            name='Reservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('debut', models.DateTimeField()),
                ('fin', models.DateTimeField()),
                ('statut', models.CharField(choices=[('reserve', 'Réservé'), ('en_cours', 'En cours'), ('termine', 'Terminé'), ('annule', 'Annulé')], default='reserve', max_length=20)),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('fonction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reservations', to='laverie.fonctionmachine')),
                ('machine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservations', to='laverie.machine')),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservations_laverie', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-debut'],
            },
        ),
    ]
