from fastapi import FastAPI, Form, Request 
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import hashlib
import sqlite3

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="change-this-secret-key")

def hash_password(password):
	return hashlib.sha256(password.encode()).hexdigest()


def init_db():
	conn = sqlite3.connect("cloudsocial.db", timeout=10)
	cursor = conn.cursor()

	cursor.execute("""
		CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT UNIQUE NOT NULL,
		password_hash TEXT NOT NULL
		)
	""")

	
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS posts(
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT NOT NULL,
		content TEXT NOT NULL
		)
	""")

	cursor.execute("""
		CREATE TABLE IF NOT EXISTS likes(
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		post_id INTEGER NOT NULL,
		username TEXT NOT NULL,
		UNIQUE(post_id, username)
		)
	""")


	conn.commit()
	conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
	current_user = request.session.get("username")

	conn = sqlite3.connect("cloudsocial.db", timeout=10)
	cursor = conn.cursor()
	cursor.execute("SELECT id, username, content FROM posts ORDER BY id DESC")
	posts = cursor.fetchall()

	feed_html = ""
	for post_id, user, content in posts:
		cursor.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,))
		like_count = cursor.fetchone()[0]

		delete_button = ""
		if current_user == user:
			delete_button = f"""
			<form method="post" action="/delete/{post_id}" style="display:inline;">
				<button type="submit">Delete</button>
			</form>
			"""
		

		feed_html += f"""
		<div style="background:#1f1f1f; padding:15px; margin-bottom:12px; border-radius:10px;">
			<h3>{user}</h3>
			<p>{content}</p>

			<form method="post" action="/like/{post_id}" style="display:inline;">
				<button type="submit">Like</button>
			</form>

			<span>{like_count} likes</span>
			{delete_button}
		</div>
		"""

	conn.close()	

	if current_user:
		auth_html = f"""
		<p>Logged in as <b>{current_user}</b> | <a href="/logout">Logout</a></p>
		<form method="post" action="/post">
			<textarea name="content" placeholder="What's happening?" required
				style="width:100%; padding:10px; height:90px;"></textarea>
			<button type="submit" style="padding:10px 20px; margin-top:10px;">Post</button>
		</form>
		"""
	
	else:
		auth_html = """
		<p><a href="/login">Login</a> | <a href="/register">Register</a></p>
		<p>You must log in to create posts.</p>
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

        <p>Social platform running on AWS + Nginx + FastAP + SQLite + Login System</p>
	{auth_html}
	<hr>
        {feed_html}
    </body>
    </html>
    """

@app.get("/register", response_class=HTMLResponse)
def register_page():
	return """
	<body style="font-family:Arial; background:#111; color:white; max-width:500px; margin:auto; padding:20px;">
		<h1>Register</h1>
		<form method="post" action="/register">
			<input name="username" placeholder="Username" required style="width:100%; padding:10px; margin-bottom:10px;">
			<input name="password" type="password" placeholder="Password" required maxlength="72" style="width:100%; padding:10px; margin-bottom:10px;">
			<button type="submit">Register</button>
		</form>
		<p><a href="/">Home</a></p>
	</body>
	"""

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
	
	if len(password.encode("utf-8")) > 72:
		return HTMLResponse(
			"<h1>Password too long</h1>"
			"<p>Please use a password under 72 characters.</p>"
			"<a href='/register'>Try again</a>"
		)



	password_hash = hash_password(password)

	conn = sqlite3.connect("cloudsocial.db", timeout=10)
	cursor = conn.cursor()

	try:
		cursor.execute(
			"""INSERT INTO users (username, password_hash) VALUES (?, ?)""",
			(username, password_hash)
		)
		conn.commit()
	except sqlite3.IntegrityError:
		conn.close()
		return HTMLResponse("<h1>Username already exists</h1><a href='/register'>Try again</a>")
		
	conn.close()
	return RedirectResponse("/login", status_code=303)	

@app.get("/login", response_class=HTMLResponse)
def login_page():
	return """
	<body style="font-family:Arial; background:#111; color:white; max-width:500px; margin:auto; padding:20px;">
		<h1>Login</h1>
		<form method="post" action="/login">
			<input name="username" placeholder="Username" required style="width:100%; padding:10px; margin-bottom:10px;">
			<input name="password" type="password" placeholder="Password" required maxlength="72" style="width:100%; padding:10px; margin-bottom:10px;">
			<button type="submit">Login</button>
		</form>
		<p><a href="/">Home</a></p>
	</body>
	"""

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
	conn = sqlite3.connect("cloudsocial.db", timeout=10)
	cursor = conn.cursor()
	cursor.execute("""SELECT password_hash FROM users WHERE username = ?""", (username,))
	user = cursor.fetchone()
	conn.close()


	if not user or hash_password(password) !=  user[0]:
		return HTMLResponse("<h1>Invalid login</h1><a href='/login'>Try again</a>")

	request.session["username"] = username
	return RedirectResponse("/", status_code=303)

@app.get("/logout")
def logout(request: Request):
	request.session.clear()
	return RedirectResponse("/", status_code=303)


@app.get("/post")
def post_redirect():
	return RedirectResponse("/", status_code=303)


@app.post("/post")
def create_post(request: Request, content: str = Form(...)):
	username = request.session.get("username")

	if not username:
		return RedirectResponse("/login", status_code=303)


	with sqlite3.connect("cloudsocial.db", timeout=10) as conn:
		cursor = conn.cursor()
		cursor.execute(
			"INSERT INTO posts (username, content) VALUES (?, ?)",
			(username, content)

		)
		conn.commit()	



	return RedirectResponse("/", status_code=303)


@app.post("/like/{post_id}")
def like_post(request: Request, post_id: int):
	username = request.session.get("username")

	if not username:
		return RedirectResponse("/login", status_code=303)

	conn = sqlite3.connect("cloudsocial.db", timeout=10)
	cursor = conn.cursor()

	cursor.execute(
		"SELECT id FROM likes WHERE post_id = ? AND username = ?",
		(post_id, username)	
	)

	existing_like = cursor.fetchone()

	if existing_like:
		cursor.execute(
			"DELETE FROM likes WHERE post_id = ? AND username = ?",
			(post_id, username)
		)
	else:
		cursor.execute(
			"INSERT INTO likes (post_id, username) VALUES (?, ?)",
			(post_id, username)
		)	

	conn.commit()
	conn.close()

	return RedirectResponse("/", status_code=303)


@app.post("/delete/{post_id}")
def delete_post(request: Request, post_id: int):
	username = request.session.get("username")

	if not username:
		return RedirectResponse("/login", status_code=303)

	conn = sqlite3.connect("cloudsocial.db", timeout=10)
	cursor = conn.cursor()

	cursor.execute(
		"DELETE FROM posts WHERE id = ? AND username = ?",	
		(post_id, username)	
	)

	cursor.execute(
		"DELETE FROM likes WHERE post_id = ?",
		(post_id,)
	)
	
	conn.commit()
	conn.close()

	return RedirectResponse("/", status_code=303)
