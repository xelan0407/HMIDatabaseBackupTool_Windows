from pickle import NONE
from typing import Optional
from pydantic import BaseModel
import ReadWriteFiles as rwf
import sqlitecommands as db
from os import listdir
from os.path import isfile, join

from fastapi import FastAPI, Depends
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)




class ConfigBaseModel(BaseModel):
    projektname: str
    projekt_path : str
    csv_path :str


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Hmi Database BackupTool",
        version="0.0.0",
        description="Tool um die Gesamte Datenbank oder nur Teilbereiche der HMI zu sichern, zu löschen oder wieder herzustellen",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app = FastAPI(docs_url=None, redoc_url=None, title="Hmi Database BackupTool")

app.openapi = custom_openapi
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Docs",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )

#--------------------------Kofiguration---------------------------------------------------------------


#>>>>>>config lesen<<<<<<<<
@app.get("/config")
async def get_project_info():
    
    """
    öffne config file und gebe die darin befindlichen daten als dict zurück. (Prjektname und Pfad)
    """


    data : ConfigBaseModel
    path = "./json"
    filename = "/config.json"

    data = rwf.read_json(path = path + filename)

    return data


#>>>>>config schreiben<<<<<<<
@app.put("/config")
async def put_project_info(data: ConfigBaseModel):
    """
    schreibe Konfigurationsdaten aus einen Dict in ein Json file (projektname und Pfad)
    Ablagepfad für die Json ist fest definiert als /json
    wichtig: Path entweder in der Form          C:\\ProgramData\\WebIQ\\WebIQ Projects\\2858_V1\\.db
                                        oder:   C:/ProgramData/WebIQ/WebIQ Projects/2858_V1/.db
    
    projektname: str = Name der Visualisierungsapp
    projekt_path : str = Pfad zur Visualiserungsapp
    csv_path :str = Pfad in den Exportierte Dateien abgelegt werden


    
    """



    path = "./json"
    filename = "/config.json"
    data.projekt_path = data.projekt_path.replace("\\", "/" )
    data.projekt_path = data.projekt_path + "/" + data.projektname + "/" + ".db"
    data_dict = {"projektname":data.projektname, "project_path":data.projekt_path, "csv_path": data.csv_path}
    folder_created = rwf.create_folder(path)

    if folder_created:
        file_created = rwf.write_json(path = path + filename, data = data_dict)

        if not file_created:
            return "File konnte nicht erezugt werden"
    else:
        return "Ordner konnte nicht angelegt werden"

    return "Nochmal gut gegangen"
    
    

#-----------------------------------------Daten auslesen---------------------------------------------------------------------

@app.get("/records/projected")
async def get_all_projected_RecordItems(projektinfo : ConfigBaseModel = Depends(get_project_info)):

    """
    Connects to the HMI Projektdatabase to read the projected Recorder Items and Databases and exports them dict
    :projektname: Name of the HMI Projekt For Example "2858_V1"
    :return: a Lsit of all data
    """

    #Ablauf: 
    # 1. Auslesen der Config Json für Projektpfad, Csv Pfad und Projektname um damit die notwendigen Verzeichnisse zu generieren
    # 2. Auslesen aller Projektierten Items aus der Projektdatenbank (projekt.sqlite)



    filename = "/project.sqlite"
    path = projektinfo["project_path"]


    try:
        conn = db.create_connection(path+filename)
        

            # create a database connection
        with conn:
            result = db.simple_select_all(conn, "_TrendItems", "*")

        return result

    except:
        print("Fehler biem lesen")
        return [[2,"wrong path or projectname", "please check config file"]]



@app.get("/records/all")
async def get_all_item_records(starttimestamp : Optional[int] =  0, endtimestamp : Optional[int] = 2147483647, projektinfo : ConfigBaseModel = Depends(get_project_info), items : dict = Depends(get_all_projected_RecordItems)): #optionale Parameter = 01.01.1970 und 19.01.2038 damit zwischen min und max für den Unix timestamp
    """
    lese die aufgenommenen Werte für alle Items aus und schreibt diese in eine csv. Standardmäßig alltime. Optional können Zeitstempel der Abfrage beigefügt werden. Dann erfolgt die Abfrage nur zwischen beiden Zeitstempeln.
    """

    #Ablauf: 
    # 1. Auslesen der Config Json für Projektpfad, Csv Pfad und Projektname um damit die notwendigen Verzeichnisse zu generieren
    # 2. Auslesen aller Projektierten Items aus der Projektdatenbank (projekt.sqlite)
    #loop:
    # 3. Mekren der datenbank in welcher das Item geloggt wird (DatabaseID=Item[2])
    # 4. Abfrage in der Item Database (DatabaseID) welche ItemID das gewünschte Item hat
    # 5. Abrufen aller geloggten Werte des Items zwischen Start und Endzeitpunkt
    # 6. Schreiben der aufegenommenen Werte in eine Json im Pfad csv
    #loop ende


    starttimestamp = starttimestamp *10000000 #da Smart HMI Zeitstempel in Nanosekunden
    endtimestamp = endtimestamp *10000000
    result_dict ={} 
    
    project_path = projektinfo["project_path"]
    csv_path = projektinfo["csv_path"]+"/"+projektinfo["projektname"]
    
    folder_created = rwf.create_folder(path=projektinfo["csv_path"]+"/"+projektinfo["projektname"])
    
    for Item in items:
    
        #an der Stelle 1 steht der Alias des Items [0] = ID [2]= verwendete Datenbank 
        itemalias = Item[1]
        DatabaseID = Item[2]
        print(DatabaseID)
        Itemdatabase = f"{project_path}/{DatabaseID}.sqlite" 
        
        #Verbindung aufbauen
        conn1 = db.create_connection(Itemdatabase)
            
        with conn1:
            cur = conn1.cursor()
            #Recorder Daten für das einzelne Item
            try:
                cur.execute(f"SELECT recorder_item_id FROM _RecorderItems WHERE item_alias =? ",(itemalias,)) #ID des Items auslesen
                recorderItemID = cur.fetchall()
                argument_list = (recorderItemID[0][0], starttimestamp, endtimestamp)
                cur.execute(f"SELECT * FROM _RecorderData WHERE recorder_item_id =? AND timestamp >=? AND timestamp <=?", argument_list) #Werte für das Item auslesen
                records_item= cur.fetchall()
                records_new = {}
                for date in records_item:
                    date= {date[0]: date[2]}
                    records_new.update(date)
                    
                if folder_created:
                        file_created = rwf.write_json(path=projektinfo["csv_path"]+"/"+projektinfo["projektname"]+f"/{itemalias}.json", data = records_new)
                        result_dict.update({itemalias: file_created})
            except Exception as e:
                print(f"Fehler beim lesen von Datenbank {DatabaseID}: {e}")
            



   
    return result_dict

