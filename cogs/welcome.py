import discord
from discord.ext import commands
import json
import os
import logging

# RÈGLE : Les commandes slash sont automatiquement enregistrées par bot.add_cog()
# Note: Ce cog n'a que des événements, pas de commandes slash

WELCOME_CHANNEL_ID = 1409924674519040122
MEMBER_ROLE_ID = 1352191536955396118
BRAND_THUMB_URL = "https://cdn.discordapp.com/attachments/1404572567645192373/1410640091726221393/download_20.jpg?ex=68b1c076&is=68b06ef6&hm=f0f1a9423d2866aa178f200f4b9e2feb184ac4618aba163d9eb57df99003cbf7&"
INVITE_STATS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "invite_stats.json")
logger = logging.getLogger("bot.welcome")


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> { code: {"uses": int, "inviter_id": int|None} }
        self.invites_cache: dict[int, dict[str, dict]] = {}
        # Stats persistées par guilde
        # {
        #   "guilds": {
        #     "<guild_id>": {
        #        "member_to_inviter": {"<member_id>": "<inviter_id>"},
        #        "net_invites": {"<inviter_id>": <count>}
        #     }
        #   }
        # }
        self.invite_stats: dict = {"guilds": {}}
        self._load_invite_stats()

    def _load_invite_stats(self):
        """Charge les statistiques d'invitations avec gestion d'erreurs robuste"""
        try:
            if os.path.exists(INVITE_STATS_FILE):
                with open(INVITE_STATS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    if "guilds" in data:
                        self.invite_stats = data
                    else:
                        # Migration d'anciens formats: repartir sur base propre
                        logger.warning("Format de données invalide dans invite_stats.json, redémarrage avec structure propre")
                        self.invite_stats = {"guilds": {}}
                else:
                    logger.warning("Type de données invalide dans invite_stats.json")
                    self.invite_stats = {"guilds": {}}
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON dans invite_stats.json: {e}")
            # Sauvegarder l'ancien fichier corrompu
            try:
                os.rename(INVITE_STATS_FILE, f"{INVITE_STATS_FILE}.backup.{int(discord.utils.utcnow().timestamp())}")
            except:
                pass
            self.invite_stats = {"guilds": {}}
        except Exception as e:
            logger.error(f"Erreur lecture invite_stats.json: {e}")
            self.invite_stats = {"guilds": {}}

    def _save_invite_stats(self):
        """Sauvegarde les statistiques d'invitations avec gestion d'erreurs robuste"""
        try:
            # Sauvegarde temporaire d'abord
            temp_file = f"{INVITE_STATS_FILE}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.invite_stats, f, ensure_ascii=False, indent=2)
            
            # Remplacer l'ancien fichier
            if os.path.exists(INVITE_STATS_FILE):
                os.replace(temp_file, INVITE_STATS_FILE)
            else:
                os.rename(temp_file, INVITE_STATS_FILE)
        except Exception as e:
            logger.error(f"Erreur sauvegarde invite_stats: {e}")
            # Nettoyer le fichier temporaire
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

    def _get_guild_stats(self, guild_id: int) -> dict:
        """Récupère les statistiques d'une guilde avec validation"""
        guilds = self.invite_stats.setdefault("guilds", {})
        gstats = guilds.setdefault(str(guild_id), {})
        gstats.setdefault("member_to_inviter", {})
        gstats.setdefault("net_invites", {})
        return gstats

    async def refresh_invites(self, guild: discord.Guild):
        """Rafraîchit le cache des invitations avec gestion d'erreurs"""
        data: dict[str, dict] = {}
        try:
            invites = await guild.invites()
            for inv in invites:
                code = inv.code
                uses = inv.uses or 0
                inviter_id = inv.inviter.id if inv.inviter else None
                data[code] = {"uses": uses, "inviter_id": inviter_id}
        except discord.Forbidden:
            logger.warning(f"Pas de permission pour lister les invitations dans {guild.id}")
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement des invitations pour {guild.id}: {e}")
            # Si impossible de lister, préserver au moins une structure vide
        self.invites_cache[guild.id] = data

    async def get_inviter_from_delta(self, guild: discord.Guild, before: dict, after: dict):
        """Détermine l'inviteur en comparant les invitations avant/après"""
        # Chercher un code dont les uses ont augmenté
        try:
            for code, a in after.items():
                b_uses = before.get(code, {"uses": 0}).get("uses", 0)
                if a.get("uses", 0) > b_uses:
                    inviter_id = a.get("inviter_id")
                    if inviter_id:
                        try:
                            return await guild.fetch_member(inviter_id)
                        except discord.NotFound:
                            try:
                                return await self.bot.fetch_user(inviter_id)
                            except discord.NotFound:
                                logger.warning(f"Inviteur {inviter_id} non trouvé")
                                return None
                        except Exception as e:
                            logger.error(f"Erreur récupération inviteur {inviter_id}: {e}")
                            return None
                    try:
                        inv = await guild.fetch_invite(code)
                        return inv.inviter
                    except Exception as e:
                        logger.error(f"Erreur récupération invitation {code}: {e}")
                        return None
            # Vanity URL ou autre cas
            try:
                vanity = await guild.vanity_invite()
                if vanity is not None:
                    return None
            except discord.HTTPException:
                # Pas de vanity URL
                pass
            except Exception as e:
                logger.error(f"Erreur vérification vanity URL: {e}")
        except Exception as e:
            logger.error(f"Erreur détermination inviteur: {e}")
        return None

    def _get_net_invites(self, guild_id: int, inviter_id: int | None) -> int | None:
        """Récupère le nombre net d'invitations d'un utilisateur"""
        if inviter_id is None:
            return None
        gstats = self._get_guild_stats(guild_id)
        return int(gstats["net_invites"].get(str(inviter_id), 0))

    @commands.Cog.listener()
    async def on_guild_available(self, guild: discord.Guild):
        """Rafraîchit les invitations quand une guilde redevient disponible"""
        await self.refresh_invites(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        """Rafraîchit les invitations quand une nouvelle est créée"""
        guild = invite.guild
        if guild:
            await self.refresh_invites(guild)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        """Rafraîchit les invitations quand une est supprimée"""
        guild = invite.guild
        if guild:
            await self.refresh_invites(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Gère l'arrivée d'un nouveau membre"""
        guild = member.guild
        
        # Donner le rôle membre dès l'arrivée (propre, avec garde-fous)
        try:
            role = guild.get_role(MEMBER_ROLE_ID)
            if role and role not in member.roles:
                await member.add_roles(role, reason="Attribution automatique du rôle membre à l'arrivée")
        except discord.Forbidden:
            logger.warning(f"Pas de permission pour ajouter le rôle membre dans {guild.id}")
        except Exception as e:
            logger.error(f"Erreur attribution rôle membre: {e}")

        # Détection de l'inviteur
        before = self.invites_cache.get(guild.id, {})
        await self.refresh_invites(guild)
        after = self.invites_cache.get(guild.id, {})

        inviter = await self.get_inviter_from_delta(guild, before, after)
        inviter_id = int(getattr(inviter, "id", 0)) if inviter is not None else None
        
        # Mise à jour des stats nettes
        try:
            gstats = self._get_guild_stats(guild.id)
            prev_inviter_id = gstats["member_to_inviter"].get(str(member.id))
            if inviter_id is not None:
                if prev_inviter_id is None:
                    # Nouveau: +1 net
                    cur = int(gstats["net_invites"].get(str(inviter_id), 0))
                    gstats["net_invites"][str(inviter_id)] = cur + 1
                elif str(prev_inviter_id) != str(inviter_id):
                    # Changement d'inviteur: +1 pour le nouveau (l'ancien a été décrémenté au départ)
                    cur = int(gstats["net_invites"].get(str(inviter_id), 0))
                    gstats["net_invites"][str(inviter_id)] = cur + 1
                # Si identique: rejoin → pas d'incrément
                gstats["member_to_inviter"][str(member.id)] = str(inviter_id)
                self._save_invite_stats()
        except Exception as e:
            logger.error(f"Erreur mise à jour stats invitations: {e}")

        # Message de bienvenue
        channel = guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            try:
                color_black = discord.Color(0x000000)
                embed = discord.Embed(
                    title="Bienvenue",
                    description=None,
                    color=color_black
                )
                # Colonnes symétriques
                embed.add_field(name="Membre", value=member.mention, inline=True)
                if inviter:
                    inviter_value = getattr(inviter, 'mention', None)
                    if not inviter_value:
                        inviter_value = getattr(inviter, 'display_name', getattr(inviter, 'name', 'Inconnu'))
                else:
                    inviter_value = "Inconnu"
                embed.add_field(name="Invité par", value=inviter_value, inline=True)
                net_val = self._get_net_invites(guild.id, inviter_id)
                invites_value = str(net_val) if net_val is not None else "N/A"
                embed.add_field(name="Nombre d'invite", value=invites_value, inline=True)
                # Image de bannière en premier plan (pleine largeur)
                embed.set_image(url=BRAND_THUMB_URL)

                await channel.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Pas de permission pour envoyer le message de bienvenue dans {channel.id}")
            except Exception as e:
                logger.error(f"Erreur envoi message bienvenue: {e}")
                # Fallback texte si l'embed échoue
                try:
                    inv_display = inviter.mention if isinstance(inviter, discord.Member) else (getattr(inviter, 'name', 'Inconnu') if inviter else 'Inconnu')
                    net_val = self._get_net_invites(guild.id, inviter_id)
                    extra = f" (Invites: {net_val})" if net_val is not None else ""
                    await channel.send(f"Bienvenue {member.mention} ! Invité par {inv_display}{extra}.")
                except Exception as e2:
                    logger.error(f"Erreur fallback message bienvenue: {e2}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Gère le départ d'un membre"""
        # Quand un membre quitte, décrémenter le net pour son inviteur d'origine
        try:
            gstats = self._get_guild_stats(member.guild.id)
            inviter_id_str = gstats["member_to_inviter"].get(str(member.id))
            if inviter_id_str is not None:
                cur = int(gstats["net_invites"].get(str(inviter_id_str), 0))
                gstats["net_invites"][str(inviter_id_str)] = max(0, cur - 1)
                # Nettoyer l'association
                try:
                    del gstats["member_to_inviter"][str(member.id)]
                except KeyError:
                    pass
                self._save_invite_stats()
        except Exception as e:
            logger.error(f"Erreur mise à jour stats départ membre: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))

