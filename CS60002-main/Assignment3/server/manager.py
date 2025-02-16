from helper import SQLHandler, DataHandler


class Manager:
    def __init__(self, shard_id=None, columns=None, dtypes=None):
        self.shard_id = shard_id
        self.columns = columns
        self.dtypes = dtypes
        self._setupSQL()

    def _setupSQL(self):
        self.sql_handler = SQLHandler(
            host="localhost", user="root", password="mysql1234", db=self.shard_id
        )
        self.data_handler = DataHandler(self.columns, self.dtypes, self.sql_handler)
    
    def copy(self):
        return self.data_handler.GetAll()
    
    def read(self, low, high):
        return self.data_handler.GetRange(low,high)
    
    def write(self, entries):
        return self.data_handler.InsertMany(entries)
    
    def update(self, Stud_id, entry):
        return self.data_handler.Update(Stud_id,entry)
    
    def delete(self, Stud_id):
        return self.data_handler.Delete(Stud_id)
    