@app.delete("/records/all")
async def delete_all_Item_records(projektinfo : dict = Depends(get_project_info), all_items: dict=Depends(get_all_projected_RecordItems)):
    """
    löscht alle aufgenommen Recorder Werte und stellt einen neuen "nackten" Table bereit
    
    """

    # Ablauf
    # 1. Verbindung zu Projextdatenbankherstellen und Datenbanknamen rausfinden(passiert in den Depends)
    # 2. Verbindung zur Recorder Datenbank herstellen (passiert in den Depends)
    # 3. alle Einträge löschen

    project_path = projektinfo["project_path"]
    result_dict =  {}

    # 3. alle Einträge löschen
    for Item in all_items:


        #an der Stelle 1 steht der Alias des Items [0] = ID [2]= verwendete Datenbank 
        itemalias = Item[1]
        DatabaseID = Item[2]
        print(DatabaseID)
        Itemdatabase = f"{project_path}/{DatabaseID}.sqlite" 

        conn1 = db.create_connection(Itemdatabase)

                
        with conn1:
            cur = conn1.cursor()

           #Item ID auslesen
            try:
                cur.execute(f"SELECT recorder_item_id FROM _RecorderItems WHERE item_alias =? ",(itemalias,)) #ID des Items auslesen
                recorderItemID = cur.fetchall()
                recorderItemID = recorderItemID[0][0]

            except Exception as e:
                print(f"Select auf {DatabaseID} _RecorderItems: {e}")

            #Delete Table Inhalt

            try:
                #cur.execute(f"DELETE FROM _RecorderData WHERE timestamp <>? AND recorder_item_id =?", (0,recorderItemID)) #ID des Items auslesen
                cur.execute(f"DROP TABLE _RecorderData")
                cur.execute(f"CREATE TABLE _RecorderData (timestamp INTEGER NOT NULL, recorder_item_id INTEGER NOT NULL REFERENCES _RecorderItems (recorder_item_id) ON DELETE CASCADE ON UPDATE CASCADE, value, PRIMARY KEY (recorder_item_id, timestamp))WITHOUT ROWID;")
                conn1.isolation_level = None
                cur.execute(f"VACUUM")
                result_dict.update({DatabaseID : "deleted"})
                print(f"{DatabaseID} {recorderItemID}: deleted")
            except Exception as e:
                result_dict.update({DatabaseID : e})
    return result_dict

@app.get("/records/item_record")
async def get_Item_Record(item_info: str , starttimestamp : Optional[int] =  0, endtimestamp : Optional[int] = 2147483647, projektinfo : ConfigBaseModel = Depends(get_project_info), all_items: dict=Depends(get_all_projected_RecordItems)): #optionale Parameter = 01.01.1970 und 19.01.2038 damit zwischen min und max für den Unix timestamp
    """
    lese die aufgenommenen Werte für ein Item aus. Standardmäßig alltime. Optional können Zeitstempel der Abfrage beigefügt werden. Dann erfolgt die Abfrage nur zwischen beiden Zeitstempeln.
    """


    #Ablauf: 
    # 1. Auslesen der Config Json für Projektpfad, Csv Pfad und Projektname um damit die notwendigen Verzeichnisse zu generieren
    # 2. Auslesen aller Projektierten Items aus der Projektdatenbank (projekt.sqlite)
    # 3. Überprüfen ob ein Item aus den Projetierten Items gleich dem über User iNterface angeforderten wert ist. Wenn nein abruch
    # 4. Mekren der datenbank in welcher das Item geloggt wird (DatabaseID=Item[2])
    # 5. Abfrage in der Item Database (DatabaseID) welche ItemID das gewünschte Item hat
    # 6. Abrufen aller geloggten Werte des Items zwischen Start und Endzeitpunkt
    # 7. Schreiben der aufegenommenen Werte in eine Json im Pfad csv


    starttimestamp = starttimestamp *10000000  #da Smart HMI Zeitstempel in Nanosekunden
    endtimestamp = endtimestamp *10000000


    
    project_path = projektinfo["project_path"]

    csv_path = projektinfo["csv_path"]+"/"+projektinfo["projektname"]
    print(csv_path + item_info)
    folder_created = rwf.create_folder(path=projektinfo["csv_path"]+"/"+projektinfo["projektname"]+ "/" + item_info)
    
    for Item in all_items:

        if Item[1] == item_info: 

            #an der Stelle 1 steht der Alias des Items [0] = ID [2]= verwendete Datenbank 
            itemalias = Item[1]
            DatabaseID = Item[2]

            Itemdatabase = f"{project_path}/{DatabaseID}.sqlite" 
            
            #Verbindung aufbauen
            conn1 = db.create_connection(Itemdatabase)
                
            with conn1:
                cur = conn1.cursor()
                #Recorder Daten für das einzelne Item
                cur.execute(f"SELECT recorder_item_id FROM _RecorderItems WHERE item_alias =? ",(itemalias,)) #ID des Items auslesen
                recorderItemID = cur.fetchall()
                argument_list = (recorderItemID[0][0], starttimestamp, endtimestamp)
                cur.execute(f"SELECT * FROM _RecorderData WHERE recorder_item_id =? AND timestamp >=? AND timestamp <=?", argument_list) #Werte für das Item auslesen
                records_item= cur.fetchall()
                records_new = {}
                for date in records_item:
                    date= {date[0]: date[2]}
                    records_new.update(date)


                
                if folder_created:
                    file_created = rwf.write_json(path=projektinfo["csv_path"]+"/"+projektinfo["projektname"]+ "/" + item_info + f"/{itemalias}.json", data = records_new)
                    print(f"{itemalias} erzeugt")


   
        return "done"
    else:
        return f"no item named {item_info}"



