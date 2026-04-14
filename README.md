# How to run this code
1. Install Claude Desktop
2. Clone project to pc
3. Add your database information instead
4. install dependencies ->  pip install -r requirements.txt
5. Open Claude Destktop -> files -> settings -> Developer -> Edit Config -> claude_desktop_config.json
6. open claude_desktop_config.json paste this code

{
  "mcpServers": {
    "cars_db": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\ABSOLUTE\\PATH\\TO\\PARENT\\FOLDER",
        "run",
        "cars.py"
      ]
    }
  }
}

<img width="499" height="349" alt="image" src="https://github.com/user-attachments/assets/581f860a-92b2-4001-a2b1-0f515dc633b3" />


# notes 
- you might need the full uv path 
  mac: which uv, windows: where uv

- for the directory path you might need your real path keep the double \\
