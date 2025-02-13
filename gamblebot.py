import random
import asyncio
import time
from aiohttp import request
import json
import requests

import discord
from discord.ext import commands
from discord import app_commands
from discord import interactions

from p import passw
from database import database
from menu import Menu
from starrDropSimulator import simulate_drop
from rankedpicks import ranked_picks
import secret



db = database(user='dbadmin', password=passw, host='localhost', database='test')
db.build_database()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

intents = discord.Intents.all()

TOKEN = secret.TOKEN

bot = commands.Bot(command_prefix=['--', '—', '——'], intents=intents)

@bot.event
async def on_ready():
    print(f'Bot started as {bot.user}')
    print('------------------------')

@bot.command()
async def synccmd(ctx):
  synced = await bot.tree.sync()
  await ctx.send(f"Syncd {len(synced)} commands")

async def get_user(userid:int):
    """
    gets user object given userid
    """

    URL = f"https://discord.com/api/users/{userid}"

    headers = {
        "Authorization" : f"Bot {TOKEN}"
    }

    response = requests.get(url=URL, headers=headers)
    data = response.json()
    return data


# =====================================================

def _get_coins(id1, id2=None):
    """
    get coins balance of specified user(s)
    input is discord ids
    """

    # get all registered ids from database
    input = db._execute_query('SELECT discord_id from users')
    ids = [i[0] for i in input]

    # add user to database if not exist (start with 1000 coins)
    if id1 not in ids:
        db._execute_query(f'INSERT INTO users (discord_id, coins) VALUES ({id1}, 1000)', commit=True)
    
    # get coins of user
    coins1 = db._execute_query(f'SELECT coins FROM users WHERE discord_id={id1}')[0][0]

    if id2 is None:
        return coins1
    
    # do same for 2nd id if inputted
    if id2 not in ids:
        db._execute_query(f'INSERT INTO users (discord_id, coins) VALUES ({id2}, 1000)', commit=True)

    coins2 = db._execute_query(f'SELECT coins FROM users WHERE discord_id={id2}')[0][0]
    
    return coins1, coins2

async def get_image(interaction:discord.Interaction, url: str, data_type: str = "json"):
    async with request("GET", url, headers={}) as response:
        if response.status == 200:
            data = await response.read()

            return json.loads(data)
        else:
            await interaction.response.send_message("Could not receive image, please try again later.", ephemeral=True)

# =====================================================

@bot.tree.command(name='say')
@app_commands.describe(arg = 'What should I say?')
async def say(interaction:discord.Interaction, arg:str):
    """
    slash command example with arguments
    """

    await interaction.response.send_message(arg)

@bot.tree.command(name='profile')
@app_commands.describe(user = 'User')
async def profile(interaction:discord.Interaction, user:discord.User = None):
    """
    get user coins profile
    """

    if user is None:
        user = interaction.user
    
    coins = _get_coins(user.id)
    
    await interaction.response.send_message(f'{user.name} coin balance: {coins}')

@bot.tree.command(name='leaderboard')
@app_commands.describe(max='Maximum leaderboard entries')
async def leaderboard(interaction:discord.Interaction, max:int = 10):
    """
    show top {max} coins holders
    """

    if max < 1:
        max = 10
    
    data = list(db._execute_query(f'SELECT discord_id, coins FROM users'))
    data.sort(key=lambda x : x[1], reverse=True)

    if len(data) < max:
        max = len(data)
    
    output = f'```Leaderboard for {interaction.guild.name}```\n'

    for i in range(max):
        user = await get_user(data[i][0])
        name = user['global_name']
        if name is None:
            name = f"<@{data[i][0]}>"

        output += f"{name} - {data[i][1]} coins\n"
    
    await interaction.response.send_message(output)

class Buttons(discord.ui.View):
    def __init__(self, *, timeout=180, int:discord.Interaction, opp:discord.User, wager:int):
        super().__init__(timeout=timeout)
        self.int = int
        self.opp = opp
        self.wager = wager
    @discord.ui.button(label="Flip!",style=discord.ButtonStyle.gray)
    async def flip(self, button:discord.ui.Button, interaction:discord.Interaction):
        int = self.int
        opp = self.opp
        wager = self.wager
        
        # int.message.delete

        # get coins of both users, check if they have enough
        coins1, coins2 = _get_coins(int.user.id, opp.id)

        if coins1 < wager:
            await int.response.send_message(f'{int.user.name} does not have enough coins')
            return
        
        if coins2 < wager and opp.id != 1234711128899063839:
            await int.response.send_message(f'{opp.name} does not have enough coins')
            return
        
        # animation gif
        embed = discord.Embed(title='Intense Coin Flip...')
        
        embed.set_image(url='https://media1.tenor.com/m/C4_CkeF1l90AAAAd/railgun-anime.gif')

        await int.channel.send(embed=embed, delete_after=3)
        await asyncio.sleep(3)
        
        # find winner, update coins in db
        r = random.randint(1, 2)
        if r == 1:
            winner = int.user
            newcoins1 = coins1+wager
            newcoins2 = coins2-wager
            winnercoins = newcoins1
        else:
            winner = opp
            newcoins1 = coins1-wager
            newcoins2 = coins2+wager
            winnercoins = newcoins2
        
        if newcoins2 < 0 and opp.id == 1234711128899063839:
            newcoins2 = 0
        

        db._execute_query(f'UPDATE users SET coins={newcoins1} WHERE discord_id={int.user.id}', commit=True)
        db._execute_query(f'UPDATE users SET coins={newcoins2} WHERE discord_id={opp.id}', commit=True)

        embed = discord.Embed(title="Coinflip...",
                        description=f"**Winner**: {winner.name}\n**Received**: {wager} coins ({winnercoins})",
                        colour=0xffcb70)

        # show winning embed
        if winner.id == bot.user.id:
            pass
            #avatar_url = bot.user.avatar.url
        else:
            avatar_url = winner.avatar.url
            embed.set_thumbnail(url=avatar_url)
        
        await int.channel.send(embed=embed)

