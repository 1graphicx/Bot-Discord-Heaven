import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import platform
import logging

# RÈGLE : Les commandes slash sont automatiquement enregistrées par bot.add_cog()

# Gestion optionnelle de psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger("bot.utilities")

class Utilities(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Afficher la latence du bot")
    async def ping_slash(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="🏓 **Pong!**",
                description=f"Latence: **{round(self.bot.latency * 1000)}ms**",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"Bot: {self.bot.user.name}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur commande ping: {e}")
            await interaction.response.send_message("❌ **Erreur lors de la vérification de la latence.**", ephemeral=True)

    @app_commands.command(name="userinfo", description="Afficher les informations d'un utilisateur")
    @app_commands.describe(member="Membre dont voir les informations")
    async def userinfo_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        try:
            # Répondre immédiatement pour éviter le timeout
            await interaction.response.defer(ephemeral=True)
            
            if member is None:
                member = interaction.user
            
            roles = [role.mention for role in member.roles[1:]]  # Exclure @everyone
            roles_str = " ".join(roles) if roles else "Aucun rôle"
            
            embed = discord.Embed(
                title=f"👤 **Informations de {member.display_name}**",
                color=member.color,
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Nom d'utilisateur", value=f"`{member.name}`", inline=True)
            embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
            embed.add_field(name="Surnom", value=f"`{member.nick or 'Aucun'}`", inline=True)
            embed.add_field(name="Compte créé le", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
            embed.add_field(name="A rejoint le", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
            embed.add_field(name="Rôles", value=roles_str[:1024] if len(roles_str) <= 1024 else roles_str[:1021] + "...", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur commande userinfo: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ **Erreur lors de la récupération des informations utilisateur.**", ephemeral=True)
            else:
                await interaction.followup.send("❌ **Erreur lors de la récupération des informations utilisateur.**", ephemeral=True)

    @app_commands.command(name="serverinfo", description="Afficher les informations du serveur")
    async def serverinfo_slash(self, interaction: discord.Interaction):
        try:
            # Répondre immédiatement pour éviter le timeout
            await interaction.response.defer(ephemeral=True)
            
            guild = interaction.guild
            
            # Statistiques des canaux
            text_channels = len(guild.text_channels)
            voice_channels = len(guild.voice_channels)
            categories = len(guild.categories)
            
            # Statistiques des membres (optimisé)
            total_members = guild.member_count
            online_members = len([m for m in guild.members if m.status != discord.Status.offline])
            
            embed = discord.Embed(
                title=f"🏠 **Informations de {guild.name}**",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            embed.add_field(name="Propriétaire", value=guild.owner.mention, inline=True)
            embed.add_field(name="ID du serveur", value=f"`{guild.id}`", inline=True)
            embed.add_field(name="Créé le", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
            embed.add_field(name="Membres", value=f"👥 {total_members} total\n🟢 {online_members} en ligne", inline=True)
            embed.add_field(name="Canaux", value=f"💬 {text_channels} textuels\n🔊 {voice_channels} vocaux\n📁 {categories} catégories", inline=True)
            embed.add_field(name="Rôles", value=f"🎭 {len(guild.roles)} rôles", inline=True)
            
            if guild.description:
                embed.add_field(name="Description", value=guild.description[:1024], inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur commande serverinfo: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ **Erreur lors de la récupération des informations du serveur.**", ephemeral=True)
            else:
                await interaction.followup.send("❌ **Erreur lors de la récupération des informations du serveur.**", ephemeral=True)

    @app_commands.command(name="avatar", description="Afficher l'avatar d'un utilisateur")
    @app_commands.describe(member="Membre dont voir l'avatar")
    async def avatar_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        try:
            if member is None:
                member = interaction.user
            
            embed = discord.Embed(
                title=f"🖼️ **Avatar de {member.display_name}**",
                color=member.color,
                timestamp=datetime.now()
            )
            embed.set_image(url=member.display_avatar.url)
            embed.add_field(name="Lien direct", value=f"[Cliquer ici]({member.display_avatar.url})", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur commande avatar: {e}")
            await interaction.response.send_message("❌ **Erreur lors de la récupération de l'avatar.**", ephemeral=True)

    @app_commands.command(name="botinfo", description="Afficher les informations du bot")
    async def botinfo_slash(self, interaction: discord.Interaction):
        try:
            # Répondre immédiatement pour éviter le timeout
            await interaction.response.defer(ephemeral=True)
            
            # Statistiques du bot
            total_servers = len(self.bot.guilds)
            total_users = sum(len(guild.members) for guild in self.bot.guilds)
            
            # Statistiques système (si psutil disponible)
            if PSUTIL_AVAILABLE:
                try:
                    cpu_percent = psutil.cpu_percent()
                    memory = psutil.virtual_memory()
                    memory_percent = memory.percent
                    system_info = f"🖥️ CPU: **{cpu_percent}%**\n💾 RAM: **{memory_percent}%**"
                except Exception as e:
                    logger.error(f"Erreur récupération stats système: {e}")
                    system_info = "💻 Système: Erreur de récupération"
            else:
                system_info = "💻 Système: Indisponible"
            
            embed = discord.Embed(
                title="🤖 **Informations du Bot**",
                description=f"**{self.bot.user.name}** - Bot Discord professionnel",
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            
            embed.add_field(name="📊 Statistiques", value=f"🖥️ **{total_servers}** serveurs\n👥 **{total_users}** utilisateurs", inline=True)
            embed.add_field(name="💻 Système", value=system_info, inline=True)
            embed.add_field(name="🔧 Technique", value=f"🐍 Python: **{platform.python_version()}**\n📚 Discord.py: **{discord.__version__}**", inline=True)
            embed.add_field(name="⏱️ Uptime", value=f"<t:{int(self.bot.start_time.timestamp())}:R>", inline=True)
            embed.add_field(name="🏓 Latence", value=f"**{round(self.bot.latency * 1000)}ms**", inline=True)
            
            embed.set_footer(text="Bot développé avec ❤️")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur commande botinfo: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ **Erreur lors de la récupération des informations du bot.**", ephemeral=True)
            else:
                await interaction.followup.send("❌ **Erreur lors de la récupération des informations du bot.**", ephemeral=True)

    @app_commands.command(name="roleinfo", description="Afficher les informations d'un rôle")
    @app_commands.describe(role="Rôle dont voir les informations")
    async def roleinfo_slash(self, interaction: discord.Interaction, role: discord.Role):
        try:
            # Répondre immédiatement pour éviter le timeout
            await interaction.response.defer(ephemeral=True)
            
            # Compter les membres avec ce rôle
            member_count = len(role.members)
            
            # Permissions importantes
            permissions = []
            if role.permissions.administrator:
                permissions.append("👑 Administrateur")
            if role.permissions.manage_guild:
                permissions.append("⚙️ Gérer le serveur")
            if role.permissions.manage_channels:
                permissions.append("📝 Gérer les canaux")
            if role.permissions.manage_messages:
                permissions.append("💬 Gérer les messages")
            if role.permissions.ban_members:
                permissions.append("🔨 Bannir des membres")
            if role.permissions.kick_members:
                permissions.append("👢 Expulser des membres")
            
            permissions_str = "\n".join(permissions) if permissions else "Aucune permission spéciale"
            
            embed = discord.Embed(
                title=f"🎭 **Informations du rôle {role.name}**",
                color=role.color,
                timestamp=datetime.now()
            )
            embed.add_field(name="ID", value=f"`{role.id}`", inline=True)
            embed.add_field(name="Couleur", value=f"`{str(role.color)}`", inline=True)
            embed.add_field(name="Position", value=f"`{role.position}`", inline=True)
            embed.add_field(name="Membres", value=f"👥 **{member_count}** membres", inline=True)
            embed.add_field(name="Mentionnable", value="✅ Oui" if role.mentionable else "❌ Non", inline=True)
            embed.add_field(name="Affiché séparément", value="✅ Oui" if role.hoist else "❌ Non", inline=True)
            embed.add_field(name="Créé le", value=f"<t:{int(role.created_at.timestamp())}:R>", inline=True)
            embed.add_field(name="Permissions importantes", value=permissions_str, inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur commande roleinfo: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ **Erreur lors de la récupération des informations du rôle.**", ephemeral=True)
            else:
                await interaction.followup.send("❌ **Erreur lors de la récupération des informations du rôle.**", ephemeral=True)

    @app_commands.command(name="channelinfo", description="Afficher les informations d'un canal")
    @app_commands.describe(channel="Canal dont voir les informations")
    async def channelinfo_slash(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        try:
            if channel is None:
                channel = interaction.channel
            
            # Répondre immédiatement pour éviter le timeout
            await interaction.response.defer(ephemeral=True)
            
            # Compter les messages (approximatif avec limite de sécurité)
            try:
                message_count = 0
                async for _ in channel.history(limit=100):  # Réduit à 100 pour plus de rapidité
                    message_count += 1
                    if message_count >= 100:
                        message_count = "100+"
                        break
            except discord.Forbidden:
                message_count = "Accès refusé"
            except Exception as e:
                logger.error(f"Erreur comptage messages: {e}")
                message_count = "Erreur"
            
            embed = discord.Embed(
                title=f"📝 **Informations du canal #{channel.name}**",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)
            embed.add_field(name="Type", value=f"💬 Canal textuel", inline=True)
            embed.add_field(name="Position", value=f"`{channel.position}`", inline=True)
            embed.add_field(name="Catégorie", value=f"`{channel.category.name if channel.category else 'Aucune'}`", inline=True)
            embed.add_field(name="Messages", value=f"💬 **{message_count}**", inline=True)
            embed.add_field(name="Créé le", value=f"<t:{int(channel.created_at.timestamp())}:R>", inline=True)
            
            if channel.topic:
                embed.add_field(name="Description", value=channel.topic[:1024], inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur commande channelinfo: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ **Erreur lors de la récupération des informations du canal.**", ephemeral=True)
            else:
                await interaction.followup.send("❌ **Erreur lors de la récupération des informations du canal.**", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utilities(bot))