@app.put("/records/all")
async def restore_all_item_records(projektinfo : ConfigBaseModel = Depends(get_project_info), all_items : dict = Depends(get_all_projected_RecordItems)):  

    """
    liest die gesicherten Daten die über get_all_item_records generiert werden zurück und schreibt sie in die richtige Datenbank. 
    Hierfür wird über get_all_projected_RecordItems eine Verbindung zwischen Item und zu verwendender Datenbank (z.b. 620_Stranddiameter.sqlite) hergestellt
    
    """

    # Ablauf:
    #
    # 1. Dateinamen im export Ordner einlesen und merken
    # Loop: (jede Datei die eine gesamtdatensicherung enthält)
    # 2. Dateinamen lesen und merken
    # 3. Dateinamen mit Itemnamen in der Projektdatenbank abgleichen (get_all_projected_RecordItems)
    # 4. Projektierte ItemDatenbank öffnen und nach der dem Item (Dateinamen) ItemID durchsuchen
    # 5. Datei öffnen
    # 6. Inhalt der Datei in Item Datenbank schreiben (um Item ID ergänzt)
    # 7. Datei wieder schließen
    # loop Ende
    
    csv_path = projektinfo["csv_path"] + f"/{projektinfo['projektname']}"
    project_path = projektinfo["project_path"]
    i=0
    all_items_without_Dupl =[]
    result_dict={}


    #1 Dateinamen aus dem Export verzeichnis auslesen

    onlyfiles = [f for f in listdir(csv_path) if isfile(join(csv_path, f))]
    for file in onlyfiles:

        #2 Dateinamen lesen und merken
        Item_alias = file.split(".json") #schneide den String in Liste von Strings an der Stelle + .json
        Item_alias = Item_alias[0] # Ergebnis von .split ist: [Itemname, Leerstring] wir brauchen nur den Item Namen


        #Duplikate aus der Liste Projektierter Items entfernen (Achtung teilweise gleiche Namen mit unterschiedlicher ID. Daher nur die Namen abgleichen) [1] Itemname [2]Datenbankname
        for Projected_item in all_items:
            if (Projected_item[1], Projected_item[2]) not in all_items_without_Dupl:
                all_items_without_Dupl.append((Projected_item[1], Projected_item[2]))
   
        #3 Datei/Itemnamen mit der Projektdatenbank abgelichen
        for Projected_item in all_items_without_Dupl:

            if Item_alias == Projected_item[0]: #Wenn das Item auch projektiert wurde

                DatabaseID = Projected_item[1]
                
                #4 Projektierte ItemDatenbank öffnen und nach der dem Item (Dateinamen) ItemID durchsuchen
                Itemdatabase = f"{project_path}/{DatabaseID}.sqlite" 
                conn1 = db.create_connection(Itemdatabase)
                
                with conn1:
                    cur = conn1.cursor()
                    #Recorder Daten für das einzelne Item
                    try:
                        cur.execute(f"SELECT recorder_item_id FROM _RecorderItems WHERE item_alias =? ",(Item_alias,)) #ID des Items auslesen
                        recorderItemID = cur.fetchall()
                        recorderItemID = recorderItemID[0][0]
                    except Exception as e:
                        print({f"Fehler beim schreiben in {DatabaseID} : {e}"})

                
                # 5. Datei öffnen
                data = rwf.read_json(csv_path+"/"+file)

                # 6. Inhalt der Datei in Item Datenbank schreiben (um Item ID ergänzt)
                data_list = []
                sql_statement = f"INSERT INTO _RecorderData VALUES "

                write_fault = ""
                for line in data:
                    
                    if i > 300:

                        sql_statement = sql_statement[:-1]
                        with conn1:
                            cur = conn1.cursor()
                            #Recorder Daten für das einzelne Item
                            try:
                                cur.execute(sql_statement,(data_list)) #ID des Items auslesen Tabelle hat die form

                               
                            except Exception as e:
                                write_fault = e

                        data_list = []
                        sql_statement = f"INSERT INTO _RecorderData VALUES "
                        i=0
                             
                
                    data_list.append(line)
                    data_list.append(recorderItemID)
                    data_list.append(data[line])
                    sql_statement = sql_statement+ f"(?, ?, ?),"
                    i= i + 1
                

                sql_statement = sql_statement[:-1]

                with conn1:
                    cur = conn1.cursor()
                    #Recorder Daten für das einzelne Item
                    try:
                        cur.execute(sql_statement,(data_list)) #ID des Items auslesen Tabelle hat die form
                    except Exception as e:
                        write_fault = e
                
                if write_fault =="":
                    result_dict.update({Item_alias : "done"})
                else:
                    result_dict.update({Item_alias : f"error {write_fault}"})

    return result_dict
                        


@app.put("/records/item_record")#Not yet implement
async def restore_item_record():

    start =1
    return start


