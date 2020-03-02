import asyncio
import discord
import random
import typing
from discord.ext import commands

bot = commands.Bot(command_prefix='$', case_insensitive=True)

maxPlayers = 10
minPlayers = 3

packs = {
    "base": "Just the basic, base pack",
    "spongebob": "SpongeBob themed cards!",
    "ex1": "The first extension pack",
    "ex2": "The sequel to the first extension pack",
    "ex3": "The sequel to the sequel to the first extension pack",
    "ex4": "Yet another extension pack",
    "ex5": "There's too many extension packs",
    "ex6": "Or maybe we can have a few more",
    "ex7": "Last one?",
    "pax": "Another pack",
    "base2": "An additional base pack/alternative extension",
    "anime": "Anime themed cards"
}

loaded_packs = []
for position, pack_data in enumerate(packs.items()):
    pack_to_read, pack_description = pack_data
    question_cards_in_pack = open(f"{pack_to_read}b.txt", "r")
    answer_cards_in_pack = open(f"{pack_to_read}w.txt", "r")
    loaded_packs.append(
        (
            pack_to_read,
            [card.strip() for card in question_cards_in_pack.readlines()],
            [card.strip() for card in answer_cards_in_pack.readlines()],
            pack_description
        )
    )
    question_cards_in_pack.close()
    answer_cards_in_pack.close()

packs = loaded_packs


class User:
    def __init__(self, member, available_cards):
        self.member = member
        self.score = 0
        self.cards = []
        self.first_card = 0
        self.second_card = 0
        self.cards.append(random.sample(available_cards, 10))


