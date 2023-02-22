import json
from importlib.resources import path
import os
import pandas as pd


def read_json(path :str): 
    """
    Liest eine Json aus und gibt sie als dict zurück
    
    path:           Pfad zur auszulesenden Datei

    return data :   {Content} (if file exists)
                    {} (otherwise)
    """
    data = {}
    try:
        with open(path, 'r') as file:
            data = json.load(file)
            file.close()
        return data
    except:
        print("Could not read file")
        return data



def write_json(path :str, data :dict):
    """    
    Liest ein Dict aus und schreibt den Inhalt in eine JSON
    path: Pfad zur zu schreibenden Datei
    return false = schreiben hat nicht geklappt
    return true = alles gut
    """
    try:

        j = json.dumps(data) #data in ein Objekt legen

        with open(path,'w') as f: #Json schreibend öffnen, wenn nicht vorhanden erstellen
            f.write(j) #Objekt ins file schreiben
            f.close()  
        return True

    except Exception as e:
        print(f"Json wurde nicht erstellt: {e}")
        return False


def write_csv(path :str, data :dict):

    """    
    Liest ein Dict aus und schreibt den Inhalt in eine JSON
    path: Pfad zur zu schreibenden Datei
    return false = schreiben hat nicht geklappt
    return true = alles gut
    """

    try:
        j = pd.DataFrame(data) #data in ein Objekt legen
        print(j)
        j.to_csv(path)

    except:
        return False


def create_folder(path:str):
    """
    Erzeugt eine Ordnerstrucktur sofern diese nicht vorhanden ist.
    return: false = Ordner nicht vorhanden und konnte nicht erzeugt werden
            True = Ordner vorhanden
    """

    exists =os.path.isdir(path) #existiert der Pfad und ist es ein Ordner?

    if exists:
        return exists 
        
    else:
        try:    
            os.makedirs(path)  #Erstelle den Pfad
            exists = os.path.isdir(path) #Hats geklappt
            return exists #Ergebnis ins Program zurück
        except Exception as e:
            print(f"Ordner konnte nicht erstellt werden: {e}")
            return exists  # nichts hat funktioniert. False ins Program zurück
