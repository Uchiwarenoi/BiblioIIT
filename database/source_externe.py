
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import List

import config
from models.modeles import LivreEnLigne

URL_RECHERCHE = "https://openlibrary.org/search.json"


class SourceExterneError(Exception):
    """Levée quand le catalogue en ligne est injoignable ou répond mal."""


class SourceOpenLibrary:
    def __init__(
        self,
        limite: int = config.NOMBRE_LIVRES_EN_LIGNE,
        delai: float = config.DELAI_RECHERCHE_EN_LIGNE,
    ):
        self._limite = min(max(1, int(limite)), 100)
        self._delai = delai

    def rechercher(self, mot_cle: str) -> List[LivreEnLigne]:
        params = urllib.parse.urlencode(
            {"title": mot_cle, "limit": self._limite, "fields": "title,author_name,first_publish_year"}
        )
        requete = urllib.request.Request(
            f"{URL_RECHERCHE}?{params}",
            headers={"User-Agent": "BiblioIIT/1.0 (projet etudiant)"},
        )
        try:
            with urllib.request.urlopen(requete, timeout=self._delai) as reponse:
                donnees = json.load(reponse)
        except urllib.error.HTTPError as err:
            raise SourceExterneError(f"le site a répondu HTTP {err.code}") from err
        except urllib.error.URLError as err:
            raise SourceExterneError(f"connexion impossible ({err.reason})") from err
        except TimeoutError as err:
            raise SourceExterneError(f"délai de {self._delai:g} s dépassé") from err
        except (OSError, ValueError) as err:
            raise SourceExterneError(f"réponse illisible ({err})") from err
        return [self._vers_livre(d) for d in donnees.get("docs", []) if d.get("title")]

    @staticmethod
    def _vers_livre(doc: dict) -> LivreEnLigne:
        auteurs = doc.get("author_name") or []
        return LivreEnLigne(
            titre=doc["title"],
            auteur=", ".join(auteurs[:2]) or "Auteur inconnu",
            annee=doc.get("first_publish_year"),
        )
