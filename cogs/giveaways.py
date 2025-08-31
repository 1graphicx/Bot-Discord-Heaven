import asyncio
from datetime import datetime, timedelta, timezone
import random
import discord
from discord.ext import commands
from discord import app_commands

GW_REACTION = "🎉"


def parse_duration(text: str) -> timedelta | None:
    try:
        text = text.strip().lower().replace(" ", "")
        total = 0
        num = ''
        units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        for ch in text:
            if ch.isdigit():
                num += ch
            elif ch in units and num:
                total += int(num) * units[ch]
                num = ''
            else:
                return None
        if num:
            total += int(num)
        if total <= 0:
            return None
        return timedelta(seconds=total)
    except Exception:
        return None


def format_timedelta(td: timedelta) -> str:
    seconds = int(td.total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}j")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def build_gw_embed(title: str, description: str, color: discord.Color, image_url: str | None = None) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_author(name="Giveaway", icon_url="https://cdn-icons-png.flaticon.com/512/942/942748.png")
    embed.set_footer(text="Participe avec 🎉 | Bonne chance ✨")
    if image_url:
        embed.set_image(url=image_url)
    return embed


class Giveaways(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active: dict[int, dict] = {}

    async def schedule_end(self, message_id: int):
        data = self.active.get(message_id)
        if not data:
            return
        now = datetime.now(timezone.utc)
        remaining = (data['end_at'] - now).total_seconds()
        if remaining > 0:
            try:
                await asyncio.sleep(remaining)
            except Exception:
                pass
        # fetch message
        channel = self.bot.get_channel(data['channel_id'])
        if channel is None:
            self.active.pop(message_id, None)
            return
        try:
            msg = await channel.fetch_message(message_id)
        except Exception:
            self.active.pop(message_id, None)
            return
        # collect entrants by scanning reactions
        entrants_set = set(data['entrants'])
        for reaction in msg.reactions:
            try:
                if (reaction.emoji == GW_REACTION) or (getattr(reaction.emoji, 'name', None) == GW_REACTION):
                    async for user in reaction.users():
                        if not user.bot:
                            entrants_set.add(user.id)
            except Exception:
                pass
        entrants = list(entrants_set)
        if not entrants:
            embed = build_gw_embed(
                title=f"{GW_REACTION} Giveaway terminé — Aucun gagnant",
                description=f"Récompense: **{data['prize']}**\nAucune participation valide.",
                color=discord.Color.red(),
                image_url=data.get('image_url'),
            )
            await msg.edit(embed=embed)
            self.active.pop(message_id, None)
            return
        winners_count = min(data['winners_count'], len(entrants))
        preferred = [uid for uid in entrants if uid in data.get('preferred_winners', set())]
        others = [uid for uid in entrants if uid not in data.get('preferred_winners', set())]
        winners_ids: list[int] = []
        if preferred:
            take = min(winners_count, len(preferred))
            winners_ids.extend(random.sample(preferred, take))
        if len(winners_ids) < winners_count and others:
            winners_ids.extend(random.sample(others, winners_count - len(winners_ids)))
        winners_mentions = " ".join([f"<@{uid}>" for uid in winners_ids])

        if data.get('is_fast'):
            announce = await channel.send(f"{GW_REACTION} Félicitations {winners_mentions} ! DM le bot pour valider ton gain.")
            start_wait = datetime.now(timezone.utc)
            def dm_check(m: discord.Message):
                return m.author.id in winners_ids and isinstance(m.channel, discord.DMChannel)
            try:
                dm_msg = await self.bot.wait_for('message', timeout=3600, check=dm_check)
                elapsed = datetime.now(timezone.utc) - start_wait
                await channel.send(f"{dm_msg.author.mention} a DM le bot en {format_timedelta(elapsed)}. Bravo !")
            except asyncio.TimeoutError:
                await channel.send("Aucun DM reçu des gagnants dans l'heure.")

        embed = build_gw_embed(
            title=f"{GW_REACTION} Giveaway terminé",
            description=(
                f"Récompense: **{data['prize']}**\n"
                f"Gagnant(s): {winners_mentions}\n"
                f"Host: <@{data['host_id']}>"
            ),
            color=discord.Color.green(),
            image_url=data.get('image_url'),
        )
        await msg.edit(embed=embed)
        self.active.pop(message_id, None)

    async def schedule_countdown(self, message_id: int):
        while message_id in self.active:
            data = self.active[message_id]
            channel = self.bot.get_channel(data['channel_id'])
            if channel is None:
                return
            try:
                msg = await channel.fetch_message(message_id)
            except Exception:
                return
            remaining_td = max(timedelta(0), data['end_at'] - datetime.now(timezone.utc))
            end_ts = int(data['end_at'].timestamp())
            description = (
                f"Récompense: **{data['prize']}**\n"
                f"Fin: **<t:{end_ts}:R>** (reste {format_timedelta(remaining_td)})\n"
                f"Gagnant(s): **{data['winners_count']}**\n"
                f"Host: <@{data['host_id']}>"
            )
            embed = build_gw_embed(title=f"{GW_REACTION} GIVEAWAY", description=description, color=discord.Color.blurple(), image_url=data.get('image_url'))
            try:
                await msg.edit(embed=embed)
            except Exception:
                pass
            await asyncio.sleep(1)

    async def create_gw_message(self, interaction: discord.Interaction, prize: str, td: timedelta, winners: int, image_url: str | None, is_fast: bool):
        end_at = datetime.now(timezone.utc) + td
        description = (
            f"Récompense: **{prize}**\n"
            f"Fin dans: **{format_timedelta(td)}**\n"
            f"Gagnant(s): **{winners}**\n"
            f"Host: {interaction.user.mention}"
        )
        embed = build_gw_embed(title=f"{GW_REACTION} GIVEAWAY" + (" (FAST)" if is_fast else ""), description=description, color=discord.Color.blurple(), image_url=image_url)
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        try:
            await msg.add_reaction(GW_REACTION)
        except Exception:
            pass
        data = {
            'message_id': msg.id,
            'channel_id': msg.channel.id,
            'host_id': interaction.user.id,
            'prize': prize,
            'end_at': end_at,
            'entrants': set(),
            'winners_count': int(winners),
            'image_url': image_url,
            'is_fast': is_fast,
            'preferred_winners': set(),
        }
        self.active[msg.id] = data
        asyncio.create_task(self.schedule_end(msg.id))
        asyncio.create_task(self.schedule_countdown(msg.id))

    # -------- slash command group
    group = app_commands.Group(name="gw", description="Giveaways professionnels")

    @group.command(name="create", description="Créer un giveaway")
    @app_commands.describe(prize="Nom / récompense", duration="Durée (ex: 10m, 2h, 1d2h)", winners="Nombre de gagnants", image_url="URL d'image (optionnel)")
    async def gw_create(self, interaction: discord.Interaction, prize: str, duration: str, winners: int, image_url: str | None = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
            return
        td = parse_duration(duration)
        if not td:
            await interaction.response.send_message("Durée invalide.", ephemeral=True)
            return
        if winners < 1 or winners > 25:
            await interaction.response.send_message("Nombre de gagnants entre 1 et 25.", ephemeral=True)
            return
        await self.create_gw_message(interaction, prize, td, winners, image_url, is_fast=False)

    @group.command(name="fast", description="Créer un giveaway FAST (attend DM du gagnant)")
    async def gw_fast(self, interaction: discord.Interaction, prize: str, duration: str, winners: int, image_url: str | None = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
            return
        td = parse_duration(duration)
        if not td:
            await interaction.response.send_message("Durée invalide.", ephemeral=True)
            return
        if winners < 1 or winners > 25:
            await interaction.response.send_message("Nombre de gagnants entre 1 et 25.", ephemeral=True)
            return
        await self.create_gw_message(interaction, prize, td, winners, image_url, is_fast=True)

    @group.command(name="end", description="Terminer le dernier giveaway du salon")
    async def gw_end(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
            return
        target = None
        for mid, d in list(self.active.items()):
            if d['channel_id'] == interaction.channel_id:
                target = mid
        if not target:
            await interaction.response.send_message("Aucun giveaway actif dans ce salon.", ephemeral=True)
            return
        self.active[target]['end_at'] = datetime.now(timezone.utc)
        await interaction.response.send_message("Giveaway terminé manuellement.", ephemeral=True)
        asyncio.create_task(self.schedule_end(target))

    @group.command(name="edit", description="Modifier le dernier giveaway du salon")
    async def gw_edit(self, interaction: discord.Interaction, prize: str | None = None, duration: str | None = None, winners: int | None = None, image_url: str | None = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
            return
        target = None
        for mid, d in list(self.active.items()):
            if d['channel_id'] == interaction.channel_id:
                target = mid
        if not target:
            await interaction.response.send_message("Aucun giveaway actif à modifier.", ephemeral=True)
            return
        data = self.active[target]
        if prize:
            data['prize'] = prize
        if duration:
            td = parse_duration(duration)
            if not td:
                await interaction.response.send_message("Durée invalide.", ephemeral=True)
                return
            data['end_at'] = datetime.now(timezone.utc) + td
        if winners is not None:
            if winners < 1 or winners > 25:
                await interaction.response.send_message("Nombre de gagnants entre 1 et 25.", ephemeral=True)
                return
            data['winners_count'] = int(winners)
        if image_url is not None:
            data['image_url'] = image_url
        channel = self.bot.get_channel(data['channel_id'])
        try:
            msg = await channel.fetch_message(target)
        except Exception:
            await interaction.response.send_message("Impossible de mettre à jour le message.", ephemeral=True)
            return
        remaining = max(timedelta(0), data['end_at'] - datetime.now(timezone.utc))
        description = (
            f"Récompense: **{data['prize']}**\n"
            f"Fin dans: **{format_timedelta(remaining)}**\n"
            f"Gagnant(s): **{data['winners_count']}**\n"
            f"Host: <@{data['host_id']}>"
        )
        embed = build_gw_embed(title=f"{GW_REACTION} GIVEAWAY", description=description, color=discord.Color.blurple(), image_url=data.get('image_url'))
        await msg.edit(embed=embed)
        await interaction.response.send_message("Giveaway mis à jour.", ephemeral=True)

    @group.command(name="start", description="Choisir manuellement le(s) gagnant(s)")
    async def gw_start(self, interaction: discord.Interaction, user1: discord.User, user2: discord.User | None = None, user3: discord.User | None = None, user4: discord.User | None = None, user5: discord.User | None = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
            return
        target = None
        for mid, d in list(self.active.items()):
            if d['channel_id'] == interaction.channel_id:
                target = mid
        if not target:
            await interaction.response.send_message("Aucun giveaway actif.", ephemeral=True)
            return
        winners = [u for u in [user1, user2, user3, user4, user5] if u is not None]
        if not winners:
            await interaction.response.send_message("Aucun gagnant fourni.", ephemeral=True)
            return
        ids = [u.id for u in winners]
        data = self.active[target]
        data['entrants'] = set(ids)
        data['winners_count'] = len(ids)
        data['end_at'] = datetime.now(timezone.utc)
        await interaction.response.send_message("Gagnants sélectionnés. Fin immédiate.", ephemeral=True)
        asyncio.create_task(self.schedule_end(target))

    @group.command(name="strat", description="Pré-sélectionner en cachette le(s) gagnant(s)")
    async def gw_strat(self, interaction: discord.Interaction, user1: discord.User, user2: discord.User | None = None, user3: discord.User | None = None, user4: discord.User | None = None, user5: discord.User | None = None):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
            return
        target = None
        for mid, d in list(self.active.items()):
            if d['channel_id'] == interaction.channel_id:
                target = mid
        if not target:
            await interaction.response.send_message("Aucun giveaway actif dans ce salon.", ephemeral=True)
            return
        picks = [u for u in [user1, user2, user3, user4, user5] if u is not None]
        data = self.active[target]
        data['preferred_winners'] = set([u.id for u in picks])
        await interaction.response.send_message("Gagnant(s) prédit(s). Ils seront privilégiés lors du tirage.", ephemeral=True)

    # reaction listeners
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.message_id in self.active and (payload.emoji.name == GW_REACTION):
            guild = self.bot.get_guild(payload.guild_id)
            member = None
            try:
                member = await guild.fetch_member(payload.user_id)
            except Exception:
                pass
            if not (member and member.bot):
                data = self.active[payload.message_id]
                data['entrants'].add(payload.user_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.message_id in self.active and (payload.emoji.name == GW_REACTION):
            data = self.active[payload.message_id]
            try:
                data['entrants'].discard(payload.user_id)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    cog = Giveaways(bot)
    await bot.add_cog(cog)
    # Attacher le groupe slash sur l'arbre
    try:
        bot.tree.add_command(cog.group)
    except Exception:
        pass

