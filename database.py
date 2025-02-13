import pymysql
from typing import Dict, Union, Tuple, List, Any, Optional
from p import passw

class database:
    def __init__(self, user: str, password: str, host: str, database: str) -> None:
        self.connection: pymysql.Connection = pymysql.connect(user=user,
                                                        password=password,
                                                        host=host,
                                                        database=database)

    def build_database(self) -> None:
        with open("build.sql", "r") as f:
            sql = f.read()

        for sql in sql.split(";"):
            if sql.strip() != "":
                self._execute_query(sql)

    def _execute_query(self, query: str, *params, fetch: str = 'all',
                        commit: bool = False, many: bool = False) -> Union[Tuple, List[Tuple], None]:
        """
        Execute a query into mysql database
        """
        
        self.connection.ping(reconnect=True)

        with self.connection.cursor() as cur:
            if many:
                cur.executemany(query, params[0])
            else:
                cur.execute(query, params)

            if commit:
                self.connection.commit()

            if fetch == 'one':
                return cur.fetchone()
            elif fetch == 'all':
                return cur.fetchall()

# ---------- self testing ------------

# db = database(user='dbadmin', password=passw, host='localhost', database='test')
# db.build_database()

# # print(db._execute_query('select * from users'))
# # #db._execute_query('INSERT INTO users (discord_id, coins) VALUES (3, 10), (4, 50)', commit=True)

# # print(db._execute_query('select discord_id from users;'))
# # # db._execute_query('DELETE FROM users WHERE coins=0', commit=True)
# # print(db._execute_query('select * from users'))

# t = db._execute_query(f'SELECT discord_id, coins FROM users')
# l = list(t)
# print(l)
# l.sort(key=lambda x : x[1], reverse=True)
# print(l)

# db.connection.commit()

# db.connection.close()