import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import json
import os
import asyncio
import logging

# RÈGLE : Les commandes slash sont automatiquement enregistrées par bot.add_cog()

TICKETS_FILE = "tickets.json"
logger = logging.getLogger("bot.tickets")

class TicketView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Créer un ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self._create_ticket(interaction)
        except Exception as e:
            logger.exception(f"Erreur dans create_ticket button: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ **Une erreur s'est produite lors de la création du ticket.**", ephemeral=True)

    async def _create_ticket(self, interaction: discord.Interaction):
        try:
            # Vérifier si l'interaction a déjà été traitée
            if interaction.response.is_done():
                return
                
            guild_id = str(interaction.guild.id)
            if guild_id not in self.cog.tickets or "config" not in self.cog.tickets[guild_id]:
                await interaction.response.send_message("❌ **Le système de tickets n'est pas configuré.**", ephemeral=True)
                return
            
            config = self.cog.tickets[guild_id]["config"]
            category = interaction.guild.get_channel(config["category_id"])
            
            if not category:
                await interaction.response.send_message("❌ **Catégorie de tickets introuvable.**", ephemeral=True)
                return
            
            # Vérifier le nombre maximum de tickets
            user_tickets = 0
            if "tickets" in self.cog.tickets[guild_id]:
                for ticket_data in self.cog.tickets[guild_id]["tickets"].values():
                    if isinstance(ticket_data, dict) and ticket_data.get("creator_id") == interaction.user.id:
                        channel = interaction.guild.get_channel(ticket_data.get("channel_id"))
                        if channel:  # Ticket encore actif
                            user_tickets += 1
            
            max_tickets = config.get("max_tickets", 1)
            if user_tickets >= max_tickets:
                await interaction.response.send_message(f"❌ **Vous avez déjà {user_tickets} ticket(s) ouvert(s). Maximum autorisé: {max_tickets}**", ephemeral=True)
                return
            
            # Créer le canal du ticket
            ticket_number = self.cog.ticket_counter
            self.cog.ticket_counter += 1
            
            channel_name = f"ticket-{ticket_number}"
            
            try:
                channel = await interaction.guild.create_text_channel(
                    name=channel_name,
                    category=category,
                    topic=f"Ticket #{ticket_number} créé par {interaction.user.display_name}"
                )
            except Exception as e:
                logger.error(f"Erreur création canal ticket: {e}")
                await interaction.response.send_message("❌ **Erreur lors de la création du canal.**", ephemeral=True)
                return
            
            # Configurer les permissions
            try:
                await channel.set_permissions(interaction.guild.default_role, view_channel=False)
                await channel.set_permissions(interaction.user, view_channel=True, send_messages=True, read_message_history=True)
                
                # Ajouter les permissions pour les rôles de support
                if config.get("support_role_id"):
                    support_role = interaction.guild.get_role(config["support_role_id"])
                    if support_role:
                        await channel.set_permissions(support_role, view_channel=True, send_messages=True, read_message_history=True, manage_messages=True)
                
                if config.get("admin_role_id"):
                    admin_role = interaction.guild.get_role(config["admin_role_id"])
                    if admin_role:
                        await channel.set_permissions(admin_role, view_channel=True, send_messages=True, read_message_history=True, manage_messages=True, manage_channels=True)
                
                if config.get("designer_role_id"):
                    designer_role = interaction.guild.get_role(config["designer_role_id"])
                    if designer_role:
                        await channel.set_permissions(designer_role, view_channel=True, send_messages=True, read_message_history=True, manage_messages=True)
            except Exception as e:
                logger.error(f"Erreur configuration permissions ticket: {e}")
                # Continuer même si les permissions échouent
            
            # Sauvegarder les informations du ticket
            if "tickets" not in self.cog.tickets[guild_id]:
                self.cog.tickets[guild_id]["tickets"] = {}
            
            self.cog.tickets[guild_id]["tickets"][channel_name] = {
                "channel_id": channel.id,
                "creator_id": interaction.user.id,
                "created_at": datetime.now().isoformat(),
                "status": "open"
            }
            self.cog._save_tickets()
            
            # Message de bienvenue
            welcome_msg = config.get("welcome_message")
            if not welcome_msg or welcome_msg.strip() == "":
                welcome_msg = "Bienvenue ! Décrivez votre problème et un modérateur vous répondra bientôt."
            
            embed = discord.Embed(
                title=f"🎫 **Ticket #{ticket_number}**",
                description=f"Bienvenue {interaction.user.mention} !\n\n{welcome_msg}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(
                name="📋 **Instructions**", 
                value="• Décrivez votre problème clairement\n• Soyez patient et respectueux\n• Attendez la réponse d'un modérateur", 
                inline=False
            )
            embed.add_field(
                name="🔧 **Commandes disponibles**", 
                value="`/ticket close` - Fermer le ticket\n`/ticket add @membre` - Ajouter quelqu'un\n`/ticket remove @membre` - Retirer quelqu'un", 
                inline=False
            )
            
            # Boutons d'action
            view = CloseTicketView(self.cog)
            
            try:
                await channel.send(embed=embed, view=view)
            except Exception as e:
                logger.error(f"Erreur envoi message bienvenue ticket: {e}")
            
            await interaction.response.send_message(f"✅ **Ticket créé avec succès !** {channel.mention}", ephemeral=True)
            
        except Exception as e:
            logger.exception(f"Erreur dans _create_ticket: {e}")
            # Ne pas envoyer de message d'erreur si l'interaction a déjà été répondue
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(f"❌ **Erreur lors de la création du ticket:** {str(e)}", ephemeral=True)
                except:
                    pass