@bot.tree.command(name='flip', description='Wager an opponent in a coin flip')
@app_commands.describe(opp='Opponent', wager='Coins Wager')
async def flip_request(interaction:discord.Interaction, opp:discord.User, wager:int):
    """
    /flip @user 2000
    """

    if interaction.user is opp:
        await interaction.response.send_message(f'You cannot bet against yourself.', ephemeral=True)
        return

    if wager < 1:
        await interaction.response.send_message(f'Wager must be at least 1', ephemeral=True)
        return

    embed = discord.Embed(title="Coinflip...",
                description=f"{opp.mention}, flip the coin.\n**Wager**: {wager} coins",
                colour=0xffcb70)

    await interaction.response.send_message(embed=embed, view=Buttons(int=interaction, opp=opp, wager=wager))


@bot.tree.command(name='deleteuser', description='Deletes user entry in database')
@app_commands.describe(discord_id='Discord id')
async def deleteuser(interaction:discord.Interaction, discord_id:str):
    """
    admin cmd
    delete a user from database
    """
    db._execute_query(f'DELETE FROM users WHERE discord_id={discord_id}', commit=True)
    await interaction.response.send_message(f'Deleted entry for user id {discord_id}', ephemeral=True)

@bot.tree.command(name='addcoins', description='Give coins to a user')
@app_commands.describe(user='User', coins='Coins')
async def addcoins(interaction:discord.Interaction, user:discord.User, coins:int):
    """
    admin cmd
    add coins to user balance
    """
    curr_coins = _get_coins(user.id)

    db._execute_query(f'UPDATE users SET coins={curr_coins+coins} WHERE discord_id={user.id}', commit=True)

    await interaction.response.send_message(f'{coins} coins added to {user.name}\'s balance.\n' +
                           f'New balance is {curr_coins+coins}')

# =====================================================

@bot.tree.command(name='starrdrop', description='Starr Drop simulation')
@app_commands.describe(rarity='Drop Rarity')
async def starrdrop(interaction:discord.Interaction, rarity:str=None):
    """
    Simulate opening a starr drop
    /StarrDrop 
    """

    rarities = ['rare', 'super rare', 'epic', 'mythic', 'legendary']

    if rarity not in rarities:
        rarity = random.choices(
            rarities,
            [0.50, 0.38, 0.15, 0.05, 0.02],
            k=1
        )[0]

    embed = simulate_drop(rarity=rarity)
    await interaction.response.send_message(embed=embed)

# ======================Ranked==========================

def genChoices(dict:dict):
    list = []
    for choice in dict.keys():
        list.append(discord.app_commands.Choice(name=choice, value=choice))
    return list

@bot.tree.command(name='ranked', description='Shows best ranked picks')
@app_commands.describe(map='Maps to choose from')
@app_commands.choices(map=genChoices(ranked_picks))
async def ranked(interaction:discord.Interaction, map:str):
    """
    Shows img with best picks on a given ranked map
    """

    embed = discord.Embed(title=map, colour=0xFFBD16)
    embed.set_image(url=ranked_picks[map])

    await interaction.response.send_message(embed=embed)

# ======================Misc===========================
@bot.tree.command(name='cat', description='Show a random cat image')
async def cat(interaction:discord.Interaction):
    """
    Shows image of a random cat
    """

    data = await get_image(interaction, "https://api.thecatapi.com/v1/images/search")
    if data:
        await interaction.response.send_message(data[0]["url"])

@bot.tree.command(name='dog', description='Show a random dog image')
async def dog(interaction:discord.Interaction):
    """
    Shows image of a random dog
    """
    
    data = await get_image(interaction, "https://api.thedogapi.com/v1/images/search")
    if data:
        await interaction.response.send_message(data[0]["url"])

@bot.event
async def on_command_error(ctx:commands.Context, error):
    """
    Error handling
    """

    if isinstance(error, commands.MemberNotFound):
        await ctx.channel.send(f'Opponent ({error.argument}) not found.')

    else:
        await ctx.channel.send(f'error: {error}')

bot.run(token=TOKEN)