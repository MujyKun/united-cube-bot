class AbstractDataBase:
    """
    Abstract Base for a DataBase.

    Inherit this class in a new model if you are using a different DB.
    """
    def __init__(self, host, database, user, password, port, schema_name="ucubebot", table_name="channels"):
        self.pool = None

        self.host = host
        self._database = database
        self.user = user
        self.port = port
        self._password = password

        self._connect_kwargs = {
            "host": self.host,
            "database": self._database,
            "user": self.user,
            "password": self._password,
            "port": self.port
        }

        self._schema_name = schema_name
        self._table_name = table_name
        self._create_schema_sql = f"CREATE SCHEMA IF NOT EXISTS {self._schema_name}"
        self._create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self._schema_name}.{self._table_name}
            (
                id serial,
                channelid bigint,
                communityname text,
                roleid bigint,
                PRIMARY KEY (id)
            )
        """
        self._insert_channel_sql = f"INSERT INTO {self._schema_name}.{self._table_name}(channelid, communityname, " \
                                   f"roleid) VALUES($1, $2, $3)"
        self._delete_channel_sql = f"DELETE FROM {self._schema_name}.{self._table_name} WHERE channelid = $1 AND " \
                                   f"communityname = $2"
        self._toggle_sql = f"UPDATE {self._schema_name}.{self._table_name} SET column_name=$1 WHERE channelid = " \
                           f"$2 AND communityname = $3"
        self._update_role_sql = self._toggle_sql.replace("column_name", "roleid")
        self._fetch_all_sql = f"SELECT channelid, communityname, roleid FROM " \
                              f"{self._schema_name}.{self._table_name}"
        self._drop_schema_sql = f"DROP SCHEMA IF EXISTS {self._schema_name}"
        self._drop_table_sql = f"DROP TABLE IF EXISTS {self._schema_name}.{self._table_name}"

    async def connect(self):
        """Create the connection for the DataBase."""
        ...

    async def __create_ucube_schema(self):
        """Create the UCube Schema."""
        ...

    async def __create_ucube_table(self):
        """Create the UCube channels table."""
        ...

    async def insert_ucube_channel(self, channel_id, community_name):
        """Insert a UCube channel.

        :param channel_id: (int) Text Channel ID.
        :param community_name: (str) The name of the community.
        """
        ...

    async def delete_ucube_channel(self, channel_id, community_name):
        """Unfollow a UCube community.

        :param channel_id: (int) Text Channel ID.
        :param community_name: (str) The name of the community.
        """
        ...

    async def update_role(self, channel_id, community_name, role_id):
        """Update the role for a channel.

        :param channel_id: (int) Text Channel ID.
        :param community_name: (str) The name of the community.
        :param role_id: (int) The Role ID.
        """
        ...

    async def fetch_channels(self):
        """Fetch channels and the channels they are following"""
        ...

    async def recreate_db(self):
        """Will update the database by dropping the table and recreating it with the new sql."""
        ...
