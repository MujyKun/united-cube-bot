from typing import Optional, TYPE_CHECKING, List, Union

import discord
from discord.ext import commands
from asyncio import get_event_loop, sleep
from os import getenv
from aiohttp import ClientSession
from models import TextChannel
from random import randint
import aiofiles
from UCube import UCubeClientAsync, models

if TYPE_CHECKING:
    from ..run import UCubeBot

DEV_MODE = False
EMBED_CAP = 1600

"""
THIS FILE USED A TEMPLATE FROM WEVERSE
UCUBE CLUBS MAY BE REFERRED TO AS COMMUNITIES HERE 
"""


class UCube(commands.Cog):
    def __init__(self, bot):
        self.bot: UCubeBot = bot
        self._channels = {}  # Community Name : { channel_id: models.TextChannel }
        loop = get_event_loop()
        loop.create_task(self.fetch_channels())
        self._web_session = ClientSession()
        client_kwargs = {
            'username': getenv("UCUBE_USERNAME"),  # ucube username
            'password': getenv("UCUBE_PASSWORD"),  # ucube password
            "verbose": True,  # Will print warning messages for links that have failed to connect or were not found.
            "web_session": self._web_session,  # Existing web session
            "loop": loop,  # current event loop
            "hook": self.on_new_notifications
        }

        self._translate_headers = {"Authorization": getenv("TRANSLATION_KEY")}
        self._translate_endpoint = getenv("TRANSLATION_URL")
        self._ucube_image_folder = getenv("UCUBE_FOLDER_LOCATION")
        self._upload_from_host = getenv("UPLOAD_FROM_HOST")

        self.ucube_client = UCubeClientAsync(**client_kwargs)

        start_kwargs = {
            "load_boards": True,
            "load_posts": False,
            "load_notices": False,
            "load_media": False,
            "load_from_artist": True,
            "load_to_artist": False,
            "load_talk": False,
            "load_comments": False,
            "follow_all_clubs": False
        }
        loop.create_task(self.ucube_client.start(**start_kwargs))

    async def cog_check(self, ctx):
        """A local check for this cog. Checks if the user is a data mod."""
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("This command can not be used in DMs.")
            return False
        return True

    async def on_new_notifications(self, notifications: List[models.Notification]):
        """Hook for when there are new notifications."""
        for notification in notifications:
            try:
                await self.send_notification(notification)
            except Exception as e:
                print(f"{e} - Notification Slug: {notification.slug} for {notification.club_name} "
                      f"[{notification.club_slug}] failed to send.")

    async def translate(self, text) -> Optional[str]:
        """Sends a request to translating endpoint from KR to EN and returns the translated string."""
        try:
            data = {
                'text': text,
                'src_lang': "ko",
                'target_lang': "en"
            }
            async with self._web_session.post(self._translate_endpoint, headers=self._translate_headers, data=data) \
                    as r:
                if r.status == 200:
                    try:
                        body: dict = await r.json()
                    except Exception as e:
                        print(f"{e} - (Exception)")
                        body = await r.json(content_type="text/html")
                    if body.get("code") == 0:
                        return body.get("text")
        except Exception as e:
            print(f"{e} - (Exception)")

    async def fetch_channels(self):
        """Fetch the channels from DB and add them to cache."""
        while not self.bot.conn.pool:
            await sleep(3)  # give time for DataBase connection to establish and properly create tables/schemas.
        for channel_id, community_name, role_id in await self.bot.conn.fetch_channels():

            self.add_to_cache(community_name, channel_id, role_id)

        # recreate the db (to match a new structure) and insert values from cache.
        await self.update_db_struct_from_cache()

    async def update_db_struct_from_cache(self):
        """Will destroy the current db and update it's structure and reinsert values from the current cache."""
        await self.bot.conn.recreate_db()
        for key, channels in self._channels.items():
            for channel in channels.values():
                await self.bot.conn.insert_ucube_channel(channel.id, f"{key}")

    def is_following(self, community_name, channel_id):
        """Check if a channel is following a community."""
        community_name = community_name.lower()
        followed_channels = self._channels.get(community_name)
        if not followed_channels:
            return False

        return channel_id in followed_channels.keys()

    def check_community_exists(self, community_name):
        """Check if a community name exists."""
        if not community_name:
            return False

        return community_name.lower() in self.get_community_names()

    def get_community_names(self) -> list:
        """Returns a list of all available community names."""
        return [t_community.name.lower() for t_community in self.ucube_client.clubs.values()]

    def get_channel(self, community_name, channel_id) -> Optional[TextChannel]:
        """Get a models.TextChannel object from a community"""
        channels = self._channels.get(community_name)
        if channels:
            return channels.get(channel_id)

    def add_to_cache(self, community_name, channel_id, role_id):
        """Add a channel to cache."""
        community_name = community_name.lower()
        channels = self._channels.get(community_name)
        this_channel = TextChannel(channel_id, role_id)
        if not channels:
            self._channels[community_name] = {channel_id: this_channel}
        else:
            channels[channel_id] = this_channel

    async def send_communities_available(self, ctx):
        """Send the available communities to a text channel."""
        community_names = ', '.join(self.get_community_names())

        return await ctx.send(f"The communities available are: ``{community_names}``.")

    async def delete_channel(self, channel_id, community_name):
        """Deletes a channel from a community in the cache and db."""
        channels = self._channels.get(community_name.lower())
        try:
            channels.pop(channel_id)
        except AttributeError or KeyError:
            pass
        await self.bot.conn.delete_ucube_channel(channel_id, community_name)

    @commands.is_owner()
    @commands.command()
    async def testucube(self, ctx):
        """Test posting CLC notifications."""
        club: Optional[models.Club] = None
        for club in self.ucube_client.clubs.values():
            if club.name.lower() == "clc":
                break

        # only grab the 5 most recent notifications.
        notifications = await self.ucube_client.fetch_club_notifications(club_slug=club.slug, notifications_per_page=5)
        for notification in notifications:
            try:
                # have the posts created
                await self.ucube_client.fetch_post(post_slug=notification.post_slug)
                # now try to post them.
                await self.send_notification(notification)
            except Exception as e:
                print(f"{e} - Failed Test on Notification.")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def list(self, ctx):
        """List the communities the current channel is following."""
        followed_communities = [community_name for community_name in self.get_community_names() if
                                self.is_following(community_name, ctx.channel.id)]
        msg_string = f"You are currently following `{', '.join(followed_communities)}`."
        return await ctx.send(msg_string)

    @commands.command(aliases=["updates"])
    @commands.has_guild_permissions(manage_messages=True)
    async def ucube(self, ctx, *, community_name: str = None):
        """Follow or Unfollow a UCube Community."""
        try:
            community_names = ', '.join(self.get_community_names())
            if not community_name:
                return await self.send_communities_available(ctx)

            community_name = community_name.lower()

            community: Optional[models.Club] = None
            for t_community in self.ucube_client.clubs.values():
                if t_community.name.lower() == community_name:
                    community = t_community

            if not community:
                return await ctx.send(f"The UCube Community Name you have entered does not exist. Your options are "
                                      f"``{community_names}``.")

            if self.is_following(community.name, ctx.channel.id):
                await self.delete_channel(ctx.channel.id, community.name)
                await ctx.send(f"You are no longer following {community_name}.")
            else:
                self.add_to_cache(community_name, ctx.channel.id, None)
                await self.bot.conn.insert_ucube_channel(ctx.channel.id, community_name)
                await ctx.send(f"You are now following {community.name}.")
        except Exception as e:
            return await ctx.send(e)

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def role(self, ctx, role: discord.Role, *, community_name: str):
        """Add a role to be notified when a community posts."""
        community_name = community_name.lower()
        text_channel = await self.get_channel_following(ctx, community_name)
        if not text_channel:
            return

        if text_channel.role_id and text_channel.role_id == role.id:
            text_channel.role_id = None
            await self.bot.conn.update_role(ctx.channel.id, community_name, None)
            return await ctx.send("This role will no longer be mentioned.")
        await self.bot.conn.update_role(ctx.channel.id, community_name, role.id)
        text_channel.role_id = role.id
        return await ctx.send("That role will now receive notifications.")

    @staticmethod
    def get_random_color():
        """Retrieves a random hex color."""
        r = lambda: randint(0, 255)
        return int(('%02X%02X%02X' % (r(), r(), r())), 16)  # must be specified to base 16 since 0x is not present

    async def get_channel_following(self, ctx, community_name) -> Optional[TextChannel]:
        """Gets the channel that is following a community.

        If the community does not exist, a list of communities will be sent instead.

        :param ctx: Context Object
        :param community_name: Community Name
        :returns: Optional[models.TextChannel]
        """
        if not self.check_community_exists(community_name):
            await self.send_communities_available(ctx)
            return

        text_channel = self.get_channel(community_name, ctx.channel.id)
        if not text_channel:
            await ctx.send(f"This channel is not currently following {community_name}.")
        return text_channel

    async def create_embed(self, title="UCube", color=None, title_desc=None,
                           footer_desc="Thanks for using UCubeBot!", icon_url=None, footer_url=None, title_url=None,
                           image_url=None):
        """Create a discord Embed."""
        from discord.embeds import EmptyEmbed
        icon_url = icon_url
        footer_url = footer_url
        color = self.get_random_color() if not color else color

        embed = discord.Embed(title=title, color=color, description=title_desc or EmptyEmbed,
                              url=title_url or EmptyEmbed)

        embed.set_author(name="UCube", url="https://www.patreon.com/mujykun?fan_landing=true",
                         icon_url=icon_url or EmptyEmbed)
        embed.set_footer(text=footer_desc, icon_url=footer_url or EmptyEmbed)
        embed.set_image(url=image_url or EmptyEmbed)
        return embed

    async def download_ucube_post(self, url, file_name):
        """Downloads an image url and returns image host url.

        If we are to upload from host, it will return the folder location instead (Unless the file is more than 8mb).


        :returns: (photos/videos)/image links and whether it is from the host.
        """
        from_host = False
        async with self._web_session.get(url) as resp:
            async with aiofiles.open(self._ucube_image_folder + file_name, mode='wb') as fd:
                data = await resp.read()
                await fd.write(data)
                print(f"{len(data)} - Length of UCube File - {file_name}")
                if len(data) >= 8000000:  # 8 mb
                    return [f"https://images.irenebot.com/ucube/{file_name}", from_host]

        if self._upload_from_host:
            from_host = True
            return [f"{self._ucube_image_folder}{file_name}", from_host]
        return [f"https://images.irenebot.com/ucube/{file_name}", from_host]

    async def get_media_files_and_urls(self, main_post: Union[models.Post]):
        """Get media files and file urls of a post or media post."""
        # will either be file locations or image links.
        photos = [await self.download_ucube_post(photo.path, photo.name)
                  for photo in main_post.images]

        videos = []
        for video in main_post.videos:
            file_name = f"{main_post.slug}_{randint(1, 50000000)}.mp4" if not video.name else video.name
            videos.append(await self.download_ucube_post(video.url, file_name))

        media_files = []  # can be photos or videos
        file_urls = []  # urls of photos or videos
        for file in photos + videos:  # a list of lists containing the image
            media = file[0]
            from_host = file[1]

            if from_host:
                # file locations
                media_files.append(media)
            else:
                file_urls.append(media)

        message = "\n".join(file_urls)

        return media_files, message

    async def send_notification(self, notification: models.Notification):
        """Send a notification post to all of the channels following."""
        post = self.ucube_client.get_post(notification.post_slug)
        club = self.ucube_client.get_club(notification.club_slug)

        channels = self._channels.get(club.name.lower())
        if not channels:
            print(f"{club.name} has no channels to send Post Slug: {post.slug} to.")
            return

        channels = (channels.copy()).values()

        embed_title = f"New [{club.name}] {post.user.name} Notification!"
        embed_list = await self.set_post_embeds(post, embed_title)
        media_files, message_text = await self.get_media_files_and_urls(post)

        for channel_info in channels:
            try:
                channel_info: TextChannel = channel_info
                await sleep(2)

                if post.slug in channel_info.already_posted:
                    continue

                channel_info.already_posted.append(post.slug)

                print(f"Sending Post Slug: {post.slug} to text channel {channel_info.id}")
                await self.send_ucube_to_channel(channel_info, message_text, embed_list, media_files, club.name)
            except Exception as e:
                print(f"{e} - Failed to send to channel id {channel_info.id}.")

    async def set_post_embeds(self, post: models.Post, embed_title) -> List[discord.Embed]:
        """Set Post Embed for Weverse.
        :param post: Post object
        :param embed_title: Title of the embed.
        :returns: Embed, file locations, and image urls.
        """
        translation = await self.translate(post.content)

        embed_description = f"Content: **{post.content}**\n" \
                            f"Translated Content: **{translation}**"

        desc_list = []
        while len(embed_description) >= EMBED_CAP:
            desc_list.append(embed_description[0:EMBED_CAP])
            embed_description = embed_description[0:len(embed_description)]

        if embed_description:
            desc_list.append(embed_description[0:len(embed_description)])

        embed_list = []
        for count, desc in enumerate(desc_list, 1):
            embed_list.append(await self.create_embed(title=f"{embed_title} - Post #{count}/{len(desc_list)}",
                                                      title_desc=desc))

        return embed_list

    async def send_ucube_to_channel(self, channel_info: TextChannel, message_text, embed_list, media_files, club_name):
        """Send a UCube post to a channel."""
        ...
        try:
            channel: discord.TextChannel = self.bot.get_channel(channel_info.id)
            if not channel:
                # fetch channel instead (assuming discord.py cache did not load)
                channel: discord.TextChannel = await self.bot.fetch_channel(channel_info.id)
        except Exception as e:
            # remove the channel from future updates as it cannot be found.
            print(f"{e} - Removing Text Channel {channel_info.id} from cache for {club_name} since it could not "
                  f"be processed/found.")
            return await self.delete_channel(channel_info.id, club_name.lower())

        msg_list: List[discord.Message] = []
        file_list = []

        try:
            mention_role = f"<@&{channel_info.role_id}>" if channel_info.role_id else None

            for count, embed in enumerate(embed_list, 1):
                msg_list.append(await channel.send(mention_role if count == 1 else None, embed=embed))

            if message_text or media_files:
                # Since an embed already exists, any individual content will not load
                # as an embed -> Make it it's own message.
                if media_files:
                    # a list of file locations
                    for photo_location in media_files:
                        file_list.append(discord.File(photo_location))

                msg_list.append(await channel.send(message_text if message_text else None, files=file_list or None))
                print(f"UCube Post for {club_name} sent to {channel_info.id}.")
        except discord.Forbidden as e:
            # no permission to post
            print(f"{e} (discord.Forbidden) - UCube Post Failed to {channel_info.id} for {club_name}")

            # remove the channel from future updates as we do not want it to clog our rate-limits.
            return await self.delete_channel(channel_info.id, club_name.lower())
        except Exception as e:
            print(f"{e} (Exception) - UCube Post Failed to {channel_info.id} for {club_name}")
            return

        if not channel.is_news():
            return

        for msg in msg_list:
            try:
                await msg.publish()
            except Exception as e:
                print(f"Failed to publish Message ID: {msg.id} for Channel ID: {channel_info.id} - {e}")


def setup(bot: commands.AutoShardedBot):
    bot.add_cog(UCube(bot))
