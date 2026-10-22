<!--built-->
<div align="center">

<img src="assets/banners/09-Administration.svg" alt="🛠️ Administration" width="100%">

![Page](https://img.shields.io/badge/Page-09_%2F_14-5fd0ff?style=flat-square) ![Niveau](https://img.shields.io/badge/Niveau-D%C3%A9butant-5dffb0?style=flat-square) ![Durée](https://img.shields.io/badge/Dur%C3%A9e-5_min-5fd0ff?style=flat-square)

<a href="08-Rediger.md"><img src="assets/nav-prev.svg" alt="Précédent" height="44"></a> <a href="Home.md"><img src="assets/nav-home.svg" alt="Sommaire" height="44"></a> <a href="10-Securite.md"><img src="assets/nav-next.svg" alt="Suivant" height="44"></a>

</div>

<details>
<summary>📑 <b>Dans cette page</b> (7 sections)</summary>

- [🔓 Accès](#-accès)
- [📊 Tableau de bord](#-tableau-de-bord)
- [♻️ Cycle de vie d'un document](#-cycle-de-vie-dun-document)
- [👥 Gérer les éditeurs](#-gérer-les-éditeurs)
- [🎞️ Médias](#-médias)
- [🏛️ Départements](#-départements)
- [✅ Bonnes pratiques éditoriales](#-bonnes-pratiques-éditoriales)

</details>

## 🔓 Accès
« Accès éditeur » → Discord → **Studio** (`/admin`). Session de **12 h** ; **Déconnexion** dans le menu.

## 📊 Tableau de bord
- Compteurs : documents, publiés, brouillons, médias.
- Filtre par titre ; liste triée par dernière modification.
- Actions par document : **Modifier**, **Voir**, **Publier/Dépublier**, **Supprimer** (avec confirmation).

## ♻️ Cycle de vie d'un document

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#0f2130","primaryTextColor":"#e6eef5","primaryBorderColor":"#5fd0ff","lineColor":"#3d89ab","secondaryColor":"#1a0d14","tertiaryColor":"#0b1824","edgeLabelBackground":"#0f2130","fontFamily":"ui-monospace, Menlo, Consolas, monospace","noteBkgColor":"#1a0d14","noteTextColor":"#ffb4bb","actorBkg":"#0f2130","actorBorder":"#5fd0ff","actorTextColor":"#e6eef5","signalColor":"#3d89ab","signalTextColor":"#3d89ab","labelBoxBkgColor":"#0f2130","labelTextColor":"#e6eef5","loopTextColor":"#3d89ab"}}}%%
stateDiagram-v2
  state "📝 Brouillon" as Brouillon
  state "✅ Publié" as Publie
  state "📌 Épinglé" as Epingle
  [*] --> Brouillon : création
  Brouillon --> Publie : Publier
  Publie --> Brouillon : Dépublier
  Publie --> Epingle : Épingler
  Epingle --> Publie : Désépingler
  Brouillon --> [*] : Supprimer
  Publie --> [*] : Supprimer
```

1. **Brouillon** : invisible du public ; les éditeurs le voient via **Voir** (bandeau « BROUILLON »).
2. **Publié** : visible partout (accueil, archives, section, tags, RSS, sitemap) ; la date de première publication est conservée.
3. **Épinglé** : remonte en tête de l'accueil (grande carte).
4. **Dépublié** : redevient brouillon, rien n'est supprimé.
5. **Supprimé** : effacé définitivement de la base (les médias restent dans la bibliothèque).

## 👥 Gérer les éditeurs
- Ajouter/retirer un compte : modifier `ADMIN_DISCORD_IDS` ([page 3](03-Discord-OAuth.md)).
- L'auteur affiché est le **nom Discord** de la personne qui a **créé** le document.
- Tous les éditeurs ont les **mêmes droits** (créer, modifier, supprimer tous les documents, gérer les médias). Il n'y a pas de rôles distincts ni d'historique des modifications.

## 🎞️ Médias
La bibliothèque est commune à tous les éditeurs ([page 7](07-Medias.md)). Supprimer un média casse son affichage dans les articles qui l'utilisent.

## 🏛️ Départements
Les 5 départements sont définis dans `app.py` (`SECTIONS`). Pour en ajouter, voir [Personnalisation](12-Personnalisation.md).

## ✅ Bonnes pratiques éditoriales
- Garde la liste d'éditeurs courte et de confiance.
- Relis l'aperçu avant de publier ; vérifie les droits des images et textes repris.
- Ajoute la mention d'attribution CC BY-SA 3.0 pour tout contenu issu du wiki SCP.

<div align="center">

<img src="assets/divider.svg" alt="" width="100%">

<a href="08-Rediger.md"><img src="assets/nav-prev.svg" alt="Précédent" height="44"></a> <a href="Home.md"><img src="assets/nav-home.svg" alt="Sommaire" height="44"></a> <a href="10-Securite.md"><img src="assets/nav-next.svg" alt="Suivant" height="44"></a>

<sub>◀ <a href="08-Rediger.md">✍️ Rédiger un article</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href="10-Securite.md">🛡️ Sécurité</a> ▶</sub>

<img src="assets/footer.svg" alt="SCP Foundation" width="100%">

<sub>⛨ <b>SCP Foundation</b> — projet de fan non officiel · contenus SCP sous licence CC BY-SA 3.0 lorsque applicable · <a href="#">⬆ retour en haut</a></sub>

</div>