@app.get("/users")
async def export_userData(projektinfo : ConfigBaseModel = Depends(get_project_info)):

    """
    Exportiere alle Daten aus der User Datenbank und schreibe diese in Json Files
    
    """

    projektname = projektinfo["projektname"]
    projekt_path = projektinfo["project_path"]
    csv_path = projektinfo["csv_path"]

    database_path = f"{projekt_path}/user.sqlite"
    export_path = f"{csv_path}/{projektname}/User_Export"

    User_folder_created = rwf.create_folder(export_path)

    if User_folder_created:

        conn1 = db.create_connection(database_path)
        
        with conn1:
            cur = conn1.cursor()
            #User Table
            cur.execute(f"SELECT * FROM _User",) #ID des Items auslesen
            data_User = cur.fetchall()
        data_User_dict={}
        for data in data_User:
            data_User_dict.update({data[0]: [data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11], data[12], data[13], data[14]]}) 

        
        User_json_exists = rwf.write_json(path= f"{export_path}/_User.json", data= data_User_dict)

        with conn1:
            cur = conn1.cursor()
            #Recorder Daten für das einzelne Item
            cur.execute(f"SELECT * FROM _UserGroupMap",) #ID des Items auslesen
            data_UserGroupMap = cur.fetchall()
        data_UserGroupMap_dict={}
        for data in data_UserGroupMap:
            data_UserGroupMap_dict.update({data[0]: [data[1],]}) 

        UserGroupMap_json_exists = rwf.write_json(path= f"{export_path}/_UserGroupMap.json", data= data_UserGroupMap_dict)


        with conn1:
            cur = conn1.cursor()
            #Recorder Daten für das einzelne Item
            cur.execute(f"SELECT * FROM _UserGroups",) #ID des Items auslesen
            data_UserGroups = cur.fetchall()
        data_UserGroups_dict={}
        for data in data_UserGroups:
            data_UserGroups_dict.update({data[0]: [data[1],]}) 

        UserGroups_json_exists = rwf.write_json(path= f"{export_path}/_UserGroups.json", data= data_UserGroups_dict)

        with conn1:
            cur = conn1.cursor()
            #Recorder Daten für das einzelne Item
            cur.execute(f"SELECT * FROM _UserGroupGroupMap",) #ID des Items auslesen
            data_UserGroupGroupMap = cur.fetchall()
        data_UserGroupGroupMap_dict={}
        for data in data_UserGroupGroupMap:
            data_UserGroupGroupMap_dict.update({data[0]: [data[1],]}) 

        UserGroupGroupMap_json_exists = rwf.write_json(path= f"{export_path}/_UserGroupGroupMap.json", data= data_UserGroupGroupMap_dict)        
    
        return {"_User": User_json_exists,  "_UserGroupMap": UserGroupMap_json_exists ,"_UserGroups": UserGroups_json_exists ,"_UserGroupGroupMap": UserGroupGroupMap_json_exists, }


@app.delete("/users")
async def delete_userData(projektinfo : ConfigBaseModel = Depends(get_project_info)):

    """
    Löscht alle Daten aus der USer Datenbank im Projektverzeichnis

    """

    projekt_path = projektinfo["project_path"]
    database_path = f"{projekt_path}/user.sqlite"
    result_dict={}
    conn1 = db.create_connection(database_path)  

    with conn1:
        cur = conn1.cursor()
        try:
            cur.execute(f"DELETE FROM _User")
            result_dict.update({"_User" : "deleted" })
        except Exception as e:
            result_dict.update({"_User" : e })

        try:
            cur.execute(f"DELETE FROM _UserGroupMap")
            result_dict.update({"_UserGroupMap" : "deleted" })
        except Exception as e:
            result_dict.update({"_UserGroupMap" : e })

        try:            
            cur.execute(f"DELETE FROM _UserGroupGroupMap")
            result_dict.update({"_UserGroupGroupMap" : "deleted" })
        except Exception as e:
            result_dict.update({"_UserGroupGroupMap" : e })

        try:
            cur.execute(f"DELETE FROM _UserGroups")
            result_dict.update({"_UserGroups" : "deleted" })
        except Exception as e:
            result_dict.update({"_UserGroups" : e })
        
        conn1.isolation_level = None
        conn1.execute("VACUUM").close()




    return result_dict


