# bot.py
# Bot Discord RP - créé simplement par Flambix
# Installation : pip install -U discord.py
# Démarrage : python bot.py
#
# IMPORTANT :
# 1. Remplace BOT_TOKEN par le token de ton bot Discord.
# 2. Dans le portail développeur Discord, active "Server Members Intent"
#    si tu veux utiliser certaines fonctions liées aux membres.
# 3. N'envoie jamais ton token à quelqu'un.

import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timezone

BOT_TOKEN = "TON_TOKEN_ICI"
DATA_FILE = "donnees_bot.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = False

bot = commands.Bot(command_prefix="!", intents=intents)


def charger_donnees():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"comptes": {}, "profils": {}, "entreprises": {}, "tickets": {}, "warnings": {}}


data = charger_donnees()


def sauvegarder():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compte(user_id):
    uid = str(user_id)
    if uid not in data["comptes"]:
        data["comptes"][uid] = {"argent": 0, "banque": 0, "inventaire": [], "dernier_daily": ""}
    return data["comptes"][uid]


def profil(user_id):
    uid = str(user_id)
    if uid not in data["profils"]:
        data["profils"][uid] = {
            "nom": "Inconnu", "prenom": "Inconnu", "age": 18,
            "metier": "Sans emploi", "permis": False, "casier": []
        }
    return data["profils"][uid]


def embed_simple(titre, description, couleur=discord.Color.blurple()):
    e = discord.Embed(title=titre, description=description, color=couleur)
    e.timestamp = datetime.now(timezone.utc)
    return e


async def est_staff(interaction: discord.Interaction):
    return interaction.guild is not None and interaction.user.guild_permissions.manage_messages


async def ouvrir_ticket(interaction: discord.Interaction):
    if interaction.guild is None:
        return await interaction.response.send_message("Cette commande fonctionne sur un serveur.", ephemeral=True)
    guild = interaction.guild
    nom = f"ticket-{interaction.user.name}".lower().replace(" ", "-")[:90]
    existant = discord.utils.get(guild.text_channels, name=nom)
    if existant:
        return await interaction.response.send_message(f"Tu as déjà un ticket : {existant.mention}", ephemeral=True)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }
    staff_role = discord.utils.find(lambda r: r.name.lower() in ("staff", "support", "administrateur"), guild.roles)
    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    channel = await guild.create_text_channel(nom, overwrites=overwrites, reason="Ouverture d'un ticket")
    data["tickets"][str(channel.id)] = {"auteur": interaction.user.id, "claim": None}
    sauvegarder()
    await channel.send(f"{interaction.user.mention}, explique ta demande ici. Un membre du staff te répondra.")
    await interaction.response.send_message(f"Ticket créé : {channel.mention}", ephemeral=True)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Connecté en tant que {bot.user} | {len(synced)} commandes synchronisées")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")


# 🏙️ RP
@bot.tree.command(name="9-1-1", description="Appeler les services d'urgence RP")
@app_commands.describe(motif="Raison de l'appel", lieu="Lieu de l'incident")
async def appel_911(interaction: discord.Interaction, motif: str, lieu: str):
    await interaction.response.send_message(
        embed=embed_simple("🏙️ Appel 9-1-1", f"**Appelant :** {interaction.user.mention}\n**Motif :** {motif}\n**Lieu :** {lieu}\n\nLes services peuvent intervenir en RP.")
    )


@bot.tree.command(name="amende", description="Donner une amende RP")
@app_commands.describe(membre="Personne concernée", montant="Montant de l'amende", motif="Motif")
async def amende(interaction: discord.Interaction, membre: discord.Member, montant: app_commands.Range[int, 1, 100000], motif: str):
    if not await est_staff(interaction):
        return await interaction.response.send_message("Tu dois être membre du staff pour utiliser cette commande.", ephemeral=True)
    c = compte(membre.id)
    c["argent"] = max(0, c["argent"] - montant)
    sauvegarder()
    await interaction.response.send_message(f"🚔 {membre.mention} reçoit une amende de **{montant}€** pour : {motif}.")


@bot.tree.command(name="arrestation", description="Enregistrer une arrestation RP")
@app_commands.describe(membre="Personne arrêtée", motif="Motif de l'arrestation")
async def arrestation(interaction: discord.Interaction, membre: discord.Member, motif: str):
    if not await est_staff(interaction):
        return await interaction.response.send_message("Commande réservée au staff.", ephemeral=True)
    p = profil(membre.id)
    p["casier"].append({"type": "Arrestation", "motif": motif, "par": str(interaction.user), "date": datetime.now().strftime("%d/%m/%Y")})
    sauvegarder()
    await interaction.response.send_message(f"🚔 Arrestation RP enregistrée pour {membre.mention}. Motif : **{motif}**.")


