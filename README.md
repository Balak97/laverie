# Dortoir 3 – Projet Django

Application web du **Dortoir 3** : laverie (réservation des machines à laver en ligne), comptes utilisateurs et messagerie.

## Démarrage

```bash
# Créer un environnement virtuel (recommandé)
python -m venv .venv
.venv\Scripts\activate   # Windows

# Installer les dépendances
pip install django djangorestframework

# Migrations
python manage.py migrate

# Créer un superutilisateur (optionnel)
python manage.py createsuperuser

# Lancer le serveur
python manage.py runserver
```

Ouvrir **http://127.0.0.1:8000/**.

- **/** → Accueil Dortoir 3
- **/laverie/** → Réservation des machines à laver
- **/accounts/login/** → Connexion
- **/admin/** → Interface d’administration Django

## Structure

- **config/** – Paramètres du projet (settings, urls, wsgi, asgi)
- **comptes/** – Authentification, profils, dashboards
- **laverie/** – Salle à laver (machines, programmes, réservations)
- **chat/** – Messagerie
- **templates/** – Templates globaux

## Variables d’environnement (optionnel)

- `DJANGO_SECRET_KEY` – Clé secrète (sinon valeur de dev)
- `DJANGO_DEBUG=0` – Désactiver le mode debug
- `ALLOWED_HOSTS=example.com,www.example.com`
