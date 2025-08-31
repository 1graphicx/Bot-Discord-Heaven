# 🤖 Bot Discord HeavenGraphX

Bot Discord complet avec système de tickets, modération, utilitaires et plus encore.

## 🔒 **SÉCURITÉ IMPORTANTE**

### ⚠️ **NE JAMAIS COMMITTER VOTRE TOKEN DISCORD !**

**❌ Ce qu'il ne faut PAS faire :**
- Créer un fichier `token.txt` avec votre token
- Mettre le token directement dans le code
- Committer le token sur GitHub

**✅ Ce qu'il faut faire :**
- Utiliser les **variables d'environnement** sur Railway
- Utiliser un fichier `.env` (non commité)
- Garder votre token **strictement privé**

### 🛡️ **Configuration Sécurisée**

**Pour Railway (Recommandé) :**
1. Allez dans votre projet Railway
2. Onglet "Variables"
3. Ajoutez : `DISCORD_TOKEN` = votre_token_discord
4. **Ne mettez jamais le token dans le code !**

**Pour développement local :**
```bash
# Créez un fichier .env (non commité)
echo "DISCORD_TOKEN=votre_token_ici" > .env
```

## 🚀 Déploiement sur Railway

### Prérequis
- Compte Discord Developer
- Token de bot Discord
- Compte Railway

### Étapes de déploiement

1. **Forkez ce repository** sur GitHub

2. **Connectez-vous à Railway**
   - Allez sur [railway.app](https://railway.app)
   - Connectez-vous avec GitHub

3. **Créez un nouveau projet**
   - Cliquez "Start a New Project"
   - Sélectionnez "Deploy from GitHub repo"
   - Choisissez votre repository

4. **Configurez les variables d'environnement**
   - Dans l'onglet "Variables"
   - Ajoutez : `DISCORD_TOKEN` = votre_token_discord
   - **IMPORTANT : Ne mettez jamais le token dans le code !**

5. **Déployez**
   - Railway détecte automatiquement Python
   - Le bot se déploie automatiquement

## 📋 Fonctionnalités

### 🎫 Système de Tickets
- Création de tickets avec boutons
- Presets configurables (Support, Graphisme, Admin, Par Défaut)
- Gestion des permissions automatique
- Limite de tickets par utilisateur

### 🛡️ Modération
- Clear, Kick, Ban, Unban
- Système d'avertissements
- Mute/Unmute temporaire
- Vérifications de permissions

### 🎉 Utilitaires
- Informations utilisateur/serveur
- Commandes de statistiques
- Gestion des rôles
- Système de giveaway

### 🎮 Fun
- 8ball, Dice, RPS
- Coinflip, Random, Choose
- Emojify, Reverse

## 🔧 Configuration

### Variables d'environnement
```env
DISCORD_TOKEN=votre_token_discord_ici
```

### Commandes principales
- `/ticket setup` - Configurer le système de tickets
- `/ticket presets` - Voir les presets disponibles
- `/sync` - Synchroniser les commandes (Admin)
- `/clear` - Nettoyer des messages
- `/userinfo` - Informations utilisateur

## 📁 Structure du projet

```
BOT/
├── python_bot.py          # Fichier principal
├── requirements.txt       # Dépendances Python
├── railway.json          # Configuration Railway
├── Procfile             # Configuration Heroku
├── runtime.txt          # Version Python
├── .gitignore           # Fichiers ignorés
├── README.md            # Documentation
└── cogs/                # Modules du bot
    ├── tickets.py       # Système de tickets
    ├── moderation.py    # Commandes de modération
    ├── utilities.py     # Commandes utilitaires
    ├── welcome.py       # Système de bienvenue
    ├── fun.py          # Commandes amusantes
    ├── giveaways.py    # Système de giveaway
    ├── roles.py        # Gestion des rôles
    └── saved_cmds.py   # Commandes sauvegardées
```

## 🛠️ Développement local

1. **Clonez le repository**
```bash
git clone https://github.com/votre-username/votre-repo.git
cd BOT
```

2. **Installez les dépendances**
```bash
pip install -r requirements.txt
```

3. **Configurez le token (SÉCURISÉ)**
```bash
# Créez un fichier .env avec votre token
echo "DISCORD_TOKEN=votre_token_ici" > .env
# Le fichier .env est automatiquement ignoré par Git
```

4. **Lancez le bot**
```bash
python python_bot.py
```

## 📊 Logs et Monitoring

Le bot utilise un système de logging avancé :
- Logs détaillés pour le debugging
- Gestion d'erreurs robuste
- Monitoring des performances

## 🔒 Sécurité

- ✅ Token Discord sécurisé via variables d'environnement
- ✅ Vérifications de permissions sur toutes les commandes
- ✅ Gestion d'erreurs complète
- ✅ Protection contre les abus
- ✅ **Aucun token en dur dans le code**

## 📞 Support

Pour toute question ou problème :
1. Vérifiez les logs Railway
2. Consultez la documentation Discord.py
3. Ouvrez une issue sur GitHub

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

---

**Développé avec ❤️ pour la communauté Discord**
