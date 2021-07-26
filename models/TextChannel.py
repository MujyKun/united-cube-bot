class TextChannel:
    def __init__(self, channel_id, role_id):
        """
        Represents a discord Text Channel and the UCube settings. Note that this is UNIQUE TO A UCube COMMUNITY.
        It is not unique to it's text channel id.

        :param channel_id: Text Channel ID
        :param role_id: Role ID
        """
        self.id = channel_id
        self.role_id = role_id
        self.already_posted = []  # list of notification ids.
