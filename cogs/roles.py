import json
import discord
from discord.ext import commands
from discord import app_commands

# RÈGLE : Les commandes slash sont automatiquement enregistrées par bot.add_cog()

ROLE_HOMME_ID = 1409863642207359057
ROLE_FEMME_ID = 1409874503919730789
ROLE_MINEUR_ID = 1409882148336308245
ROLE_MAJEUR_ID = 1409882350514343966

EMOJI_HOMME = "👕"
EMOJI_FEMME = "👗"
EMOJI_MINEUR = "⛏"
EMOJI_MAJEUR = "🔞"

CHANNEL_ID = 1373016949201698970

GIF_GENRE_URL = "https://i.pinimg.com/originals/f5/f2/74/f5f27448c036af645c27467c789ad759.gif"
GIF_AGE_URL = "https://mugen.karaokes.moe/images/articles/ngioaezb.gif"

STATE_FILE = "reaction_roles.json"


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_id_genre: int | None = None
        self.message_id_age: int | None = None
        self._load_state()

    # -------- persistence
    def _save_state(self):
        data = {
            "message_id_genre": self.message_id_genre,
            "message_id_age": self.message_id_age,
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _load_state(self):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.message_id_genre = data.get("message_id_genre")
                self.message_id_age = data.get("message_id_age")
        except Exception:
            pass

    # -------- commands
    @app_commands.command(name="role", description="Publier les messages de rôles réactifs")
    async def role_slash(self, interaction: discord.Interaction):
        embed_genre = discord.Embed(
            title="De quel genre es-tu ?",
            description="Réagis avec 👕 pour le rôle homme ou 👗 pour le rôle femme.",
            color=discord.Color.blue(),
        )
        embed_genre.set_image(url=GIF_GENRE_URL)
        await interaction.response.send_message(embed=embed_genre)
        msg_genre = await interaction.original_response()
        await msg_genre.add_reaction(EMOJI_HOMME)
        await msg_genre.add_reaction(EMOJI_FEMME)
        self.message_id_genre = msg_genre.id

        embed_age = discord.Embed(
            title="Quel est ton statut d’âge ?",
            description="Réagis avec ⛏ pour mineur ou 🔞 pour majeur.",
            color=discord.Color.red(),
        )
        embed_age.set_image(url=GIF_AGE_URL)
        msg_age = await interaction.channel.send(embed=embed_age)
        await msg_age.add_reaction(EMOJI_MINEUR)
        await msg_age.add_reaction(EMOJI_MAJEUR)
        self.message_id_age = msg_age.id
        self._save_state()

    # -------- events
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        if self.message_id_genre and payload.message_id == self.message_id_genre:
            if payload.emoji.name == EMOJI_HOMME:
                role = guild.get_role(ROLE_HOMME_ID)
                member = await guild.fetch_member(payload.user_id)
                if role and member:
                    await member.add_roles(role)
            elif payload.emoji.name == EMOJI_FEMME:
                role = guild.get_role(ROLE_FEMME_ID)
                member = await guild.fetch_member(payload.user_id)
                if role and member:
                    await member.add_roles(role)
        if self.message_id_age and payload.message_id == self.message_id_age:
            if payload.emoji.name == EMOJI_MINEUR:
                role = guild.get_role(ROLE_MINEUR_ID)
                member = await guild.fetch_member(payload.user_id)
                if role and member:
                    await member.add_roles(role)
            elif payload.emoji.name == EMOJI_MAJEUR:
                role = guild.get_role(ROLE_MAJEUR_ID)
                member = await guild.fetch_member(payload.user_id)
                if role and member:
                    await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        if self.message_id_genre and payload.message_id == self.message_id_genre:
            if payload.emoji.name == EMOJI_HOMME:
                role = guild.get_role(ROLE_HOMME_ID)
                member = await guild.fetch_member(payload.user_id)
                if role and member:
                    await member.remove_roles(role)
            elif payload.emoji.name == EMOJI_FEMME:
                role = guild.get_role(ROLE_FEMME_ID)
                member = await guild.fetch_member(payload.user_id)
                if role and member:
                    await member.remove_roles(role)
        if self.message_id_age and payload.message_id == self.message_id_age:
            if payload.emoji.name == EMOJI_MINEUR:
                role = guild.get_role(ROLE_MINEUR_ID)
                member = await guild.fetch_member(payload.user_id)
                if role and member:
                    await member.remove_roles(role)
            elif payload.emoji.name == EMOJI_MAJEUR:
                role = guild.get_role(ROLE_MAJEUR_ID)
                member = await guild.fetch_member(payload.user_id)
                if role and member:
                    await member.remove_roles(role)


async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot))