@bot.tree.command(name="plainte", description="Déposer une plainte RP")
@app_commands.describe(membre="Personne visée", motif="Motif de la plainte")
async def plainte(interaction: discord.Interaction, membre: discord.Member, motif: str):
    await interaction.response.send_message(embed=embed_simple("📄 Plainte RP", f"**Plaignant :** {interaction.user.mention}\n**Personne visée :** {membre.mention}\n**Motif :** {motif}"))


@bot.tree.command(name="profil", description="Afficher ou créer ton profil RP")
async def profil_cmd(interaction: discord.Interaction):
    p = profil(interaction.user.id)
    await interaction.response.send_message(embed=embed_simple("🪪 Profil RP", f"**Nom :** {p['prenom']} {p['nom']}\n**Âge :** {p['age']}\n**Métier :** {p['metier']}\n**Permis :** {'Oui' if p['permis'] else 'Non'}"))


@bot.tree.command(name="identite", description="Modifier ton identité RP")
@app_commands.describe(prenom="Ton prénom RP", nom="Ton nom RP", age="Ton âge RP")
async def identite(interaction: discord.Interaction, prenom: str, nom: str, age: app_commands.Range[int, 16, 100]):
    p = profil(interaction.user.id)
    p.update({"prenom": prenom, "nom": nom, "age": age})
    sauvegarder()
    await interaction.response.send_message(f"🪪 Identité enregistrée : **{prenom} {nom}**, {age} ans.")


@bot.tree.command(name="permis", description="Consulter ou modifier ton permis RP")
@app_commands.describe(membre="Membre concerné (facultatif)", accorder="Accorder le permis (staff uniquement)")
async def permis(interaction: discord.Interaction, membre: discord.Member = None, accorder: bool = False):
    cible = membre or interaction.user
    if accorder:
        if not await est_staff(interaction):
            return await interaction.response.send_message("Seul le staff peut accorder un permis.", ephemeral=True)
        profil(cible.id)["permis"] = True
        sauvegarder()
        return await interaction.response.send_message(f"✅ Permis RP accordé à {cible.mention}.")
    await interaction.response.send_message(f"🪪 Permis RP de {cible.mention} : {'valide' if profil(cible.id)['permis'] else 'non enregistré'}.")


@bot.tree.command(name="casier", description="Consulter un casier judiciaire RP")
@app_commands.describe(membre="Membre concerné (facultatif)")
async def casier(interaction: discord.Interaction, membre: discord.Member = None):
    cible = membre or interaction.user
    entrees = profil(cible.id)["casier"]
    texte = "\n".join(f"• {x['type']} — {x['motif']} ({x['date']})" for x in entrees) or "Aucune entrée."
    await interaction.response.send_message(embed=embed_simple(f"📁 Casier RP — {cible.display_name}", texte), ephemeral=True)


