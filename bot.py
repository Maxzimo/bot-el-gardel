import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import sqlite3
from datetime import datetime, timezone

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1374458065130225857
GUILD_OBJ = discord.Object(id=GUILD_ID)

# ========= DATABASE =========
conn = sqlite3.connect("robos.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS robos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    monto REAL,
    texto TEXT,
    participantes TEXT,
    imagen TEXT,
    fecha TEXT
)
""")
conn.commit()

# ========= BOT =========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

ROLES_PERMITIDOS = [1374458115663200296, 1374459987874680925]
ROLES_ROBO = [1374458125977129130]
ROLES_VERROBOS = [1374458125977129130]
ROLES_RESET = [1374458115663200296, 1374459987874680925, 1374458121363390485]  # ← tercer rol aquí
ROLES_EDITAR_ROBO = [1374458125977129130]  # ID del rol permitido


# ================= /clear =================
@bot.tree.command(name="clear", description="Elimina mensajes", guild=GUILD_OBJ)
@app_commands.describe(cantidad="Cantidad de mensajes")
async def clear(interaction: discord.Interaction, cantidad: int):

    if not any(role.id in ROLES_PERMITIDOS for role in interaction.user.roles):
        await interaction.response.send_message("🚫 No tenes permisos.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    deleted = await interaction.channel.purge(limit=cantidad)

    embed = discord.Embed(
        title="🧹 Mensajes eliminados",
        description=f"Se eliminaron {len(deleted)} mensajes",
        color=0x00ffcc,
        timestamp=datetime.now(timezone.utc)
    )

    await interaction.followup.send(embed=embed, ephemeral=True)

# ================= /robo =================
@bot.tree.command(name="robo", description="Registrar robo", guild=GUILD_OBJ)
@app_commands.describe(
    monto="Monto del robo",
    texto="Descripción",
    participantes="Participantes",
    archivo="Imagen del robo"
)
async def robo(
    interaction: discord.Interaction,
    monto: float,
    texto: str,
    participantes: str,
    archivo: discord.Attachment
):

    if not any(role.id in ROLES_ROBO for role in interaction.user.roles):
        await interaction.response.send_message("🚫 No tenes permisos.", ephemeral=True)
        return

    fecha = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        INSERT INTO robos (usuario, monto, texto, participantes, imagen, fecha)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        str(interaction.user),
        monto,
        texto,
        participantes,
        archivo.url,
        fecha
    ))

    conn.commit()

    robo_id = cursor.lastrowid  # ← número automático

    embed = discord.Embed(
        title=f"📝 Robo #{robo_id} registrado",
        description=f"Monto: ${int(monto)}",
        color=0xff9900
    )

    embed.add_field(name="Descripción", value=texto, inline=False)
    embed.add_field(name="Participantes", value=participantes, inline=False)
    embed.set_image(url=archivo.url)

    await interaction.response.send_message(embed=embed)

#================= /editarrobo =================
@bot.tree.command(name="editarrobo", description="Editar un robo", guild=GUILD_OBJ)
@app_commands.describe(
    id="Número del robo",
    monto="Nuevo monto",
    texto="Nueva descripción",
    participantes="Nuevos participantes",
    archivo="Nueva imagen"
)
async def editarrobo(
    interaction: discord.Interaction,
    id: int,
    monto: float = None,
    texto: str = None,
    participantes: str = None,
    archivo: discord.Attachment = None
):

    if not any(role.id in ROLES_EDITAR_ROBO for role in interaction.user.roles):
        await interaction.response.send_message("🚫 No tenes permisos.", ephemeral=True)
        return

    cursor.execute("""
        SELECT monto, texto, participantes, imagen
        FROM robos
        WHERE id = ?
    """, (id,))
    
    robo_actual = cursor.fetchone()

    if not robo_actual:
        await interaction.response.send_message("❌ Robo no encontrado.", ephemeral=True)
        return

    monto_db, texto_db, participantes_db, imagen_db = robo_actual

    nuevo_monto = monto if monto is not None else monto_db
    nuevo_texto = texto if texto is not None else texto_db
    nuevos_participantes = participantes if participantes is not None else participantes_db
    nueva_imagen = archivo.url if archivo else imagen_db

    cursor.execute("""
        UPDATE robos
        SET monto = ?, texto = ?, participantes = ?, imagen = ?
        WHERE id = ?
    """, (
        nuevo_monto,
        nuevo_texto,
        nuevos_participantes,
        nueva_imagen,
        id
    ))
    conn.commit()

    embed = discord.Embed(
        title=f"✏️ Robo #{id} editado",
        color=0xF1C40F
    )

    embed.add_field(name="💰 Monto", value=f"${int(nuevo_monto)}", inline=False)
    embed.add_field(name="📝 Descripción", value=nuevo_texto, inline=False)
    embed.add_field(name="👥 Participantes", value=nuevos_participantes, inline=False)

    if nueva_imagen:
        embed.set_image(url=nueva_imagen)

    # Mensaje público en el canal
    await interaction.response.send_message("✅ Robo editado correctamente.", ephemeral=True)
    await interaction.channel.send(embed=embed)

# ================= /verrobos =================
@bot.tree.command(name="verrobos", description="Ver robos", guild=GUILD_OBJ)
async def verrobos(interaction: discord.Interaction):

    if not any(role.id in ROLES_VERROBOS for role in interaction.user.roles):
        await interaction.response.send_message("🚫 No tenes permisos.", ephemeral=True)
        return

    cursor.execute("""
        SELECT id, usuario, monto, texto, participantes, imagen, fecha
        FROM robos
        ORDER BY id DESC
    """)
    robos = cursor.fetchall()

    if not robos:
        await interaction.response.send_message("No hay robos registrados.", ephemeral=True)
        return

    total = sum(r[2] for r in robos)

    await interaction.response.send_message(
        f"Mostrando robos...\n💵 Total robado: ${int(total)}",
        ephemeral=True
    )

    for robo_id, usuario, monto, texto, participantes, imagen, fecha in robos:

        fecha_fmt = datetime.fromisoformat(fecha).strftime('%d/%m/%Y %H:%M')

        embed = discord.Embed(
            title=f"💰 Robo #{robo_id} — ${int(monto)}",
            description=texto,
            color=0xff5500
        )

        embed.add_field(name="Participantes", value=participantes, inline=False)
        embed.set_image(url=imagen)
        embed.set_footer(text=f"{usuario} • {fecha_fmt}")

        await interaction.channel.send(embed=embed)

# ================= /reset =================
@bot.tree.command(name="reset", description="Borrar todos los robos", guild=GUILD_OBJ)
async def reset(interaction: discord.Interaction):

    if not any(role.id in ROLES_RESET for role in interaction.user.roles):
        await interaction.response.send_message("🚫 No tenes permisos.", ephemeral=True)
        return

    cursor.execute("DELETE FROM robos")
    conn.commit()

    await interaction.response.send_message("✅ Todos los robos fueron reinciados.")


# ================= READY =================
@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")

    synced = await bot.tree.sync(guild=GUILD_OBJ)
    print(f"✅ {len(synced)} comandos sincronizados")

bot.run(TOKEN)
