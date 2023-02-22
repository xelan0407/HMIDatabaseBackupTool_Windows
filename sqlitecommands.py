import sqlite3
from sqlite3 import Error, Connection

def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn


def simple_select_all(conn : Connection, tablename, rowname):
    """
    Query all rows in the tasks table
    :param conn: the Connection object
    :rowname: Name of the column with the wanted data
    :tablename: Name of the Table in the database
    :return: result, all collected data as a tuple (row) in a list
    """
    cur = conn.cursor()
    cur.execute(f"SELECT {rowname} FROM {tablename}")
    

    result = cur.fetchall()

    return result

def select(conn :Connection, tablename, SelectRowName, WhereRowName, alias):
    
    cur = conn.cursor()
    cur.execute(f"SELECT {SelectRowName} FROM {tablename} WHERE {WhereRowName}=?", alias)
    

    result = cur.fetchall()
    return result



def write_data_in_DB(conn: Connection, tablename :str, data: dict):

    """
    in eine Datenbank schreiben
    
    conn: Verbindung zur Datenbank
    tablename: Name des Tables in den geschrieben werden soll
    data: Daten die in die Tablle geschrieben werden sollen (Key ist Wert der Spalte 0)

    return: Fehlerfrei: "done"
            mit Fehler: Fehlermeldung1,Fehlermeldung2,....FehlermeldungX
    """

    data_list = []
    sql_statement = f"INSERT INTO {tablename} VALUES ("
    write_fault = ""
    
    for line in data:
        
        #maximale Größe des Datenblocks begrenzen und immer bei Voll einmal schreiben (hier 301 Datensätze)
        if i > 300:  

            with conn:  #in Die übergebene datenbank
                cur = conn.cursor()
                try:
                    sql_statement = sql_statement[:-1] #letztes komma löschen
                    cur.execute(sql_statement,(data_list)) 
                    
                except Exception as e:
                    write_fault = write_fault + e +","

            data_list = []
            sql_statement = f"INSERT INTO {tablename} VALUES "
            i=0
                    
        #Data umformatieren
        data_list.append(line)
        data_list.append(data[line])

        #sql statement zusammenbausen
        # 
        sql_statement = sql_statement +"("  
        for j in range(0, len(line)):  
            sql_statement = sql_statement+ f"?,"
        sql_statement = sql_statement[:-1] #letztes komma löschen
        sql_statement = sql_statement +"),"
        i= i + 1



    with conn:
        cur = conn.cursor()
        #Recorder Daten für das einzelne Item
        try:
            sql_statement = sql_statement[:-1] #letztes komma löschen
            cur.execute(sql_statement,(data_list)) #ID des Items auslesen Tabelle hat die form
        except Exception as e:
            write_fault = write_fault + e +","

    if write_fault =="":
        result = "done"
    else:
        result = write_fault

    return result