@bot.tree.command(name="radio", description="Envoyer un message radio RP")
@app_commands.describe(message="Message à transmettre")
async def radio(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(embed=embed_simple("📻 Radio RP", f"**{interaction.user.display_name} :** {message}"))


# 💰 ÉCONOMIE
@bot.tree.command(name="bank", description="Consulter ton compte bancaire")
async def bank(interaction: discord.Interaction):
    c = compte(interaction.user.id)
    await interaction.response.send_message(f"🏦 **Banque :** {c['banque']}€\n💵 **Portefeuille :** {c['argent']}€", ephemeral=True)


@bot.tree.command(name="payer", description="Payer un autre membre")
@app_commands.describe(membre="Destinataire", montant="Montant à payer")
async def payer(interaction: discord.Interaction, membre: discord.Member, montant: app_commands.Range[int, 1, 100000]):
    if membre.bot or membre.id == interaction.user.id:
        return await interaction.response.send_message("Choisis un autre membre.", ephemeral=True)
    c = compte(interaction.user.id)
    if c["argent"] < montant:
        return await interaction.response.send_message("Tu n'as pas assez d'argent sur toi.", ephemeral=True)
    c["argent"] -= montant
    compte(membre.id)["argent"] += montant
    sauvegarder()
    await interaction.response.send_message(f"💸 {interaction.user.mention} a payé **{montant}€** à {membre.mention}.")


@bot.tree.command(name="daily", description="Récupérer ta récompense quotidienne")
async def daily(interaction: discord.Interaction):
    c = compte(interaction.user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    if c["dernier_daily"] == today:
        return await interaction.response.send_message("Tu as déjà récupéré ton daily aujourd'hui.", ephemeral=True)
    gain = random.randint(100, 500)
    c["argent"] += gain
    c["dernier_daily"] = today
    sauvegarder()
    await interaction.response.send_message(f"🎁 Tu reçois **{gain}€**. Reviens demain !")


@bot.tree.command(name="work", description="Travailler pour gagner de l'argent")
async def work(interaction: discord.Interaction):
    gain = random.randint(50, 250)
    compte(interaction.user.id)["argent"] += gain
    sauvegarder()
    await interaction.response.send_message(f"💼 Tu as travaillé et gagné **{gain}€**.")


SHOP = {"Téléphone": 300, "Sandwich": 15, "Radio": 120, "Voiture": 5000}


@bot.tree.command(name="shop", description="Afficher la boutique")
async def shop(interaction: discord.Interaction):
    await interaction.response.send_message(embed=embed_simple("🛒 Boutique", "\n".join(f"**{nom}** — {prix}€" for nom, prix in SHOP.items())))


@bot.tree.command(name="inventory", description="Voir ton inventaire")
async def inventory(interaction: discord.Interaction):
    inv = compte(interaction.user.id)["inventaire"]
    await interaction.response.send_message("🎒 **Inventaire :** " + (", ".join(inv) if inv else "vide"), ephemeral=True)


@bot.tree.command(name="leaderboard", description="Classement des plus riches")
async def leaderboard(interaction: discord.Interaction):
    classement = sorted(data["comptes"].items(), key=lambda item: item[1]["argent"] + item[1]["banque"], reverse=True)[:10]
    lignes = []
    for i, (uid, c) in enumerate(classement, 1):
        membre = interaction.guild.get_member(int(uid)) if interaction.guild else None
        nom = membre.display_name if membre else f"Utilisateur {uid}"
        lignes.append(f"**{i}.** {nom} — {c['argent'] + c['banque']}€")
    await interaction.response.send_message(embed=embed_simple("🏆 Classement", "\n".join(lignes) or "Aucun compte."))


# 🎫 TICKETS
@bot.tree.command(name="ticket", description="Ouvrir un ticket support")
async def ticket(interaction: discord.Interaction):
    await ouvrir_ticket(interaction)


@bot.tree.command(name="ticket-fermer", description="Fermer le ticket actuel")
async def ticket_fermer(interaction: discord.Interaction):
    if interaction.channel is None or str(interaction.channel.id) not in data["tickets"]:
        return await interaction.response.send_message("Cette commande doit être utilisée dans un ticket.", ephemeral=True)
    infos = data["tickets"][str(interaction.channel.id)]
    if interaction.user.id != infos["auteur"] and not await est_staff(interaction):
        return await interaction.response.send_message("Seul l'auteur du ticket ou le staff peut le fermer.", ephemeral=True)
    await interaction.response.send_message("🔒 Ticket fermé. Suppression dans 5 secondes.")
    await interaction.channel.delete(delay=5)
    data["tickets"].pop(str(interaction.channel.id), None)
    sauvegarder()


@bot.tree.command(name="ticket-claim", description="Prendre en charge un ticket")
async def ticket_claim(interaction: discord.Interaction):
    key = str(interaction.channel.id)
    if key not in data["tickets"]:
        return await interaction.response.send_message("Utilise cette commande dans un ticket.", ephemeral=True)
    if not await est_staff(interaction):
        return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
    data["tickets"][key]["claim"] = interaction.user.id
    sauvegarder()
    await interaction.response.send_message(f"🎫 Ticket pris en charge par {interaction.user.mention}.")


async def modifier_ticket(interaction, membre, ajouter):
    key = str(interaction.channel.id)
    if key not in data["tickets"]:
        return await interaction.response.send_message("Utilise cette commande dans un ticket.", ephemeral=True)
    if not await est_staff(interaction):
        return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
    await interaction.channel.set_permissions(membre, view_channel=ajouter, send_messages=ajouter, read_message_history=ajouter)
    await interaction.response.send_message(f"{'➕' if ajouter else '➖'} {membre.mention} {'ajouté au' if ajouter else 'retiré du'} ticket.")


@bot.tree.command(name="ticket-ajouter", description="Ajouter un membre au ticket")
@app_commands.describe(membre="Membre à ajouter")
async def ticket_ajouter(interaction: discord.Interaction, membre: discord.Member):
    await modifier_ticket(interaction, membre, True)


@bot.tree.command(name="ticket-retirer", description="Retirer un membre du ticket")
@app_commands.describe(membre="Membre à retirer")
async def ticket_retirer(interaction: discord.Interaction, membre: discord.Member):
    await modifier_ticket(interaction, membre, False)


# 🛡️ STAFF
@bot.tree.command(name="warn", description="Avertir un membre")
@app_commands.describe(membre="Membre concerné", motif="Motif de l'avertissement")
async def warn(interaction: discord.Interaction, membre: discord.Member, motif: str):
    if not await est_staff(interaction):
        return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
    data["warnings"].setdefault(str(membre.id), []).append({"motif": motif, "par": str(interaction.user), "date": datetime.now().strftime("%d/%m/%Y")})
    sauvegarder()
    await interaction.response.send_message(f"⚠️ {membre.mention} a reçu un avertissement. Motif : {motif}")


@bot.tree.command(name="timeout", description="Mettre un membre en timeout")
@app_commands.describe(membre="Membre", minutes="Durée en minutes", motif="Motif")
async def timeout_cmd(interaction: discord.Interaction, membre: discord.Member, minutes: app_commands.Range[int, 1, 40320], motif: str):
    if not await est_staff(interaction):
        return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
    try:
        await membre.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes), reason=motif)
    except AttributeError:
        from datetime import timedelta
        await membre.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=motif)
    await interaction.response.send_message(f"🔇 {membre.mention} est en timeout pendant {minutes} minute(s). Motif : {motif}")


