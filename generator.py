import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import string
from datetime import datetime, timedelta

TOKEN = "MTQ3NTQ3NzkxNjEzNjYzNjU0Ng.GiRMZD.7D98AEjnSRDsEc_bn8tS4lTaVOfHCN7mvF2DcU"
ADMIN_IDS = [1475101884087009341]  # palitan mo ng discord user id mo

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------ FILE SETUP ------------------

os.makedirs("data", exist_ok=True)
os.makedirs("stock", exist_ok=True)

for file in ["data/keys.json", "data/users.json"]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

# ------------------ LOAD SAVE ------------------

def load(file):
    with open(file, "r") as f:
        return json.load(f)

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ------------------ KEY GENERATOR ------------------

def generate_key():
    numbers = "-".join(["".join(random.choices(string.digits, k=3)) for _ in range(3)])
    return f"DiavalsVault-{numbers}"

# ------------------ EXPIRATION ------------------

def get_expiration(key_type):
    if key_type == "30days":
        return (datetime.utcnow() + timedelta(days=30)).isoformat()
    elif key_type == "Vip+":
        return (datetime.utcnow() + timedelta(days=365)).isoformat()
    elif key_type == "Lifetime":
        return "Lifetime"

# ------------------ LIMITS ------------------

def get_limit(key_type):
    if key_type == "30days":
        return 500
    elif key_type == "Vip+":
        return 1500
    elif key_type == "Lifetime":
        return 2000

# ------------------ EVENTS ------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ------------------ USER COMMANDS ------------------

@bot.tree.command(name="help", description="See all commands")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("""
User Commands:
/redeem
/generate <category>
/status
/checkstock
/feedback <message>
/report <message>

Admin Commands:
/genkey
/addstock
/checkstatus
/removeaccess
/message
/giveaways
""", ephemeral=True)

# ------------------ REDEEM ------------------

@bot.tree.command(name="redeem")
@app_commands.describe(key="Enter your key")
async def redeem(interaction: discord.Interaction, key: str):
    keys = load("data/keys.json")
    users = load("data/users.json")

    if key not in keys:
        return await interaction.response.send_message("Invalid key.", ephemeral=True)

    if keys[key]["used"]:
        return await interaction.response.send_message("Key already used.", ephemeral=True)

    keys[key]["used"] = True
    users[str(interaction.user.id)] = {
        "type": keys[key]["type"],
        "expiration": keys[key]["expiration"],
        "generated": 0
    }

    save("data/keys.json", keys)
    save("data/users.json", users)

    await interaction.response.send_message("Key redeemed successfully!", ephemeral=True)

# ------------------ STATUS ------------------

@bot.tree.command(name="status")
async def status(interaction: discord.Interaction):
    users = load("data/users.json")
    user = users.get(str(interaction.user.id))

    if not user:
        return await interaction.response.send_message("No active key.", ephemeral=True)

    await interaction.response.send_message(
        f"Type: {user['type']}\nExpiration: {user['expiration']}\nGenerated: {user['generated']}",
        ephemeral=True
    )

# ------------------ CHECK STOCK ------------------

@bot.tree.command(name="checkstock")
async def checkstock(interaction: discord.Interaction):
    categories = os.listdir("stock")
    msg = ""

    for cat in categories:
        with open(f"stock/{cat}", "r") as f:
            count = len(f.readlines())
        msg += f"{cat.replace('.txt','')} - {count}\n"

    await interaction.response.send_message(msg if msg else "No stock available.", ephemeral=True)

# ------------------ GENERATE ------------------

@bot.tree.command(name="generate")
@app_commands.describe(category="Stock category name")
async def generate(interaction: discord.Interaction, category: str):

    users = load("data/users.json")
    user = users.get(str(interaction.user.id))

    if not user:
        return await interaction.response.send_message("Redeem a key first.", ephemeral=True)

    limit = get_limit(user["type"])
    if user["generated"] >= limit:
        return await interaction.response.send_message("Generation limit reached.", ephemeral=True)

    file_path = f"stock/{category}.txt"
    if not os.path.exists(file_path):
        return await interaction.response.send_message("Category not found.", ephemeral=True)

    with open(file_path, "r") as f:
        lines = f.readlines()

    if not lines:
        return await interaction.response.send_message("Out of stock.", ephemeral=True)

    item = lines[0]
    with open(file_path, "w") as f:
        f.writelines(lines[1:])

    user["generated"] += 1
    save("data/users.json", users)

    await interaction.user.send(f"Generated Item:\n{item}")
    await interaction.response.send_message("Check your DMs!", ephemeral=True)

# ------------------ ADMIN ------------------

@bot.tree.command(name="genkey")
@app_commands.describe(amount="1-1000", type="30days / Vip+ / Lifetime")
async def genkey(interaction: discord.Interaction, amount: int, type: str):

    if interaction.user.id not in ADMIN_IDS:
        return await interaction.response.send_message("No permission.", ephemeral=True)

    if amount < 1 or amount > 1000:
        return await interaction.response.send_message("Max 1000.", ephemeral=True)

    keys = load("data/keys.json")
    generated_keys = []

    for _ in range(amount):
        key = generate_key()
        keys[key] = {
            "type": type,
            "expiration": get_expiration(type),
            "used": False
        }
        generated_keys.append(key)

    save("data/keys.json", keys)

    await interaction.response.send_message("\n".join(generated_keys), ephemeral=True)

# ------------------

bot.run(TOKEN)
