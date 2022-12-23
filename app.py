import os
import dotenv
import discord
import json
from discord.ext import commands
from src.twitter_client import client as t_client
from src.piper import DataStream

dotenv.load_dotenv(dotenv.find_dotenv())

client = commands.Bot(command_prefix="lolcat ", intents=discord.Intents.all())

running_streams = []

@client.command()
async def stream_from_account(ctx, account_id, name, role_id=None, keyword_config=None):
    for stream in running_streams:
        if ((stream.user_id == account_id) and (stream.keyword_config == keyword_config)) or (stream.name == name):
            await ctx.send(f"```Stream to {account_id} already exists.```")
            return
    
    with open("keywords_config.json", "r") as f:
        config = json.load(f)
    running_streams.append(DataStream(t_client, account_id, name, config[keyword_config] if keyword_config else None))
    stream_index = len(running_streams) - 1
    account_color = discord.Color.from_rgb(int(account_id[0:3]) % 255, int(account_id[3:6]) % 255, int(account_id[6:9]) % 255)

    await ctx.send(f"```Started stream {name} listening to {account_id}.```")
    async for tweet in running_streams[stream_index].stream():
        if role_id:
            await ctx.send(f"<@&{role_id}>")
        embed = embed=discord.Embed(
            color=account_color,
            description=f"{tweet.text}\n\n[Intip bounty joki](https://twitter.com/i/web/status/{tweet.id})",
        )
        embed.set_author(
            name=f"@{running_streams[stream_index].user.username}",
            url=f"https://twitter.com/{running_streams[stream_index].user.username}",
            icon_url=f"{running_streams[stream_index].user.profile_image_url}"
        )
        embed.set_footer(text=f"Tweet created at {tweet.created_at}\nFrom stream {name}")
        await ctx.send(embed=embed)

@client.command()
async def list_streams(ctx):
    if running_streams:
        embed = discord.Embed(title="Running streams", color=discord.Color.green())
        embed.add_field(name="Name", value="\n".join([stream.name for stream in running_streams]), inline=True)
        embed.add_field(name="Account ID", value="\n".join([stream.user_id for stream in running_streams]), inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"```No running streams.```")

@client.command()
async def stop_stream(ctx, name):
    for stream in running_streams:
        if stream.name == name:
            stream.stop_stream()
            running_streams.remove(stream)
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