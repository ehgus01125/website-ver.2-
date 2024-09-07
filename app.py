from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import sys

import pymysql.cursors

app = Flask(__name__)
app.secret_key = 'ddd'
def connect_db():
    return pymysql.connect(host='localhost', user='root', db='notice',charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

def init_db():
    db = pymysql.connect(host='localhost', user='root', charset='utf8mb4')
    try:
        with db.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS notice")
            cursor.execute("USE notice")
            cursor.execute("CREATE TABLE IF NOT EXISTS User (id INTEGER AUTO_INCREMENT PRIMARY KEY, username VARCHAR(10) NOT NULL UNIQUE, password VARCHAR(20) NOT NULL)")
            cursor.execute("SELECT * FROM User WHERE username = 'admin'")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO User (id, username, password) VALUES (1,'admin','admin')")
                db.commit()
            cursor.execute("CREATE TABLE IF NOT EXISTS Post (Post_id INTEGER AUTO_INCREMENT PRIMARY KEY, title VARCHAR(100) NOT NULL, content TEXT NOT NULL, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_id INTEGER, view INTEGER DEFAULT 0, FOREIGN KEY (user_id) REFERENCES User(id))")
    except Exception as e:
        print(f"오류 \n{e}")
        sys.exit()
    finally:
        db.close()

def king(user_id):
    db = connect_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT username FROM User WHERE id = %s", (user_id,))
    user=cursor.fetchone()
    db.close()
    return user and user['username'] == 'admin'

def find_user(username):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM User WHERE username = %s", (username,))
    user = cursor.fetchone()
    db.close()
    if user:
        return user
    else : 
        return None


def check_password(username, password):
    user = find_user(username)
    if user and user['password'] == password:
        return True
    return False

@app.route("/", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            return render_template("index.html", message="제대로 입력해주세요.")
        
        if check_password(username, password):
            user = find_user(username)
            session['user_id'] = user['id']
            return redirect(url_for('post'))
        else:
            return render_template("index.html", message="로그인 실패")
    return render_template("index.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    message = ""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = find_user(username)
        if existing_user:
            message = "이미 존재합니다."
        else:
            try:
                db =connect_db()
                cursor = db.cursor()
                cursor.execute("INSERT INTO User (username, password) VALUES (%s, %s)", (username, password))
                db.commit()
                message = "회원가입이 되었습니다."
                return redirect(url_for('login'))
            except Exception as e:
                db.rollback()
                message = f"회원가입 실패: {str(e)}"
            finally:
                db.close()
    return render_template("register.html", message=message)

@app.route("/post")
def post():
    try:
        if 'user_id' not in session:
            return redirect(url_for('login'))
        db = connect_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM User WHERE id = %s", (session['user_id'],))
        current_user = cursor.fetchone()
        cursor.execute("SELECT Post.Post_id, Post.user_id, Post.title, User.username, Post.time, Post.view FROM Post JOIN User ON Post.user_id = User.id ORDER BY Post.time DESC")
        posts = cursor.fetchall()
        return render_template("post.html", current_user=current_user, posts=posts)
    except Exception as e:
        print(e)
        return "error", 500
    finally:
        db.close()

@app.route("/search",methods=['GET', 'POST'])
def search():
    search_len = 0
    search_type = request.args.get('search_type','title')
    search_db= request.args.get('search_db','').strip()
    if not search_db:
        return redirect(url_for('post'))
    try:
        db = connect_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM User WHERE id = %s", (session['user_id'],))
        current_user = cursor.fetchone()

        if search_type == 'all':
            cursor.execute("SELECT Post.Post_id, Post.title, User.username, Post.time, Post.view FROM Post JOIN User ON Post.user_id = User.id WHERE Post.title LIKE %s OR User.username LIKE %s OR Post.content LIKE %s ORDER BY Post.time DESC", (f'%{search_db}%', f'%{search_db}%', f'%{search_db}%'))
        elif search_type == 'title':
            cursor.execute("SELECT Post_id, Post.title, User.username, Post.time, Post.view FROM Post Join User ON Post.user_id = User.id WHERE Post.title LIKE %s ORDER BY time DESC", (f'%{search_db}%',))
        elif search_type == 'content':
            cursor.execute("SELECT Post.Post_id, Post.title, User.username, Post.time, Post.view FROM Post JOIN User ON Post.user_id = User.id WHERE Post.content LIKE %s ORDER BY Post.time DESC", (f'%{search_db}%',))
        elif search_type == 'writeman':
            cursor.execute("SELECT Post_id, Post.title, User.username, Post.time, Post.view FROM Post Join User ON Post.user_id = User.id WHERE User.username LIKE %s ORDER BY Post.time DESC", (f'%{search_db}%',))
        posts = cursor.fetchall()
        search_len=len(posts)
    except Exception as e:
        return "error", 500
    finally:
        db.close()
        return render_template("post.html", posts=posts, search_db = search_db, search_type = search_type, search_len=search_len, current_user=current_user)
    
@app.route("/create_post",methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('create_post.html')

    if request.method == 'POST':
        try:
            db = connect_db()
            cursor = db.cursor()
            create_title = request.form.get('title','')
            create_content = request.form.get('content','')
    
            cursor.execute("INSERT INTO Post(title, content, user_id) VALUES (%s, %s, %s)", (create_title, create_content, session['user_id']))
            db.commit()
            return redirect(url_for('post'))
        except Exception as e:
            db.rollback()
            print(e)
            return "error", 500

        finally:
            db.close()     

@app.route("/post/<int:Post_id>", methods=['GET'])
def read_post(Post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        db = connect_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT Post.*, User.username FROM Post JOIN User ON Post.user_id = User.id WHERE Post.Post_id = %s", (Post_id,))
        post = cursor.fetchone()
        cursor.execute("UPDATE Post SET view = view + 1 WHERE Post_id = %s", (Post_id,))
        db.commit()
        current_user=session['user_id']
        admin = king(current_user)
        return render_template("read_post.html", post=post, current_user=current_user, king = admin)
    except Exception as e:
        print(e)
        return "error", 400
    finally:
        db.close()

@app.route("/post/<int:Post_id>/edit", methods=['GET','POST'])
def edit_post(Post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = connect_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Post WHERE Post_id = %s", (Post_id,))
    post = cursor.fetchone()

    if post['user_id'] != session['user_id']:
        db.close()
        return render_template('edit_post.html', error_message="수정 할 수 없습니다.")
 
    if request.method =='POST':
        title=request.form['title']
        content=request.form['content']
        if not title or not content:
            return render_template('edit_post.html', post=post, error_message="빈칸이 있습니다.")

        cursor.execute("UPDATE Post SET title = %s, content = %s WHERE Post_id =%s",(title, content, Post_id))
        db.commit()
        db.close()
        return redirect(url_for('post', Post_id=Post_id))
    db.close()
    return render_template('edit_post.html', post=post)
    
@app.route("/post/<int:Post_id>/delete", methods=['POST'])
def delete_post(Post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        db = connect_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM Post WHERE Post_id = %s", (Post_id,))
        post = cursor.fetchone()
        if post:
            if post['user_id'] == session['user_id'] or king(session['user_id']):
                cursor.execute("DELETE FROM Post WHERE Post_id = %s", (Post_id,))
                db.commit()
                return redirect(url_for("post"))
    except Exception as e:
        print(e)
    finally:
        db.close()


    #삭제 만들기
            # 관리자 페이지 만들어서 삭제하기
            # sql인젝션, crsf 필터링 만들기
            #  


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)