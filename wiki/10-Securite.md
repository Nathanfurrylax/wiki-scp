<div align="center">

<img src="assets/banners/10-Securite.svg" alt="🛡️ Sécurité" width="100%">

![Page](https://img.shields.io/badge/Page-10_%2F_14-ff4d5e?style=flat-square) ![Niveau](https://img.shields.io/badge/Niveau-Tous_niveaux-5fd0ff?style=flat-square) ![Durée](https://img.shields.io/badge/Dur%C3%A9e-10_min-5fd0ff?style=flat-square)

<a href="09-Administration"><img src="assets/nav-prev.svg" alt="Précédent" height="44"></a> <a href="Home"><img src="assets/nav-home.svg" alt="Sommaire" height="44"></a> <a href="11-Architecture"><img src="assets/nav-next.svg" alt="Suivant" height="44"></a>

</div>

<details>
<summary>📑 <b>Dans cette page</b> (5 sections)</summary>

- [🔒 Protections intégrées](#-protections-intégrées)
- [📌 À faire de ton côté](#-à-faire-de-ton-côté)
- [⚠️ Limites à connaître](#-limites-à-connaître)
- [🍪 Données personnelles (information, pas un avis juridique)](#-données-personnelles-information-pas-un-avis-juridique)
- [📣 Signaler une faille](#-signaler-une-faille)

</details>

## 🔒 Protections intégrées

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#0f2130","primaryTextColor":"#e6eef5","primaryBorderColor":"#5fd0ff","lineColor":"#3d89ab","secondaryColor":"#1a0d14","tertiaryColor":"#0b1824","edgeLabelBackground":"#0f2130","fontFamily":"ui-monospace, Menlo, Consolas, monospace","noteBkgColor":"#1a0d14","noteTextColor":"#ffb4bb","actorBkg":"#0f2130","actorBorder":"#5fd0ff","actorTextColor":"#e6eef5","signalColor":"#3d89ab","signalTextColor":"#3d89ab","labelBoxBkgColor":"#0f2130","labelTextColor":"#e6eef5","loopTextColor":"#3d89ab"}}}%%
flowchart LR
  R(["🌍 Requête"]) --> H["🧱 En-têtes + CSP"] --> L["🚦 Limitation de requêtes"] --> C["🧾 Jeton CSRF"] --> A{"🔐 ID dans la liste blanche ?"}
  A -->|"oui"| OK(["✅ Action autorisée"])
  A -->|"non"| NO(["⛔ Refus ou redirection"])
  class OK ok
  class NO bad
  classDef cloud fill:#0f2130,stroke:#5fd0ff,color:#e6eef5
  classDef ok fill:#0c241b,stroke:#5dffb0,color:#e6eef5
  classDef bad fill:#241219,stroke:#ff4d5e,color:#ffb4bb
```

| Protection | Détail |
|---|---|
| **Liste blanche d'éditeurs** | ID Discord vérifié à **chaque** requête d'administration |
| **OAuth2 avec `state`** | Anti-falsification de la connexion ; session renouvelée après connexion |
| **CSRF** | Jeton obligatoire sur tous les envois (formulaires et requêtes de l'éditeur) |
| **Cookies de session** | `HttpOnly`, `SameSite=Lax`, `Secure` sur Render, durée 12 h |
| **HTML assaini** | Contenu passé par `bleach` : pas de script, style ni iframe arbitraire |
| **Politique CSP stricte** | Aucun script en ligne ; seuls les scripts du site ; iframes limitées à YouTube (nocookie) |
| **En-têtes** | `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, HSTS sur Render |
| **Envois de fichiers** | Signature réelle vérifiée, types restreints, noms aléatoires, tailles plafonnées, SVG refusé |
| **Limitation de requêtes** | 600/min par IP en général ; 20/min sur la connexion ; 60/min sur l'envoi de médias |
| **Admin non indexée** | `noindex`, `no-store`, exclue par `robots.txt` |
| **Requêtes SQL paramétrées** | SQLAlchemy ; recherche avec échappement des jokers |

## 📌 À faire de ton côté

> [!IMPORTANT]
> Active la **double authentification** sur chaque compte Discord éditeur et garde la liste `ADMIN_DISCORD_IDS` la plus courte possible.

- **Secrets** : jamais dans Git. En cas de fuite : Reset immédiat (Discord, Supabase, R2).
- **Dépôt GitHub privé**.
- **Compte Discord des éditeurs** : active la double authentification.
- **Liste d'ID minimale** et revue régulière.
- **HTTPS** uniquement (automatique sur Render).
- **Mises à jour** des dépendances ([page 14](14-Maintenance)).

## ⚠️ Limites à connaître
- Tous les éditeurs sont **équivalents** (pas de rôles, pas de journal d'audit).
- La limitation de requêtes est comptée **par worker** (mémoire) ; pour un compteur partagé, configure `RATELIMIT_STORAGE_URI` (Redis).
- Les médias sont **publics** par adresse (adresses non devinables, mais non protégées).
- Un shortcode `[[media: https://…]]` peut charger une image hébergée ailleurs (le navigateur du visiteur contacte ce site tiers).

## 🍪 Données personnelles (information, pas un avis juridique)
- Pour les visiteurs : aucun compte, aucun traceur ajouté ; polices chargées depuis Google Fonts.
- Pour les éditeurs : l'ID et le nom Discord sont conservés dans le **cookie de session** ; le **nom** de l'auteur est enregistré avec chaque document.
- Un site public en France peut nécessiter des **mentions légales** (éditeur/hébergeur) et une information sur les cookies strictement nécessaires : rédige-les selon ta situation.

## 📣 Signaler une faille
Ajoute un fichier `SECURITY.md` à ton dépôt indiquant un contact privé pour les signalements.

<div align="center">

<img src="assets/divider.svg" alt="" width="100%">

<a href="09-Administration"><img src="assets/nav-prev.svg" alt="Précédent" height="44"></a> <a href="Home"><img src="assets/nav-home.svg" alt="Sommaire" height="44"></a> <a href="11-Architecture"><img src="assets/nav-next.svg" alt="Suivant" height="44"></a>

<sub>◀ <a href="09-Administration">🛠️ Administration</a>&nbsp;&nbsp;·&nbsp;&nbsp;<a href="11-Architecture">🧬 Architecture</a> ▶</sub>

<img src="assets/footer.svg" alt="SCP Foundation" width="100%">

<sub>⛨ <b>SCP Foundation</b> — projet de fan non officiel · contenus SCP sous licence CC BY-SA 3.0 lorsque applicable · <a href="#">⬆ retour en haut</a></sub>

</div>
