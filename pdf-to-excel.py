# importing required modules
import json
import re

from pprint import pprint
from PyPDF2 import PdfReader
import pandas as pd


def create_datamodel(reader):
    """
    Creates a datamodel of all factions with their corresponding units, 
    compositions, and enhancements.
    """

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
        "Leagues Of Votann",
        "Necrons",
        "Orks",
        "Space Marines",
        "Space Wolves",
        "T’Au Empire",
        "Thousand Sons",
        "Tyranids",
        "World Eaters"
    ]

    # Lines that contain any of these strings will be completely ignored.
    IGNORED_LINES = [
        "FORGE WORLD POINTS VALUES",
    ]

    # Initialize faction data structures.
    model = {}
    model["factions"] = [ {"name": faction, "units": [], "enhancements": [] } for faction in ALL_FACTIONS ] 

    current_faction_name = None # Set this outside of the page loop to keep state across pages.

    for i in range(0, len(reader.pages)):
        if i == 0: continue # Skip title page.

        page = reader.pages[i]
        text = page.extract_text()
        lines = text.split("\n")
        page_title = lines[0].strip().title()
        current_faction_name = page_title if page_title in [ faction["name"] for faction in model["factions"] ] else current_faction_name # Current faction is whatever the last valid page title was.
        current_faction = [ faction for faction in model["factions"] if faction["name"] == current_faction_name ][0] # Object reference of the faction name found above.
        lines.pop() # Remove page number.
        lines.pop(0) # Remove title.

        # if current_faction_name == "Astra Militarum": # Temporarily only generate for a certain faction.
        if True:
            print(f"Current faction: {current_faction_name}")

            # Default unit data structure.
            current_unit = {
                "name": None,
                "composition": []
            }

            is_enhancement = False # Enhancements treat their 'composition' differently.
            line_wrapped = False # When a line wraps across multiple lines the lines after the first should be ignored.

            # for line in lines:
            for i in range(0, len(lines)):
                line = lines[i]


                if line_wrapped: # If the line is wrapped, reset the line_wrapped state and skip this line.
                    line_wrapped = False
                    continue

                # print(repr(line))

                is_enhancement = "DETACHMENT ENHANCEMENTS" in line or is_enhancement
                if line in IGNORED_LINES: continue

                # The "DETACHMENT ENHANCEMENTS" line indicates only Enhancements will be added from this point on, so add & clear the current unit before doing that.
                # Then skip this step of the loop because we don't care about "DETACHMENT ENHANCEMENTS" otherwise. (continue)
                if "DETACHMENT ENHANCEMENTS" in line:
                    current_unit = add_unit_and_clear(current_unit, current_faction["units"])
                    continue

                if re.search(r"[.]+", line): # Matches the general 'x models ........... 1234 pts' pattern.
                    if not (line.endswith("pts") or line.endswith("pts ")): # Sometimes a parsing error can result in 'x models ...... 1234 ptsNew Unit Name'. Detect this and add & clear before continuing.
                        split = re.split(r"pts", line)
                        current_unit["composition"].append(split[0])
                        current_unit = add_unit_and_clear(current_unit, current_faction["units"])
                        current_unit["name"] = fix(split[1])
                    else:

                        if is_enhancement: # Enhancements set their 'name' to the first half of their line and their 'composition' to the last half.
                            split = re.split(r"[.]+", line)
                            current_unit["name"] = fix(split[0])
                            current_unit["composition"].append(split[1].strip())
                            current_unit = add_unit_and_clear(current_unit, current_faction["enhancements"])
                        else: # Not an enhancement so just add the entire line as is into the composition.
                            current_unit["composition"].append(line)

                else: # Doesn't match the 'x models ..... 1234 pts' pattern - that means this must be the name of a unit.
                    if current_unit["name"] and not is_multiline_composition(line): # If the current unit already has a 'name' key, then this is the name of the next unit. So add & clear.
                        current_unit = add_unit_and_clear(current_unit, current_faction["units"] if not is_enhancement else current_faction["enhancements"])

                    # Then, add the line to the 'name' key.
                    if line.endswith(" "): # Detect if a name wrapped across multiple lines.
                        line_wrapped = True;

                        if is_multiline_composition(line):
                            current_unit["composition"].append(f"{line.strip()} {lines[i + 1].strip()}")
                            # print(current_unit)
                        else:
                            current_unit["name"] = f"{fix(line)} {fix(lines[i + 1])}"
                    else:
                        current_unit["name"] = fix(line)

    return model



def add_unit_and_clear(unit, units):
    """
    Adds a provided unit to the provided list 'units', then returns a "cleared" (no data) unit.
    """
    units.append(unit)
    # print(f"Adding {unit['name']}")

    # Clear current unit.
    return {
        "name": None,
        "composition": []
    }



