#!/usr/bin/env python3
"""Chaîne de quêtes kweebec du mod Peuples d'Orbis (étape 6 du plan d'implémentation).

GDD, La chaîne de chaque peuple : « L'arbre Grand-Père dépérit : la sève est volée par les Trorks. 1 soigner les jeunes
pousses (sève) · 2 libérer les prisonniers du camp trork · 3 replanter le bosquet brûlé · 4 veiller le Grand-Père
pendant un raid de nuit · 5 le Treesinger offre une graine d'Écho. » Une étape par rang, de toléré à champion.

Écrit :
  * les trois étapes menées comme des demandes (Server/Nakasar/Requests/Kweebec/Kweebec_Chain_*.json, poids 0 : jamais
    au tableau) : escorte des prisonniers, plantation du bosquet brûlé, veillée pendant un raid ; chacune pose son
    drapeau de chaîne sur le joueur quand elle est remplie ;
  * le dialogue du chef (Server/Nakasar/Dialogues/Kweebec/Kweebec_Chef.json), qui propose chaque étape selon les
    drapeaux et le rang du joueur, prend la sève (étape 1) et donne la Graine d'Écho (étape 5).

Drapeaux : Kweebec_Chain_<n> = étape n faite.

    python3 tools/generate_chain.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "src/main/resources/Server"
REQUESTS = RES / "Nakasar/Requests/Kweebec"
DIALOGUES = RES / "Nakasar/Dialogues/Kweebec"

P = "Kweebec"
K = "nakasar_peuples.dialogue.Kweebec_Chef."
R = "nakasar_peuples.request."
SAP = "Ingredient_Tree_Sap"
SAP_COUNT = 10
SAP_REPUTATION = 80
SEED = "Nakasar_Peuples_Echo_Seed"
# La veillée (étape 4) se joue autour du Grand-Père, bâtiment du palier Bourg : sans lui, le chef attend.
VIGIL_BUILDING = "Grand_Pere"


def flag(n):
    return f"{P}_Chain_{n}"


# (étape, modèle, type, champs propres, réputation, faveurs)
STEPS = [
    (2, "Kweebec_Chain_Prisoners", "Escort",
     {"Spawns": ["Trork_Guard", "Trork_Guard", "Trork_Warrior"], "MinDistance": 90, "MaxDistance": 150}, 120, 5),
    (3, "Kweebec_Chain_Grove", "Plant",
     {"ItemId": "Plant_Sapling_Oak", "Quantity": 6, "MinDistance": 60, "MaxDistance": 110}, 150, 5),
    (4, "Kweebec_Chain_Vigil", "Defense", {}, 200, 6),
]


def template(step, tid, kind, extra, reputation, favors):
    doc = {
        "$Comment": f"Étape {step} de la chaîne kweebec (étape 6), générée par tools/generate_chain.py : donnée par le "
                    "dialogue du chef (StartChainRequest), jamais tirée au tableau (Weight 0). Remplie, elle pose le "
                    f"drapeau {flag(step)} sur le joueur.",
        "People": P,
        "Type": kind,
        "Weight": 0,
        "TitleKey": f"{R}{tid}.title",
        "TaskKey": f"{R}{tid}.task",
    }
    doc.update(extra)
    doc.update({"Essor": 0, "Favors": favors, "Reputation": reputation, "Flag": flag(step)})
    return doc


def bye():
    return {"TextKey": K + "aurevoir"}


def news():
    return {"TextKey": K + "nouvelles", "Effects": [{"Type": "RaidStatus"}], "Next": "Nouvelles"}


def rank(r):
    return [{"Type": "Rank", "Min": r}]


def start(tid, rank_needed, next_node):
    return {"TextKey": K + "accepter", "HintKey": "nakasar_peuples.dialogue.hint.chain", "Conditions": rank(rank_needed),
            "FailKey": f"nakasar_peuples.dialogue.fail.rank.{rank_needed}",
            "Effects": [{"Type": "StartChainRequest", "Template": tid}], "Next": next_node}


def node(nid, key, responses):
    return {"Id": nid, "TextKey": K + key, "Responses": responses}


def dialogue():
    entries = [
        {"Node": "AuxArmes", "Conditions": [{"Type": "Raid", "State": "Active"}]},
        {"Node": "Honni", "Conditions": [{"Type": "Rank", "Max": "Honni"}]},
        {"Node": "Etranger", "Conditions": [{"Type": "Rank", "Max": "Etranger"}]},
        {"Node": "Fin", "Conditions": [{"Type": "Flag", "Flag": flag(5)}]},
        {"Node": "Graine", "Conditions": [{"Type": "Flag", "Flag": flag(4)}]},
        {"Node": "VeilleEnCours", "Conditions": [{"Type": "ChainRequest", "Template": "Kweebec_Chain_Vigil"}]},
        {"Node": "VeilleAttente", "Conditions": [{"Type": "Flag", "Flag": flag(3)},
                                                 {"Type": "Building", "Id": VIGIL_BUILDING, "Standing": False}]},
        {"Node": "Veille", "Conditions": [{"Type": "Flag", "Flag": flag(3)}]},
        {"Node": "BosquetEnCours", "Conditions": [{"Type": "ChainRequest", "Template": "Kweebec_Chain_Grove"}]},
        {"Node": "Bosquet", "Conditions": [{"Type": "Flag", "Flag": flag(2)}]},
        {"Node": "PrisonniersEnCours", "Conditions": [{"Type": "ChainRequest", "Template": "Kweebec_Chain_Prisoners"}]},
        {"Node": "Prisonniers", "Conditions": [{"Type": "Flag", "Flag": flag(1)}]},
        {"Node": "Seve"},
    ]
    nodes = [
        node("AuxArmes", "auxArmes", [news(), bye()]),
        node("Honni", "honni", [bye()]),
        node("Etranger", "etranger", [{"TextKey": K + "commentAider", "Next": "Conseil"}, bye()]),
        node("Conseil", "conseil", [
            {"TextKey": K + "voirDemandes", "HintKey": "nakasar_peuples.dialogue.hint.openRequests",
             "Conditions": [{"Type": "InVillage", "People": P}], "FailKey": "nakasar_peuples.dialogue.fail.inVillage",
             "Effects": [{"Type": "OpenRequests"}]},
            bye()]),
        # Étape 1 : la sève, rendue au chef.
        node("Seve", "seve", [
            {"TextKey": K + "donnerSeve", "HintKey": "nakasar_peuples.dialogue.hint.chainSap",
             "Conditions": rank("Tolere") + [{"Type": "HasItem", "ItemId": SAP, "Quantity": SAP_COUNT}],
             "FailKey": K + "failSeve",
             "Effects": [{"Type": "TakeItem", "ItemId": SAP, "Quantity": SAP_COUNT},
                         {"Type": "AddReputation", "Amount": SAP_REPUTATION},
                         {"Type": "SetFlag", "Flag": flag(1)}],
             "Next": "Prisonniers"},
            news(), bye()]),
        # Étape 2 : les prisonniers du camp trork.
        node("Prisonniers", "prisonniers", [start("Kweebec_Chain_Prisoners", "Ami", "Accepte"), news(), bye()]),
        node("PrisonniersEnCours", "prisonniersEnCours", [news(), bye()]),
        # Étape 3 : le bosquet brûlé.
        node("Bosquet", "bosquet", [start("Kweebec_Chain_Grove", "Ami", "Accepte"), news(), bye()]),
        node("BosquetEnCours", "bosquetEnCours", [news(), bye()]),
        # Étape 4 : la veillée du Grand-Père, pendant un raid.
        node("Veille", "veille", [start("Kweebec_Chain_Vigil", "Hote", "VeilleAcceptee"), news(), bye()]),
        node("VeilleAttente", "veilleAttente", [
            {"TextKey": K + "accepter", "HintKey": "nakasar_peuples.dialogue.hint.chain",
             "Conditions": [{"Type": "Building", "Id": VIGIL_BUILDING}],
             "FailKey": f"nakasar_peuples.dialogue.fail.building.{VIGIL_BUILDING}"},
            news(), bye()]),
        node("VeilleAcceptee", "veilleAcceptee", [news(), bye()]),
        node("VeilleEnCours", "veilleEnCours", [news(), bye()]),
        # Étape 5 : la Graine d'Écho.
        node("Graine", "graine", [
            {"TextKey": K + "recevoirGraine", "HintKey": "nakasar_peuples.dialogue.hint.chainSeed",
             "Conditions": rank("Champion"), "FailKey": "nakasar_peuples.dialogue.fail.rank.Champion",
             "Effects": [{"Type": "GiveItem", "ItemId": SEED, "Quantity": 1}, {"Type": "SetFlag", "Flag": flag(5)}],
             "Next": "Fin"},
            news(), bye()]),
        node("Fin", "fin", [news(), bye()]),
        node("Accepte", "accepte", [bye()]),
        node("Nouvelles", "nouvellesTexte", [bye()]),
    ]
    return {
        "$Comment": "Le chef d'un village kweebec (étape 6), généré par tools/generate_chain.py : la chaîne du peuple "
                    "(GDD, La chaîne de chaque peuple), une étape par rang. Le nœud d'entrée suit le GDD : raid en cours → "
                    "« Aux armes ! », puis l'étape en cours ou la suivante. Une étape au-dessus du rang du joueur reste "
                    "visible, grisée avec le rang qu'il faut.",
        "NpcNameKey": K + "npc",
        "RoleKey": K + "role",
        "People": P,
        "Entries": entries,
        "Nodes": nodes,
    }


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


def main():
    for s in STEPS:
        write(REQUESTS / f"{s[1]}.json", template(*s))
    write(DIALOGUES / "Kweebec_Chef.json", dialogue())


if __name__ == "__main__":
    main()
