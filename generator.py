import discord
from discord import app_commands
import json
import random
import datetime
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)
    with open(file, "r") as f:
        return json.load(f)

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

config = load("config.json")

# ---------- USER COMMANDS ----------

@tree.command(name="help")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        "/redeem /generate /status /checkstock /feedback /report",
        ephemeral=True
    )

@tree.command(name="redeem")
@app_commands.describe(key="Your key")
async def redeem(interaction: discord.Interaction, key: str):
    keys = load("keys.json")
    users = load("users.json")

    if key not in keys:
        await interaction.response.send_message("Invalid key.", ephemeral=True)
        return

    key_type = keys[key]["type"]
    expire = None

    if key_type == "30days":
        expire = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat()
    elif key_type == "Vip+":
        expire = (datetime.datetime.utcnow() + datetime.timedelta(days=365)).isoformat()

    users[str(interaction.user.id)] = {
        "type": key_type,
        "expire": expire
    }

    del keys[key]

    save("users.json", users)
    save("keys.json", keys)

    await interaction.response.send_message(f"Redeemed: {key_type}", ephemeral=True)

@tree.command(name="status")
async def status(interaction: discord.Interaction):
    users = load("users.json")
    user_id = str(interaction.user.id)

    if user_id not in users:
        await interaction.response.send_message("No active key.", ephemeral=True)
        return

    data = users[user_id]
    await interaction.response.send_message(f"Type: {data['type']}\nExpire: {data['expire']}", ephemeral=True)

@tree.command(name="checkstock")
async def checkstock(interaction: discord.Interaction):
    stock = load("stock.json")
    message = ""

    for cat in stock:
        message += f"{cat} : {len(stock[cat])}\n"

    await interaction.response.send_message(message if message else "No stock.", ephemeral=True)

@tree.command(name="generate")
@app_commands.describe(category="Category name")
async def generate(interaction: discord.Interaction, category: str):
    users = load("users.json")
    stock = load("stock.json")
    user_id = str(interaction.user.id)

    if user_id not in users:
        await interaction.response.send_message("Redeem a key first.", ephemeral=True)
        return

    user = users[user_id]

    if user["expire"]:
        if datetime.datetime.utcnow() > datetime.datetime.fromisoformat(user["expire"]):
            await interaction.response.send_message("Key expired.", ephemeral=True)
            return

    if category not in stock or len(stock[category]) == 0:
        await interaction.response.send_message("No stock available.", ephemeral=True)
        return

    limits = {
        "30days": 500,
        "Vip+": 1500,
        "Lifetime": 2000
    }

    account = stock[category].pop(0)
    save("stock.json", stock)

    try:
        await interaction.user.send(f"Generated Account:\n{account}")
        await interaction.response.send_message("Sent to DM.", ephemeral=True)
    except:
        await interaction.response.send_message("Enable your DM first.", ephemeral=True)

@tree.command(name="feedback")
@app_commands.describe(message="Your feedback")
async def feedback(interaction: discord.Interaction, message: str):
    channel = client.get_channel(config["feedback_logs"])
    if channel:
        await channel.send(f"Feedback from {interaction.user}:\n{message}")
    await interaction.response.send_message("Feedback sent.", ephemeral=True)

@tree.command(name="report")
@app_commands.describe(message="Your report")
async def report(interaction: discord.Interaction, message: str):
    channel = client.get_channel(config["report_logs"])
    if channel:
        await channel.send(f"Report from {interaction.user}:\n{message}")
    await interaction.response.send_message("Report sent.", ephemeral=True)

# ---------- ADMIN COMMANDS ----------

@tree.command(name="genkey")
@app_commands.describe(amount="1-1000", type="30days / Vip+ / Lifetime")
async def genkey(interaction: discord.Interaction, amount: int, type: str):
    if config["admin_role_id"] not in [r.id for r in interaction.user.roles]:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    keys = load("keys.json")

    for _ in range(amount):
        key = f"superino-{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(100,999)}"
        keys[key] = {"type": type}

    save("keys.json", keys)

    await interaction.response.send_message(f"{amount} keys generated.", ephemeral=True)

@tree.command(name="addstock")
@app_commands.describe(category="Category name")
async def addstock(interaction: discord.Interaction, category: str):
    if config["admin_role_id"] not in [r.id for r in interaction.user.roles]:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    if not interaction.attachments:
        await interaction.response.send_message("Attach .txt file.", ephemeral=True)
        return

    attachment = interaction.attachments[0]
    content = await attachment.read()
    lines = content.decode().splitlines()

    stock = load("stock.json")

    if category not in stock:
        stock[category] = []

    stock[category].extend(lines)
    save("stock.json", stock)

    await interaction.response.send_message(f"Added {len(lines)} accounts to {category}.", ephemeral=True)

# ---------- READY ----------

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

client.run(config["token"])