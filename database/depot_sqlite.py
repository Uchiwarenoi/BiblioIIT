"""Dépôt SQLite : persistance des livres, étudiants et emprunts."""

import sqlite3
from datetime import date
from pathlib import Path
from typing import List, Optional

from models.modeles import Emprunt, Etudiant, Livre
from models.regles import normaliser_texte

CHEMIN_PAR_DEFAUT = Path(__file__).resolve().parent / "biblioiit.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS livres (
    code TEXT PRIMARY KEY, titre TEXT NOT NULL,
    auteur TEXT NOT NULL, annee INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS etudiants (
    matricule TEXT PRIMARY KEY, nom TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS emprunts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    code_livre TEXT NOT NULL REFERENCES livres(code),
    matricule TEXT REFERENCES etudiants(matricule),
    date_emprunt TEXT NOT NULL,
    date_retour_prevue TEXT NOT NULL,
    date_retour_effective TEXT);
"""


class DepotSQLite:
    def __init__(self, chemin=CHEMIN_PAR_DEFAUT):
        self._cnx = sqlite3.connect(chemin)
        self._cnx.row_factory = sqlite3.Row
        self._creer_tables()

    def _creer_tables(self) -> None:
        colonnes = [r["name"] for r in self._cnx.execute("PRAGMA table_info(emprunts)")]
        ancien_schema = bool(colonnes) and "code" not in colonnes
        if ancien_schema:
            self._cnx.execute("ALTER TABLE emprunts RENAME TO emprunts_ancien")
        self._cnx.executescript(_SCHEMA)
        if ancien_schema:
            self._cnx.execute(
                "INSERT INTO emprunts (id, code, code_livre, matricule, date_emprunt,"
                " date_retour_prevue, date_retour_effective)"
                " SELECT id, printf('EMP-%04d', id), code_livre, matricule, date_emprunt,"
                " date_retour_prevue, date_retour_effective FROM emprunts_ancien"
            )
            self._cnx.execute("DROP TABLE emprunts_ancien")
        self._cnx.commit()

    # --- Livres / étudiants ---
    def ajouter_livre(self, livre: Livre) -> None:
        self._cnx.execute(
            "INSERT OR IGNORE INTO livres VALUES (?, ?, ?, ?)",
            (livre.code, livre.titre, livre.auteur, livre.annee),
        )
        self._cnx.commit()

    def ajouter_etudiant(self, etudiant: Etudiant) -> None:
        self._cnx.execute(
            "INSERT OR IGNORE INTO etudiants VALUES (?, ?)",
            (etudiant.matricule, etudiant.nom),
        )
        self._cnx.commit()

    def obtenir_livre(self, code: str) -> Optional[Livre]:
        r = self._cnx.execute("SELECT * FROM livres WHERE code = ?", (code,)).fetchone()
        return Livre(**dict(r)) if r else None

    def obtenir_etudiant(self, matricule: str) -> Optional[Etudiant]:
        r = self._cnx.execute(
            "SELECT * FROM etudiants WHERE matricule = ?", (matricule,)
        ).fetchone()
        return Etudiant(**dict(r)) if r else None

    def rechercher_livres(self, mot_cle: str) -> List[Livre]:
        cle = normaliser_texte(mot_cle)
        lignes = self._cnx.execute("SELECT * FROM livres ORDER BY code").fetchall()
        return [Livre(**dict(r)) for r in lignes if cle in normaliser_texte(r["titre"])]

    def lister_livres(self) -> List[Livre]:
        return [Livre(**dict(r)) for r in self._cnx.execute("SELECT * FROM livres ORDER BY code")]

    def prochain_code_livre(self) -> str:
        n = self._cnx.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(code, 2) AS INTEGER)), 0) FROM livres"
        ).fetchone()[0]
        return f"L{n + 1:03d}"

    def obtenir_ou_creer_livre(self, titre: str, auteur: str, annee: Optional[int]) -> Livre:
        """Retourne le livre déjà en base (même titre et auteur) ou l'enregistre avec un nouveau code."""
        cle = (normaliser_texte(titre), normaliser_texte(auteur))
        for r in self._cnx.execute("SELECT * FROM livres ORDER BY code").fetchall():
            if (normaliser_texte(r["titre"]), normaliser_texte(r["auteur"])) == cle:
                return Livre(**dict(r))
        livre = Livre(self.prochain_code_livre(), titre, auteur, annee or 0)
        self.ajouter_livre(livre)
        return livre

    # --- Emprunts ---
    @staticmethod
    def _vers_emprunt(r: sqlite3.Row) -> Emprunt:
        eff = r["date_retour_effective"]
        return Emprunt(
            id=r["id"],
            code=r["code"],
            code_livre=r["code_livre"],
            matricule=r["matricule"],
            date_emprunt=date.fromisoformat(r["date_emprunt"]),
            date_retour_prevue=date.fromisoformat(r["date_retour_prevue"]),
            date_retour_effective=date.fromisoformat(eff) if eff else None,
        )

    def prochain_code_emprunt(self) -> str:
        n = self._cnx.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(code, 5) AS INTEGER)), 0) FROM emprunts"
        ).fetchone()[0]
        return f"EMP-{n + 1:04d}"

    def emprunt_en_cours_du_livre(self, code_livre: str) -> Optional[Emprunt]:
        r = self._cnx.execute(
            "SELECT * FROM emprunts WHERE code_livre = ? AND date_retour_effective IS NULL",
            (code_livre,),
        ).fetchone()
        return self._vers_emprunt(r) if r else None

    def emprunt_en_cours_par_code(self, code: str) -> Optional[Emprunt]:
        r = self._cnx.execute(
            "SELECT * FROM emprunts WHERE code = ? AND date_retour_effective IS NULL",
            (code,),
        ).fetchone()
        return self._vers_emprunt(r) if r else None

    def compter_emprunts_en_cours(self, matricule: str) -> int:
        return self._cnx.execute(
            "SELECT COUNT(*) FROM emprunts WHERE matricule = ? AND date_retour_effective IS NULL",
            (matricule,),
        ).fetchone()[0]

    def lister_emprunts_en_cours(self) -> List[Emprunt]:
        lignes = self._cnx.execute(
            "SELECT * FROM emprunts WHERE date_retour_effective IS NULL ORDER BY date_retour_prevue"
        ).fetchall()
        return [self._vers_emprunt(r) for r in lignes]

    def enregistrer_emprunt(self, e: Emprunt) -> Emprunt:
        cur = self._cnx.execute(
            "INSERT INTO emprunts (code, code_livre, matricule, date_emprunt, date_retour_prevue)"
            " VALUES (?, ?, ?, ?, ?)",
            (e.code, e.code_livre, e.matricule, e.date_emprunt.isoformat(),
             e.date_retour_prevue.isoformat()),
        )
        self._cnx.commit()
        e.id = cur.lastrowid
        return e

    def cloturer_emprunt(self, emprunt_id: int, date_retour: date) -> None:
        self._cnx.execute(
            "UPDATE emprunts SET date_retour_effective = ? WHERE id = ?",
            (date_retour.isoformat(), emprunt_id),
        )
        self._cnx.commit()

    def fermer(self) -> None:
        self._cnx.close()


def charger_donnees_demo(depot: DepotSQLite) -> None:
    """Jeu de données de démonstration (idempotent)."""
    for livre in (
        Livre("L001", "En attendant le vote des bêtes sauvages", "Ahmadou Kourouma", 1998),
        Livre("L002", "Les Soleils des indépendances", "Ahmadou Kourouma", 1968),
        Livre("L003", "Une si longue lettre", "Mariama Bâ", 1979),
        Livre("L004", "Allah n'est pas obligé", "Ahmadou Kourouma", 2000),
    ):
        depot.ajouter_livre(livre)
    for etu in (
        Etudiant("E2026-001", "Étudiant 1"),
        Etudiant("E2026-002", "Étudiant 2"),
        Etudiant("E2026-003", "Étudiant 3"),
    ):
        depot.ajouter_etudiant(etu)