@bot.tree.command(name="kick", description="Expulser un membre")
@app_commands.describe(membre="Membre à expulser", motif="Motif")
async def kick(interaction: discord.Interaction, membre: discord.Member, motif: str = "Aucun motif"):
    if not await est_staff(interaction):
        return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
    await membre.kick(reason=motif)
    await interaction.response.send_message(f"👢 {membre.mention} a été expulsé. Motif : {motif}")


@bot.tree.command(name="ban", description="Bannir un membre")
@app_commands.describe(membre="Membre à bannir", motif="Motif")
async def ban(interaction: discord.Interaction, membre: discord.Member, motif: str = "Aucun motif"):
    if not await est_staff(interaction):
        return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
    await membre.ban(reason=motif)
    await interaction.response.send_message(f"🔨 {membre.mention} a été banni. Motif : {motif}")


@bot.tree.command(name="clear", description="Supprimer des messages")
@app_commands.describe(nombre="Nombre de messages à supprimer (1 à 100)")
async def clear(interaction: discord.Interaction, nombre: app_commands.Range[int, 1, 100]):
    if interaction.guild is None or not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("Tu n'as pas la permission de gérer les messages.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    supprimés = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(f"🧹 {len(supprimés)} message(s) supprimé(s).", ephemeral=True)


@bot.tree.command(name="lock", description="Verrouiller le salon actuel")
async def lock(interaction: discord.Interaction):
    if interaction.guild is None or not interaction.user.guild_permissions.manage_channels:
        return await interaction.response.send_message("Tu n'as pas la permission de gérer les salons.", ephemeral=True)
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("🔒 Salon verrouillé.")


@bot.tree.command(name="unlock", description="Déverrouiller le salon actuel")
async def unlock(interaction: discord.Interaction):
    if interaction.guild is None or not interaction.user.guild_permissions.manage_channels:
        return await interaction.response.send_message("Tu n'as pas la permission de gérer les salons.", ephemeral=True)
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
    await interaction.response.send_message("🔓 Salon déverrouillé.")


@bot.tree.command(name="session", description="Annoncer le début ou la fin d'une session RP")
@app_commands.describe(action="Début ou fin", details="Informations de session")
@app_commands.choices(action=[app_commands.Choice(name="Début", value="debut"), app_commands.Choice(name="Fin", value="fin")])
async def session(interaction: discord.Interaction, action: app_commands.Choice[str], details: str = "Aucune information"):
    if not await est_staff(interaction):
        return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
    titre = "🟢 Session RP ouverte" if action.value == "debut" else "🔴 Session RP terminée"
    await interaction.response.send_message(embed=embed_simple(titre, details))


@bot.tree.command(name="appel-staff", description="Appeler le staff")
@app_commands.describe(motif="Raison de l'appel")
async def appel_staff(interaction: discord.I
