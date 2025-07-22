# Xenia Manager Database

This repository serves as a centralized public database for Xbox 360 game compatibility, patches, and related metadata, intended for use with [Xenia Manager](https://github.com/xenia-manager/xenia-manager). Its goal is to provide a unified source for comprehensive information about Xbox 360 games.

---

## 📁 Repository Structure

The `data` folder contains several JSON files and subfolders, organized as follows:

- `game-compatibility/`  
  - `stable.json` — Xenia Stable Compatibility List  
  - `canary.json` — Xenia Canary Compatibility List

- `launchbox_games.json` — (Outdated) Launchbox database export

- `wikipedia_games.json` — (Deprecated) Wikipedia-based game list

- `patches/`  
  - `canary.json` — Canary build patches  
  - `netplay.json` — Netplay-specific patches

---

## 🌐 Data Information

### Game Information

- **Xenia Stable Compatibility List:**  
  [stable.json](https://raw.githubusercontent.com/xenia-manager/database/main/data/game-compatibility/stable.json)  
  `data/game-compatibility/stable.json`

- **Xenia Canary Compatibility List:**  
  [canary.json](https://raw.githubusercontent.com/xenia-manager/database/main/data/game-compatibility/canary.json)  
  `data/game-compatibility/canary.json`

### Game Information

- **Launchbox Database (Currently outdated):**  
  [launchbox_games.json](https://raw.githubusercontent.com/xenia-manager/database/main/data/launchbox_games.json)  
  `data/launchbox_games.json`

- **Wikipedia List of Xbox360 Games (No longer used):**  
  [wikipedia_games.json](https://raw.githubusercontent.com/xenia-manager/database/main/data/wikipedia_games.json)  
  `data/wikipedia_games.json`

### Patches

- **Canary Patches:**  
  [patches/canary_patches.json](https://raw.githubusercontent.com/xenia-manager/database/main/data/patches/canary.json)  
  `data/patches/canary.json`

- **Netplay Patches:**  
  [patches/netplay_patches.json](https://raw.githubusercontent.com/xenia-manager/database/main/data/patches/netplay.json)  
  `data/patches/netplay.json`

## How It Works

- **Data Format:**  
  All files are in JSON format, making them easy to parse in any programming language.

- **Autoupdate:**  
  The `update_database.yml` GitHub Actions workflow automatically updates game compatibility and patch data twice a day by fetching the latest information from official Xenia sources and relevant repositories.

- **Usage:**  
  Fork the repository.
  You can fetch and use these files in your own tools, scripts, or applications.