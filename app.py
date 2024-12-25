from flask import Flask,request,render_template,redirect,url_for,flash,session,send_file
import mysql.connector
from otp import genotp
from cmail import sendmail
from stoken import encode,decode
from flask_session import Session
import flask_excel as excel
import re
from io import BytesIO
app=Flask(__name__)
excel.init_excel(app)
app.config['SESSION_TYPE']='filesystem'
app.secret_key='parvez aslam'
mytdb=mysql.connector.connect(host='localhost',user='root',password='Parvez@123#',db='snmproject')
Session(app)
@app.route('/')
def home():
    return render_template('welcome.html')
@app.route('/create',methods=['GET','POST'])
def create():
    if request.method=='POST':
        print(request.form)
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']
        cpassword=request.form['cpassword']
        cursor=mytdb.cursor()
        cursor.execute('select count(useremail) from users where useremail=%s',[email])
        result=cursor.fetchone()
        print(result)
        if result[0]==0:
            gotp=genotp()
            udata={'username':username,'email':email,'password':password,'otp':gotp}
            print(gotp)
            subject='OTP For Simple Notes Manager'
            body=f'otp for registration of simple notes manager {gotp} '
            sendmail(to=email,subject=subject,body=body)
            flash('OTP has to given Mail.')
            return redirect(url_for('otp',enudata=encode(data=udata)))
        elif result[0]>0:
            flash('email already existed')
            return redirect(url_for('login'))
        else:
            return 'Something Wrong'
    return render_template('create.html')
