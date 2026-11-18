"""Règles métier de BiblioIIT (aucune dépendance à la base ni à l'affichage)."""

import re
import unicodedata
from datetime import date, timedelta
from difflib import SequenceMatcher
from typing import Iterable

DUREE_EMPRUNT_JOURS = 14
SEUIL_CORRESPONDANCE = 0.7


class RegleMetierError(Exception):
    """Levée lorsqu'une règle métier n'est pas respectée."""


def normaliser_texte(texte: str) -> str:
    """Minuscules, sans accents ni ponctuation, pour comparer des titres."""
    texte = unicodedata.normalize("NFD", texte.lower())
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return re.sub(r"[\W_]+", " ", texte).strip()


def score_correspondance(nom: str, titre: str) -> float:
    """Ressemblance entre un nom saisi et un titre (0 à 1). Tolère les fautes et les mots manquants."""
    a, b = normaliser_texte(nom), normaliser_texte(titre)
    if not a or not b:
        return 0.0
    if a in b:
        return 1.0
    mots_titre = b.split()
    par_mot = [max(SequenceMatcher(None, m, t).ratio() for t in mots_titre) for m in a.split()]
    return max(sum(par_mot) / len(par_mot), SequenceMatcher(None, a, b).ratio())


def valider_duree_emprunt(duree_jours: int, autorisees: Iterable[int]) -> int:
    if duree_jours not in tuple(autorisees):
        raise RegleMetierError(f"Période d'emprunt invalide : {duree_jours} jours.")
    return duree_jours


def valider_code_livre(code: str) -> str:
    code = code.strip().upper()
    if not re.match(r"^L\d{3,}$", code):
        raise RegleMetierError(f"Code de livre invalide : « {code} » (ex. L002).")
    return code


def valider_code_emprunt(code: str) -> str:
    code = code.strip().upper()
    if not re.match(r"^EMP-\d{4,}$", code):
        raise RegleMetierError(f"Code d'emprunt invalide : « {code} » (ex. EMP-0001).")
    return code


def calculer_date_retour(date_emprunt: date, duree_jours: int = DUREE_EMPRUNT_JOURS) -> date:
    return date_emprunt + timedelta(days=duree_jours)


def est_en_retard(date_retour_prevue: date, aujourdhui: date) -> bool:
    return aujourdhui > date_retour_prevue


def verifier_emprunt_possible(titre: str, deja_emprunte: bool) -> None:
    if deja_emprunte:
        raise RegleMetierError(f"Le livre « {titre} » est déjà emprunté.")