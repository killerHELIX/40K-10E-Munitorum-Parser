# importing required modules
import json
import re
import csv

from pprint import pprint
from PyPDF2 import PdfReader
import pandas as pd

def find_faction_page(faction, reader):
    print(f"Finding faction {faction} with reader {reader}")

    for i in range(0, len(reader.pages)):
        page = reader.pages[i]
        text = page.extract_text()
        lines = text.split("\n")
        page_title = lines[0]
        # print(page_title)
        if page_title.upper() == faction.upper():
            # pprint(lines)
            # print(f"Found {faction} on page {i}")
            return i


def create_datamodel(faction, page, reader, pages_to_parse):

    unit_faction = []
    enh_faction = []
    unit_names = []
    unit_points = []
    enh_names = []
    enh_points = []

    # for i in range(page, page + pages_to_parse):
    for i in range(0, len(reader.pages)):
        page = reader.pages[i]

        if i == 0: continue # Skip title page.

        page = reader.pages[i]
        text = page.extract_text()
        lines = text.split("\n")
        lines.pop() # Remove page number.

        faction = clean_faction_name(lines[0])
        print(f"Faction {faction}")

        unit_name = ""
        enhancements_found = False
        for line in lines:
            # print(line)
            split = re.split(r"[.]+", line)

            if len(split) == 1: # If the split only has one item, most of the time it's the unit name.
                unit_name = clean_unit_name(split[0].strip())
                if enhancements_found or unit_name == "DETACHMENT ENHANCEMENTS":
                    enhancements_found = True
                continue

            # names.append(split[0].strip())
            if len(split) > 1: 

                first = split[0].strip().replace(" models", "").replace(" model", "")
                last = split[1].strip().replace(" pts", "")
                last_num = re.findall(r"\d+", last)[0]

                if not enhancements_found:

                    name = f"{first} {unit_name}" if not enhancements_found else f"{first}"
                    name = re.sub("^1 ", "", name) # If a unit only has one model just remove the '1 '
                    # print(name)
                    unit_faction.append(faction)
                    unit_names.append(name)
                    unit_points.append(last_num)
                    enh_faction.append("")
                    enh_names.append("")
                    enh_points.append("")
                
                else: # enhancements_found is true
                    name = f"{first} {unit_name}" if not enhancements_found else f"{first}"
                    name = re.sub("^1 ", "", name) # If a unit only has one model just remove the '1 '
                    # print(name)
                    unit_faction.append("")
                    unit_names.append("")
                    unit_points.append("")
                    enh_faction.append(faction)
                    enh_names.append(name)
                    enh_points.append(last_num)

                    unit_name = unit_name if (last.isnumeric()) else re.findall(r"\D+", last)[0]
        
    df = pd.DataFrame()

    # Creating two columns
    df["Unit Faction"] = unit_faction
    df["Unit Name"] = unit_names
    df["Unit Cost"] = unit_points
    df["Enhancement Faction"] = enh_faction
    df["Enhancement Name"] = enh_names
    df["Enhancement Cost"] = enh_points

    # Converting to excel
    df.to_excel('result.xlsx', index = False)

def clean_unit_name(unit_name):
    return unit_name\
        .replace("T ank", "Tank")\
        .replace("T aurox", "Taurox")\
        .replace("T arantula", "Tarantula")

def clean_faction_name(faction):
    return faction.replace("T'Au", "Tau").title().strip()



def create_datamodel_2(reader):

    ALL_FACTIONS = [
        "Adepta Sororitas",
        "Adeptus Custodes",
        "Adeptus Mechanicus",
        "Adeptus Titanicus",
        "Aeldari",
        "Agents Of The Imperium",
        "Astra Militarum",
        "Black Templars",
        "Blood Angels",
        "Chaos Daemons",
        "Chaos Knights",
        "Chaos Space Marines",
        "Dark Angels",
        "Death Guard",
        "Deathwatch",
        "Drukhari",
        "Genestealer Cults",
        "Grey Knights",
        "Imperial Knights",
        "Leagues of Votann",
        "Necrons",
        "Orks",
        "Space Marines",
        "Space Wolves",
        "T’Au Empire",
        "Thousand Sons",
        "Tyranids",
        "World Eaters"
    ]

    IGNORED_LINES = [
        "FORGE WORLD POINTS VALUES",
        "DETACHMENT ENHANCEMENTS"
    ]

    # Initialize faction data structures.
    model = {}
    # model["factions"] = ALL_FACTIONS
    # for faction in model["factions"]:
    #     faction_name = faction
    #     faction = model["factions"].get(faction)
    #     faction["units"] = {}
    #     faction["enhancements"] = {}
    model["factions"] = [ {"name": faction, "units": [], "enhancements": [] } for faction in ALL_FACTIONS ] 

    current_faction_name = None
    for i in range(0, len(reader.pages)):
        if i == 0: continue # Skip title page.

        page = reader.pages[i]
        text = page.extract_text()
        lines = text.split("\n")
        page_title = lines[0].strip().title()
        current_faction_name = page_title if page_title in [ faction["name"] for faction in model["factions"] ] else current_faction_name
        current_faction = [ faction for faction in model["factions"] if faction["name"] == current_faction_name ][0]
        lines.pop() # Remove page number.
        lines.pop(0) # Remove title.

        if current_faction_name == "Adeptus Custodes":
            print(f"Current faction: {current_faction_name}")
            # pprint(lines)

            current_unit = {
                "name": None,
                "composition": []
            }

            is_enhancement = False

            for line in lines:

                is_enhancement = "DETACHMENT ENHANCEMENTS" in line or is_enhancement

                if line in IGNORED_LINES: continue

                print(line)
                if re.search(r"[.]+", line):
                    # print(f"{line} has dots in it")
                    if not line.endswith("pts"):
                        # line += " INVALID"
                        split = re.split(r"pts", line)
                        current_unit["composition"].append(split[0])
                        current_unit = add_unit_and_clear(current_unit, current_faction["units"] if not is_enhancement else current_faction["enhancements"])
                        current_unit["name"] = split[1]
                    else:
                        current_unit["composition"].append(line)

                else:
                    # print(f"{line} NO dots in it")
                    if current_unit["name"]:
                        current_unit = add_unit_and_clear(current_unit, current_faction["units"] if not is_enhancement else current_faction["enhancements"])

                    current_unit["name"] = line

                # print("Current Unit")
                # pprint(current_unit)

                # if "FORGE WORLD" in line: break
            current_unit = add_unit_and_clear(current_unit, current_faction["units"]) # Add & clear the final unit on the page.
                
                        
            # print("Current Faction")
            # pprint(current_faction)

    return model

def add_unit_and_clear(unit, units):
    units.append(unit)
    # print(f"Adding {unit['name']} to units")

    # Clear current unit.
    return {
        "name": None,
        "composition": []
    }
  
if __name__ == "__main__":
    PDF = "Munitorum.pdf"
    # # FACTION = "Black Templars"
    # PAGES_TO_PARSE = 1

    reader = PdfReader(PDF)

    # faction_page = find_faction_page(FACTION, reader)
    # create_datamodel(FACTION, faction_page, reader, PAGES_TO_PARSE)

    model = create_datamodel_2(reader)
    # pprint(model)
    with open("result.json", "w") as outfile:
        json.dump(model, outfile, indent=2)
