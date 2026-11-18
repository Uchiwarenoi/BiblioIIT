from controllers.service import BibliothequeService
from database.depot_sqlite import DepotSQLite, charger_donnees_demo
from database.source_externe import SourceOpenLibrary
from models.regles import RegleMetierError, normaliser_texte

MENU = """
=== BiblioIIT ===
1. Rechercher un livre   2. Emprunter
3. Rendre               4. Retards
5. Livres empruntés     0. Quitter"""


def _fmt(d) -> str:
    return d.strftime("%d/%m/%Y")


def _ligne(livre) -> str:
    annee = f" ({livre.annee})" if livre.annee else ""
    return f"  {livre.code}  {livre.titre} - {livre.auteur}{annee}"


class ConsoleView:
    def __init__(self, service: BibliothequeService):
        self._service = service

    def lancer(self) -> None:
        actions = {
            "1": self._rechercher,
            "2": self._emprunter,
            "3": self._rendre,
            "4": self._retards,
            "5": self._empruntes,
        }
        while True:
            print(MENU)
            choix = input("Votre choix : ").strip()
            if choix == "0":
                print("Au revoir.")
                return
            action = actions.get(choix)
            if action is None:
                print("Choix invalide.")
                continue
            try:
                action()
            except RegleMetierError as err:
                print(f"Impossible : {err}")

    def _rechercher(self) -> None:
        mot_cle = input("Mot-clé : ")
        livres = self._service.rechercher(mot_cle)
        if not livres:
            print("Aucun livre trouvé en bibliothèque locale, recherche en ligne en cours...")
        for l in livres:
            print(_ligne(l))
        try:
            en_ligne = self._service.rechercher_en_ligne(mot_cle)
        except RegleMetierError as err:
            print(f"  ({err})")
            return
        codes_locaux = {l.code for l in livres}
        nouveaux = [l for l in en_ligne if l.code not in codes_locaux]
        if nouveaux:
            print("Trouvés en ligne (enregistrés dans la bibliothèque locale) :")
            for l in nouveaux:
                print(_ligne(l))

    @staticmethod
    def _demander_numero(invite: str, maxi: int, zero_ok: bool = False) -> int:
        """Redemande tant que la saisie n'est pas un numéro de la liste."""
        while True:
            saisie = input(invite).strip()
            if saisie.isdigit() and ((zero_ok and int(saisie) == 0) or 1 <= int(saisie) <= maxi):
                return int(saisie)
            print("Choix invalide : saisis un numéro de la liste.")

    def _choisir_livre(self, nom: str):
        """Affiche les livres au nom proche et fait choisir. Retourne None si l'emprunt est annulé."""
        livres = self._service.livres_proches(nom)
        en_ligne_fait = False
        if not livres:
            print(f"Aucun livre proche de « {nom.strip()} » en bibliothèque, recherche en ligne...")
            livres = self._service.livres_proches_en_ligne(nom)
            en_ligne_fait = True
            if not livres:
                raise RegleMetierError(f"Aucun livre trouvé pour « {nom.strip()} ».")
        while True:
            exact = len(livres) == 1 and normaliser_texte(livres[0].titre) == normaliser_texte(nom)
            if exact:
                return livres[0]
            print("Livres correspondants :")
            for i, l in enumerate(livres, 1):
                emprunte = "  [déjà emprunté]" if self._service.est_emprunte(l.code) else ""
                print(f" {i}.{_ligne(l)}{emprunte}")
            zero = "0 = annuler" if en_ligne_fait else "0 = chercher en ligne"
            numero = self._demander_numero(f"Numéro du livre à emprunter ({zero}) : ", len(livres), True)
            if numero:
                return livres[numero - 1]
            if en_ligne_fait:
                return None
            livres = self._service.livres_proches_en_ligne(nom)
            en_ligne_fait = True

    def _choisir_periode(self) -> int:
        periodes = self._service.periodes_avec_retour()
        print("Période d'emprunt :")
        for i, (jours, retour) in enumerate(periodes, 1):
            print(f" {i}. {jours} jours (retour le {_fmt(retour)})")
        return periodes[self._demander_numero("Votre choix : ", len(periodes)) - 1][0]

    def _emprunter(self) -> None:
        livre = self._choisir_livre(input("Nom du livre : "))
        if livre is None:
            print("Emprunt annulé.")
            return
        self._service.verifier_livre_libre(livre)
        print(f"Livre choisi :\n{_ligne(livre)}")
        e = self._service.emprunter(livre.code, self._choisir_periode())
        print(
            f"Emprunt enregistré. Code d'emprunt : {e.code}. "
            f"Retour prévu le {_fmt(e.date_retour_prevue)}."
        )

    def _rendre(self) -> None:
        e, en_retard = self._service.rendre(input("Code d'emprunt ou du livre : "))
        titre = self._service.titre_du_livre(e.code_livre)
        print(f"Livre « {titre} » rendu." + (" Attention : retour en retard." if en_retard else ""))

    def _retards(self) -> None:
        retards = self._service.retards()
        if not retards:
            print("Aucun retard.")
        for e in retards:
            print(
                f"  {e.code}  {self._service.titre_du_livre(e.code_livre)}"
                f" (prévu le {_fmt(e.date_retour_prevue)})"
            )


    def _empruntes(self) -> None:
        emprunts = self._service.emprunts_en_cours()
        if not emprunts:
            print("Aucun livre emprunté en ce moment.")
            return
        codes_en_retard = {r.code for r in self._service.retards()}
        print("Livres empruntés :")
        for e in emprunts:
            retard = "  EN RETARD" if e.code in codes_en_retard else ""
            print(
                f"  {e.code}  {e.code_livre}  {self._service.titre_du_livre(e.code_livre)}"
                f" - emprunté le {_fmt(e.date_emprunt)}, retour prévu le {_fmt(e.date_retour_prevue)}{retard}"
            )


def main() -> None:
    depot = DepotSQLite()
    charger_donnees_demo(depot)
    try:
        ConsoleView(BibliothequeService(depot, SourceOpenLibrary())).lancer()
    finally:
        depot.fermer()


if __name__ == "__main__":
    main()
