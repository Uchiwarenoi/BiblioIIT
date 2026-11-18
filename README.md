# BiblioIIT : gestion de la bibliothèque

Application console en Python (architecture MVC), base SQLite.

## Structure

```
main.py
requirements.txt
biblioiit/
├── config.py             # Réglages (nombre de livres en ligne, périodes d'emprunt)
├── models/
│   ├── modeles.py        # Entités : Livre, Etudiant, Emprunt
│   └── regles.py         # Règles métier (périodes, validation, ressemblance des titres)
├── views/
│   └── console.py        # Menu et saisies console
├── controllers/
│   └── service.py        # Orchestration règles + dépôt
└── database/
    ├── depot_sqlite.py   # Persistance SQLite
    ├── source_externe.py # Recherche de titres sur Open Library
    └── biblioiit.db      # Créé au premier lancement
```

## Installation

Il faut Python 3.8 ou plus récent. Vérifie avec `python --version` (Windows) ou `python3 --version` (Mac).
Les commandes se tapent dans un terminal ouvert dans le dossier du projet (celui qui contient `main.py`).

### Windows

```
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

- Dans PowerShell, si l'activation est bloquée (« l'exécution de scripts est désactivée »), tape d'abord
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`, puis `.venv\Scripts\Activate.ps1`.
- Si `py` n'est pas reconnu, installe Python depuis python.org en cochant « Add python.exe to PATH ».

### Mac

```
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python main.py
```

- Si `python3` n'existe pas, installe Python depuis python.org ou avec `brew install python`.

Dans les deux cas, `(.venv)` apparaît au début de la ligne du terminal quand l'environnement est actif.
Pour le quitter : `deactivate`. Aux lancements suivants, il suffit de l'activer à nouveau puis de taper `python main.py`.

`requirements.txt` est vide pour l'instant : le projet n'utilise que la bibliothèque standard de Python.

## Fonctionnement

- **Rechercher :** le mot-clé est cherché dans les titres. Affiche les livres de la bibliothèque, puis ceux trouvés en ligne (Open Library). Les livres trouvés en ligne sont enregistrés automatiquement dans la base, avec un code généré (L005, L006...). Sans Internet, un message indique la cause et la recherche locale continue de fonctionner.
- **Emprunter :** demande le nom du livre et affiche la liste des livres dont le titre y ressemble (fautes tolérées, `[déjà emprunté]` signalé). On choisit par numéro ; `0` lance la recherche en ligne. Puis on choisit la période (7, 14, 21 ou 30 jours, réglable dans `config.py`) : la date d'emprunt est celle du jour et la date de retour est calculée. Un code d'emprunt est généré (EMP-0001...).
- **Rendre :** demande le code d'emprunt (EMP-0001) ou le code du livre (L002).
- **Livres empruntés :** liste les emprunts en cours avec leur code d'emprunt et le code du livre. Un livre rendu disparaît de la liste.
- **Retards :** liste les emprunts en cours dont la date de retour est dépassée, avec leur code d'emprunt.
- **Réglages :** `biblioiit/config.py` permet de choisir le nombre de livres récupérés en ligne (5, 10, 20...), les périodes d'emprunt proposées et le délai d'attente du site.

## Branches (travail d'équipe)

`feature/regles` (A), `feature/modeles` (B), `feature/base` (C), `feature/service` (D), `feature/menu` (E).
