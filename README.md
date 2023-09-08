# UCubeBot

| :exclamation:  This project is no longer being maintained. I'm not sure if it still works.  :exclamation:  |
|-----------------------------------------|

## [Invite to your Server](https://discord.com/oauth2/authorize?client_id=867675755177836555&scope=bot&permissions=2952997936)

[![Discord Bots](https://top.gg/api/widget/867675755177836555.svg)](https://top.gg/bot/867675755177836555)

## To Self-Host:

You will need a PostgreSQL Server. After you have one running, you can do the below.  

``git clone https://github.com/MujyKun/united-cube-bot``  

``pip install -r requirements.txt``

Rename `.env.example` to `.env`  
Open the `.env` file and change the ucube login, discord bot token, and postgres login to your own.  
[Tutorial for ucube login here.](https://ucube.readthedocs.io/en/latest/api.html#get-account-token)

## Commands:

**The Bot Prefix is set to `&` by default. There is currently no way to change it.**  
**Anything in brackets [] is optional.**  
**Anything in () is required.**  
**In order to disable/enable features, retyping the same exact command will toggle it.**


&ucube [Community Name] -> Follow a UCube community. Use without the community name to get a list of communities.  
&role (Role) (Community Name) -> Will add or update a role to mention for a community.  
&list -> Will list the currently followed communities in the channel.  

&patreon -> Link to patreon.  
&invite -> Link to invite bot.  
&support -> Link to support server.  
&ping -> Receives Client Ping.  
&servercount -> Displays amount of servers connected to the bot.

