from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Livre:
    code: str
    titre: str
    auteur: str
    annee: int  # 0 = année inconnue


@dataclass(frozen=True)
class LivreEnLigne:
    """Titre trouvé sur un catalogue externe, avant son enregistrement en base."""

    titre: str
    auteur: str
    annee: Optional[int] = None


@dataclass
class Emprunt:
    id: Optional[int]
    code_livre: str
    date_emprunt: date
    date_retour_prevue: date
    date_retour_effective: Optional[date] = None
    code: Optional[str] = None  # code d'emprunt généré, ex. EMP-0001

    @property
    def en_cours(self) -> bool:
        return self.date_retour_effective is None