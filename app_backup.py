from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3

app = FastAPI()

def init_db():
	conn = sqlite3.connect("cloudsocial.db")
	cursor = conn.cursor()
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS posts (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		user TEXT NOT NULL,
		content TEXT NOT NULL
		)
	""")
	conn.commit()
	conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
def home():
	conn = sqlite3.connect("cloudsocial.db")
	cursor = conn.cursor()
	cursor.execute("SELECT user, content FROM posts ORDER BY id DESC")
	posts = cursor.fetchall()
	conn.close()

	feed_html = ""

	for user, content in posts:
		feed_html += f"""
		<div style="background:#1f1f1f; padding:15px; margin-bottom:12px; border-radius:10px;">
			<h3>{user}</h3>
			<p>{content}</p>
		</div>
		"""

	return f"""
    <html>
    <head>
        <title>CloudSocial</title>
    </head>

    <body style="
        font-family:Arial;
        background:#111;
        color:white;
        max-width:700px;
        margin:auto;
        padding:20px;
    ">

        <h1>CloudSocial</h1>

        <p>Social platform running on AWS + Nginx + FastAP + SQLite</p>

	<form method="post" action="/post">
	        <input method="user" placeholder="Your name" required
			style="width:100%; padding:10px; margin-bottom:10px;">

		<textarea name="content" placeholder="What's happening?" required
			style="width:100%; padding:10px; height:90px;"></textarea>

	<button type="submit" style="padding:10px 20px; margin-top:10px;">
		Post
	</button>
	</form>

	<hr>
        {feed_html}
    </body>
    </html>
    """
@app.get("/post")
def post_redirect():
	return RedirectResponse("/", status_code=303)


@app.post("/post")
def create_post(user: str = Form(...), content: str = Form(...)):
	conn = sqlite3.connect("cloudsocial.db")
	cursor = conn.cursor()
	cursor.execute(
		"INSERT INTO posts (user, content) VALUES (?, ?)",
		(user, content)

	)
	conn.commit()
	conn.close()	



	return RedirectResponse("/", status_code=303)
