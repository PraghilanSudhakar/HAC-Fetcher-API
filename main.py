from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from fastapi.middleware.cors import CORSMiddleware
import pickle
import os

app = FastAPI()

# Configure CORS
origins = [
    "http://127.0.0.1:5500",  # Replace with the origin of your HTML file
    "http://localhost:5500",  # Add additional origins if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Credentials(BaseModel):
    username: str
    password: str

def save_cookies(session, filename):
    with open(filename, 'wb') as file:
        pickle.dump(session.cookies, file)

def load_cookies(session, filename):
    with open(filename, 'rb') as file:
        session.cookies = pickle.load(file)

def login(username, password):
    login_data = {
        '__RequestVerificationToken': '',
        'SCKTY00328510CustomEnabled': True,
        'SCKTY00436568CustomEnabled': True,
        'Database': 10,
        'VerificationOption': 'UsernamePassword',
        'LogOnDetails.UserName': username,
        'tempUN': '',
        'tempPW': '',
        'LogOnDetails.Password': password
    }

    link = "https://homeaccess.katyisd.org/"
    ses = requests.Session()
    login_url = link + "HomeAccess/Account/LogOn"
    cookies_file = 'cookies.pkl'

    if os.path.isfile(cookies_file):
        # Load cookies from file
        load_cookies(ses, cookies_file)
        # Attempt authentication with loaded cookies
        r = ses.get(link)
        if 'LogOn?logonError=true' in r.url:
            print("Authentication with saved cookies failed. Deleting the cookie file and logging in with username and password...")
            os.remove(cookies_file)
        else:
            print("Authentication with saved cookies successful")
            return ses

    r = ses.get(login_url)
    soup = BeautifulSoup(r.content, 'lxml')
    login_data['__RequestVerificationToken'] = soup.find('input', attrs={'name': '__RequestVerificationToken'})['value']
    post = ses.post(login_url, data=login_data)

    if post.url == login_url:
        print("Authentication with username and password failed")
        return None

    save_cookies(ses, cookies_file)
    print("Authentication with username and password successful")
    return ses

def get_student_info(ses):
    student_info = {}

    link = "https://homeaccess.katyisd.org/"

    registration_url = link + "HomeAccess/Content/Student/Registration.aspx"
    r = ses.get(registration_url)
    soup = BeautifulSoup(r.content, 'lxml')

    if soup.find('span', {'id': 'plnMain_lblRegStudentName'}) is not None:
        # Get student name
        name = soup.find('span', {'id': 'plnMain_lblRegStudentName'}).text.strip()
        student_info['name'] = name

        # Get student grade level
        grade_level = soup.find('span', {'id': 'plnMain_lblGrade'}).text.strip()
        student_info['grade_level'] = grade_level

        # Get student school
        school = soup.find('span', {'id': 'plnMain_lblBuildingName'}).text.strip()
        student_info['school'] = school

        # Get student date of birth
        dob = soup.find('span', {'id': 'plnMain_lblBirthDate'}).text.strip()
        student_info['dob'] = dob

        # Get student counselor
        counselor = soup.find('span', {'id': 'plnMain_lblCounselor'}).text.strip()
        student_info['counselor'] = counselor

        # Get student language
        language = soup.find('span', {'id': 'plnMain_lblLanguage'}).text.strip()
        student_info['language'] = language

        # Get student cohort year
        cohort_year = soup.find('span', {'id': 'plnMain_lblCohortYear'}).text.strip()
        student_info['cohort_year'] = cohort_year

        return student_info
    else:
        return None
    
# Modify the get_student_grades function

def get_student_grades(ses):
    student_grades = []

    link = "https://homeaccess.katyisd.org/"
    grades_url = link + "HomeAccess/Content/Student/Assignments.aspx"
    r = ses.get(grades_url)
    soup = BeautifulSoup(r.content, 'lxml')

    assignment_classes = soup.find_all('div', class_='AssignmentClass')
    for ac in assignment_classes:
        class_name = ac.find('a', class_='sg-header-heading').text.strip()[12:]
        class_average = ac.find('span', class_='sg-header-heading sg-right').text.strip()  # Extract class average

        # Navigate to the sg-asp-table table
        table = ac.find('table', class_='sg-asp-table')

        # Find all the rows within the table
        rows = table.find_all('tr', {'class': 'sg-asp-table-data-row'})
        for row in rows:
            cols = row.find_all('td')[:6]
            date_due = cols[0].text.strip()
            date_assigned = cols[1].text.strip()
            assignment = cols[2].text.strip().replace('\r\n', '').replace('\n*', '').strip()
            category = cols[3].text.strip()
            score = cols[4].text.strip()
            total_points = cols[5].text.strip()
            grade_entry = {
                'Class Name': class_name,
                'Class Average': class_average, 
                'Date Due': date_due,
                'Date Assigned': date_assigned,
                'Assignment': assignment,
                'Category': category,
                'Score': score,
                'Total Points': total_points
            }
            student_grades.append(grade_entry)

    return student_grades


@app.post("/api/login")
def api_login(credentials: Credentials):
    ses = login(credentials.username, credentials.password)
    if ses:
        student_info = get_student_info(ses)
        student_grades = get_student_grades(ses)
        return {"student_info": student_info, "student_grades": student_grades}
    else:
        raise HTTPException(status_code=401, detail="Login failed")
    
@app.get("/")
def root():
    return {"message": "API is running"}
