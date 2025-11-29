import sqlite3

conn = sqlite3.connect("bot_gpt.db")
cursor = conn.cursor()

for row in cursor.execute("SELECT * FROM document_chunks"):
    print(row)