def fix(line):
    """
    Utility function to fix any oddities from the PDF parsing of provided text.
    """
    line = line.replace("T a", "Ta")
    line = line.replace("Spore MInes", "Spore Mines")
    return line.strip()



def is_multiline_composition(line):
    """
    This function solely exists for the few units in the Munitorum PDF that have
    one composition value wrapped across multiple lines.

    Handling one of these is effectively the same as handling a unit name wrapped, but 
    since this is a composition it has to be treated differently, hence this function's existence.

    There has to be a better way than this.
    """
    return "Sword Brother" in line or "Inquisitorial Acolyte" in line



def parse_unit_compositions(model):
    """
    Parses given model's unit compositions into data structures.
    The model's unit compositions are assumed to be of the following pattern: 'x models ...... 123 pts'.
    Essentially splits that string by the '.....' and assigns each side to a key/value pair.

    For enhancements, there is no "count" - only "cost".
    """

    for faction in model["factions"]:
        for unit in faction["units"]:

            new_composition = []
            for entry in unit["composition"]: # Reorganize unit compositions.
                new_entry = { "count": None, "cost": None }
                [ new_entry["count"], new_entry["cost"] ] = re.split(r"[.]+", entry)
                new_entry["count"] = new_entry["count"].strip()
                new_entry["cost"] = re.findall(r"\d+", new_entry["cost"])[0] # Only take numbers for the cost.
                new_composition.append(new_entry)
            
            unit["composition"] = new_composition

        for enhancement in faction["enhancements"]:

            new_composition = []
            for entry in enhancement["composition"]: # Reorganize enhancement "compositions".
                new_entry = { "cost": None }
                new_entry["cost"] = re.findall(r"\d+", entry)[0] # Only take numbers for the cost.
                new_composition.append(new_entry)
            
            enhancement["composition"] = new_composition
    
    return model

def move_faction_to_end(faction_name, model):
    """
    Finds the given faction and moves it to the end of the given model's faction list.
    This ordering matters for xlsx output - when FILTER queries are added together it concatenates them in the order they are found.
    If these factions are at the end of the model's faction list, they will display last when in a FILTER query result.
    This is preferential for the specific use cases of Space Marines and Agents of the Imperium.
    """
    factions = model["factions"]

    faction = [ faction for faction in factions if faction["name"] == faction_name ][0]
    factions.remove(faction)
    factions.append(faction)

    return model



def write_json(model):
    """
    Writes the given model to a json output.
    """
    with open("result.json", "w") as outfile:
        json.dump(model, outfile, indent=2)




def write_xlsx(model):
    """
    Writes the given model to an xlsx output with the following structure:

    | Unit Faction | Unit Name | Unit Cost | Enhancement Faction | Enhancement Name | Enhancement Cost |
    ====================================================================================================
    |     ...      |    ...    |     ...   |         ...         |       ...        |       ...        |
    ----------------------------------------------------------------------------------------------------
    |     ...      |    ...    |     ...   |         ...         |       ...        |       ...        |
    ----------------------------------------------------------------------------------------------------

    """

    df = pd.DataFrame()

    # Initialize column lists.
    unit_faction = []
    unit_names = []
    unit_cost = []
    enh_faction = []
    enh_names = []
    enh_cost = []


    for faction in model["factions"]:
        for unit in faction["units"]:
            for entry in unit["composition"]:
                unit_faction.append(faction["name"])
                unit_names.append(f"{unit['name']} - {entry['count']}")
                unit_cost.append(entry["cost"])
                
                # The dataframe has to have columns equal size, so add blanks to Enhancement while adding actual data to Units.
                enh_faction.append("")
                enh_names.append("")
                enh_cost.append("")

        for enhancement in faction["enhancements"]:
            for entry in enhancement["composition"]:
                # The dataframe has to have columns equal size, so add blanks to Units while adding actual data to Enhancements.
                unit_faction.append("")
                unit_names.append("")
                unit_cost.append("")

                enh_faction.append(faction["name"])
                enh_names.append(f"{enhancement['name']}")
                enh_cost.append(entry["cost"])

    # Assign columns.
    df["Unit Faction"] = unit_faction
    df["Unit Name"] = unit_names
    df["Unit Cost"] = unit_cost
    df["Enhancement Faction"] = enh_faction
    df["Enhancement Name"] = enh_names
    df["Enhancement Cost"] = enh_cost

    df.to_excel('result.xlsx', index = False)


if __name__ == "__main__":
    PDF = "Munitorum.pdf" 
    reader = PdfReader(PDF)

    model = create_datamodel(reader)
    model = parse_unit_compositions(model)
    model = move_faction_to_end("Chaos Space Marines", model)
    model = move_faction_to_end("Space Marines", model)
    model = move_faction_to_end("Chaos Knights", model)
    model = move_faction_to_end("Imperial Knights", model)
    model = move_faction_to_end("Agents Of The Imperium", model)

    write_json(model)
    write_xlsx(model)

