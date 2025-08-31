import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import json
import os
import asyncio
import logging

# RÈGLE : Les commandes slash sont automatiquement enregistrées par bot.add_cog()

WARNINGS_FILE = "warnings.json"
logger = logging.getLogger("bot.moderation")

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.warnings = self._load_warnings()

    def _load_warnings(self):
        """Charge les avertissements avec gestion d'erreurs robuste"""
        if os.path.exists(WARNINGS_FILE):
            try:
                with open(WARNINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    else:
                        logger.warning("Format de données invalide dans warnings.json")
                        return {}
            except json.JSONDecodeError as e:
                logger.error(f"Erreur JSON dans warnings.json: {e}")
                # Sauvegarder l'ancien fichier corrompu
                try:
                    os.rename(WARNINGS_FILE, f"{WARNINGS_FILE}.backup.{int(datetime.now().timestamp())}")
                except:
                    pass
                return {}
            except Exception as e:
                logger.error(f"Erreur lecture warnings.json: {e}")
                return {}
        return {}

    def _save_warnings(self):
        """Sauvegarde les avertissements avec gestion d'erreurs robuste"""
        try:
            # Sauvegarde temporaire d'abord
            temp_file = f"{WARNINGS_FILE}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.warnings, f, indent=2, ensure_ascii=False)
            
            # Remplacer l'ancien fichier
            if os.path.exists(WARNINGS_FILE):
                os.replace(temp_file, WARNINGS_FILE)
            else:
                os.rename(temp_file, WARNINGS_FILE)
        except Exception as e:
            logger.error(f"Erreur sauvegarde warnings: {e}")
            # Nettoyer le fichier temporaire
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

    def _get_user_warnings(self, guild_id: int, user_id: int) -> list:
        """Récupère les avertissements d'un utilisateur avec validation"""
        guild_id = str(guild_id)
        user_id = str(user_id)
        if guild_id not in self.warnings:
            self.warnings[guild_id] = {}
        if user_id not in self.warnings[guild_id]:
            self.warnings[guild_id][user_id] = []
        
        # Validation des avertissements
        warnings = self.warnings[guild_id][user_id]
        if not isinstance(warnings, list):
            warnings = []
            self.warnings[guild_id][user_id] = warnings
        
        return warnings

    @app_commands.command(name="clear", description="Supprimer un nombre de messages dans ce salon")
    @app_commands.describe(amount="Nombre de messages à supprimer")
    async def clear_slash(self, interaction: discord.Interaction, amount: int):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ **Permission refusée.** Vous devez pouvoir gérer les messages.", ephemeral=True)
            return
        if amount < 1 or amount > 100:
            await interaction.response.send_message("❌ **Le nombre doit être entre 1 et 100.**", ephemeral=True)
            return
        
        try:
            # Répondre immédiatement pour éviter le timeout
            await interaction.response.defer(ephemeral=True)
            
            deleted = await interaction.channel.purge(limit=amount)
            embed = discord.Embed(
                title="🧹 **Messages supprimés**",
                description=f"**{len(deleted)}** message(s) ont été supprimés.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            embed.add_field(name="Canal", value=interaction.channel.mention, inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur suppression messages: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ **Erreur lors de la suppression:** {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ **Erreur lors de la suppression:** {str(e)}", ephemeral=True)

    @app_commands.command(name="kick", description="Expulser un membre du serveur")
    @app_commands.describe(member="Membre à expulser", reason="Raison de l'expulsion")
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison spécifiée"):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("❌ **Permission refusée.** Vous devez pouvoir expulser des membres.", ephemeral=True)
            return
        
        # Vérifications de sécurité
        if member == interaction.user:
            await interaction.response.send_message("❌ **Vous ne pouvez pas vous expulser vous-même.**", ephemeral=True)
            return
        
        if member == interaction.guild.owner:
            await interaction.response.send_message("❌ **Vous ne pouvez pas expulser le propriétaire du serveur.**", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ **Vous ne pouvez pas expulser ce membre.**", ephemeral=True)
            return
        
        try:
            await member.kick(reason=f"Par {interaction.user}: {reason}")
            embed = discord.Embed(
                title="👢 **Membre expulsé**",
                description=f"**{member.display_name}** a été expulsé du serveur.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Raison", value=reason, inline=False)
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Erreur expulsion: {e}")
            await interaction.response.send_message(f"❌ **Erreur lors de l'expulsion:** {str(e)}", ephemeral=True)

    @app_commands.command(name="ban", description="Bannir un membre du serveur")
    @app_commands.describe(member="Membre à bannir", reason="Raison du bannissement", delete_days="Nombre de jours de messages à supprimer (0-7)")
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison spécifiée", delete_days: int = 0):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ **Permission refusée.** Vous devez pouvoir bannir des membres.", ephemeral=True)
            return
        
        # Vérifications de sécurité
        if member == interaction.user:
            await interaction.response.send_message("❌ **Vous ne pouvez pas vous bannir vous-même.**", ephemeral=True)
            return
        
        if member == interaction.guild.owner:
            await interaction.response.send_message("❌ **Vous ne pouvez pas bannir le propriétaire du serveur.**", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ **Vous ne pouvez pas bannir ce membre.**", ephemeral=True)
            return
        
        if delete_days < 0 or delete_days > 7:
            await interaction.response.send_message("❌ **delete_days doit être entre 0 et 7.**", ephemeral=True)
            return
        
        try:
            await member.ban(reason=f"Par {interaction.user}: {reason}", delete_message_days=delete_days)
            embed = discord.Embed(
                title="🔨 **Membre banni**",
                description=f"**{member.display_name}** a été banni du serveur.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Raison", value=reason, inline=False)
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            embed.add_field(name="Messages supprimés", value=f"{delete_days} jours", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Erreur bannissement: {e}")
            await interaction.response.send_message(f"❌ **Erreur lors du bannissement:** {str(e)}", ephemeral=True)

    @app_commands.command(name="unban", description="Débannir un utilisateur")
    @app_commands.describe(user_id="ID de l'utilisateur à débannir", reason="Raison du débannissement")
    async def unban_slash(self, interaction: discord.Interaction, user_id: str, reason: str = "Aucune raison spécifiée"):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ **Permission refusée.** Vous devez pouvoir bannir des membres.", ephemeral=True)
            return
        
        try:
            user_id = int(user_id)
            user = await self.bot.fetch_user(user_id)
            await interaction.guild.unban(user, reason=f"Par {interaction.user}: {reason}")
            embed = discord.Embed(
                title="🔓 **Utilisateur débanni**",
                description=f"**{user.display_name}** a été débanni du serveur.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Raison", value=reason, inline=False)
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        except ValueError:
            await interaction.response.send_message("❌ **ID utilisateur invalide.**", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ **Utilisateur non trouvé ou non banni.**", ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur débannissement: {e}")
            await interaction.response.send_message(f"❌ **Erreur lors du débannissement:** {str(e)}", ephemeral=True)

    @app_commands.command(name="warn", description="Avertir un membre")
    @app_commands.describe(member="Membre à avertir", reason="Raison de l'avertissement")
    async def warn_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison spécifiée"):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ **Permission refusée.** Vous devez pouvoir gérer les messages.", ephemeral=True)
            return
        
        # Vérifications de sécurité
        if member == interaction.user:
            await interaction.response.send_message("❌ **Vous ne pouvez pas vous avertir vous-même.**", ephemeral=True)
            return
        
        if member == interaction.guild.owner:
            await interaction.response.send_message("❌ **Vous ne pouvez pas avertir le propriétaire du serveur.**", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ **Vous ne pouvez pas avertir ce membre.**", ephemeral=True)
            return
        
        try:
            warnings = self._get_user_warnings(interaction.guild.id, member.id)
            warning_data = {
                "reason": reason,
                "moderator": interaction.user.id,
                "timestamp": datetime.now().isoformat()
            }
            warnings.append(warning_data)
            self._save_warnings()
            
            embed = discord.Embed(
                title="⚠️ **Membre averti**",
                description=f"**{member.display_name}** a reçu un avertissement.",
                color=discord.Color.yellow(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Raison", value=reason, inline=False)
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            embed.add_field(name="Total d'avertissements", value=len(warnings), inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Erreur avertissement: {e}")
            await interaction.response.send_message(f"❌ **Erreur lors de l'avertissement:** {str(e)}", ephemeral=True)

    @app_commands.command(name="warnings", description="Voir les avertissements d'un membre")
    @app_commands.describe(member="Membre dont voir les avertissements")
    async def warnings_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ **Permission refusée.** Vous devez pouvoir gérer les messages.", ephemeral=True)
            return
        
        try:
            warnings = self._get_user_warnings(interaction.guild.id, member.id)
            if not warnings:
                await interaction.response.send_message(f"✅ **{member.display_name}** n'a aucun avertissement.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"⚠️ **Avertissements de {member.display_name}**",
                description=f"**{len(warnings)}** avertissement(s) au total",
                color=discord.Color.yellow(),
                timestamp=datetime.now()
            )
            
            for i, warning in enumerate(warnings[-5:], 1):  # Afficher les 5 derniers
                try:
                    moderator = interaction.guild.get_member(warning["moderator"])
                    mod_name = moderator.display_name if moderator else "Modérateur inconnu"
                    embed.add_field(
                        name=f"Avertissement #{i}",
                        value=f"**Raison:** {warning['reason']}\n**Modérateur:** {mod_name}\n**Date:** <t:{int(datetime.fromisoformat(warning['timestamp']).timestamp())}:R>",
                        inline=False
                    )
                except Exception as e:
                    logger.error(f"Erreur affichage avertissement: {e}")
                    continue
            
            embed.set_thumbnail(url=member.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur affichage avertissements: {e}")
            await interaction.response.send_message(f"❌ **Erreur lors de l'affichage des avertissements:** {str(e)}", ephemeral=True)

    @app_commands.command(name="unwarn", description="Retirer le dernier avertissement d'un membre")
    @app_commands.describe(member="Membre dont retirer l'avertissement")
    async def unwarn_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ **Permission refusée.** Vous devez pouvoir gérer les messages.", ephemeral=True)
            return
        
        try:
            warnings = self._get_user_warnings(interaction.guild.id, member.id)
            if not warnings:
                await interaction.response.send_message(f"✅ **{member.display_name}** n'a aucun avertissement à retirer.", ephemeral=True)
                return
            
            removed_warning = warnings.pop()
            self._save_warnings()
            
            embed = discord.Embed(
                title="✅ **Avertissement retiré**",
                description=f"Le dernier avertissement de **{member.display_name}** a été retiré.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Raison retirée", value=removed_warning["reason"], inline=False)
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            embed.add_field(name="Avertissements restants", value=len(warnings), inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Erreur retrait avertissement: {e}")
            await interaction.response.send_message(f"❌ **Erreur lors du retrait de l'avertissement:** {str(e)}", ephemeral=True)

    @app_commands.command(name="mute", description="Exclure temporairement un membre")
    @app_commands.describe(member="Membre à exclure", duration="Durée (ex: 10m, 2h, 1d)", reason="Raison de l'exclusion")
    async def mute_slash(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "Aucune raison spécifiée"):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ **Permission refusée.** Vous devez pouvoir gérer les rôles.", ephemeral=True)
            return
        
        # Vérifications de sécurité
        if member == interaction.user:
            await interaction.response.send_message("❌ **Vous ne pouvez pas vous exclure vous-même.**", ephemeral=True)
            return
        
        if member == interaction.guild.owner:
            await interaction.response.send_message("❌ **Vous ne pouvez pas exclure le propriétaire du serveur.**", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ **Vous ne pouvez pas exclure ce membre.**", ephemeral=True)
            return
        
        # Parse duration
        try:
            duration = duration.strip().lower().replace(" ", "")
            total = 0
            num = ''
            units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            for ch in duration:
                if ch.isdigit():
                    num += ch
                elif ch in units and num:
                    total += int(num) * units[ch]
                    num = ''
                else:
                    return await interaction.response.send_message("❌ **Durée invalide. Exemples: 10m, 2h, 1d**", ephemeral=True)
            if num:
                total += int(num)
            if total <= 0:
                return await interaction.response.send_message("❌ **Durée invalide.**", ephemeral=True)
            if total > 2419200:  # 28 jours max
                return await interaction.response.send_message("❌ **Durée trop longue. Maximum 28 jours.**", ephemeral=True)
            mute_duration = timedelta(seconds=total)
        except:
            await interaction.response.send_message("❌ **Durée invalide. Exemples: 10m, 2h, 1d**", ephemeral=True)
            return
        
        try:
            # Exclusion temporaire
            await member.timeout(mute_duration, reason=f"Par {interaction.user}: {reason}")
            
            embed = discord.Embed(
                title="🔇 **Membre exclu temporairement**",
                description=f"**{member.display_name}** a été exclu temporairement.",
                color=discord.Color.dark_grey(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Raison", value=reason, inline=False)
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            embed.add_field(name="Durée", value=f"{mute_duration}", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Erreur exclusion: {e}")
            await interaction.response.send_message(f"❌ **Erreur lors de l'exclusion:** {str(e)}", ephemeral=True)

    @app_commands.command(name="unmute", description="Retirer l'exclusion d'un membre")
    @app_commands.describe(member="Membre à unexclude")
    async def unmute_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ **Permission refusée.** Vous devez pouvoir gérer les rôles.", ephemeral=True)
            return
        
        if not member.timed_out:
            await interaction.response.send_message(f"✅ **{member.display_name}** n'est pas exclu.", ephemeral=True)
            return
        
        try:
            await member.timeout(None, reason=f"Par {interaction.user}")
            embed = discord.Embed(
                title="🔊 **Exclusion retirée**",
                description=f"**{member.display_name}** n'est plus exclu.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Erreur retrait exclusion: {e}")
            await interaction.response.send_message(f"❌ **Erreur lors du retrait de l'exclusion:** {str(e)}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))

