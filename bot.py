import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime, timedelta, timezone

# Cargar token desde .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ROLES_PERMITIDOS = [
    1374458115663200296,  # reemplaza con tu rol
    1374459987874680925,  # otro rol
]

@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos slash")
    except Exception as e:
        print(e)

@bot.tree.command(name="clear", description="Elimina mensajes en el canal")
@app_commands.describe(cantidad="Cantidad de mensajes a eliminar (1-1000)")
async def clear(interaction: discord.Interaction, cantidad: int):
    # Verificar roles permitidos
    user_roles = [role.id for role in interaction.user.roles]
    if not any(role_id in ROLES_PERMITIDOS for role_id in user_roles):
        await interaction.response.send_message(
            "❌ No tienes permiso para usar este comando. Necesitas un rol autorizado.", 
            ephemeral=True
        )
        return

    if cantidad < 1:
        await interaction.response.send_message("❌ La cantidad debe ser al menos 1.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    deleted_total = 0

    # Borrar en lotes de 50 mensajes
    for i in range(0, cantidad, 50):
        batch = min(50, cantidad - i)
        deleted = await interaction.channel.purge(limit=batch)
        deleted_total += len(deleted)
        await asyncio.sleep(1)  # pausa para evitar rate limit

    embed = discord.Embed(
        title="🧹 Mensajes eliminados",
        description=f"Se eliminaron **{deleted_total}** mensajes correctamente.",
        color=0x00ffcc
    )
    embed.set_author(name="Clear Bot", icon_url=bot.user.display_avatar.url)
    embed.set_footer(text=f"Ejecutado por {interaction.user}", icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Canal", value=interaction.channel.mention, inline=True)
    embed.add_field(name="Cantidad solicitada", value=str(cantidad), inline=True)
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3097/3097980.png")
    embed.timestamp = datetime.now(timezone.utc)

    await interaction.followup.send(embed=embed, ephemeral=True)


bot.run(TOKEN)
