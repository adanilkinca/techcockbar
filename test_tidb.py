import pymysql

connection = pymysql.connect(
    host="gateway01.us-west-2.prod.aws.tidbcloud.com",
    port=4000,
    user="8JGSLxusvWdD9Zo.root",           # EXACT from Connect panel
    password="VBQoCuSXmiWK1zcR",    # freshly generated
    database="test",                       # or your actual DB name
    ssl={"ca": r"isrgrootx1.pem"},         # CA file path
    charset="utf8mb4",
    cursorclass=pymysql.cursors.Cursor,
)

with connection.cursor() as cur:
    cur.execute("SELECT NOW();")
    print("Connected! Server time:", cur.fetchone()[0])

connection.close()
