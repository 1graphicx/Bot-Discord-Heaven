import discord
from discord.ext import commands
from discord import app_commands

# RÈGLE : Les commandes slash sont automatiquement enregistrées par bot.add_cog()


class SavedCmds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.saved_commands: dict[int, dict[int, list[str]]] = {}

    @app_commands.command(name="save", description="Sauvegarder les 25 derniers messages d'un membre dans un slot")
    @app_commands.describe(slot="Numéro de slot", member="Membre")
    async def save_slash(self, interaction: discord.Interaction, slot: int, member: discord.Member):
        messages: list[str] = []
        async for msg in interaction.channel.history(limit=150):
            if msg.author == member:
                if msg.content:
                    messages.append(msg.content)
            if len(messages) == 25:
                break
        if member.id not in self.saved_commands:
            self.saved_commands[member.id] = {}
        self.saved_commands[member.id][slot] = messages
        embed = discord.Embed(
            title="Commande enregistrée !",
            description=f"Les 25 derniers messages de {member.mention} ont été sauvegardés dans le slot {slot}.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cmd", description="Afficher une commande sauvegardée d'un membre par slot")
    @app_commands.describe(member="Membre concerné")
    async def cmd_slash(self, interaction: discord.Interaction, member: discord.Member):
        slots = self.saved_commands.get(member.id)
        if not slots:
            await interaction.response.send_message(f"Aucune commande enregistrée pour {member.mention}.", ephemeral=True)
            return
        slot_list = "\n".join([f"{i}. Slot {i}" for i in slots.keys()])
        embed = discord.Embed(
            title=f"Commandes sauvegardées pour {member.display_name}",
            description=f"Choisis le numéro du slot à afficher :\n{slot_list}\n\nRéponds par le numéro du slot.",
            color=discord.Color.purple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        def check(m: discord.Message):
            return m.author == interaction.user and m.channel == interaction.channel and m.content.isdigit() and int(m.content) in slots

        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            slot = int(msg.content)
            messages = slots[slot]
            if not messages:
                await interaction.followup.send(f"Le slot {slot} est vide pour {member.mention}.", ephemeral=True)
                return
            # Tri par catégories simples
            banner_msgs = [m for m in messages if "bannière" in m.lower()]
            logo_msgs = [m for m in messages if "logo" in m.lower()]
            color_msgs = [m for m in messages if "couleur" in m.lower()]
            text_msgs = [m for m in messages if "texte" in m.lower()]
            format_msgs = [m for m in messages if "format" in m.lower()]
            deadline_msgs = [m for m in messages if "dead" in m.lower() or "date" in m.lower()]
            other_msgs = [m for m in messages if m not in banner_msgs + logo_msgs + color_msgs + text_msgs + format_msgs + deadline_msgs]

            embed2 = discord.Embed(
                title=f"Commande structurée - Slot {slot} de {member.display_name}",
                color=discord.Color.green(),
            )
            if banner_msgs:
                embed2.add_field(name="🖼️ Bannière", value="\n".join(banner_msgs), inline=False)
            if logo_msgs:
                embed2.add_field(name="🎨 Logo", value="\n".join(logo_msgs), inline=False)
            if color_msgs:
                embed2.add_field(name="🌈 Couleurs", value="\n".join(color_msgs), inline=False)
            if text_msgs:
                embed2.add_field(name="✏️ Texte", value="\n".join(text_msgs), inline=False)
            if format_msgs:
                embed2.add_field(name="📐 Format", value="\n".join(format_msgs), inline=False)
            if deadline_msgs:
                embed2.add_field(name="⏰ Deadline/Date", value="\n".join(deadline_msgs), inline=False)
            if other_msgs:
                embed2.add_field(name="📋 Autres infos", value="\n".join(other_msgs), inline=False)

            await interaction.followup.send(embed=embed2, ephemeral=True)
        except Exception:
            await interaction.followup.send("Aucune réponse ou slot invalide. Commande annulée.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SavedCmds(bot))

