import discord
from discord.ext import commands
import discord.app_commands
import os
import logging
import asyncio
from datetime import datetime
import json

# Configuration du logging pour Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(name)-12s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('bot')

# Configuration du bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

def get_token():
    """Récupère le token Discord de manière sécurisée pour Railway"""
    # Priorité 1: Variable d'environnement (Railway)
    token = os.getenv('DISCORD_TOKEN')
    if token:
        logger.info("Token récupéré depuis la variable d'environnement DISCORD_TOKEN")
        return token
    
    # Priorité 2: Fichier .env (si python-dotenv est installé)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('DISCORD_TOKEN')
        if token:
            logger.info("Token récupéré depuis le fichier .env")
            return token
    except ImportError:
        logger.info("python-dotenv non installé, passage au fichier token.txt")
    
    # Priorité 3: Fichier token.txt (fallback local)
    try:
        with open('token.txt', 'r') as f:
            token = f.read().strip()
            if token and token != "VOTRE_TOKEN_ICI":
                logger.info("Token récupéré depuis token.txt")
                return token
    except FileNotFoundError:
        logger.error("Aucun fichier token.txt trouvé")
    except Exception as e:
        logger.error(f"Erreur lecture token.txt: {e}")
    
    return None

@bot.event
async def on_ready():
    """Événement déclenché quand le bot est prêt"""
    logger.info(f"Bot connecté en tant que {bot.user}")
    logger.info(f"ID du bot: {bot.user.id}")
    logger.info(f"Connecté à {len(bot.guilds)} serveur(s)")
    
    # Chargement des cogs
    cogs_to_load = [
        'cogs.roles',
        'cogs.giveaways', 
        'cogs.saved_cmds',
        'cogs.moderation',
        'cogs.welcome',
        'cogs.utilities',
        'cogs.fun',
        'cogs.tickets'
    ]
    
    for cog in cogs_to_load:
        try:
            logger.info(f"Chargement du cog: {cog}")
            await bot.load_extension(cog)
            logger.info(f"Cog chargé: {cog}")
        except Exception as e:
            logger.error(f"Erreur chargement cog {cog}: {e}")
    
    # Synchronisation des commandes
    try:
        logger.info("Début de la sync globale...")
        await bot.tree.sync()
        logger.info("Sync globale effectuée")
        
        logger.info("Début de la sync par guilde...")
        for guild in bot.guilds:
            try:
                await bot.tree.sync(guild=guild)
                logger.info(f"Sync effectuée pour la guilde: {guild.name} [ {guild.id} ]")
            except Exception as e:
                logger.error(f"Erreur sync guilde {guild.name}: {e}")
        logger.info("Sync par guilde terminée")
        
        logger.info(f"Bot prêt avec {len(bot.tree.get_commands())} commandes")
        logger.info("Bot opérationnel !")
        
    except Exception as e:
        logger.error(f"Erreur sync commandes: {e}")

@bot.event
async def on_guild_join(guild):
    """Événement déclenché quand le bot rejoint un serveur"""
    logger.info(f"Bot rejoint le serveur: {guild.name} [ {guild.id} ]")
    try:
        await bot.tree.sync(guild=guild)
        logger.info(f"Sync effectuée pour le nouveau serveur: {guild.name}")
    except Exception as e:
        logger.error(f"Erreur sync nouveau serveur {guild.name}: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    """Gestionnaire d'erreurs global"""
    logger.error(f"Erreur dans l'événement {event}: {args} {kwargs}")

@bot.tree.command(name="sync", description="Synchronise les commandes slash (Admin uniquement)")
@app_commands.describe(scope="Portée de la synchronisation (global ou guild)")
async def sync_slash(interaction: discord.Interaction, scope: str = "guild"):
    """Commande pour synchroniser les commandes slash"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ **Vous devez être administrateur pour utiliser cette commande.**", ephemeral=True)
        return
    
    try:
        if scope.lower() == "global":
            await bot.tree.sync()
            await interaction.response.send_message("✅ **Synchronisation globale effectuée !**", ephemeral=True)
            logger.info(f"Sync globale demandée par {interaction.user}")
        else:
            await bot.tree.sync(guild=interaction.guild)
            await interaction.response.send_message("✅ **Synchronisation du serveur effectuée !**", ephemeral=True)
            logger.info(f"Sync guilde demandée par {interaction.user} sur {interaction.guild.name}")
    except Exception as e:
        logger.error(f"Erreur sync commande: {e}")
        await interaction.response.send_message(f"❌ **Erreur lors de la synchronisation:** {str(e)}", ephemeral=True)

# Configuration pour Railway
if __name__ == "__main__":
    token = get_token()
    if not token:
        logger.error("❌ Token Discord non trouvé ! Vérifiez vos variables d'environnement ou le fichier token.txt")
        exit(1)
    
    logger.info("Démarrage du bot...")
    logger.info("Token récupéré avec succès, connexion en cours...")
    
    try:
        bot.run(token, log_handler=None)
    except Exception as e:
        logger.error(f"Erreur connexion bot: {e}")
        exit(1)