@app.route('/otp/<enudata>',methods=['GET','POST'])
def otp(enudata):
    if request.method=='POST':
        eotp=request.form['otp']
        try:
            dudata=decode(data=enudata)
        except Exception as e:
            print(e)
            return 'something went wrong'
        else:
            if dudata['otp']==eotp:
                cursor=mytdb.cursor()
                cursor.execute('insert into users(username,useremail,password) values(%s,%s,%s)',[dudata['username'],dudata['email'],dudata['password']])
                mytdb.commit()
                cursor.close()
                flash('registration Successful')
                return redirect(url_for('login'))
            else:
                return 'otp was wrong pls register again'
    return render_template('otp.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=="POST":
        email=request.form['email']
        password=request.form['password']
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select count(useremail) from users where useremail=%s',[email])
        bdata=cursor.fetchone() 
        if bdata[0]==1:
            cursor.execute('select password from users where useremail=%s',[email])
            bpassword=cursor.fetchone() 
            if password==bpassword[0].decode('utf-8'):
                print(session)
                session['user']=email
                print(session)
                return redirect(url_for('dashboard'))
            else:
                flash('password is wrong')
                return redirect(url_for('login'))
        elif bdata[0]==0:
            flash('email not existed')
            return redirect(url_for('create'))
        else:
            return 'something went wrong'
    return render_template('login.html')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')
@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    if request.method=='POST':
        title=request.form['title']
        description=request.form['description']
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select userid from users where useremail=%s',[session.get('user')])
        uid=cursor.fetchone()
        print(uid)
        if uid:
            try:
                cursor.execute('insert into notes(title,ndescription,userid) values(%s,%s,%s)',[title,description,uid[0]])
                mytdb.commit()
                cursor.close()
            except mysql.connector.errors.IntegrityError:
                flash('Duplicate Title Entry')
                return redirect(url_for('dashboard'))
            except mysql.connector.errors.ProgrammingError:
                flash('could not add notes')
                print(mysql.connector.errors.ProgrammingError)
                return redirect(url_for('dashboard'))
            else:
                flash('Notes Added Successfully')
                return redirect(url_for('dashboard'))
        else:
            return 'Something Went Wrong'
    return render_template('addnotes.html')

@app.route('/viewallnotes')
def viewallnotes():
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select userid from users where useremail=%s',[session.get('user')])
        uid=cursor.fetchone()
        cursor.execute('select nid,title,create_at from notes where userid=%s',[uid[0]])
        ndata=cursor.fetchall()
    except Exception as e:
        print(e)
        flash('no data found')
        return redirect(url_for('dashboard'))
    else:
        return render_template('viewallnotes.html',ndata=ndata)

@app.route('/viewnotes/<nid>')
def viewnotes(nid):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select * from notes where nid=%s',[nid])
        ndata=cursor.fetchone()
    except Exception as e:
        print(e)
        flash('No data found')
        return redirect(url_for('dashboard'))
    else:
        return render_template('viewnotes.html',ndata=ndata)
@app.route('/updatenotes/<nid>',methods=['GET','POST'])
def updatenotes(nid):
    cursor=mytdb.cursor(buffered=True)
    cursor.execute('select *from notes where nid=%s',[nid])
    ndata=cursor.fetchone()
    if request.method=='POST':
        title=request.form['title']
        description=request.form['description']
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('update notes set title=%s,ndescription=%s where nid=%s',[title,description,nid])
        mytdb.commit()
        cursor.close()
        flash('notes updated successfully')
        return redirect(url_for('viewnotes',nid=nid))
    return render_template('updatenotes.html',ndata=ndata)
@app.route('/deletenotes/<nid>')
def deletenotes(nid):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('delete from notes where nid=%s',[nid])
        mytdb.commit()
        cursor.close()
    except Exception as e:
        print(e)
        flash('could not delete notes')
        return redirect(url_for('viewallnotes'))
    else:
        flash('notes deleted sucessfully')
        return redirect(url_for('viewallnotes'))

@app.route('/uploadfiles',methods=['GET','POST'])
def uploadfiles():
    if request.method=='POST':
        filedata=request.files['file']
        fname=filedata.filename
        fdata=filedata.read()
        try:
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select userid from users where useremail=%s',[session.get('user')])
            uid=cursor.fetchone()
            cursor.execute('insert into filedata(filename,fdata,added_by) values(%s,%s,%s)',[fname,fdata,uid[0]])
            mytdb.commit()
        except Exception as e:
            print(e)
            flash("couldn't upload file" )
            return redirect(url_for('dashboard'))
        else:
            flash('file uploaded successfully')
            return redirect(url_for('dashboard'))
    return render_template('fileupload.html')

@app.route('/allfiles')
def allfiles():
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select userid from users where useremail=%s',[session.get('user')])
        uid=cursor.fetchone()
        cursor.execute('select fid,filename,create_at from filedata where added_by=%s',[uid[0]])
        filedata=cursor.fetchall()
    except Exception as e:
        print(e)
        flash('No Data Found')
        return redirect(url_for('dashboard'))
    else:
        return render_template('allfiles.html',filedata=filedata)

@app.route('/viewfiles/<fid>')
def viewfiles(fid):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select filename,fdata from filedata where fid=%s',[fid])
        fdata=cursor.fetchone()
        bytes_data=BytesIO(fdata[1])
        return send_file(bytes_data,download_name=fdata[0],as_attachment=False)
    except Exception as e:
        print(e)
        flash("couldn't open the file")
        return redirect(url_for('dashboard'))

@app.route('/downloadfiles/<fid>')
def downloadfiles(fid):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select filename,fdata from filedata where fid=%s',[fid])
        fdata=cursor.fetchone()
        bytes_data=BytesIO(fdata[1])
        return send_file(bytes_data,download_name=fdata[0],as_attachment=True)
    except Exception as e:
        print(e)
        flash("couldn't open the file")
        return redirect(url_for('dashboard'))

@app.route('/delete/<fid>')
def delete(fid):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('delete from filedata where fid=%s',[fid])
        mytdb.commit()
        cursor.close()
    except Exception as e:
        print(e)
        flash('could not delete notes')
        return redirect(url_for('allfiles'))
    else:
        flash('file deleted sucessfully')
        return redirect(url_for('allfiles'))

@app.route('/getexceldata')
def getexceldata():
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select userid from users where useremail=%s',[session.get('user')])
        uid = cursor.fetchone()
        cursor.execute('select nid,title,ndescription,create_at from notes where userid=%s',[uid[0]])
        ndata=cursor.fetchall()
    except Exception as e:
        print(e)
        flash('No data found')
        return redirect(url_for('dashboard'))
    else:
        array_data = [list(i) for i in ndata]
        columns = ['Notesid','Title','Context','Creted_Time']
        array_data.insert(0,columns)
        return excel.make_response_from_array(array_data,'xlsx',filename='notesdata')
@app.route('/logout')
def logout():
    if session.get('user'):
        if session.get('user'):
            session.pop('user')
            return redirect(url_for('home'))
        else:
            return redirect(url_for('login'))
    else:
        return render_template(url_for('login'))
@app.route('/search',methods=['GET','POST'])
def search():
    if session.get('user'):
        try:
            if request.method=='POST':
                sdata=request.form['sname']
                strg=['A-Za-z0-9']
                pattern=re.compile(f'^{strg}',re.IGNORECASE)
                if (pattern.match(sdata)):
                    cursor=mytdb.cursor(buffered=True)
                    cursor.execute('select * from notes where nid like %s or title like %s or ndescription like %s or create_at like %s',[sdata+'%',sdata+'%',sdata+'%',sdata+'%'])
                    sdata=cursor.fetchall()
                    cursor.close()
                    return render_template('dashboard.html',sdata=sdata)
                else:
                    flash('No Data Found')
                    return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('dashboard'))
        except Exception as e:
            print(e)
            flash("can't find anything")
            return redirect(url_for('dashboard'))
    else:
        return render_template(url_for('login'))
app.run(use_reloader=True,debug=True)