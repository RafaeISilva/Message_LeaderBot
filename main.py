import discord
from discord.ext import commands, tasks
import json
import os
import uuid


class HelpCmd(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot
        commands = bot.commands

        result = []
        for cmd in commands:
            sign = self.get_command_signature(cmd)
            result.append(f"`{sign}`: {cmd.help}")

        await ctx.send("\n\n".join(result))

    send_cog_help = send_command_help = send_group_help = send_bot_help


class MsgLeaderBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="-",
            help_command=HelpCmd(),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        # start json updater
        self.json_updater.start()

    async def on_ready(self):
        # launch everytime bot is online (not only first boot)
        # just a way to know if the bot is online
        print("Bot online!")

    @tasks.loop(hours=8)
    async def json_updater(self):
        # update json every 8 hours
        print("Updated!")
        update_json()

    @json_updater.before_loop
    async def before_update(self):
        # wait until bot is ready before updating json
        await bot.wait_until_ready()


bot = MsgLeaderBot()

try:
    with open("settings.json", "r") as a:
        bot.settings = json.loads(a.read())
except FileNotFoundError:
    token = input("input bot token: ")
    bot.settings = {"token": token, "minimum": 20000, "listen_to_all": True}
    with open("settings.json", "w+") as a:
        json.dump(bot.settings, a, indent=4)

filename = "messages.json"
settings = "settings.json"

try:
    with open("messages.json", "r") as b:
        bot.msg_dic = json.loads(b.read())
except FileNotFoundError:
    bot.msg_dic = {}


def update_settings():
    temp = f"{uuid.uuid4()}-{settings}.tmp"
    with open(temp, "w") as c:
        json.dump(bot.settings.copy(), c, indent=4)

    os.replace(temp, settings)


def update_json():
    temp = f"{uuid.uuid4()}-{filename}.tmp"
    with open(temp, "w") as d:
        json.dump(bot.msg_dic.copy(), d, indent=4)

    os.replace(temp, filename)


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def autoupdate(ctx):
    """turns on/off automatic addition of new users to the leaderboard"""
    if bot.settings["listen_to_all"]:
        bot.settings["listen_to_all"] = False
        update_settings()
        return await ctx.send(
            "New users **will not** get added to the leaderboard anymore"
        )

    else:
        bot.settings["listen_to_all"] = True
        update_settings()
        return await ctx.send("New users **will** get added to the leaderboard")


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def edit(ctx, user: discord.User, message_number: int):
    """update a user's message number"""
    name = user.name
    if str(user.id) not in bot.msg_dic:
        bot.msg_dic[str(user.id)] = {
            "messages": message_number,
            "name": name,
            "alt": None,
            "is_alt": False,
            "is_bot": False,
        }
    else:
        bot.msg_dic[str(user.id)]["messages"] = message_number
    update_json()
    await ctx.send(f"{name} was saved with {message_number} messages")


@edit.error
async def edit_err(ctx, error):
    # error handler for minimum command
    if isinstance(error, commands.BadArgument):
        return await ctx.send("Error: you must input a valid number of messages")
    await on_command_error(ctx, error, bypass_check=True)


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def alt(ctx, user: discord.User, alt: discord.User):
    """adds up the alt's messages to the user's messages (1 alt per user)"""
    if user == alt:
        return await ctx.send(f"{user} can't be an alt of itself")

    elif str(user.id) not in bot.msg_dic:
        return await ctx.send(
            f"Error: {user} not found, try doing `-edit {user.id} <message_number>` first"
        )

    elif str(alt.id) not in bot.msg_dic:
        return await ctx.send(
            f"Error: {alt} not found, try doing `-edit {alt.id} <message_number>` first"
        )

    elif bot.msg_dic[str(alt.id)]["is_alt"]:
        return await ctx.send(f"Error: {alt.name} ({alt.id}) is already an alt")

    else:
        bot.msg_dic[str(user.id)]["alt"] = str(alt.id)
        bot.msg_dic[str(alt.id)]["is_alt"] = True
        update_json()

        await ctx.send(f"{alt} was saved as an alt of {user}")


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def removealt(ctx, user: discord.User, alt: discord.User):
    """removes alt from user"""
    # command to remove an user's alt
    if user == alt:
        return await ctx.send(f"{user} can't be an alt of itself")

    elif str(user.id) not in bot.msg_dic:
        return await ctx.send(f"Error: {user} not found")

    elif str(alt.id) not in bot.msg_dic:
        return await ctx.send(f"Error: {alt} not found")

    elif not bot.msg_dic[str(user.id)]["alt"]:
        return await ctx.send(f"Error: {user} has no alts")

    elif not bot.msg_dic[str(alt.id)]["is_alt"]:
        return await ctx.send(f"Error: {alt} is not an alt")

    else:
        bot.msg_dic[str(user.id)]["alt"] = None
        bot.msg_dic[str(alt.id)]["is_alt"] = False
        update_json()

        await ctx.send(f"{alt} is no longer an alt of {user}")


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def addbot(ctx, user: discord.User):
    """saves a user as a bot (displayed on the bottom of the leaderboard)"""
    if bot.msg_dic[str(user.id)]["is_bot"]:
        await ctx.send(f"{user} is already a bot")

    try:
        bot.msg_dic[str(user.id)]["is_bot"] = True
        update_json()
        await ctx.send(f"{user} is now a bot")
    except KeyError:
        await ctx.send(f"Error: {user} is not listed in the leaderboard")


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def rmvbot(ctx, user: discord.User):
    """removes bot tag form a user"""
    if not bot.msg_dic[str(user.id)]["is_bot"]:
        await ctx.send(f"{user} is already not a bot")

    try:
        bot.msg_dic[str(user.id)]["is_bot"] = False
        update_json()
        await ctx.send(f"{user} is no longer a bot")
    except KeyError:
        await ctx.send(f"Error: {user} is not listed in the leaderboard")


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def delete(ctx, user: discord.User):
    """delete a user from the leaderboard"""
    try:
        bot.msg_dic.pop(str(user.id))
        update_json()
        await ctx.send(f"{user} was deleted")
    except KeyError:
        await ctx.send(f"Error: {user} is not listed in the leaderboard")


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def minimum(ctx, value: int):
    """change the minimum amount of messages necessary to appear on the leaderboard (defaults to 20000)"""
    bot.settings["minimum"] = value
    update_settings()
    if value == 1:
        await ctx.send(
            f"Every user with more than {value} message will now be displayed on the leadeboard"
        )
    else:
        await ctx.send(
            f"Every user with more than {value} messages will now be displayed on the leadeboard"
        )


@minimum.error
async def minimum_err(ctx, error):
    # error handler for minimum command
    if isinstance(error, commands.BadArgument):
        return await ctx.send("Error: invalid value")
    await on_command_error(ctx, error, bypass_check=True)


@bot.command()
async def source(ctx):
    """prints the source code link"""
    await ctx.send("https://github.com/RafaeI11/Message_LeaderBot")


@bot.command()
async def minfo(ctx):
    """prints the current minimum value to appear on the leaderboard"""
    await ctx.send(f"The current minimum is {bot.settings['minimum']} messages")


@bot.command()
async def name(ctx):
    """updates author's name on the leadeboard"""
    author = ctx.author

    if str(author.id) not in bot.msg_dic:
        return

    name = author.name

    if name == bot.msg_dic[str(author.id)]["name"]:
        return await ctx.send("Your name is already up to date")

    else:
        bot.msg_dic[str(author.id)]["name"] = name
        await ctx.send(f"Name updated to {name}")


@bot.command()
async def msglb(ctx):
    """prints the message leaderboard"""
    update_json()
    simple_msg_dic = {}
    msg_lb = ""
    bots_lb = ""
    msg_dic = bot.msg_dic

    for id in msg_dic:
        # excludes alt users from the leadeboard
        if not msg_dic[id]["alt"] and not msg_dic[id]["is_alt"]:
            simple_msg_dic[id] = msg_dic[id]["messages"]

        # sums the number of messages of users with alts to its respective alts
        if msg_dic[id]["alt"] and not msg_dic[id]["is_alt"]:
            simple_msg_dic[id] = (
                msg_dic[id]["messages"] + msg_dic[msg_dic[id]["alt"]]["messages"]
            )

    # sorts the leaderboard by most messages in probably the ugliest way possible
    almost_sorted_msg_dic = sorted(
        simple_msg_dic.items(), key=lambda x: x[1], reverse=True
    )
    sorted_msg_dic = {}

    for item in almost_sorted_msg_dic:
        sorted_msg_dic[str(item[0])] = int(item[1])

    # restricts the leaderboard to only users with more than a certain minimum
    for user in sorted_msg_dic:
        # prevents bots from being on the top
        if msg_dic[user]["is_bot"]:
            bots_lb += f"{simple_msg_dic[user]}: {msg_dic[user]['name']}\n"
        elif int(sorted_msg_dic[user]) >= bot.settings["minimum"]:
            if msg_dic[user]["alt"] is not None:
                msg_lb += f"{simple_msg_dic[user]}: {msg_dic[user]['name']} + alt\n"
            else:
                msg_lb += f"{simple_msg_dic[user]}: {msg_dic[user]['name']}\n"

    # adds bots to the end
    msg_lb += "\n" + bots_lb

    embed = discord.Embed(
        title="Message Leaderboard", color=7419530, description=msg_lb
    )
    await ctx.send(embed=embed)


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # adds a point to the author everytime a message is sent
    if str(message.author.id) not in bot.msg_dic and bot.settings["listen_to_all"]:
        if message.author.bot:
            bot.msg_dic[str(message.author.id)] = {
                "messages": 1,
                "name": message.author.name,
                "alt": None,
                "is_alt": False,
                "is_bot": True,
            }
        else:
            bot.msg_dic[str(message.author.id)] = {
                "messages": 1,
                "name": message.author.name,
                "alt": None,
                "is_alt": False,
                "is_bot": False,
            }

    elif str(message.author.id) in bot.msg_dic:
        bot.msg_dic[str(message.author.id)]["messages"] += 1

    # process a command (if valid)
    await bot.process_commands(message)


@bot.event
async def on_message_delete(message):
    bot.msg_dic[str(message.author.id)]["messages"] -= 1


@bot.event
async def on_command_error(
    ctx, error: commands.CommandError, *, bypass_check: bool = False
):
    # handles command error

    if ctx.command and ctx.command.has_error_handler() and not bypass_check:
        # already have error handler
        return

    # get the "real" error
    error = getattr(error, "original", error)

    if isinstance(error, commands.CommandNotFound):
        # command not found is annoying for most bot user, so just return nothing
        return

    if isinstance(error, commands.UserNotFound):
        return await ctx.send(f"Error: user '{error.argument}' not found")

    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(f"Error: you must input a valid `{error.param.name}`")

    if isinstance(error, commands.MissingPermissions):
        # probably i made it too over-complicated,
        # but its so that the message stays consistent with the other error messages
        error = str(error)
        return await ctx.send(f"Error: {error[0].lower()}{error[1:-1]}")

    raise error


bot.run(bot.settings["token"])
