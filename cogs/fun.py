import discord
from discord.ext import commands
from discord import app_commands
import random

# RÈGLE : Les commandes slash sont automatiquement enregistrées par bot.add_cog()
from datetime import datetime

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="8ball", description="Poser une question à la boule magique")
    @app_commands.describe(question="Votre question")
    async def eightball_slash(self, interaction: discord.Interaction, question: str):
        responses = [
            "🎱 C'est certain.",
            "🎱 C'est décidément ainsi.",
            "🎱 Sans aucun doute.",
            "🎱 Oui, définitivement.",
            "🎱 Vous pouvez compter dessus.",
            "🎱 Comme je le vois, oui.",
            "🎱 Très probablement.",
            "🎱 Les perspectives sont bonnes.",
            "🎱 Oui.",
            "🎱 Les signes pointent vers oui.",
            "🎱 Réponse floue, réessayez.",
            "🎱 Redemandez plus tard.",
            "🎱 Il vaut mieux ne pas vous le dire maintenant.",
            "🎱 Impossible de prédire maintenant.",
            "🎱 Concentrez-vous et redemandez.",
            "🎱 Ne comptez pas dessus.",
            "🎱 Ma réponse est non.",
            "🎱 Mes sources disent non.",
            "🎱 Les perspectives ne sont pas très bonnes.",
            "🎱 Très douteux."
        ]
        
        embed = discord.Embed(
            title="🎱 Boule Magique",
            description=f"**Question:** {question}",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Réponse", value=random.choice(responses), inline=False)
        embed.set_footer(text=f"Demandé par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip", description="Lancer une pièce")
    async def coinflip_slash(self, interaction: discord.Interaction):
        result = random.choice(["Pile", "Face"])
        emoji = "🪙" if result == "Pile" else "🪙"
        
        embed = discord.Embed(
            title="🪙 Lancer de Pièce",
            description=f"La pièce tourne...",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Résultat", value=f"{emoji} **{result}**", inline=False)
        embed.set_footer(text=f"Lancé par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dice", description="Lancer un ou plusieurs dés")
    @app_commands.describe(number="Nombre de dés (1-10)", sides="Nombre de faces (2-100)")
    async def dice_slash(self, interaction: discord.Interaction, number: int = 1, sides: int = 6):
        if number < 1 or number > 10:
            await interaction.response.send_message("Le nombre de dés doit être entre 1 et 10.", ephemeral=True)
            return
        if sides < 2 or sides > 100:
            await interaction.response.send_message("Le nombre de faces doit être entre 2 et 100.", ephemeral=True)
            return
        
        results = [random.randint(1, sides) for _ in range(number)]
        total = sum(results)
        
        embed = discord.Embed(
            title="🎲 Lancer de Dés",
            description=f"Lancement de **{number}** dé(s) à **{sides}** faces",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Résultats", value=", ".join(map(str, results)), inline=True)
        embed.add_field(name="Total", value=f"**{total}**", inline=True)
        embed.set_footer(text=f"Lancé par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rps", description="Pierre, Papier, Ciseaux")
    @app_commands.describe(choice="Votre choix")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Pierre 🪨", value="pierre"),
        app_commands.Choice(name="Papier 📄", value="papier"),
        app_commands.Choice(name="Ciseaux ✂️", value="ciseaux")
    ])
    async def rps_slash(self, interaction: discord.Interaction, choice: str):
        bot_choice = random.choice(["pierre", "papier", "ciseaux"])
        
        # Déterminer le gagnant
        if choice == bot_choice:
            result = "Égalité! 🤝"
            color = discord.Color.greyple()
        elif (
            (choice == "pierre" and bot_choice == "ciseaux") or
            (choice == "papier" and bot_choice == "pierre") or
            (choice == "ciseaux" and bot_choice == "papier")
        ):
            result = "Vous gagnez! 🎉"
            color = discord.Color.green()
        else:
            result = "Je gagne! 😎"
            color = discord.Color.red()
        
        # Emojis pour les choix
        choice_emojis = {"pierre": "🪨", "papier": "📄", "ciseaux": "✂️"}
        
        embed = discord.Embed(
            title="🪨📄✂️ Pierre, Papier, Ciseaux",
            description=f"**{result}**",
            color=color,
            timestamp=datetime.now()
        )
        embed.add_field(name="Votre choix", value=f"{choice_emojis[choice]} {choice.title()}", inline=True)
        embed.add_field(name="Mon choix", value=f"{choice_emojis[bot_choice]} {bot_choice.title()}", inline=True)
        embed.set_footer(text=f"Joué par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="random", description="Générer un nombre aléatoire")
    @app_commands.describe(min_value="Valeur minimum", max_value="Valeur maximum")
    async def random_slash(self, interaction: discord.Interaction, min_value: int, max_value: int):
        if min_value > max_value:
            min_value, max_value = max_value, min_value
        
        if max_value - min_value > 1000000:
            await interaction.response.send_message("L'intervalle est trop grand. Maximum 1,000,000.", ephemeral=True)
            return
        
        result = random.randint(min_value, max_value)
        
        embed = discord.Embed(
            title="🎲 Nombre Aléatoire",
            description=f"Entre **{min_value}** et **{max_value}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Résultat", value=f"**{result}**", inline=False)
        embed.set_footer(text=f"Généré par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="choose", description="Choisir aléatoirement parmi des options")
    @app_commands.describe(options="Options séparées par des virgules")
    async def choose_slash(self, interaction: discord.Interaction, options: str):
        choices = [opt.strip() for opt in options.split(",") if opt.strip()]
        
        if len(choices) < 2:
            await interaction.response.send_message("Donnez au moins 2 options séparées par des virgules.", ephemeral=True)
            return
        
        if len(choices) > 20:
            await interaction.response.send_message("Maximum 20 options autorisées.", ephemeral=True)
            return
        
        chosen = random.choice(choices)
        
        embed = discord.Embed(
            title="🤔 Choix Aléatoire",
            description=f"Parmi **{len(choices)}** options",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Options", value="\n".join(f"• {choice}" for choice in choices), inline=False)
        embed.add_field(name="Choix", value=f"**{chosen}**", inline=False)
        embed.set_footer(text=f"Choisi par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reverse", description="Inverser un texte")
    @app_commands.describe(text="Texte à inverser")
    async def reverse_slash(self, interaction: discord.Interaction, text: str):
        reversed_text = text[::-1]
        
        embed = discord.Embed(
            title="🔄 Texte Inversé",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Original", value=text, inline=False)
        embed.add_field(name="Inversé", value=reversed_text, inline=False)
        embed.set_footer(text=f"Inversé par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="emojify", description="Convertir du texte en emojis")
    @app_commands.describe(text="Texte à convertir")
    async def emojify_slash(self, interaction: discord.Interaction, text: str):
        emoji_map = {
            'a': '🅰️', 'b': '🅱️', 'c': '©️', 'd': '🇩', 'e': '📧', 'f': '🎏', 'g': '🇬', 'h': '♓',
            'i': 'ℹ️', 'j': '🗾', 'k': '🇰', 'l': '🇱', 'm': 'Ⓜ️', 'n': '🇳', 'o': '⭕', 'p': '🅿️',
            'q': '🇶', 'r': '®️', 's': '💲', 't': '✝️', 'u': '🇺', 'v': '♈', 'w': '〰️', 'x': '❌',
            'y': '💴', 'z': '💤', '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
            '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣', '!': '❗', '?': '❓'
        }
        
        emojified = ""
        for char in text.lower():
            emojified += emoji_map.get(char, char) + " "
        
        if len(emojified) > 2000:
            await interaction.response.send_message("Le texte est trop long pour être converti.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="😀 Emojification",
            description=emojified,
            color=discord.Color.yellow(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Emojifié par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