class CloseTicketView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self._close_ticket(interaction)
        except Exception as e:
            logger.exception(f"Erreur dans close_ticket button: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ **Une erreur s'est produite lors de la fermeture du ticket.**", ephemeral=True)

    async def _close_ticket(self, interaction: discord.Interaction):
        try:
            # Vérifier si l'interaction a déjà été traitée
            if interaction.response.is_done():
                return
                
            embed = discord.Embed(
                title="🔒 **Ticket fermé**",
                description="Ce ticket sera supprimé dans 5 secondes.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Fermé par", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed)
            
            # Supprimer le canal après 5 secondes
            await asyncio.sleep(5)
            
            # Marquer le ticket comme fermé dans la base de données
            guild_id = str(interaction.guild.id)
            if guild_id in self.cog.tickets and "tickets" in self.cog.tickets[guild_id]:
                for ticket_id, ticket_data in self.cog.tickets[guild_id]["tickets"].items():
                    if isinstance(ticket_data, dict) and ticket_data.get("channel_id") == interaction.channel.id:
                        ticket_data["status"] = "closed"
                        ticket_data["closed_by"] = interaction.user.id
                        ticket_data["closed_at"] = datetime.now().isoformat()
                        self.cog._save_tickets()
                        break
            
            try:
                await interaction.channel.delete()
            except Exception as e:
                logger.error(f"Erreur suppression canal ticket: {e}")
            
        except Exception as e:
            logger.exception(f"Erreur dans _close_ticket: {e}")
            # Ne pas envoyer de message d'erreur si l'interaction a déjà été répondue
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(f"❌ **Erreur lors de la fermeture du ticket:** {str(e)}", ephemeral=True)
                except:
                    pass

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tickets = self._load_tickets()
        self.ticket_counter = self._get_next_ticket_number()
        
        # Enregistrer les vues persistantes
        self.bot.add_view(TicketView(self))
        self.bot.add_view(CloseTicketView(self))

    def _load_tickets(self):
        """Charge les tickets depuis le fichier JSON avec gestion d'erreurs robuste"""
        if os.path.exists(TICKETS_FILE):
            try:
                with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Validation des données
                    if isinstance(data, dict):
                        return data
                    else:
                        logger.warning("Format de données invalide dans tickets.json, redémarrage avec structure vide")
                        return {}
            except json.JSONDecodeError as e:
                logger.error(f"Erreur JSON dans tickets.json: {e}")
                # Sauvegarder l'ancien fichier corrompu
                try:
                    os.rename(TICKETS_FILE, f"{TICKETS_FILE}.backup.{int(datetime.now().timestamp())}")
            except:
                    pass
                return {}
            except Exception as e:
                logger.error(f"Erreur lecture tickets.json: {e}")
                return {}
        return {}

    def _save_tickets(self):
        """Sauvegarde les tickets avec gestion d'erreurs robuste"""
        try:
            # Sauvegarde temporaire d'abord
            temp_file = f"{TICKETS_FILE}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.tickets, f, indent=2, ensure_ascii=False)
            
            # Remplacer l'ancien fichier
            if os.path.exists(TICKETS_FILE):
                os.replace(temp_file, TICKETS_FILE)
            else:
                os.rename(temp_file, TICKETS_FILE)
        except Exception as e:
            logger.error(f"Erreur sauvegarde tickets: {e}")
            # Nettoyer le fichier temporaire
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

    def _get_next_ticket_number(self):
        """Calcule le prochain numéro de ticket de manière robuste"""
        if not self.tickets:
            return 1
        
        max_num = 0
        for guild_data in self.tickets.values():
            if isinstance(guild_data, dict) and "tickets" in guild_data:
                for ticket_id in guild_data["tickets"]:
                    try:
                        if isinstance(ticket_id, str) and ticket_id.startswith("ticket-"):
                        num = int(ticket_id.split("-")[-1])
                        max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        continue
        return max_num + 1

    def _validate_config(self, config):
        """Valide la configuration des tickets"""
        required_fields = ["channel_id", "category_id"]
        for field in required_fields:
            if field not in config or not config[field]:
                return False, f"Champ requis manquant: {field}"
        
        # Validation des valeurs par défaut
        if not config.get("welcome_message", "").strip():
            config["welcome_message"] = "Bienvenue ! Décrivez votre problème et un modérateur vous répondra bientôt."
        
        if not config.get("embed_title", "").strip():
            config["embed_title"] = "🎫 **Système de Tickets**"
        
        if not config.get("embed_description", "").strip():
            config["embed_description"] = "Cliquez sur le bouton ci-dessous pour créer un ticket de support."
        
        if not config.get("max_tickets"):
            config["max_tickets"] = 1
        
        return True, "Configuration valide"

    # Groupe de commandes pour les tickets
    group = app_commands.Group(name="ticket", description="Commandes de gestion des tickets")

    @group.command(name="setup", description="Configurer le système de tickets")
    @app_commands.describe(
        channel="Canal pour créer les tickets",
        category="Catégorie pour les tickets",
        support_role="Rôle des modérateurs support",
        admin_role="Rôle des administrateurs",
        designer_role="Rôle des graphistes",
        welcome_message="Message de bienvenue personnalisé",
        max_tickets="Nombre maximum de tickets par utilisateur",
        image_url="URL de l'image pour le message de création",
        embed_title="Titre de l'embed de création (optionnel)",
        embed_description="Description de l'embed de création (optionnel)",
        preset="Preset de configuration rapide"
    )
    @app_commands.choices(preset=[
        app_commands.Choice(name="Par Défaut", value="default"),
        app_commands.Choice(name="Support Général", value="support"),
        app_commands.Choice(name="Graphisme", value="graphism"),
        app_commands.Choice(name="Administration", value="admin"),
        app_commands.Choice(name="Personnalisé", value="custom")
    ])
    async def ticket_setup(self, interaction: discord.Interaction, 
                          channel: discord.TextChannel, 
                          category: discord.CategoryChannel,
                          preset: str = "custom",
                          support_role: discord.Role = None,
                          admin_role: discord.Role = None,
                          designer_role: discord.Role = None,
                          welcome_message: str = None,
                          max_tickets: int = 1,
                          image_url: str = None,
                          embed_title: str = None,
                          embed_description: str = None):
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ **Permission refusée.** Vous devez être administrateur.", ephemeral=True)
            return
        
        # Validation des paramètres
        if max_tickets < 1 or max_tickets > 10:
            await interaction.response.send_message("❌ **Le nombre maximum de tickets doit être entre 1 et 10.**", ephemeral=True)
            return
        
        try:
            # Répondre immédiatement pour éviter le timeout
            await interaction.response.defer(ephemeral=True)
            
            # Appliquer les presets
            if preset == "default":
                embed_title = embed_title or "👉 Commander une bannière"
                embed_description = embed_description or "Pour toute commande, tu peux directement utiliser le bouton ci-dessous."
                welcome_message = welcome_message or "Veuillez patienter, votre graphiste arrive bientôt !"
                image_url = image_url or "https://cdn.discordapp.com/attachments/1351595532191273083/1409966101349138542/BANNERS_HEAVEN_CC.png?ex=68b53b82&is=68b3ea02&hm=519de0de1ed10ff03816e29015565b4020604e09dfec4ce0b65658bbd1595ff5&"
                max_tickets = max_tickets if max_tickets != 1 else 3
            elif preset == "support":
                embed_title = embed_title or "🎫 **Support Technique**"
                embed_description = embed_description or "Besoin d'aide ? Créez un ticket de support !"
                welcome_message = welcome_message or "Bienvenue dans votre ticket de support ! Décrivez votre problème et un modérateur vous répondra bientôt."
                image_url = image_url or "https://i.imgur.com/8tBXd6L.png"
            elif preset == "graphism":
                embed_title = embed_title or "🎨 **Demande de Graphisme**"
                embed_description = embed_description or "Demandez vos créations graphiques ici !"
                welcome_message = welcome_message or "Bienvenue ! Décrivez votre demande de graphisme en détail (type, couleurs, style, etc.) et un graphiste vous répondra."
                image_url = image_url or "https://i.imgur.com/JQ7X8Yq.png"
            elif preset == "admin":
                embed_title = embed_title or "👑 **Administration**"
                embed_description = embed_description or "Demandes administratives et importantes"
                welcome_message = welcome_message or "Bienvenue ! Cette section est réservée aux demandes administratives importantes. Soyez précis dans votre demande."
                image_url = image_url or "https://i.imgur.com/2X8YqJQ.png"
            else:  # custom
                embed_title = embed_title or "🎫 **Système de Tickets**"
                embed_description = embed_description or "Cliquez sur le bouton ci-dessous pour créer un ticket de support."
                welcome_message = welcome_message or "Bienvenue ! Décrivez votre problème et un modérateur vous répondra bientôt."
        
        # Sauvegarder la configuration
        guild_id = str(interaction.guild.id)
        if guild_id not in self.tickets:
            self.tickets[guild_id] = {"tickets": {}, "config": {}}
        
            config = {
            "channel_id": channel.id,
            "category_id": category.id,
            "support_role_id": support_role.id if support_role else None,
            "admin_role_id": admin_role.id if admin_role else None,
            "designer_role_id": designer_role.id if designer_role else None,
                "welcome_message": welcome_message,
            "max_tickets": max_tickets,
            "image_url": image_url,
                "embed_title": embed_title,
                "embed_description": embed_description,
                "preset": preset,
            "setup_by": interaction.user.id,
            "setup_at": datetime.now().isoformat()
        }
            
            # Validation de la configuration
            is_valid, message = self._validate_config(config)
            if not is_valid:
                await interaction.followup.send(f"❌ **Configuration invalide:** {message}", ephemeral=True)
                return
            
            self.tickets[guild_id]["config"] = config
        self._save_tickets()
        
        # Créer le message de création de tickets
        embed = discord.Embed(
                title=config["embed_title"],
                description=config["embed_description"],
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Ajouter les champs de configuration
        config_fields = []
        config_fields.append(f"• **Canal:** {channel.mention}")
        config_fields.append(f"• **Catégorie:** {category.name}")
        config_fields.append(f"• **Support:** {support_role.mention if support_role else 'Non défini'}")
        config_fields.append(f"• **Admin:** {admin_role.mention if admin_role else 'Non défini'}")
        config_fields.append(f"• **Graphiste:** {designer_role.mention if designer_role else 'Non défini'}")
        config_fields.append(f"• **Max tickets:** {max_tickets}")
            config_fields.append(f"• **Preset:** {preset.title()}")
        
        embed.add_field(
            name="📋 **Instructions**", 
            value="• Décrivez votre problème clairement\n• Soyez patient, un modérateur vous répondra\n• Restez respectueux et constructif", 
            inline=False
        )
        embed.add_field(
            name="⚙️ **Configuration**",
            value="\n".join(config_fields),
            inline=False
        )
        
        # Ajouter l'image si fournie
        if image_url:
            embed.set_image(url=image_url)
            
        embed.set_footer(text="Support - Système de Tickets")
        
        # Créer le bouton avec la vue persistante
        view = TicketView(self)
        
        await channel.send(embed=embed, view=view)
            await interaction.followup.send("✅ **Système de tickets configuré avec succès !**", ephemeral=True)
        except Exception as e:
            logger.error(f"Erreur envoi message setup: {e}")
            await interaction.followup.send("✅ **Configuration sauvegardée mais erreur lors de l'envoi du message.**", ephemeral=True)

    @group.command(name="config", description="Voir la configuration actuelle")
    async def ticket_config(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ **Permission refusée.**", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        if guild_id not in self.tickets or "config" not in self.tickets[guild_id]:
            await interaction.response.send_message("❌ **Aucune configuration trouvée.** Utilisez `/ticket setup` d'abord.", ephemeral=True)
            return
        
        config = self.tickets[guild_id]["config"]
        channel = interaction.guild.get_channel(config.get("channel_id"))
        category = interaction.guild.get_channel(config.get("category_id"))
        support_role = interaction.guild.get_role(config.get("support_role_id")) if config.get("support_role_id") else None
        admin_role = interaction.guild.get_role(config.get("admin_role_id")) if config.get("admin_role_id") else None
        designer_role = interaction.guild.get_role(config.get("designer_role_id")) if config.get("designer_role_id") else None
        
        embed = discord.Embed(
            title="⚙️ **Configuration des Tickets**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="📺 Canal", value=channel.mention if channel else "❌ Introuvable", inline=True)
        embed.add_field(name="📁 Catégorie", value=category.name if category else "❌ Introuvable", inline=True)
        embed.add_field(name="🛡️ Support", value=support_role.mention if support_role else "❌ Non défini", inline=True)
        embed.add_field(name="👑 Admin", value=admin_role.mention if admin_role else "❌ Non défini", inline=True)
        embed.add_field(name="🎨 Graphiste", value=designer_role.mention if designer_role else "❌ Non défini", inline=True)
        embed.add_field(name="📊 Max tickets", value=str(config.get("max_tickets", 1)), inline=True)
        embed.add_field(name="💬 Message", value=config.get("welcome_message", "Non défini")[:50] + "...", inline=True)
        embed.add_field(name="🖼️ Image", value="✅ Configurée" if config.get("image_url") else "❌ Non définie", inline=True)
        embed.add_field(name="📝 Titre embed", value=config.get("embed_title", "Non défini")[:30] + "...", inline=True)
        embed.add_field(name="📄 Description embed", value=config.get("embed_description", "Non défini")[:30] + "...", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @group.command(name="close", description="Fermer un ticket")
    async def ticket_close(self, interaction: discord.Interaction):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ **Cette commande ne peut être utilisée que dans un ticket.**", ephemeral=True)
            return
        
        # Vérifier les permissions
        has_permission = await self._check_ticket_permissions(interaction)
        if not has_permission:
            await interaction.response.send_message("❌ **Permission refusée.**", ephemeral=True)
            return
        
        await self._close_ticket(interaction)

    @group.command(name="add", description="Ajouter un membre au ticket")
    @app_commands.describe(member="Membre à ajouter")
    async def ticket_add(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ **Cette commande ne peut être utilisée que dans un ticket.**", ephemeral=True)
            return
        
        # Vérifier les permissions
        has_permission = await self._check_ticket_permissions(interaction)
        if not has_permission:
            await interaction.response.send_message("❌ **Permission refusée.**", ephemeral=True)
            return
        
        try:
            await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
            embed = discord.Embed(
                title="✅ **Membre ajouté**",
                description=f"**{member.display_name}** a été ajouté au ticket.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Ajouté par", value=interaction.user.mention, inline=True)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Erreur ajout membre ticket: {e}")
            await interaction.response.send_message(f"❌ **Erreur lors de l'ajout:** {str(e)}", ephemeral=True)

    @group.command(name="fix", description="Corriger la configuration des tickets")
    async def ticket_fix(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ **Permission refusée.**", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        if guild_id not in self.tickets or "config" not in self.tickets[guild_id]:
            await interaction.response.send_message("❌ **Aucune configuration trouvée.** Utilisez `/ticket setup` d'abord.", ephemeral=True)
            return
        
        config = self.tickets[guild_id]["config"]
        
        # Vérifier et corriger les valeurs par défaut
        is_valid, message = self._validate_config(config)
        if not is_valid:
            await interaction.response.send_message(f"❌ **Configuration invalide:** {message}", ephemeral=True)
            return
        
        self._save_tickets()
        
        embed = discord.Embed(
            title="🔧 **Configuration corrigée**",
            description="La configuration des tickets a été corrigée avec succès !",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Message de bienvenue", value=config["welcome_message"][:100] + "...", inline=False)
        embed.add_field(name="Titre embed", value=config["embed_title"], inline=True)
        embed.add_field(name="Description embed", value=config["embed_description"][:50] + "...", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @group.command(name="remove", description="Retirer un membre du ticket")
    @app_commands.describe(member="Membre à retirer")
    async def ticket_remove(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ **Cette commande ne peut être utilisée que dans un ticket.**", ephemeral=True)
            return
        
        # Vérifier les permissions
        has_permission = await self._check_ticket_permissions(interaction)
        if not has_permission:
            await interaction.response.send_message("❌ **Permission refusée.**", ephemeral=True)
            return
        
        try:
            await interaction.channel.set_permissions(member, overwrite=None)
            embed = discord.Embed(
                title="❌ **Membre retiré**",
                description=f"**{member.display_name}** a été retiré du ticket.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Retiré par", value=interaction.user.mention, inline=True)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Erreur retrait membre ticket: {e}")
            await interaction.response.send_message(f"❌ **Erreur lors du retrait:** {str(e)}", ephemeral=True)

    @group.command(name="presets", description="Voir les presets de configuration disponibles")
    async def ticket_presets(self, interaction: discord.Interaction):
            embed = discord.Embed(
            title="🎨 **Presets de Configuration**",
            description="Voici les presets disponibles pour configurer rapidement votre système de tickets :",
            color=discord.Color.blue(),
                timestamp=datetime.now()
            )
        
            embed.add_field(
            name="🎯 **Par Défaut**",
            value="• Titre: 👉 Commander une bannière\n• Description: Pour toute commande, tu peux directement utiliser le bouton ci-dessous.\n• Message: Veuillez patienter, votre graphiste arrive bientôt !\n• Image: Bannière HeavenGraphX\n• Max tickets: 3",
                inline=False
            )
        
            embed.add_field(
            name="🎫 **Support Général**",
            value="• Titre: Support Technique\n• Description: Besoin d'aide ? Créez un ticket de support !\n• Message: Accueil standard pour le support\n• Image: Icône de support",
                inline=False
            )
            
        embed.add_field(
            name="🎨 **Graphisme**",
            value="• Titre: Demande de Graphisme\n• Description: Demandez vos créations graphiques ici !\n• Message: Spécialisé pour les demandes graphiques\n• Image: Icône de graphisme",
            inline=False
        )
        
        embed.add_field(
            name="👑 **Administration**",
            value="• Titre: Administration\n• Description: Demandes administratives et importantes\n• Message: Pour les demandes administratives\n• Image: Icône d'administration",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ **Personnalisé**",
            value="• Titre: Système de Tickets\n• Description: Configuration manuelle complète\n• Message: Message personnalisable\n• Image: Aucune par défaut",
            inline=False
        )
        
        embed.add_field(
            name="📝 **Utilisation**",
            value="Utilisez `/ticket setup` avec le paramètre `preset` pour choisir un preset. Vous pouvez toujours personnaliser les autres paramètres par la suite.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _check_ticket_permissions(self, interaction: discord.Interaction) -> bool:
        """Vérifie les permissions pour les actions sur les tickets"""
        if interaction.user.guild_permissions.manage_channels:
            return True
        
            guild_id = str(interaction.guild.id)
        if guild_id in self.tickets and "config" in self.tickets[guild_id]:
            config = self.tickets[guild_id]["config"]
            support_role = interaction.guild.get_role(config.get("support_role_id"))
            admin_role = interaction.guild.get_role(config.get("admin_role_id"))
            designer_role = interaction.guild.get_role(config.get("designer_role_id"))
            
            if support_role and support_role in interaction.user.roles:
                return True
            if admin_role and admin_role in interaction.user.roles:
                return True
            if designer_role and designer_role in interaction.user.roles:
                return True
        
        return False

async def setup(bot: commands.Bot):
    cog = Tickets(bot)
    await bot.add_cog(cog)
    # Attacher le groupe slash sur l'arbre seulement s'il n'est pas déjà enregistré
    try:
        # Vérifier si le groupe existe déjà
        existing_commands = [cmd.name for cmd in bot.tree.get_commands()]
        if "ticket" not in existing_commands:
        bot.tree.add_command(cog.group)
            logger.info("Groupe ticket ajouté à l'arbre des commandes")
        else:
            logger.info("Groupe ticket déjà présent dans l'arbre des commandes")
    except Exception as e:
        logger.error(f"Erreur ajout groupe ticket: {e}")
