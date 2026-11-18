from datetime import date
from typing import List, Optional, Tuple

import config
from database.depot_sqlite import DepotSQLite
from database.source_externe import SourceExterneError
from models import regles
from models.modeles import Emprunt, Livre
from models.regles import RegleMetierError


class BibliothequeService:
    def __init__(self, depot: DepotSQLite, source=None):
        self._depot = depot
        self._source = source

    def rechercher(self, mot_cle: str) -> List[Livre]:
        return self._depot.rechercher_livres(mot_cle)

    def rechercher_en_ligne(self, mot_cle: str) -> List[Livre]:
        if self._source is None:
            return []
        try:
            trouves = self._source.rechercher(mot_cle)
        except SourceExterneError as err:
            raise RegleMetierError(
                f"Catalogue en ligne indisponible : {err}. Vérifie ta connexion Internet."
            ) from err
        livres = {}
        for t in trouves:
            livre = self._depot.obtenir_ou_creer_livre(t.titre, t.auteur, t.annee)
            livres[livre.code] = livre
        return list(livres.values())

    def livres_proches(self, nom: str) -> List[Livre]:
        """Livres de la bibliothèque dont le titre ressemble au nom saisi, du plus proche au moins proche."""
        nom = nom.strip()
        if not nom:
            raise RegleMetierError("Saisis le nom du livre.")
        notes = [(regles.score_correspondance(nom, l.titre), l) for l in self._depot.lister_livres()]
        retenus = [(s, l) for s, l in notes if s >= regles.SEUIL_CORRESPONDANCE]
        retenus.sort(key=lambda sl: (-sl[0], sl[1].code))
        return [l for _, l in retenus]

    def livres_proches_en_ligne(self, nom: str) -> List[Livre]:
        """Comme livres_proches, complétés par les livres trouvés en ligne (enregistrés au passage)."""
        locaux = self.livres_proches(nom)
        codes = {l.code for l in locaux}
        return locaux + [l for l in self.rechercher_en_ligne(nom) if l.code not in codes]

    def est_emprunte(self, code_livre: str) -> bool:
        return self._depot.emprunt_en_cours_du_livre(code_livre) is not None

    def verifier_livre_libre(self, livre: Livre) -> None:
        regles.verifier_emprunt_possible(livre.titre, self.est_emprunte(livre.code))

    def periodes_proposees(self) -> List[int]:
        return list(config.PERIODES_EMPRUNT_JOURS)

    def periodes_avec_retour(self, aujourdhui: Optional[date] = None) -> List[Tuple[int, date]]:
        """Chaque période proposée avec la date de retour qu'elle donnerait si on emprunte aujourd'hui."""
        aujourdhui = aujourdhui or date.today()
        return [(j, regles.calculer_date_retour(aujourdhui, j)) for j in self.periodes_proposees()]

    def emprunter(
        self, code_livre: str, duree_jours: int, aujourdhui: Optional[date] = None
    ) -> Emprunt:
        """Enregistre l'emprunt (date d'emprunt = aujourd'hui) et lui génère un code (EMP-0001...)."""
        date_emprunt = aujourdhui or date.today()
        duree_jours = regles.valider_duree_emprunt(duree_jours, self.periodes_proposees())
        code = regles.valider_code_livre(code_livre)
        livre = self._depot.obtenir_livre(code)
        if livre is None:
            raise RegleMetierError(f"Livre introuvable : {code}.")
        regles.verifier_emprunt_possible(
            livre.titre, self._depot.emprunt_en_cours_du_livre(code) is not None
        )
        emprunt = Emprunt(
            id=None,
            code=self._depot.prochain_code_emprunt(),
            code_livre=code,
            date_emprunt=date_emprunt,
            date_retour_prevue=regles.calculer_date_retour(date_emprunt, duree_jours),
        )
        return self._depot.enregistrer_emprunt(emprunt)

    def rendre(self, code: str, aujourdhui: Optional[date] = None) -> Tuple[Emprunt, bool]:
        """Rend un livre à partir du code d'emprunt (EMP-0001) ou du code du livre (L002).

        Retourne (emprunt clôturé, en_retard)."""
        aujourdhui = aujourdhui or date.today()
        if code.strip().upper().startswith("EMP"):
            code = regles.valider_code_emprunt(code)
            emprunt = self._depot.emprunt_en_cours_par_code(code)
        else:
            code = regles.valider_code_livre(code)
            emprunt = self._depot.emprunt_en_cours_du_livre(code)
        if emprunt is None:
            raise RegleMetierError(f"Aucun emprunt en cours pour le code {code}.")
        self._depot.cloturer_emprunt(emprunt.id, aujourdhui)
        emprunt.date_retour_effective = aujourdhui
        return emprunt, regles.est_en_retard(emprunt.date_retour_prevue, aujourdhui)

    def emprunts_en_cours(self) -> List[Emprunt]:
        """Livres actuellement empruntés (ceux déjà rendus n'y figurent plus)."""
        return self._depot.lister_emprunts_en_cours()

    def retards(self, aujourdhui: Optional[date] = None) -> List[Emprunt]:
        aujourdhui = aujourdhui or date.today()
        return [
            e for e in self._depot.lister_emprunts_en_cours()
            if regles.est_en_retard(e.date_retour_prevue, aujourdhui)
        ]

    def titre_du_livre(self, code: str) -> str:
        livre = self._depot.obtenir_livre(code)
        return livre.titre if livre else code