# How to run this code
1. Install Claude Desktop
2. Clone project to pc
3. Add your database information instead
4. install dependencies ->  pip install -r requirements.txt
5. Open Claude Destktop -> files -> settings -> Developer -> Edit Config -> claude_desktop_config.json
6. open claude_desktop_config.json paste this code


  "mcpServers": {
    "cars_db": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8080/mcp"
      ]
    }
  }

# notes
- fast_api.py: to test tools

