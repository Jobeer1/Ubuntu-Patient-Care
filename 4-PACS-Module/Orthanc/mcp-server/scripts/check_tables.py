import sqlite3
conn = sqlite3.connect('mcp_server.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables in mcp_server.db:")
for t in sorted(tables):
    print(f"  - {t}")
conn.close()