class Game:
    def __init__(self, channel, users, cards, creator, max_rounds):
        cards = cards or ["base"]

        self.active = False
        self.answer_cards = []
        self.question_cards = []
        self.creator = creator

        games[channel] = self

        for pack, questions, answers, _ in packs:
            if pack in cards or "all" in cards:
                self.question_cards += questions
                self.answer_cards += answers

        self.channel = channel
        self.users = [User(member, self.answer_cards) for member in users]
        random.shuffle(self.users)
        self.turn_count = 0
        self.rounds = 0
        self.max_rounds = max_rounds * len(self.users)

    async def start(self):
        self.active = True
        self.rounds = 0
        while self.active and (self.max_rounds is None or self.max_rounds > self.rounds):
            self.rounds += 1
            await self.begin_round()
        final_scores = "\n".join([f'{user.member}: {user.score}' for user in self.users])
        await self.channel.send(
            embed=discord.Embed(
                title=f"The game has ended! Here are the scores\nScoreboard:",
                description=final_scores,
                color=discord.Color(0x3f51b5)
            )
        )
        del games[self.channel]

    async def begin_round(self):
        self.turn_count += 1
        question = random.choice(self.question_cards)
        tsar = self.users[self.turn_count % len(self.users)]
        scores = "\n".join([f'{user.member}: {user.score}' for user in self.users])
        await self.channel.send(
            embed=discord.Embed(
                title=f"Scoreboard (before round {self.rounds}" +
                      (f"/{self.max_rounds}):" if self.max_rounds is not None else ")"),
                description=scores,
                color=discord.Color(0x3f51b5)
            )
        )
        await asyncio.sleep(5)
        await self.channel.send(embed=discord.Embed(
            title=f"The card tsar is {tsar.member.name}.",
            description=f"{question}\n\nEveryone check your dms for your card list.",
            color=discord.Color(0x212121)
        ))

        coroutines = []
        for user in self.users:
            if user != tsar:
                cards = f"In {self.channel.mention}\n\n{question}\n" + \
                        "\n".join([f"{card_position + 1}: {card}" for card_position, card in enumerate(user.cards[0])])
                await user.member.send(
                    embed=discord.Embed(title=f"Cards for {user.member}:", description=cards,
                                        color=discord.Color(0x212121))
                )

                async def wait_for_message(player_to_wait_for):
                    def wait_check(message: discord.Message):
                        try:
                            return 0 <= int(message.content) <= 10 \
                                   and message.author == player_to_wait_for.member \
                                   and message.guild is None
                        except ValueError:
                            return False

                    await player_to_wait_for.member.send(
                        embed=discord.Embed(
                            title=f"Please select a card from 1 to 10. You have 20 seconds to decide" +
                                  (" (1/2)" if question.count(r"\_\_") == 2 else ""),
                            color=discord.Color(0x212121)
                        )
                    )
                    try:
                        player_to_wait_for.first_card = (
                            await bot.wait_for('message', check=wait_check, timeout=20)
                        ).content
                    except asyncio.TimeoutError:
                        player_to_wait_for.first_card = random.randint(1, 10)
                    if question.count(r"\_\_") == 2:
                        await player_to_wait_for.member.send(
                            embed=discord.Embed(
                                title=f"Please select a card from 1 to 10. You have 20 seconds to decide" + " (2/2)",
                                color=discord.Color(0x212121)
                            )
                        )
                        try:
                            player_to_wait_for.second_card = (
                                await bot.wait_for('message', check=wait_check, timeout=20)
                            ).content
                        except asyncio.TimeoutError:
                            player_to_wait_for.second_card = random.randint(1, 10)
                    await player_to_wait_for.member.send(embed=discord.Embed(
                        title=f"Please wait for all players to select their card",
                        description=f'The game will continue in {self.channel.mention}',
                        color=discord.Color(0x8bc34a)
                    ))
                    await self.channel.send(embed=discord.Embed(
                        description=f"{player_to_wait_for.member} has selected their card",
                        color=discord.Color(0x8bc34a)
                    ))
                    return None

                coroutines.append(wait_for_message(user))
        await asyncio.gather(*coroutines)

        playing_users = self.users.copy()
        playing_users.remove(tsar)
        playing_users.sort(key=lambda user: random.random())

        responses = ""
        if question.count(r"\_\_") < 2:
            for user_position, user in enumerate(playing_users):
                responses += f'{user_position + 1}: {user.cards[0][int(user.first_card) - 1]}\n'
        else:
            for user_position, user in enumerate(playing_users):
                responses += f'{user_position + 1}: {user.cards[0][int(user.first_card) - 1]} ' \
                             f'| {user.cards[0][int(user.second_card) - 1]}\n'

        responses += "\n*(Player order is random)*"

        embed = discord.Embed(
            title=f'Select the winner, {tsar.member.name}',
            description=f'{question}\n\n{responses}',
            color=discord.Color(0x212121)
        )
        await self.channel.send(embed=embed)
        await tsar.member.send(embed=embed)
        await self.channel.send(embed=discord.Embed(title=f"Please answer in your DM", color=discord.Color(0x8bc34a)))

        def check(message: discord.Message):
            try:
                return 1 <= int(message.content) <= len(playing_users) \
                       and message.author == tsar.member \
                       and message.guild is None
            except ValueError:
                return False

        winner = random.randint(1, len(playing_users))

        try:
            winner = (
                await bot.wait_for('message', check=check, timeout=20)
            ).content
        except asyncio.TimeoutError:
            pass

        winner = playing_users[int(winner) - 1]
        await tsar.member.send(
            embed=discord.Embed(
                description=f"Selected. The game will continue in {self.channel.mention}",
                color=discord.Color(0x8bc34a)
            )
        )

        winner.score += 1

        await self.channel.send(
            embed=discord.Embed(
                title=f"The winner is:",
                description=f'{winner.member}! :tada:\n{winner.cards[0][int(winner.first_card) - 1]}' + (
                    f" | {winner.cards[0][int(winner.second_card) - 1]}" if question.count(r"\_\_") == 2 else ""
                ),
                color=discord.Color(0x8bc34a)
            )
        )

        if question.count(r"\_\_") < 2:
            for player in self.users:
                if player != tsar:
                    player.cards[0].pop(int(player.first_card) - 1)
                    player.cards[0].append(random.choice(self.answer_cards))
        else:
            for player in self.users:
                if player != tsar:
                    player.cards[0].pop(int(player.first_card) - 1)
                    if int(player.first_card) < int(player.second_card):
                        player.cards[0].pop(int(player.second_card) - 2)
                    else:
                        player.cards[0].pop(int(player.second_card) - 1)
                    for _ in range(2):
                        player.cards[0].append(random.choice(self.answer_cards))

        await asyncio.sleep(10)


class HelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        filtered = await filter_commands(mapping[None])
        custom_help_descriptions = {
            "help": "The help command shows this message, and that's about it!",
        }
        descriptions = {
            command.name: (
                    command.help.replace("%%", self.context.bot.main_prefix) or "No help available"
            ) for command in filtered
        }
        for cmd, desc in custom_help_descriptions.items():
            descriptions[cmd] = desc
        embed = discord.Embed(
            title='CARDS AGAINST HUMANITY - COMMANDS LIST',
            description="\n".join(
                [f"```diff\n- {self.context.bot.main_prefix}{command}: {description}```"
                 for command, description in descriptions.items()]
            ),
            color=discord.Color(0x8bc34a)
        )
        embed.add_field(
            name="Contact",
            value="Co-owners: PineappleFan#9955\n"
                  "& Minion3665#6456",
            inline=False
        )
        embed.add_field(
            name="Server",
            value="https://discord.gg/ScFHrUB",
            inline=False
        )
        embed.add_field(
            name="Invite me!",
            value="[Press here]"
                  "(https://discordapp.com/oauth2/authorize?client_id=679361555732627476&scope=bot&permissions=130048)"
                  "\n*(Please note we need certain permissions, such as embed links, to function)*",
            inline=False
        )
        await self.context.send(embed=embed)


games = {}
main_prefix = "$"

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(main_prefix),
    case_insensitive=True,
    help_command=HelpCommand()
)
bot.main_prefix = main_prefix


@bot.event
async def on_ready():
    print(f'Logged in successfully as {bot.user}')


@bot.command()
async def play(ctx, players: commands.Greedy[discord.Member], max_rounds: typing.Optional[int] = 4, *enabled_packs):
    """Play a game
    Run %%play [@ping as many players as you like] [number of rounds, or enter 0 for unlimited (default 4)] [packs]

  optionally specify how many rounds to play each (default 4), or press 0 to have unlimited rounds.
  *NOTICE: This will be multiplied by the number of players in the game*

  optionally specify which packs to include (run %%packs to view all the options or enter all to go crazy)"""
    players = [user for user in players if not user.bot]
    players.append(ctx.author)
    players = set(players)
    if len(players) < minPlayers:
        embed = discord.Embed(
            description=f'There too few players in this game. '
                        f'Please ping a minimum of {minPlayers - 1} '
                        f'people for a {minPlayers} player game',
            color=discord.Color(0xf44336)
        )
        return await ctx.channel.send(embed=embed)
    if len(players) > maxPlayers:
        embed = discord.Embed(
            description=f'There too many players in this game. '
                        f'Please ping a maximum of {maxPlayers - 1} '
                        f'people for a {maxPlayers} player game',
            color=discord.Color(0xf44336)
        )
        return await ctx.channel.send(embed=embed)
    if games.get(ctx.channel, None):
        return await ctx.channel.send("A game is already in progress.")
    await Game(ctx.channel, players, enabled_packs, ctx.author, max_rounds if max_rounds > 0 else None).start()


@bot.command(name="packs")
async def show_packs(ctx):
    """Shows a list of packs to enable and disable in the game

  They are added when using the %%play command"""
    embed = discord.Embed(
        title=f'Packs ( {len(packs)} )',
        description='Do $play {@ people} {packs} to activate specific packs. '
                    'If no packs are chosen, base only will be selected. '
                    'Alternatively, setting the pack to "all" will enable all packs.\n\n'
                    + "\n".join(f"{pack[0]}: {pack[3]}" for pack in packs),
        color=discord.Color(0xf44336))
    await ctx.channel.send(embed=embed)


@bot.command()
async def end(ctx):
    """End the game

  Note- You must have manage channels or be playing to end the game"""
    game = games.get(ctx.channel, None)
    if not game:
        return await ctx.send("There doesn't appear to be a game running in this channel...")
    if (
            game.users and ctx.author not in [user.member for user in game.users]
    ) and not ctx.author.permissions_in(ctx.channel).manage_channels:
        return await ctx.send("You aren't playing and you don't have manage channels, so you can't end this game...")
    embed = discord.Embed(description='The game will end after this round', color=discord.Color(0x8bc34a))
    game.active = False
    await ctx.channel.send(embed=embed)


with open('token.txt', 'r') as f:
    token = [line.strip() for line in f]
bot.run(token[0])
