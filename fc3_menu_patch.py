import os
import sys
import shutil
import xml.etree.ElementTree as ET
import hashlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FC3MenuPatch')

def find_game_directory():
    """Try to find the Far Cry 3 installation directory."""
    possible_paths = [
        r"C:\Games\Far Cry 3",
        r"C:\Games\Far Cry 3\Far Cry 3",
        r"C:\Games\Far Cry 3\Far Cry 3\bin",
        r"C:\Program Files (x86)\Ubisoft\Far Cry 3",
        r"C:\Program Files\Ubisoft\Far Cry 3",
        r"D:\Program Files (x86)\Ubisoft\Far Cry 3",
        r"D:\Program Files\Ubisoft\Far Cry 3",
        r"E:\Program Files (x86)\Ubisoft\Far Cry 3",
        r"E:\Program Files\Ubisoft\Far Cry 3"
    ]
    
    # Check Steam paths
    steam_paths = [
        r"C:\Program Files (x86)\Steam\steamapps\common\Far Cry 3",
        r"C:\Program Files\Steam\steamapps\common\Far Cry 3",
        r"D:\Steam\steamapps\common\Far Cry 3",
        r"E:\Steam\steamapps\common\Far Cry 3"
    ]
    
    possible_paths.extend(steam_paths)
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(os.path.join(path, "farcry3.exe")):
            return path
    
    return None

def backup_file(file_path):
    """Create a backup of the specified file."""
    backup_path = file_path + ".bak"
    if not os.path.exists(backup_path):
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    
    return backup_path

def calculate_md5(file_path):
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def patch_menu_xml(game_dir):
    """Patch the main menu XML to add the multiplayer option."""
    menu_path = os.path.join(game_dir, "data_win32", "menus", "mainmenu.xml")
    
    if not os.path.exists(menu_path):
        logger.error(f"Menu file not found: {menu_path}")
        return False
    
    # Create backup
    backup_file(menu_path)
    
    try:
        # Parse the XML
        tree = ET.parse(menu_path)
        root = tree.getroot()
        
        # Check if multiplayer entry already exists
        main_menu = root.find(".//menu[@name='MainMenu']")
        if main_menu is None:
            logger.error("MainMenu element not found in XML")
            return False
        
        # Check if multiplayer option already exists
        mp_option = main_menu.find(".//*[@name='Multiplayer']")
        if mp_option is not None:
            logger.info("Multiplayer menu option already exists")
            return True
        
        # Find the Campaign and Options entries to position our new entry
        campaign_option = main_menu.find(".//*[@name='Campaign']")
        options_option = main_menu.find(".//*[@name='Options']")
        
        if campaign_option is None or options_option is None:
            logger.error("Could not find required menu entries")
            return False
        
        # Create new multiplayer option
        mp_element = ET.Element("menuElement")
        mp_element.set("name", "Multiplayer")
        mp_element.set("show", "1")
        
        # Add subelements
        text_elem = ET.SubElement(mp_element, "text")
        text_elem.text = "MULTIPLAYER"
        
        action_elem = ET.SubElement(mp_element, "action")
        action_elem.set("name", "LoadMenu")
        action_elem.set("param1", "MPMenu")
        
        # Insert after Campaign
        index = list(main_menu).index(campaign_option) + 1
        main_menu.insert(index, mp_element)
        
        # Write modified XML back to file
        tree.write(menu_path, encoding="utf-8", xml_declaration=True)
        logger.info("Successfully added Multiplayer option to main menu")
        
        # Now create the MP menu XML if it doesn't exist
        create_mp_menu_xml(game_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"Error patching menu XML: {str(e)}")
        return False

def create_mp_menu_xml(game_dir):
    """Create the multiplayer menu XML file."""
    mp_menu_path = os.path.join(game_dir, "data_win32", "menus", "mpmenu.xml")
    
    if os.path.exists(mp_menu_path):
        logger.info("MP menu file already exists")
        return True
    
    try:
        # Create a basic MP menu
        root = ET.Element("menu")
        
        # Menu header
        header = ET.SubElement(root, "header")
        header.set("name", "MPMenu")
        header.set("parent", "MainMenu")
        
        # Menu elements
        menu_elem = ET.SubElement(root, "menu")
        menu_elem.set("name", "MPMenu")
        
        # Join Game option
        join_elem = ET.SubElement(menu_elem, "menuElement")
        join_elem.set("name", "JoinGame")
        join_elem.set("show", "1")
        
        join_text = ET.SubElement(join_elem, "text")
        join_text.text = "JOIN GAME"
        
        join_action = ET.SubElement(join_elem, "action")
        join_action.set("name", "JoinGame")
        
        # Back option
        back_elem = ET.SubElement(menu_elem, "menuElement")
        back_elem.set("name", "Back")
        back_elem.set("show", "1")
        
        back_text = ET.SubElement(back_elem, "text")
        back_text.text = "BACK"
        
        back_action = ET.SubElement(back_elem, "action")
        back_action.set("name", "Back")
        
        # Write to file
        tree = ET.ElementTree(root)
        tree.write(mp_menu_path, encoding="utf-8", xml_declaration=True)
        logger.info(f"Created MP menu file: {mp_menu_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating MP menu XML: {str(e)}")
        return False

def main():
    logger.info("Far Cry 3 Menu Patcher")
    
    # Find game directory
    game_dir = find_game_directory()
    if not game_dir:
        game_dir = input("Please enter the Far Cry 3 installation directory: ")
        if not os.path.exists(game_dir) or not os.path.isfile(os.path.join(game_dir, "farcry3.exe")):
            logger.error("Invalid game directory")
            input("Press Enter to exit...")
            return
    
    logger.info(f"Found Far Cry 3 at: {game_dir}")
    
    # Patch menu
    if patch_menu_xml(game_dir):
        logger.info("Menu patching completed successfully")
    else:
        logger.error("Failed to patch menu files")
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()