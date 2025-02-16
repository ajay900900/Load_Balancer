import os
import pymysql
from multiprocessing.dummy import Pool


class DataHandler:
    def __init__(self, columns=None, dtypes=None, SQL_handle=None, table_name="StudT"):
        self.columns = columns
        self.dtypes = dtypes
        self.SQL_handle = SQL_handle
        self._setup(table_name)

    def _setup(self, table_name):
        self.table_name = self.SQL_handle.jobrunner.apply(
            self.SQL_handle.hasTable, (table_name, self.columns, self.dtypes)
        )

    def Insert(self, row):
        id = self.SQL_handle.jobrunner.apply(
            self.SQL_handle.insert, (self.table_name, row)
        )
        return id

    def InsertMany(self, entries):
        for entry in entries:
            id = self.SQL_handle.jobrunner.apply(
                self.SQL_handle.insert, (self.table_name, entry)
            )
        return id

    def GetAll(self):
        return self.SQL_handle.jobrunner.apply(
            self.SQL_handle.getAll, (self.table_name,)
        )

    def GetRange(self, low, high):
        return self.SQL_handle.jobrunner.apply(
            self.SQL_handle.getRangeVals, (self.table_name, low, high)
        )

    def Update(self, Stud_id, entry):
        return self.SQL_handle.jobrunner.apply(
            self.SQL_handle.update, (self.table_name, Stud_id, entry)
        )

    def Delete(self, Stud_id):
        return self.SQL_handle.jobrunner.apply(
            self.SQL_handle.delete, (self.table_name, Stud_id)
        )


class SQLHandler:
    def __init__(self, host="localhost", user="root", password="mysql1234", db="sh1"):
        self.jobrunner = Pool(1)
        self.host = host
        self.user = user
        self.password = password
        self.db = db

    def connect(self):
        connected = False
        while not connected:
            try:
                self.mydb = pymysql.connect(
                    host=self.host, user=self.user, password=self.password
                )
                self.useDB(self.db)
                connected = True
            except Exception as e:
                print(e)
                pass

    def query(self, sql):
        try:
            cursor = self.mydb.cursor(pymysql.cursors.DictCursor)
            cursor.execute(sql)
        except Exception:
            self.connect()
            cursor = self.mydb.cursor(pymysql.cursors.DictCursor)
            cursor.execute(sql)
        res = cursor.fetchall()
        cursor.close()
        self.mydb.commit()
        return res

    def count(self, table_name):
        res = self.query(f"SELECT count(id) AS count FROM {table_name}")
        return res[0]["count"]
    
    def useDB(self, dbname=None):
        res = self.query("SHOW DATABASES")
        if dbname not in [r["Database"] for r in res]:
            self.query(f"CREATE DATABASE {dbname}")
        self.query(f"USE {dbname}")

    def hasTable(self, tabname=None, columns=None, dtypes=None):
        res = self.query("SHOW TABLES")
        if tabname not in [r[f"Tables_in_{self.db}"] for r in res]:
            dmap = {"Number": "INT", "String": "VARCHAR(32)"}
            col_config = ""
            for c, d in zip(columns, dtypes):
                col_config += f", {c} {dmap[d]}"
            self.query(
                f"CREATE TABLE {tabname} (id INT AUTO_INCREMENT PRIMARY KEY{col_config})"
            )
        return tabname

    def getAll(self, table_name):
        rows = self.query(f"SELECT * FROM {table_name}")
        return rows

    def getRangeVals(self, table_name, low, high):
        rows = self.query(
            f"SELECT * FROM {table_name} WHERE Stud_id>={low} AND Stud_id<={high}"
        )
        return rows

    def update(self, table_name, Stud_id, entry):
        queryString = ""
        for k, v in entry.items():
            queryString += f"{k} = '{v}', "
        queryString = queryString[:-2]
        queryString = f"UPDATE {table_name} SET {queryString} WHERE Stud_id = {Stud_id}"
        self.query(queryString)

    def delete(self, table_name, Stud_id):
        self.query(f"DELETE FROM {table_name} WHERE Stud_id = {Stud_id}")

    def insert(self, table_name, row):
        id = self.count(table_name)
        row_str = "0"
        for k, v in row.items():
            row_str += f", '{v}'"
        self.query(f"INSERT INTO {table_name} VALUES ({row_str})")
        return id

