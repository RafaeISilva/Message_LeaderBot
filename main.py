import json

import discord
from discord.ext import commands, tasks

from utils import *


class HelpCmd(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot
        commands = bot.commands
        result = []

        for cmd in commands:
            sign = self.get_command_signature(cmd)
            result.append(f"`{sign.strip()}`: {cmd.help}")

        await ctx.send("\n".join(result))

    send_cog_help = send_command_help = send_group_help = send_bot_help


class MsgLeaderBot(commands.Bot):
    def __init__(self):
        helpattr = {"usage": ""}
        super().__init__(
            command_prefix="-",
            help_command=HelpCmd(command_attrs=helpattr),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        # start json updater and file saver
        self.json_updater.start()
        self.save.start()

    async def on_ready(self):
        # launch everytime bot is online (not only first boot)
        # just a way to know if the bot is online
        print("Bot online!")

    @tasks.loop(hours=8)
    async def json_updater(self):
        # update json every 8 hours
        print("Updated!")
        update_json(bot.msg_dic)

    @tasks.loop(hours=24)
    async def save(self):
        # create/update json for every server every 24 hours
        saver()

    @json_updater.before_loop
    async def before_update(self):
        await bot.wait_until_ready()

    @save.before_loop
    async def before_save(self):
        await bot.wait_until_ready()


bot = MsgLeaderBot()

try:
    with open("settings.json", "r") as a:
        bot.settings = json.loads(a.read())
    bot.settings["token"]
except (FileNotFoundError, KeyError, json.decoder.JSONDecodeError):
    token = input("input bot token: ")
    bot.settings = {"token": token}
    with open("settings.json", "w+") as a:
        json.dump(bot.settings, a, indent=4)

try:
    with open("messages.json", "r") as b:
        bot.msg_dic = json.loads(b.read())
except (FileNotFoundError, json.decoder.JSONDecodeError):
    bot.msg_dic = {}


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def autoupdate(ctx):
    """turns on/off automatic addition of new users to the leaderboard"""
    server = str(ctx.message.guild.id)

    if bot.settings[server]["listen_to_all"]:
        bot.settings[server]["listen_to_all"] = False
        update_settings(bot.settings)
        return await ctx.send(
            "New users **will not** get added to the leaderboard anymore"
        )

    else:
        bot.settings[server]["listen_to_all"] = True
        update_settings(bot.settings)
        return await ctx.send("New users **will** get added to the leaderboard")


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def edit(ctx, user: discord.User, message_number: int):
    """update a user's message number"""
    name = user.name
    server = str(ctx.message.guild.id)
    if str(user.id) not in bot.msg_dic[server]:
        bot.msg_dic[server][str(user.id)] = {
            "messages": message_number,
            "name": name,
            "alt": None,
            "is_alt": False,
            "is_bot": False,
        }

    else:
        bot.msg_dic[server][str(user.id)]["messages"] = message_number

    update_json(bot.msg_dic)
    await ctx.send(f"{name} was saved with {message_number} messages")


@edit.error
async def edit_err(ctx, error):
    # error handler for edit command
    if isinstance(error, commands.BadArgument):
        return await ctx.send("Error: you must input a valid number of messages")

    await on_command_error(ctx, error, bypass_check=True)


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def alt(ctx, user: discord.User, alt: discord.User):
    """adds up the alt's messages to the user's messages"""
    await ctx.send(alt_handler(bot, ctx, user, alt))


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def removealt(ctx, user: discord.User, alt: discord.User):
    """removes alt from user"""
    await ctx.send(alt_handler(bot, ctx, user, alt, add=False))


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def addbot(ctx, user: discord.User):
    """saves a user as a bot (displayed on the bottom of the leaderboard)"""
    server = str(ctx.message.guild.id)

    try:
        if bot.msg_dic[server][str(user.id)]["is_bot"]:
            await ctx.send(f"{user} is already a bot")
        else:
            bot.msg_dic[server][str(user.id)]["is_bot"] = True
            update_json(bot.msg_dic)
            await ctx.send(f"{user} is now a bot")
    except KeyError:
        await ctx.send(f"Error: {user} is not listed in the leaderboard")


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def rmvbot(ctx, user: discord.User):
    """removes bot tag from a user"""
    server = str(ctx.message.guild.id)

    try:
        if not bot.msg_dic[server][str(user.id)]["is_bot"]:
            await ctx.send(f"{user} is already not a bot")
        else:
            bot.msg_dic[server][str(user.id)]["is_bot"] = False
            update_json(bot.msg_dic)
            await ctx.send(f"{user} is no longer a bot")
    except KeyError:
        await ctx.send(f"Error: {user} is not listed in the leaderboard")


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def delete(ctx, user: discord.User):
    """delete a user from the leaderboard"""
    server = str(ctx.message.guild.id)
    try:
        bot.msg_dic[server].pop(str(user.id))
        update_json(bot.msg_dic)
        await ctx.send(f"{user} was deleted")
    except KeyError:
        await ctx.send(f"Error: {user} is not listed in the leaderboard")


@bot.command()
@commands.has_guild_permissions(manage_channels=True)
async def minimum(ctx, value: int):
    """change the minimum amount of messages necessary to appear on the leaderboard (defaults to 20000)"""
    server = str(ctx.message.guild.id)
    bot.settings[server]["minimum"] = value
    update_settings(bot.settings)

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
    await ctx.send("https://github.com/RafaeISilva/Message_LeaderBot")


@bot.command()
async def ping(ctx):
    """Tells the ping of the bot to the discord servers"""
    update_json(bot.msg_dic)  # because why not
    await ctx.send(f"Pong! {round(bot.latency*1000)}ms")


@bot.command()
async def minfo(ctx):
    """prints the current minimum value to appear on the leaderboard"""
    await ctx.send(
        f"The current minimum is {bot.settings[str(ctx.message.guild.id)]['minimum']} messages"
    )


@bot.command()
async def name(ctx):
    """updates author's name on the leadeboard"""
    author = ctx.author
    msg_dic = bot.msg_dic[str(ctx.message.guild.id)]

    if str(author.id) not in msg_dic:
        return

    name = author.name

    if name == msg_dic[str(author.id)]["name"]:
        return await ctx.send("Your name is already up to date")

    else:
        msg_dic[str(author.id)]["name"] = name
        await ctx.send(f"Name updated to {name}")


@bot.command()
async def msglb(ctx):
    """prints the message leaderboard"""
    update_json(bot.msg_dic)
    server = str(ctx.message.guild.id)
    author = str(ctx.author.id)
    smgs_dic = {}
    msg_lb = ""
    bots_lb = ""
    top_users = []
    msg_dic = bot.msg_dic[server]

    if author in msg_dic and msg_dic[author]["is_alt"]:
        for id in msg_dic:
            if msg_dic[id]["alt"] is not None and author in msg_dic[id]["alt"]:
                author = id
                break

    for id in msg_dic:
        # excludes alt users from the leadeboard
        if not msg_dic[id]["is_alt"]:
            if not msg_dic[id]["alt"]:
                smgs_dic[id] = msg_dic[id]["messages"]

            # sums the number of messages of users with alts to its respective alts
            if msg_dic[id]["alt"]:
                messages = 0

                for alt in msg_dic[id]["alt"]:
                    messages += msg_dic[alt]["messages"]

                smgs_dic[id] = msg_dic[id]["messages"] + messages

    # sorts the leaderboard
    smgs_dic = dict(sorted(smgs_dic.items(), key=lambda item: item[1], reverse=True))

    # restricts the leaderboard to only users with more than a certain minimum
    for user in smgs_dic:
        if int(smgs_dic[user]) >= bot.settings[server]["minimum"]:
            top_users.append(user)

            # prevents bots from being on the top
            if msg_dic[user]["is_bot"]:
                bots_lb += f"{smgs_dic[user]}: {msg_dic[user]['name']}\n"

            elif msg_dic[user]["alt"] is not None:
                if author == user:
                    msg_lb += "**"

                if len(msg_dic[user]["alt"]) == 1:
                    msg_lb += f"{smgs_dic[user]}: {msg_dic[user]['name']} + alt\n"

                else:
                    alts = len(msg_dic[user]["alt"])
                    msg_lb += (
                        f"{smgs_dic[user]}: {msg_dic[user]['name']} +{alts} alts\n"
                    )

                if author == user:
                    msg_lb += "**"

            else:
                if author == user:
                    msg_lb += "**"

                msg_lb += f"{smgs_dic[user]}: {msg_dic[user]['name']}\n"

                if author == user:
                    msg_lb += "**"

    # adds bots to the end
    msg_lb += "\n" + bots_lb

    # adds message author to the end if not already on the leaderboard
    if author in msg_dic and author not in top_users:
        if msg_dic[author]["alt"]:
            if len(msg_dic[author]["alt"]) == 1:
                msg_lb += f"**{smgs_dic[author]}: {msg_dic[author]['name']} + alt**"

            else:
                alts = len(msg_dic[author]["alt"])
                msg_lb += (
                    f"**{smgs_dic[author]}: {msg_dic[author]['name']} +{alts} alts**"
                )

        else:
            msg_lb += f"**{smgs_dic[author]}: {msg_dic[author]['name']}**"

    embed = discord.Embed(
        title="Message Leaderboard", color=7419530, description=msg_lb
    )
    await ctx.send(embed=embed)


@bot.command()
async def msg(ctx, username: str = ""):
    """check how many messages a user has"""
    msg_dic = bot.msg_dic[str(ctx.message.guild.id)]
    success = False

    if not username:
        username = str(ctx.author.id)

    # checks if input is a user's id on the leadeboard
    if username.isdecimal():
        try:
            msg_dic[username]
            success = True
        except KeyError:
            await ctx.send(
                discord.utils.escape_mentions(f"Error: {username} not found")
            )

    # checks if input is a user mention and if user's id is on the leaderboard
    elif "<@" in username:
        if "!" in username:
            username = username.replace("!", "")

        username = username.replace("<@", "").replace(">", "")

        try:
            msg_dic[username]
            success = True
        except KeyError:
            await ctx.send(
                discord.utils.escape_mentions(f"Error: {username} not found")
            )

    # checks if input is a username on the leaderboard
    else:
        for id in msg_dic:
            if msg_dic[id]["name"].lower() == username.lower():
                username = id
                success = True
                break

        try:
            msg_dic[username]
        except KeyError:
            await ctx.send(
                discord.utils.escape_mentions(f"Error: {username} not found")
            )

    if success:
        name = msg_dic[username]["name"]
        messages = msg_dic[username]["messages"]

        if msg_dic[username]["alt"] is None:
            await ctx.send(
                discord.utils.escape_mentions(f"{name} has {messages} messages")
            )

        else:
            alt_messages = 0

            for alt in msg_dic[username]["alt"]:
                alt_messages += msg_dic[alt]["messages"]

            await ctx.send(
                discord.utils.escape_mentions(
                    f"{name} has {messages} (+{alt_messages}) messages"
                )
            )


@bot.command()
async def altinfo(ctx, username: str):
    """check the name of a user's alt or vice versa"""
    msg_dic = bot.msg_dic[str(ctx.message.guild.id)]
    result = ""
    success = False

    # checks if input is a user's id on the leadeboard
    if username.isdecimal():
        try:
            msg_dic[username]
            success = True
        except KeyError:
            await ctx.send(
                discord.utils.escape_mentions(f"Error: {username} not found")
            )

    # checks if input is a user mention and if user's id is on the leaderboard
    elif "<@" in username:
        if "!" in username:
            username = username.replace("!", "")

        username = username.replace("<@", "").replace(">", "")

        try:
            msg_dic[username]
            success = True
        except KeyError:
            await ctx.send(
                discord.utils.escape_mentions(f"Error: {username} not found")
            )

    # checks if input is a username on the leaderboard
    else:
        for id in msg_dic:
            if msg_dic[id]["name"].lower() == username.lower():
                username = id
                success = True
                break

        try:
            msg_dic[username]
        except KeyError:
            await ctx.send(
                discord.utils.escape_mentions(f"Error: {username} not found")
            )

    if success:
        # checks if username is an alt and gets its name
        if msg_dic[username]["is_alt"]:
            for id in msg_dic:
                if msg_dic[id]["alt"] is not None and username in msg_dic[id]["alt"]:
                    result = f"{msg_dic[username]['name']} is an alt of {msg_dic[id]['name']}"
                    break

        # checks if username has an alt and gets its name
        elif msg_dic[username]["alt"] is not None:
            if len(msg_dic[username]["alt"]) == 1:
                result = f"{msg_dic[msg_dic[username]['alt'][0]]['name']} is an alt of {msg_dic[username]['name']}"

            else:
                alt_list = msg_dic[username]["alt"]
                result = ", ".join(msg_dic[alt]["name"] for alt in alt_list[0:-1])
                result += f" and {msg_dic[alt_list[-1]]['name']} are alts of {msg_dic[username]['name']}"

        else:
            result = f"{msg_dic[username]['name']} has no alts/is not an alt"

        await ctx.send(result)


@bot.event
async def on_message(message):
    user = message.author
    if user == bot.user:
        return

    try:
        msg_dic = bot.msg_dic[str(message.guild.id)]
    except KeyError:
        msg_dic = bot.msg_dic[str(message.guild.id)] = {}

    try:
        bot.settings[str(message.guild.id)]["minimum"]
        bot.settings[str(message.guild.id)]["listen_to_all"]
    except KeyError:
        bot.settings[str(message.guild.id)] = {"minimum": 20000, "listen_to_all": True}
        update_settings(bot.settings)
    settings = bot.settings[str(message.guild.id)]

    # adds a point to the author everytime a message is sent
    if str(user.id) not in msg_dic and settings["listen_to_all"]:
        if user.bot:
            msg_dic[str(user.id)] = {
                "messages": 1,
                "name": user.name,
                "alt": None,
                "is_alt": False,
                "is_bot": True,
            }
        else:
            msg_dic[str(user.id)] = {
                "messages": 1,
                "name": user.name,
                "alt": None,
                "is_alt": False,
                "is_bot": False,
            }

    elif str(user.id) in msg_dic:
        msg_dic[str(user.id)]["messages"] += 1

    # process a command (if valid)
    await bot.process_commands(message)


@bot.event
async def on_message_delete(message):
    user = str(message.author.id)
    msg_dic = bot.msg_dic[str(message.guild.id)]

    if user in msg_dic:
        msg_dic[user]["messages"] -= 1


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
        # command not found is annoying for most bot users, so just return nothing
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

    try:
        raise error
    except discord.errors.Forbidden:
        await ctx.author.send(f"```\n{error}\n```")


if __name__ == "__main__":
    bot.run(bot.settings["token"])
