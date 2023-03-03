import discord
import os
import pymongo
import certifi
import threading
import keep_alive
import logging

logging.basicConfig(format='%(levelname)s %(asctime)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

client = discord.Client(intents=discord.Intents.all())
db = pymongo.MongoClient(os.getenv("URL_MONGODB"),
                         tlsCAFile=certifi.where())[os.getenv('DB_NAME')]

TAB_PLAYERS_HED = 'Name, Class, Level, Clan'
LIMIT_PLAYERS = 10


@client.event
async def on_ready():
    logger.info('Logged')


def sanitize(*list_str):
    for s in list_str:
        if not s.replace(' ', '').isalnum():
            return False
    return True


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    logger.info(message.content)
    if message.content.startswith('.players'):
        server, *user = message.content.split(' ')[1:]
        if not sanitize(server, *user):
            res = "No special symbols allowed"
        else:
            user_name = ' '.join(user)
            user_data = db.user.aggregate([{
                '$match': {
                    'name': {
                        '$regex': f'.*{user_name}.*',
                        '$options': 'si'
                    },
                    'server': server
                }
            }, {
                '$limit': LIMIT_PLAYERS
            }, {
                '$addFields': {
                    'last_level': {
                        '$last': '$level.lvl'
                    },
                    'last_clan': {
                        '$last': '$clan.clan'
                    }
                }
            }, {
                '$project': {
                    '_id': 0,
                    'name': 1,
                    'last_level': 1,
                    'last_clan': 1,
                    'class': 1
                }
            }])

            num = 0
            res = f'Results limited to {LIMIT_PLAYERS}\n'
            res += f'**[{TAB_PLAYERS_HED}]**\n'
            num = 0
            for user in user_data:
                num += 1
                res += f"{user['name']}, {user['class']}, {user['last_level']}, {user['last_clan']}\n"

            if num == 0:
                res = 'No data'

    elif message.content.startswith('.player'):
        server, *user = message.content.split(' ')[1:]
        if not sanitize(server, *user):
            res = "No special symbols allowed"
        else:
            user_name = ' '.join(user)
            user_data = db.user.find_one({'id': f'{user_name}@{server}'}, {
                '_id': 0,
                'clan': 1,
                'class': 1,
                'level': 1,
            })
            if user_data == None:
                res = "Not found"
            else:
                user_data['clan'] = ', '.join([
                    f'({c["clan"]} - {c["date"]:%Y/%m})'
                    for c in user_data['clan']
                ])
                user_data['level'] = ', '.join([
                    f'({l["lvl"]} - {l["date"]:%Y/%m})'
                    for l in user_data['level']
                ])

                res = f'Name: {user_name}\nServer: {server}\nClan: {user_data["clan"]}\nClass: {user_data["class"]}\nLevel: {user_data["level"]}\n'

    elif message.content.startswith('.clan'):
        server, *clan = message.content.split(' ')[1:]
        if not sanitize(server, *clan):
            res = "No special symbols allowed"
        else:
            clan_name = ' '.join(clan)
            clan_data = db.user.aggregate([{
                '$project': {
                    '_id': 0,
                    'clan': 1,
                    'server': 1,
                    'class': 1
                }
            }, {
                '$match': {
                    'server': server
                }
            }, {
                '$addFields': {
                    'last_clan': {
                        '$last': '$clan.clan'
                    }
                }
            }, {
                '$match': {
                    'last_clan': clan_name
                }
            }, {
                '$group': {
                    '_id': '$class',
                    'num': {
                        '$sum': 1
                    }
                }
            }])

            total_members = 0
            res = f'{clan_name} in {server} has:\n'
            for clazz in clan_data:
                num = clazz["num"]
                total_members += num
                res += f'{clazz["_id"]}: {num}\n'

            if total_members == 0:
                res = 'Not found'
            else:
                res += f'Total members: {total_members}'
    elif message.content.startswith('.help'):
        res = 'Usage:\n**.players** {Server} {Player name} _Find players with similar name in a server_\n**.player** {Server} {Player name} _Get stats about a player in a server_\n**.clan** {Server} {Clan name} _Get stats about a clan in a server_\n'

    logger.info(res)
    await message.channel.send(res)


threading.Thread(target=keep_alive.run, daemon=True).start()

client.run(os.getenv("TOKEN"))