@app.put("/users")
async def restore_userData(projektinfo : ConfigBaseModel = Depends(get_project_info)):

    """
    Stellt die User Datenbank mit den, über export_userData exportierten, Json daten wieder her. 

    return: dict
    """

    projektname = projektinfo["projektname"]
    projekt_path = projektinfo["project_path"]
    csv_path = projektinfo["csv_path"]

    database_path = f"{projekt_path}/user.sqlite"
    export_path = f"{csv_path}/{projektname}/User_Export"

    conn1 = db.create_connection(database_path)  

    data_User = rwf.read_json(f"{export_path}/_User.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO _User VALUES"
        data_list=[]
        for data in data_User:
            sql_statement = sql_statement+ f"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?),"
            data_list.append(data)
            data_list = data_list + data_User[data]
        sql_statement = sql_statement[:-1]

        
        try:
            cur.execute(sql_statement, data_list)
            UserImported =f"imported"
        except Exception as e:
            UserImported = f"Error while insert in _UserGroupGroupMap: {e}"



    data_UserGroups = rwf.read_json(f"{export_path}/_UserGroups.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO _UserGroups VALUES"
        data_list=[]
        for data in data_UserGroups:
            sql_statement = sql_statement+ f"(?, ?),"
            data_list.append(data)
            data_list = data_list + data_UserGroups[data]
        sql_statement = sql_statement[:-1]

        
        try:
            cur.execute(sql_statement, data_list)
            UserGroupsImported = f"imported"
        except Exception as e:
            UserGroupsImported = f"Error while insert in _UserGroupGroupMap: {e}"


    data_UserGroupGroupMap = rwf.read_json(f"{export_path}/_UserGroupGroupMap.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO _UserGroupGroupMap VALUES"
        data_list=[]
        for data in data_UserGroupGroupMap:
            sql_statement = sql_statement+ f"(?, ?),"
            data_list.append(data)
            data_list = data_list + data_UserGroupGroupMap[data]
        sql_statement = sql_statement[:-1]

        
        try:
            cur.execute(sql_statement, data_list)
            UserGroupGroupMapImported =f"imported"
        except Exception as e:
            UserGroupGroupMapImported = f"Error while insert in _UserGroupGroupMap: {e}"


    data_UserGroupMap = rwf.read_json(f"{export_path}/_UserGroupMap.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO _UserGroupMap VALUES"
        data_list=[]
        for data in data_UserGroupMap:
            sql_statement = sql_statement+ f"(?, ?),"
            data_list.append(data)
            data_list = data_list + data_UserGroupMap[data]
        sql_statement = sql_statement[:-1]

        
        try:
            cur.execute(sql_statement, data_list)
            UserGroupMapImported =f"imported"
        except Exception as e:
            UserGroupMapImported = f"Error while insert in _UserGroupMap: {e}"

    return {"User Imported": UserImported , "UserGroups Imported":  UserGroupsImported ,"UserGroupMap Imported": UserGroupMapImported ,"UserGroupGroupMap Imported": UserGroupGroupMapImported   }


@app.get("/recipe/all")
async def get_all_recipes(projektinfo : ConfigBaseModel = Depends(get_project_info)):
    """
    Sichert alle fürs Rezeptmanagement relevanten Datenbanktables in Json Dateien im Export Ordner
    
    """

    projektname = projektinfo["projektname"]
    projekt_path = projektinfo["project_path"]
    csv_path = projektinfo["csv_path"]

    database_path = f"{projekt_path}/hmi.sqlite"
    export_path = f"{csv_path}/{projektname}/Recipe_Export"


    _RecipeDefinitionsExported = 1
    _RecipeItemsExported = 1
    _RecipeValuesExported = 1
    _RecipeVersionsExported = 1
    _RecipesExported = 1

    User_folder_created = rwf.create_folder(export_path)

    if User_folder_created:

        conn1 = db.create_connection(database_path)
        

    #_RecipeDefinitions

        with conn1:
            cur = conn1.cursor()
            cur.execute(f"SELECT * FROM _RecipeDefinitions",) 
            data_RecipeDefinitions = cur.fetchall()
            data_RecipeDefinitions_dict={}

        for data in data_RecipeDefinitions:
            data_RecipeDefinitions_dict.update({data[0]: [data[1], data[2]]}) 

        
        _RecipeDefinitionsExported = rwf.write_json(path= f"{export_path}/_RecipeDefinitions.json", data= data_RecipeDefinitions_dict)


    #_RecipeItems

        with conn1:
            cur = conn1.cursor()
            cur.execute(f"SELECT * FROM _RecipeItems",) 
            data_RecipeItems = cur.fetchall()
            data_RecipeItems_dict={}
        row = 0
        for data in data_RecipeItems:
            row = row +1
            data_RecipeItems_dict.update({row: [data[0], data[1], data[2]]}) 

        
        _RecipeItemsExported = rwf.write_json(path= f"{export_path}/_RecipeItems.json", data= data_RecipeItems_dict)

    #_Recipes

        with conn1:
            cur = conn1.cursor()
            cur.execute(f"SELECT * FROM _Recipes",) 
            data_Recipes = cur.fetchall()
            data_Recipes_dict={}

        for data in data_Recipes:
            data_Recipes_dict.update({data[0]: [data[1], data[2]]}) 

        
        _RecipesExported = rwf.write_json(path= f"{export_path}/_Recipes.json", data= data_Recipes_dict)

    #_RecipeValues    

        with conn1:
            cur = conn1.cursor()
            cur.execute(f"SELECT * FROM _RecipeValues",) 
            data_RecipeValues = cur.fetchall()
            data_RecipeValues_dict={}
        row = 0
        for data in data_RecipeValues:
            row = row+1
            data_RecipeValues_dict.update({row: [data[0], data[1], data[2], data[3], data[4]]}) 

        
        _RecipeValuesExported = rwf.write_json(path= f"{export_path}/_RecipeValues.json", data= data_RecipeValues_dict)


    #_RecipeVersions    

        with conn1:
            cur = conn1.cursor()
            cur.execute(f"SELECT * FROM _RecipeVersions",) 
            data_RecipeVersions = cur.fetchall()
            data_RecipeVersions_dict={}
        row = 0
        for data in data_RecipeVersions:
            row = row+1
            data_RecipeVersions_dict.update({ data[0]: [data[1], data[2], data[3], data[4], data[5], data[6], data[7]]}) 

        
        _RecipeVersionsExported = rwf.write_json(path= f"{export_path}/_RecipeVersions.json", data= data_RecipeVersions_dict)


    return {"_RecipeDefinions": _RecipeDefinitionsExported , "_RecipeItems": _RecipeItemsExported, "_Recipes": _RecipesExported, "_RecipeValues" : _RecipeValuesExported , "_RecipeVersions" : _RecipeVersionsExported }


@app.delete("/recipe/all")
async def delete_all_recipes(projektinfo : ConfigBaseModel = Depends(get_project_info)):

    """
    Löscht alles was mit Rezepten zu tun hat
    """

    projekt_path = projektinfo["project_path"]
    database_path = f"{projekt_path}/hmi.sqlite"

    conn1 = db.create_connection(database_path)  

    with conn1:

        cur = conn1.cursor()
        try:
            cur.execute(f"DELETE FROM _RecipeDefinitions")
            _RecipeDefinitionsDeleted = "deleted"
        except Exception as e:
            _RecipeDefinitionsDeleted = f"Error while deleting _RecipeDefinitions: {e}"

        try:
            cur.execute(f"DELETE FROM _Recipes")
            _RecipesDeleted = "deleted"
        except Exception as e:
            _RecipesDeleted = f"Error while deleting _Recipes: {e}"

        try:
            cur.execute(f"DELETE FROM _RecipeValues")
            _RecipeValuesDeleted = "deleted"
        except Exception as e:
            _RecipeValuesDeleted = f"Error while deleting _RecipeValues: {e}"

        try:
            cur.execute(f"DELETE FROM _RecipeItems")
            _RecipeItemsDeleted = "deleted"
        except Exception as e:
            _RecipeItemsDeleted = f"Error while deleting _RecipeItems: {e}"

        try:
            cur.execute(f"DELETE FROM _RecipeVersions")
            _RecipeVersionsDeleted = "deleted"
        except Exception as e:
            _RecipeVersionsDeleted = f"Error while deleting _RecipeVersions: {e}"

        conn1.isolation_level = None
        cur.execute("VACUUM")

    return {"_RecipeVersions": _RecipeVersionsDeleted, "_RecipeItems": _RecipeItemsDeleted,  "_RecipeValues": _RecipeValuesDeleted, "_Recipes": _RecipesDeleted, "_RecipeDefinitions": _RecipeDefinitionsDeleted}

@app.put("/recipe/all")
async def restore_all_recipes(projektinfo : ConfigBaseModel = Depends(get_project_info)):
   
    """
    Stellt die Rezept Datenbank mit den, über get_all_recipes exportierten, Json daten wieder her. 

    return: dict
    """

    projektname = projektinfo["projektname"]
    projekt_path = projektinfo["project_path"]
    csv_path = projektinfo["csv_path"]

    database_path = f"{projekt_path}/hmi.sqlite"
    export_path = f"{csv_path}/{projektname}/Recipe_Export"

    conn1 = db.create_connection(database_path)  

    #_RecipeItems

    data_RecipeItems = rwf.read_json(f"{export_path}/_RecipeItems.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO _RecipeItems VALUES"
        data_list=[]
        i=0
        for data in data_RecipeItems:
            if i > 300:

                sql_statement = sql_statement[:-1]       
                try:
                    cur.execute(sql_statement, data_list)
                    _RecipeItemsImported =f"imported"
                except Exception as e:
                    print(f"Error while insert in _RecipeItems: {e}")
                    _RecipeItemsImported = f"Error while insert in _RecipeItems: {e}"
                
                sql_statement =f"INSERT INTO _RecipeItems VALUES"
                data_list=[]
                i=0
            i=i+1
            sql_statement = sql_statement+ f"(?, ?, ?),"
            data_list = data_list + data_RecipeItems[data]

        sql_statement = sql_statement[:-1]       
        try:
            cur.execute(sql_statement, data_list)
            _RecipeItemsImported =f"imported"
        except Exception as e:
            print(f"Error while insert in _RecipeItems: {e}")
            _RecipeItemsImported = f"Error while insert in _RecipeItems: {e}"


    #_Recipes

    data_Recipes = rwf.read_json(f"{export_path}/_Recipes.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO _Recipes VALUES"
        data_list=[]
        i=0
        for data in data_Recipes:
            if i > 300:

                sql_statement = sql_statement[:-1]       
                try:
                    cur.execute(sql_statement, data_list)
                    _RecipesImported =f"imported"
                except Exception as e:
                    print(f"Error while insert in _Recipes: {e}")
                    _RecipesImported = f"Error while insert in _Recipes: {e}"
                
                sql_statement =f"INSERT INTO _Recipes VALUES"
                data_list=[]
                i=0
            i=i+1
            sql_statement = sql_statement+ f"(?, ?, ?),"
            data_list.append(data)
            data_list = data_list + data_Recipes[data]

        sql_statement = sql_statement[:-1]       
        try:
            cur.execute(sql_statement, data_list)
            _RecipesImported =f"imported"
        except Exception as e:
            print(f"Error while insert in _Recipes: {e}")
            _RecipesImported = f"Error while insert in _Recipes: {e}"       


    #_RecipeValues

    data_RecipeValues = rwf.read_json(f"{export_path}/_RecipeValues.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO _RecipeValues VALUES"
        data_list=[]
        i=0
        for data in data_RecipeValues:
            if i > 300:

                sql_statement = sql_statement[:-1]       
                try:
                    cur.execute(sql_statement, data_list)
                    _RecipeValuesImported =f"imported"
                except Exception as e:
                    print(f"Error while insert in _RecipeValues: {e}")
                    _RecipeValuesImported = f"Error while insert in _RecipeValues: {e}"
                
                sql_statement =f"INSERT INTO _RecipeValues VALUES"
                data_list=[]
                i=0
            i=i+1
            sql_statement = sql_statement+ f"(?, ?, ?, ?, ?),"
            data_list = data_list + data_RecipeValues[data]

        sql_statement = sql_statement[:-1]       
        try:
            cur.execute(sql_statement, data_list)
            _RecipeValuesImported =f"imported"
        except Exception as e:
            sqlLength = sql_statement.count("(?, ?, ?, ?, ?)")
            print(f"Error while insert in _RecipeValues: {e} sql arg{sqlLength} datalength{len(data_list)}" )
            _RecipeValuesImported = f"Error while insert in _RecipeValues: {e}"

    #_RecipeDefinitions

    data_RecipeDefinitions = rwf.read_json(f"{export_path}/_RecipeDefinitions.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO _RecipeDefinitions VALUES"
        data_list=[]
        i=0
        for data in data_RecipeDefinitions:
            if i > 300:

                sql_statement = sql_statement[:-1]       
                try:
                    cur.execute(sql_statement, data_list)
                    _RecipeDefinitionsImported =f"imported"
                except Exception as e:
                    print(f"Error while insert in _RecipeDefinitions: {e}")
                    _RecipeDefinitionsImported = f"Error while insert in _RecipeDefinitions: {e}"

                sql_statement =f"INSERT INTO _RecipeDefinitions VALUES"
                data_list=[]
                i=0
            i=i+1
            sql_statement = sql_statement+ f"(?, ?, ?),"
            data_list.append(data)
            data_list = data_list + data_RecipeDefinitions[data]

        sql_statement = sql_statement[:-1]       
        try:
            cur.execute(sql_statement, data_list)
            _RecipeDefinitionsImported =f"imported"
        except Exception as e:
            print(f"Error while insert in _RecipeDefinitions: {e}")
            _RecipeDefinitionsImported = f"Error while insert in _RecipeDefinitions: {e}" 

    #_RecipeVersions

    data_RecipeVersions = rwf.read_json(f"{export_path}/_RecipeVersions.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO _RecipeVersions VALUES"
        data_list=[]
        i=0
        for data in data_RecipeVersions:
            if i > 300:

                sql_statement = sql_statement[:-1]       
                try:
                    cur.execute(sql_statement, data_list)
                    _RecipeVersionsImported =f"imported"
                except Exception as e:
                    print(f"Error while insert in _RecipeVersions: {e}")
                    _RecipeVersionsImported = f"Error while insert in _RecipeVersions: {e}"
                
                sql_statement =f"INSERT INTO _RecipeVersions VALUES"
                data_list=[]
                i=0
            i=i+1
            sql_statement = sql_statement+ f"(?, ?, ?, ?, ?, ?, ?, ?),"
            data_list.append(data)
            data_list = data_list + data_RecipeVersions[data]

        sql_statement = sql_statement[:-1]       
        try:
            cur.execute(sql_statement, data_list)
            _RecipeVersionsImported =f"imported"
        except Exception as e:
            print(f"Error while insert in _RecipeVersions: {e}")
            _RecipeVersionsImported = f"Error while insert in _RecipeVersions: {e}" 

 
    return {"_RecipeItems": _RecipeItemsImported, "_Recipes": _RecipesImported, "_RecipeValues": _RecipeValuesImported, "_RecipeDefinitions": _RecipeDefinitionsImported,"_RecipeVersions": _RecipeVersionsImported,}


@app.get("/alarms")
async def get_historic_alarms(projektinfo : ConfigBaseModel = Depends(get_project_info)):
    """
    Sichert alle für dei Alarmhistorie relevanten Datenbanktables in Json Dateien im Export Ordner
    
    """

    projektname = projektinfo["projektname"]
    projekt_path = projektinfo["project_path"]
    csv_path = projektinfo["csv_path"]

    database_path = f"{projekt_path}/hmi.sqlite"
    export_path = f"{csv_path}/{projektname}/Alarms_Export"

    User_folder_created = rwf.create_folder(export_path)


    if User_folder_created:

        conn1 = db.create_connection(database_path)
        

    #_HistAlarms

        with conn1:
            cur = conn1.cursor()
            cur.execute(f"SELECT * FROM _HistAlarms",) 
            data_HistAlarms = cur.fetchall()
            data_HistAlarms_dict={}

        for data in data_HistAlarms:
            data_HistAlarms_dict.update({data[0]: [data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9]]}) 

        
        _HistAlarmsExported = rwf.write_json(path= f"{export_path}/_HistAlarms.json", data= data_HistAlarms_dict)

    return {"_HistAlarms": _HistAlarmsExported,}


@app.delete("/alarms")
async def delete_historic_alarms(projektinfo : ConfigBaseModel = Depends(get_project_info)):

    """
    Löscht alles was mit Alarmen zu tun hat
    """

    projekt_path = projektinfo["project_path"]
    database_path = f"{projekt_path}/hmi.sqlite"

    conn1 = db.create_connection(database_path)  

    with conn1:

        cur = conn1.cursor()
        try:
            cur.execute(f"DELETE FROM _HistAlarms")
            _HistAlarmsDeleted = "deleted"
        except Exception as e:
            _HistAlarmsDeleted = f"Error while deleting _HistAlarms: {e}"

        conn1.isolation_level = None
        cur.execute("VACUUM")   

    return {"_HistAlarms" : _HistAlarmsDeleted}

@app.put("/alarms")
async def restore_historic_alarms(projektinfo : ConfigBaseModel = Depends(get_project_info)):
    """
    Stellt die Alarm Datenbank mit den, über get_historic_alarms exportierten, Json daten wieder her. 

    return: dict
    """

    projektname = projektinfo["projektname"]
    projekt_path = projektinfo["project_path"]
    csv_path = projektinfo["csv_path"]

    database_path = f"{projekt_path}/hmi.sqlite"
    export_path = f"{csv_path}/{projektname}/Alarms_Export"

    conn1 = db.create_connection(database_path)  

    #_HistAlarms

    data_HistAlarms = rwf.read_json(f"{export_path}/_HistAlarms.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO _HistAlarms VALUES"
        data_list=[]
        i=0
        for data in data_HistAlarms:
            if i > 300:

                sql_statement = sql_statement[:-1]       
                try:
                    cur.execute(sql_statement, data_list)
                    _HistAlarmsImported =f"imported"
                except Exception as e:
                    _HistAlarmsImported = f"Error while insert in _HistAlarms: {e}"
                
                sql_statement =f"INSERT INTO _HistAlarms VALUES"
                data_list=[]
                i=0
            i=i+1
            sql_statement = sql_statement+ f"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?),"
            data_list.append(data)
            data_list = data_list + data_HistAlarms[data]


        sql_statement = sql_statement[:-1]       
        try:
            cur.execute(sql_statement, data_list)
            _HistAlarmsImported =f"imported"
        except Exception as e:
            _HistAlarmsImported = f"Error while insert in _HistAlarms: {e}"

    return {"_HistAlarms": _HistAlarmsImported}


@app.get("/jobs")
async def get_job_database(projektinfo : ConfigBaseModel = Depends(get_project_info)):
    """
    Sichert alle für die Auftragsverwaltung relevanten Datenbanktables in Json Dateien im Export Ordner
    
    """

    projektname = projektinfo["projektname"]
    projekt_path = projektinfo["project_path"]
    csv_path = projektinfo["csv_path"]

    database_path = f"{projekt_path}/hmi.sqlite"
    export_path = f"{csv_path}/{projektname}/Job_ListExport"

    User_folder_created = rwf.create_folder(export_path)

    job_listExported= []
    spool_report_dataExported =[]
    spool_reportsExported=[]

    if User_folder_created:

        conn1 = db.create_connection(database_path)

    #job_list

        with conn1:
            cur = conn1.cursor()

        try:
            cur.execute(f"SELECT * FROM job_list",) 
            datajob_list = cur.fetchall()
            datajob_list_dict={}

            for data in datajob_list:
                datajob_list_dict.update({data[0]: [data[1], data[2], data[3], data[4], data[5], data[6], data[7]]}) 

        
            job_listExported = rwf.write_json(path= f"{export_path}/job_list.json", data= datajob_list_dict)

        except Exception as e:
            print(f"Fehler beim lesen aus job_list : {e}")



    #spool_report_data

        with conn1:
            cur = conn1.cursor()

            try:
                cur.execute(f"SELECT * FROM spool_report_data",) 
                dataspool_report_data = cur.fetchall()
                dataspool_report_data_dict={}

                for data in dataspool_report_data:
                    dataspool_report_data_dict.update({data[0]: [data[1], data[2]]}) 
                spool_report_dataExported = rwf.write_json(path= f"{export_path}/spool_report_data.json", data= dataspool_report_data_dict)

            except Exception as e:
                print(f"Fehler beim lesen aus report data : {e}")

        



    #spool_reports

        with conn1:
            cur = conn1.cursor()
            try:
                cur.execute(f"SELECT * FROM spool_reports",) 
                dataspool_reports = cur.fetchall()
                dataspool_reports_dict={}

                for data in dataspool_reports:
                    dataspool_reports_dict.update({data[0]: [data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[7],\
                        data[8], data[9], data[10], data[11], data[12], data[13], data[14], data[15], data[16], data[17], data[18],\
                        data[19], data[20], data[21], data[22], data[23], data[24], data[25], data[26], data[27], data[28], data[29],\
                        data[30], data[31], data[32], data[33], data[34], data[35], data[36]]}) 

                
                spool_reportsExported = rwf.write_json(path= f"{export_path}/spool_reports.json", data= dataspool_reports_dict)

            except Exception as e:
                print(f"Fehler beim lesen aus spool_reports : {e}")




    return {"job_list": job_listExported, "spool_report_data": spool_report_dataExported, "spool_reports": spool_reportsExported,}

    
@app.delete("/jobs")
async def delete_job_database(projektinfo : ConfigBaseModel = Depends(get_project_info)):

    """
    Löscht alles was mit Job Management zu tun hat
    """

    projekt_path = projektinfo["project_path"]
    database_path = f"{projekt_path}/hmi.sqlite"

    conn1 = db.create_connection(database_path)  

    with conn1:

        cur = conn1.cursor()
        try:
            cur.execute(f"DELETE FROM job_list")
            job_listDeleted = "deleted"
        except Exception as e:
            job_listDeleted = f"Error while deleting job_list: {e}"    

        try:
            cur.execute(f"DELETE FROM spool_reports")
            spool_reportsDeleted = "deleted"
        except Exception as e:
            spool_reportsDeleted = f"Error while deleting spool_reports: {e}"    

        try:
            cur.execute(f"DELETE FROM spool_report_data")
            spool_report_dataDeleted = "deleted"
        except Exception as e:
            spool_report_dataDeleted = f"Error while deleting spool_report_data: {e}"  

        conn1.isolation_level = None
        cur.execute("VACUUM")  

    return {"job_list" : job_listDeleted, "spool_reports" : spool_reportsDeleted,"spool_report_data" : spool_report_dataDeleted}

    
@app.put("/jobs")
async def restore_job_database(projektinfo : ConfigBaseModel = Depends(get_project_info)):
    """
    Stellt die Job Datenbank mit den, über get_job_Database exportierten, Json daten wieder her. 

    return: dict
    """

    projektname = projektinfo["projektname"]
    projekt_path = projektinfo["project_path"]
    csv_path = projektinfo["csv_path"]

    database_path = f"{projekt_path}/hmi.sqlite"
    export_path = f"{csv_path}/{projektname}/Alarms_Export"

    conn1 = db.create_connection(database_path)  

    #job_list

    datajob_list = rwf.read_json(f"{export_path}/job_list.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO job_list VALUES"
        data_list=[]
        i=0
        for data in datajob_list:
            if i > 300:

                sql_statement = sql_statement[:-1]       
                try:
                    cur.execute(sql_statement, data_list)
                    job_listImported =f"imported"
                except Exception as e:
                    job_listImported = f"Error while insert in job_list: {e}"
                
                sql_statement =f"INSERT INTO job_list VALUES"
                data_list=[]
                i=0
            i=i+1
            sql_statement = sql_statement+ f"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?),"
            data_list.append(data)
            data_list = data_list + datajob_list[data]


        sql_statement = sql_statement[:-1]       
        try:
            cur.execute(sql_statement, data_list)
            job_listImported =f"imported"
        except Exception as e:
            job_listImported = f"Error while insert in job_list: {e}"

    #spool_reports

    dataspool_reports = rwf.read_json(f"{export_path}/spool_reports.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO spool_reports VALUES"
        data_list=[]
        i=0
        for data in dataspool_reports:
            if i > 300:

                sql_statement = sql_statement[:-1]       
                try:
                    cur.execute(sql_statement, data_list)
                    spool_reportsImported =f"imported"
                except Exception as e:
                    spool_reportsImported = f"Error while insert in spool_reports: {e}"
                
                sql_statement =f"INSERT INTO spool_reports VALUES"
                data_list=[]
                i=0
            i=i+1
            sql_statement = sql_statement+ f"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?),"
            data_list.append(data)
            data_list = data_list + dataspool_reports[data]


        sql_statement = sql_statement[:-1]       
        try:
            cur.execute(sql_statement, data_list)
            spool_reportsImported =f"imported"
        except Exception as e:
            spool_reportsImported = f"Error while insert in spool_reports: {e}"


    #spool_report_data

    dataspool_report_data = rwf.read_json(f"{export_path}/spool_report_data.json")

    with conn1:
        cur = conn1.cursor()

        sql_statement =f"INSERT INTO spool_report_data VALUES"
        data_list=[]
        i=0
        for data in dataspool_report_data:
            if i > 300:

                sql_statement = sql_statement[:-1]       
                try:
                    cur.execute(sql_statement, data_list)
                    spool_report_dataImported =f"imported"
                except Exception as e:
                    spool_report_dataImported = f"Error while insert in spool_report_data: {e}"
                
                sql_statement =f"INSERT INTO spool_report_data VALUES"
                data_list=[]
                i=0
            i=i+1
            sql_statement = sql_statement+ f"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?),"
            data_list.append(data)
            data_list = data_list + dataspool_report_data[data]


        sql_statement = sql_statement[:-1]       
        try:
            cur.execute(sql_statement, data_list)
            spool_report_dataImported =f"imported"
        except Exception as e:
            spool_report_dataImported = f"Error while insert in spool_report_data: {e}"

    return {"job_list": job_listImported,"spool_reports": spool_reportsImported,"spool_report_data": spool_report_dataImported,}


@app.get("/backup")
async def create_backup(result1 : str = Depends(get_all_item_records), result2 : dict = Depends(export_userData), result3 : dict = Depends(get_all_recipes), result4 : dict = Depends(get_historic_alarms), result5 : dict = Depends(get_job_database)):
    result_dict ={}
    result_dict.update(result1)
    result_dict.update(result2)
    result_dict.update(result3)
    result_dict.update(result4)
    result_dict.update(result5)
    return result_dict 


@app.delete("/backup")
async def delete_databases(result1 : dict = Depends(delete_all_Item_records), result2 : dict = Depends(delete_userData), result3 : dict = Depends(delete_all_recipes), result4 : dict = Depends(delete_historic_alarms), result5 : dict = Depends(delete_job_database)):
    result_dict ={}
    result_dict.update(result1)
    result_dict.update(result2)
    result_dict.update(result3)
    result_dict.update(result4)
    result_dict.update(result5)
    return result_dict 


@app.put("/backup")
async def restore_databases(result1 : str = Depends(restore_all_item_records), result2 : dict = Depends(restore_userData), result3 : dict = Depends(restore_all_recipes), result4 : dict = Depends(restore_historic_alarms), result5 : dict = Depends(restore_job_database)):
    result_dict ={}
    result_dict.update(result1)
    result_dict.update(result2)
    result_dict.update(result3)
    result_dict.update(result4)
    result_dict.update(result5)
    return result_dict 


