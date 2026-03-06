# Application Laverie (salle à laver du dortoir)

Réservation en ligne des machines à laver : les étudiants prennent un ticket sans descendre ; les agents (administration) gèrent les machines et leurs programmes.

## Installation

1. **Ajouter l’app dans les settings**  
   Dans le fichier `settings.py` du projet Django, ajoutez `'laverie'` dans `INSTALLED_APPS` :

   ```python
   INSTALLED_APPS = [
       # ...
       'comptes',
       'monkilo',
       'chat',
       'laverie',  # ← ajouter ici
   ]
   ```

2. **URLs**  
   Les URLs sont déjà incluses dans `comptes/urls.py` sous le préfixe `/laverie/`.

3. **Migrations**  
   Exécutez :

   ```bash
   python manage.py makemigrations laverie
   python manage.py migrate
   ```

4. **Données de test (optionnel)**  
   Depuis le shell Django ou l’admin, créez quelques machines et fonctions (ex. Machine 1 : Coton 90 min, Jeans 60 min, Délicat 45 min).

## Rôles

- **Étudiants** (utilisateurs connectés, ex. `user_type == 'client'`)  
  - Voir les machines et leurs programmes (nom + durée).  
  - Prendre un ticket : choisir machine, programme, créneau (date/heure de début).  
  - Voir et annuler leurs réservations.

- **Agents** (`user_type == 'ADMIN'`)  
  - Tout ce que font les étudiants.  
  - Ajouter / modifier des **machines**.  
  - Ajouter / modifier des **fonctions** (programmes) par machine, avec durée en minutes.

## URLs principales

| URL | Description |
|-----|-------------|
| `/laverie/` | Accueil : liste des machines et liens « Prendre un ticket » / « Mes tickets » |
| `/laverie/reserver/` | Formulaire de réservation (machine, programme, créneau) |
| `/laverie/mes-tickets/` | Liste des réservations de l’utilisateur |
| `/laverie/agent/machines/` | Gestion des machines (agents) |
| `/laverie/agent/machines/ajout/` | Ajouter une machine |
| `/laverie/agent/fonctions/ajout/` | Ajouter une fonction à une machine |

## Modèles

- **Machine** : nom, ordre, active.
- **FonctionMachine** : machine, nom (ex. Coton, Jeans), durée en minutes, ordre, active.
- **Reservation** : utilisateur, machine, fonction, début, fin, statut (réservé, en cours, terminé, annulé).

Les créneaux sont calculés à partir de la date/heure de début et de la durée de la fonction ; les chevauchements sur une même machine sont interdits.
