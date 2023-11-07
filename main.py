from flask import Flask, session, flash, redirect, url_for, render_template, request, Response
from functools import wraps
from flask_pymongo import MongoClient
from pymongo.server_api import ServerApi
from hashlib import sha256
import nmap, socket, datetime, pandas as pd, time, os
from getmac import get_mac_address
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(2)

nm = nmap.PortScanner()

ip = socket.gethostbyname(socket.gethostname())+"/24"

app = Flask(__name__)
app.config["SECRET_KEY"]="SECRET"
mongo = MongoClient("mongodb+srv://nasaapplication:password123parthandnasaapplication@cluster0.kq6h2lm.mongodb.net/?retryWrites=true&w=majority", server_api=ServerApi('1'))

mongo = mongo["SSIP"]
Students = mongo.students
Courses = mongo.courses
Attendance = mongo.attendance
Admin = mongo.admin

def student_present(course):
    print("Start")
    ip_list = list(nm.scan(hosts=ip, arguments="-T4 -sn")["scan"].keys())
    for i in ip_list:
        mac = get_mac_address(ip=i)
        student = Students.find_one({"macID":mac})
        if student != None:
            a = {
            "roll":student["roll"],
            "course":course,
            "date": {
                "$gte": (pd.to_datetime(f"{datetime.datetime.now().year}-{datetime.datetime.now().month}-{datetime.datetime.now().day}")),
                '$lt': (pd.to_datetime(f"{datetime.datetime.now().year}-{datetime.datetime.now().month}-{datetime.datetime.now().day+1}"))
                }
                }
            if list(Attendance.find(a))==[]:
                Attendance.insert_one({"roll":student["roll"],"course":course, "date":datetime.datetime.now(), "status": "PRESENT"})
    print("End")
def getUserMac():
    ip_list = list(nm.scan(hosts=ip, arguments="-T4 -F -sn")["scan"].keys())
    for i in ip_list:
        mac = get_mac_address(ip=i)
        if mac != None and Students.count_documents({"macID":mac}) > 0:
            Students.find_one_and_update({"macID":mac})

# @app.get("/present/<course>")
# def present(course):
#     mac = get_mac_address(ip = request.remote_addr)
#     student_present(mac, course)

@app.get("/admin/login")
def login():
    return render_template("admin_login.html")

@app.post("/admin/login")
def login_post():
    email = request.form.get("email")
    passw = sha256(request.form.get("password").encode("ascii")).hexdigest()
    admin = Admin.find_one({"email":email, "pass":passw})
    if admin != None:
        session["admin"]=admin["adminID"]
        return redirect("/admin/dashboard")
    flash("wrong Email or Password!")
    return redirect("/admin/login")

@app.get("/admin/attendance")
def attendance():
    return render_template("attendance.html", courses = Courses.find())


@app.post("/admin/attendance")
def attendance_post():
    usr_course = request.form.get("course")
    t0 = time.time()
    student_present(usr_course)
    # os.system(f"python a.py {usr_course}")
    print(time.time() - t0)
    return render_template("attendance.html")

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def monthly_attendance():
    if request.method == 'POST':
        # Get selected month and year from the form
        month = int(request.form.get('month'))
        year = int(request.form.get('year'))

        # Fetch attendance records for the selected month and year
        start_date = f"{year}-{month}-01"
        end_date = f"{year}-{month + 1}-01" if int(month) < 12 else f"{int(year) + 1}-01-01"

        attendance_records = list(Attendance.find({
            'date': {'$gte': pd.to_datetime(start_date), '$lt': pd.to_datetime(end_date)}
        }))

        # Create a DataFrame from the MongoDB data
        df = pd.DataFrame(attendance_records)

        # Export DataFrame to Excel
        excel_filename = f"monthly_attendance_{month}_{year}.xlsx"
        df.to_excel(excel_filename, index=False)

        return render_template('admin_dashboard.html', attendance_records=attendance_records, excel_filename=excel_filename)

    return render_template('admin_dashboard.html')

@app.get("/create_course")
def course():
    return render_template("course.html")
@app.post("/create_course")
def course_post():
    mac = get_mac_address(ip = request.remote_addr)
    if Courses.count_documents({"courseID":request.form.get("courseID")}) != 0:
        flash("Course Already Registered!")
        return redirect("/create_course")
    Courses.insert_one({"courseID":request.form.get("courseID"),"course":request.form.get("name")})
    return redirect("/create_course")

@app.get("/")
def index():
    return render_template("students.html")
@app.post("/")
def index_post():
    mac = get_mac_address(ip = request.remote_addr)
    if Students.count_documents({"macID":mac}) != 0 or Students.count_documents({"email":request.form.get("email")}) != 0:
        flash("Student Already Registered!")
        return redirect("/")
    Students.insert_one({"macID":mac,"fname":request.form.get("fname"), "lname":request.form.get("lname"), "email":request.form.get("email"), "roll":request.form.get("roll"), "password":sha256(request.form.get("password").encode("ascii")).hexdigest(), "reg_date":datetime.datetime.now()})
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")