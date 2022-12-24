import os
import dotenv
import discord
import json
from discord.ext import commands
from src.twitter_client import client as t_client
from src.piper import DataStream, FilterStream
from datetime import datetime

dotenv.load_dotenv(dotenv.find_dotenv())

client = commands.Bot(command_prefix="lolcat ", intents=discord.Intents.all())

running_filter_streams = []
running_data_streams = []

@client.command()
async def stream_from_account(ctx, user_id, name, role_id=None, keyword_config=None):
    with open("keywords_config.json", "r") as f:
        config = json.load(f)
    for filter_stream in running_filter_streams:
        if ((filter_stream.name == name)) or ((filter_stream.data_stream.user_id == user_id) and (filter_stream.keyword_config_name == keyword_config)):
            await ctx.send(f"```Stream with the same name or same user_id and config name already exists.```")
            return
    filter_stream_index = None
    for data_stream in running_data_streams:
        if data_stream.user_id == user_id:
            running_filter_streams.append(FilterStream(name, data_stream, config[keyword_config], keyword_config))
            filter_stream_index = len(running_filter_streams) - 1
            data_stream_index = running_data_streams.index(data_stream)
            break
    if filter_stream_index is None:
        running_data_streams.append(DataStream(t_client, user_id))
        running_filter_streams.append(FilterStream(name, running_data_streams[-1], config[keyword_config], keyword_config))
        filter_stream_index = len(running_filter_streams) - 1
        data_stream_index = len(running_data_streams) - 1
    account_color = discord.Color.from_rgb(int(user_id[0:3]) % 255, int(user_id[3:6]) % 255, int(user_id[6:9]) % 255)

    await ctx.send(f"```Started stream {name} listening to {user_id}.```")
    async for tweet in running_filter_streams[filter_stream_index].stream():
        if role_id:
            await ctx.send(f"<@&{role_id}>")
        embed = embed=discord.Embed(
            color=account_color,
            description=f"{tweet.text}\n\n[Intip bounty joki](https://twitter.com/i/web/status/{tweet.id})",
        )
        embed.set_author(
            name=f"@{running_data_streams[data_stream_index].user.username}",
            url=f"https://twitter.com/{running_data_streams[data_stream_index].user.username}",
            icon_url=f"{running_data_streams[data_stream_index].user.profile_image_url}"
        )
        timestamp = datetime.strptime(tweet.created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
        embed.set_footer(text=f"{timestamp} ∙ from {name}")
        await ctx.send(embed=embed)

@client.command()
async def show_running_filter_streams(ctx):
    if running_filter_streams:
        embed = discord.Embed(title="Running filter streams", color=discord.Color.green())
        embed.add_field(name="Name", value="\n".join([filter_stream.name for filter_stream in running_filter_streams]), inline=True)
        embed.add_field(name="Keyword config", value="\n".join([filter_stream.keyword_config_name for filter_stream in running_filter_streams]), inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"```No running streams.```")

@client.command()
async def stop_filter_stream(ctx, name):
    for filter_stream in running_filter_streams:
        if filter_stream.name == name:
            filter_stream.stop_stream()
            running_filter_streams.remove(filter_stream)
            await ctx.send(f"```Stopped stream {name}.```")
            return
    await ctx.send(f"```Stream {name} not found.```")

@client.command()
async def show_running_data_streams(ctx):
    if running_data_streams:
        embed = discord.Embed(title="Running data streams", color=discord.Color.green())
        embed.add_field(name="Name", value="\n".join([data_stream.name for data_stream in running_data_streams]), inline=True)
        embed.add_field(name="User ID", value="\n".join([data_stream.user_id for data_stream in running_data_streams]), inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"```No running streams.```")

@client.command()
async def stop_data_stream(ctx, name):
    for data_stream in running_data_streams:
        if data_stream.name == name:
            data_stream.stop_stream()
            running_data_streams.remove(data_stream)
            await ctx.send(f"```Stopped stream {name}.```")
            return
    await ctx.send(f"```Stream {name} not found.```")

@client.command()
async def show_keyword_configs(ctx, name=None):
    with open("keywords_config.json", "r") as f:
        keywords_config = json.load(f)
    if keywords_config:
        if name:
            if name in keywords_config:
                embed = discord.Embed(title=f"Keyword config for {name}", color=discord.Color.green())
                embed.add_field(name="Keywords to include", value=" ".join([keyword for keyword in keywords_config[name]["keywords_include"]]), inline=True)
                embed.add_field(name="Keywords to exclude", value=" ".join([keyword for keyword in keywords_config[name]["keywords_exclude"]]), inline=True)
                await ctx.send(embed=embed)
                return
            else:
                await ctx.send(f"```Keyword config {name} not found.```")
                return
        else:
            embed = discord.Embed(title="Keyword configs", color=discord.Color.green())
            embed.add_field(name="Name", value="\n".join([keyword_config for keyword_config in keywords_config]), inline=True)
            await ctx.send(embed=embed)
    else:
        await ctx.send(f"```No keyword configs.```")

@client.command()
async def add_keyword_config(ctx, name, *, keywords):
    with open("keywords_config.json", "r") as f:
        keywords_config = json.load(f)
    if name in keywords_config:
        await ctx.send(f"```Keyword config {name} already exists.```")
        return
    keywords = keywords.split("|")
    keywords_config.update({name: {"keywords_include": keywords[0].split(), "keywords_exclude": keywords[1].split()}})
    with open("keywords_config.json", "w") as f:
        json.dump(keywords_config, f, indent=4)
    embed = discord.Embed(title=f"Keyword config for {name}", color=discord.Color.green())
    embed.add_field(name="Keywords to include", value=" ".join([keyword for keyword in keywords[0]]), inline=True)
    embed.add_field(name="Keywords to exclude", value=" ".join([keyword for keyword in keywords[1]]), inline=True)
    await ctx.send(embed=embed)

@client.command()
async def remove_keyword_config(ctx, name):
    with open("keywords_config.json", "r") as f:
        keywords_config = json.load(f)
    if name not in keywords_config:
        await ctx.send(f"```Keyword config {name} not found.```")
        return
    keywords_config.pop(name)
    with open("keywords_config.json", "w") as f:
        json.dump(keywords_config, f, indent=4)
    await ctx.send(f"```Keyword config {name} removed.```")

@client.command()
async def ping(ctx):
    await ctx.send("pong")

@client.command()
async def evaluate(ctx):
    msg = ctx.message.content[16:]
    unallowed_keywords = ["os", "import", "from", "client", "print", "t_client"]
    if (not any(keyword in msg for keyword in unallowed_keywords)):
        await ctx.send(eval(ctx.message.content[16:]))

client.run(os.getenv("DC_TOKEN"))