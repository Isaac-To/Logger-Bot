import disnake
from disnake.ext import commands
import sqlite3
import os
import json


intents = disnake.Intents.all()
# Create bot
bot = commands.Bot(
    command_prefix="!",
    sync_commands_debug=True,
    intents=intents,
)

# Storage in RAM for enabled channels
enabled_cache = []

message_log = dict()


@bot.slash_command(description="Turn on message logging")
@commands.default_member_permissions(manage_guild=True)
async def log(inter):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM readable_channels WHERE sid=? AND cid=?",
              (inter.guild.id, inter.channel.id,))
    if (c.fetchone() is None):
        c.execute("INSERT INTO readable_channels VALUES (?, ?)",
                  (inter.guild.id, inter.channel.id,))
        conn.commit()
        await inter.response.send_message("Logging was turned on")
        enabled_cache.append((inter.guild.id, inter.channel.id))
    else:
        c.execute("DELETE FROM readable_channels WHERE sid=? and cid=?",
                  (inter.guild.id, inter.channel.id,))
        conn.commit()
        await inter.response.send_message("Logging was turned off")
        enabled_cache.remove((inter.guild.id, inter.channel.id))
    conn.close()


@bot.slash_command(description="Clears all messages in the channel")
@commands.default_member_permissions(manage_guild=True)
async def clear(inter):
    await inter.response.send_message("Clear may take a while... Please wait patiently")
    messages = await inter.channel.history().flatten()
    for msg in messages:
        await msg.delete()


@bot.slash_command(description="Exports json file containing the recorded logs")
@commands.default_member_permissions(manage_guild=True)
async def export(inter):
    try:
        f = open(f"{inter.channel.id}.json", "w")
        f.write(json.dumps(message_log[inter.channel.id]))
        f.close()
        await inter.response.send_message(file=disnake.File(f"{inter.channel.id}.json"))
        os.remove(f"{inter.channel.id}.json")

    except KeyError:
        await inter.response.send_message("There are no saved logs")


@bot.slash_command(description="Deletes the message log saved in ram")
@commands.default_member_permissions(manage_guild=True)
async def delete_logs(inter):
    try:
        del message_log[inter.channel.id]
        await inter.response.send_message("Logs were cleared from ram")
    except KeyError:
        await inter.response.send_message("There are no saved logs")


@bot.event
async def on_message(message):
    if message.author == bot.user or not (message.guild.id, message.channel.id) in enabled_cache:
        # No bot loopback
        return
    try:
        message_log[message.channel.id].append(
            {"author": message.author.name, "content": message.content, "timestamp": message.created_at.isoformat()})
    except KeyError:
        message_log[message.channel.id] = []
        message_log[message.channel.id].append(
            {"author": message.author.name, "content": message.content, "timestamp": message.created_at.isoformat()})
    await message.add_reaction("🔴")


if __name__ == "__main__":
    # Create table table for storing name and tokens
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS bot_data (
        name TEXT,
        token TEXT
        )""")
    conn.commit()
    # Import enabled channels
    c.execute(
        """CREATE TABLE IF NOT EXISTS readable_channels (sid INTEGER, cid INTEGER)""")
    conn.commit()
    c.execute("SELECT * FROM readable_channels")
    for sid, cid in c.fetchall():
        enabled_cache.append((sid, cid))
    # If there aren't any rows in the table, add one
    c.execute("SELECT * FROM bot_data")
    # Add the name and token to the table
    if c.fetchone() is None:
        # Prompt to get name and token
        name = input("Enter your name: ")
        token = input("Enter your token: ")
        c.execute("INSERT INTO bot_data VALUES (?, ?)",
                  (name, token))
        conn.commit()
    # Get name and token from db
    c.execute("SELECT * FROM bot_data")
    name, token = c.fetchone()
    c.close()
    # Create bot
    bot.run(token)
