# Xenia Manager Database

This repository serves as a centralized public database for Xbox 360 game compatibility, patches, and related metadata, intended for use with [Xenia Manager](https://github.com/xenia-manager/xenia-manager). Its goal is to provide a unified source for comprehensive information about Xbox 360 games.

---

## 📁 Repository Structure

The `Database` folder contains several JSON files and subfolders, organized as follows:

- `Game Compatibility/`  
  - `stable.json` — Xenia Stable Compatibility List  
  - `canary.json` — Xenia Canary Compatibility List

- `xbox_marketplace_games.json` — Master list of Xbox Marketplace games

- `Xbox Marketplace/`  
  - `<TitleID>/<TitleID>.json` — Detailed info for each game by Title ID

- `launchbox_games.json` — (Outdated) Launchbox database export

- `wikipedia_games.json` — (Deprecated) Wikipedia-based game list

- `Patches/`  
  - `canary_patches.json` — Canary build patches  
  - `netplay_patches.json` — Netplay-specific patches

---

## 🌐 Data Information

### Game Information

- **Xenia Stable Compatibility List:**  
  [stable.json](https://raw.githubusercontent.com/xenia-manager/Database/refs/heads/main/Database/Game%20Compatibility/stable.json)  
  `Database/Game Compatibility/stable.json`

- **Xenia Canary Compatibility List:**  
  [canary.json](https://raw.githubusercontent.com/xenia-manager/Database/refs/heads/main/Database/Game%20Compatibility/canary.json)  
  `Database/Game Compatibility/canary.json`

### Game Information

- **Xbox Marketplace:**  
  [xbox_marketplace_games.json](https://raw.githubusercontent.com/xenia-manager/Database/refs/heads/main/Database/xbox_marketplace_games.json)  
  `Database/xbox_marketplace_games.json`

  Each folder under `Xbox Marketplace/` corresponds to a specific title ID. For example:

  - **Example Title Folder:**  
    [Xbox Marketplace/TitleID/<TitleID>.json](https://raw.githubusercontent.com/xenia-manager/Database/refs/heads/main/Database/Xbox%20Marketplace/303407D4/303407D4.json)  
    `Database/Xbox Marketplace/<TitleID>/<TitleID>.json`

- **Launchbox Database (Currently outdated):**  
  [launchbox_games.json](https://raw.githubusercontent.com/xenia-manager/Database/refs/heads/main/Database/launchbox_games.json)  
  `Database/launchbox_games.json`

- **Wikipedia List of Xbox360 Games (No longer used):**  
  [wikipedia_games.json](https://raw.githubusercontent.com/xenia-manager/Database/refs/heads/main/Database/wikipedia_games.json)  
  `Database/wikipedia_games.json`

### Patches

- **Canary Patches:**  
  [Patches/canary_patches.json](https://raw.githubusercontent.com/xenia-manager/Database/refs/heads/main/Database/Patches/canary_patches.json)  
  `Database/Patches/canary_patches.json`

- **Netplay Patches:**  
  [Patches/netplay_patches.json](https://raw.githubusercontent.com/xenia-manager/Database/refs/heads/main/Database/Patches/netplay_patches.json)  
  `Database/Patches/netplay_patches.json`

## How It Works

- **Data Format:**  
  All files are in JSON format, making them easy to parse in any programming language.

- **Autoupdate:**  
  The `update_database.yml` GitHub Actions workflow automatically updates game compatibility and patch data twice a day by fetching the latest information from official Xenia sources and relevant repositories.

- **Usage:**  
  Fork the repository.
  You can fetch and use these files in your own tools, scripts, or applications.