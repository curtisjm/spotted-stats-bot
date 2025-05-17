import discord
from dotenv import load_dotenv

load_dotenv()

SPOTTED_CHANNEL_ID = 1259628406471917618
LEADERBOARD_CHANNEL_ID = 0

class SpottedPlayer:
    def __init__(self, user: discord.User):
        self.user = user
        self.spotted_count = 0
        self.spotter_count = 0

    def __repr__(self):
        return f"SpottedPlayer(user={self.user}, spotted_count={self.spotted_count}, spotter_count={self.spotter_count})"

    def __eq__(self, other):
        if isinstance(other, SpottedPlayer):
            return self.user.id == other.user.id
        return False

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

spotted_players = {}
spotted_channel = client.get_channel(SPOTTED_CHANNEL_ID)

def increment_spotter_count(author: discord.User):
    if author.id in spotted_players:
        spotted_player = spotted_players[author.id]
        spotted_player.spotter_count += 1
    else:
        spotted_player = SpottedPlayer(author)
        spotted_player.spotter_count += 1
        spotted_players[author.id] = spotted_player

def increment_spotted_count(mention: discord.User):
    if mention.id in spotted_players:
        spotted_player = spotted_players[mention.id]
        spotted_player.spotted_count += 1
    else:
        spotted_player = SpottedPlayer(mention)
        spotted_player.spotted_count += 1
        spotted_players[mention.id] = spotted_player

# TODO: implement this
def update_leaderboard():
    return

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})\n----------------')
    past_messages = [message async for message in spotted_channel.history(limit=None)]
    for message in past_messages:
        if message.author.id != client.user.id:
            increment_spotter_count(message.author)
            for mention in message.mentions:
                increment_spotted_count(mention)
    update_leaderboard()

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if message.channel.id != SPOTTED_CHANNEL_ID:
        return
    increment_spotter_count(message.author)
    for mention in message.mentions:
        increment_spotted_count(mention)
    update_leaderboard()

# TODO: setup dotenv and change this
client.run('your token here')
