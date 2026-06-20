from fastapi import FastAPI, Form, Request 
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import hashlib
import os
import psycopg2

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="change-this-secret-key")

def hash_password(password):
	return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        database=os.getenv("DB_NAME", "cloudsocial"),
        user=os.getenv("DB_USER", "clouduser"),
        password=os.getenv("DB_PASSWORD", "cloudpass"),
         port=os.getenv("DB_PORT", "5432"),
    )
    

def init_db():
	conn = get_db_connection()
	cursor = conn.cursor()

	cursor.execute("""
		CREATE TABLE IF NOT EXISTS users(
		id SERIAL PRIMARY KEY,
		username TEXT UNIQUE NOT NULL,
		password_hash TEXT NOT NULL
		)
	""")

	
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS posts(
		id SERIAL PRIMARY KEY,
		username TEXT NOT NULL,
		content TEXT NOT NULL
		)
	""")

	cursor.execute("""
		CREATE TABLE IF NOT EXISTS likes(
		id SERIAL PRIMARY KEY,
		post_id INTEGER NOT NULL,
		username TEXT NOT NULL,
		UNIQUE(post_id, username)
		)
	""")

	cursor.execute("""
		CREATE TABLE IF NOT EXISTS comments(
		id SERIAL PRIMARY KEY,
		post_id INTEGER NOT NULL,
		username TEXT NOT NULL,
		content TEXT NOT NULL
		)
	""")

	conn.commit()
	conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
	current_user = request.session.get("username")

	conn = get_db_connection()
	cursor = conn.cursor()
	cursor.execute("SELECT id, username, content FROM posts ORDER BY id DESC")
	posts = cursor.fetchall()

	feed_html = ""
	for post_id, user, content in posts:
		cursor.execute("SELECT COUNT(*) FROM likes WHERE post_id = %s", (post_id,))
		like_count = cursor.fetchone()[0]

		cursor.execute(
			"""
			SELECT username, content
			FROM comments
			WHERE post_id = %s
			ORDER BY id
			""",
			(post_id,)
		)

		comments = cursor.fetchall()


		comments_html = ""

		for comment_user, comment_content in comments:
			comments_html += f"""
			<div style="margin-left:20px;">
				<b>{comment_user}</b>: {comment_content}
			</div>
			"""


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
		
		
		<hr>
	
		<form method="post" action="/comment/{post_id}">
			<input
				type="text"
				name="content"
				placeholder="Write a comment..."
				required>
			<button type="submit">Comment</button>
		</form>
		
		{comments_html}

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

	conn = get_db_connection()
	cursor = conn.cursor()

	try:
		cursor.execute(
			"""INSERT INTO users (username, password_hash) VALUES (%s, %s)""",
			(username, password_hash)
		)
		conn.commit()
	except psycopg2.errors.UniqueViolation:
		conn.rollback()
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
	conn = get_db_connection()
	cursor = conn.cursor()
	cursor.execute("""SELECT password_hash FROM users WHERE username = %s""", (username,))
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


	with get_db_connection() as conn:
		cursor = conn.cursor()
		cursor.execute(
			"INSERT INTO posts (username, content) VALUES (%s, %s)",
			(username, content)

		)
		conn.commit()	



	return RedirectResponse("/", status_code=303)


@app.post("/like/{post_id}")
def like_post(request: Request, post_id: int):
	username = request.session.get("username")

	if not username:
		return RedirectResponse("/login", status_code=303)

	conn = get_db_connection()
	cursor = conn.cursor()

	cursor.execute(
		"SELECT id FROM likes WHERE post_id = %s AND username = %s",
		(post_id, username)	
	)

	existing_like = cursor.fetchone()

	if existing_like:
		cursor.execute(
			"DELETE FROM likes WHERE post_id = %s AND username = %s",
			(post_id, username)
		)
	else:
		cursor.execute(
			"INSERT INTO likes (post_id, username) VALUES (%s, %s)",
			(post_id, username)
		)	

	conn.commit()
	conn.close()

	return RedirectResponse("/", status_code=303)

@app.post("/comment/{post_id}")
def add_comment(
	request: Request,
	post_id: int,
	content: str = Form(...)
):
	username = request.session.get("username")

	if not username:
		return RedirectResponse("/login", status_code=303)

	conn = get_db_connection()
	cursor = conn.cursor()

	cursor.execute(
		"""
		INSERT INTO comments
		(post_id, username, content)
		VALUES (%s, %s, %s)
		""",
		(post_id, username, content)
	)		

	conn.commit()
	conn.close()

	return RedirectResponse("/", status_code=303)

@app.post("/delete/{post_id}")
def delete_post(request: Request, post_id: int):
	username = request.session.get("username")

	if not username:
		return RedirectResponse("/login", status_code=303)

	conn = get_db_connection()
	cursor = conn.cursor()

	cursor.execute(
		"DELETE FROM posts WHERE id = %s AND username = %s",	
		(post_id, username)	
	)

	cursor.execute(
		"DELETE FROM likes WHERE post_id = %s",
		(post_id,)
	)
	
	conn.commit()
	conn.close()

	return RedirectResponse("/", status_code=303)
