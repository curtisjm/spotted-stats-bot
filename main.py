import discord

SPOTTED_CHANNEL_ID = 1259628406471917618

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

spotted_players = {}

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
    channel = client.get_channel(SPOTTED_CHANNEL_ID)
    past_messages = [message async for message in channel.history(limit=None)]

client.run('your token here')
