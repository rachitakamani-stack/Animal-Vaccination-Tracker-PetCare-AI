import os
from functools import wraps

import mysql.connector
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_mail import Mail, Message 
from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)
from werkzeug.utils import secure_filename

app = Flask(__name__)

# =========================
# Email Configuration
# =========================

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "rachitakamani@gmail.com"
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")

mail = Mail(app)
app.secret_key = os.environ.get("SECRET_KEY", "")


# =========================
# MySQL Configuration
# =========================

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "petcare_db"

# =========================
# Email Reminder Settings
# =========================

REMINDER_DAYS = 2


# =========================
# Database Connection
# =========================

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# =========================
# Send Vaccination Reminder Email
# =========================

def send_vaccination_reminder_email(
    email,
    pet_name,
    vaccine_name,
    due_date
):
    try:

        msg = Message(
            subject="PetCare AI - Vaccination Reminder",
            sender=app.config["MAIL_USERNAME"],
            recipients=[email]
        )

        msg.body = f"""
Hello,

This is a reminder from PetCare AI.

Your pet {pet_name}'s vaccination is due on {due_date}.

Vaccine: {vaccine_name}

This reminder is being sent 2 days before the vaccination due date.

Please contact a qualified veterinarian for the appropriate vaccination schedule.

Regards,
PetCare AI Team
"""

        mail.send(msg)

        print(
            f"Reminder email sent to {email} "
            f"for {pet_name} - {vaccine_name}"
        )

        return True

    except Exception as error:

        print("Email sending failed:")
        print(error)

        return False

# =========================
# Check Vaccination Reminders
# =========================

def check_vaccination_reminders():
    from datetime import date, timedelta

    target_date = date.today() + timedelta(days=REMINDER_DAYS)

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                u.email,
                p.pet_name,
                v.vaccine_name,
                v.next_due_date
            FROM vaccinations v
            JOIN users u
                ON v.user_id = u.id
            JOIN pets p
                ON v.pet_id = p.id
            WHERE v.next_due_date = %s
        """, (target_date,))

        reminders = cursor.fetchall()

        cursor.close()
        db.close()

        for reminder in reminders:
            with app.app_context():
                send_vaccination_reminder_email(
                    reminder["email"],
                    reminder["pet_name"],
                    reminder["vaccine_name"],
                    reminder["next_due_date"]
                )

    except Exception as error:
        print("Reminder check failed:")
        print(error)

# =========================
# Initialize Database
# =========================

def init_db():

    try:

        # Connect to MySQL
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = conn.cursor()

        # Create database
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"
        )

        cursor.close()
        conn.close()

        # Connect to PetCare database
        conn = get_db_connection()
        cursor = conn.cursor()

        


        # =========================
        # Users Table
        # =========================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # =========================
        # Contact Messages Table
        # =========================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL,
                phone VARCHAR(20),
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # =========================
        # Pets Table
        # =========================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                pet_name VARCHAR(100) NOT NULL,
                pet_type VARCHAR(50) NOT NULL,
                breed VARCHAR(100),
                age INT,
                weight DECIMAL(6,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
            )
        """)

        # =========================
        # Vaccinations Table
        # =========================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vaccinations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                pet_id INT NOT NULL,
                vaccine_name VARCHAR(150) NOT NULL,
                vaccination_date DATE NOT NULL,
                next_due_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

                FOREIGN KEY (pet_id)
                REFERENCES pets(id)
                ON DELETE CASCADE
            )
        """)

        # =========================
        # Health Records Table
        # =========================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                pet_id INT NOT NULL,
                record_date DATE NOT NULL,
                record_type VARCHAR(100) NOT NULL,
                details TEXT NOT NULL,
                report_file VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

                FOREIGN KEY (pet_id)
                REFERENCES pets(id)
                ON DELETE CASCADE
            )
        """)

        # -----------------------------
        # Add report_file column if missing
        # -----------------------------
        cursor.execute("""
            SHOW COLUMNS FROM health_records
            LIKE 'report_file'
        """)

        report_column = cursor.fetchone()

        if not report_column:
            cursor.execute("""
                ALTER TABLE health_records
                ADD COLUMN report_file VARCHAR(255) NULL
            """)
        conn.commit()

        cursor.close()
        conn.close()

        print("================================")
        print("Database connected successfully!")
        print("PetCare AI database is ready.")
        print("================================")

    except mysql.connector.Error as error:

        print("Database Error:")
        print(error)




# =========================
# Login Required
# =========================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login first.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return wrapper


# =========================
# Home Page
# =========================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================
# Register
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "error"
            )

            return render_template(
                "register.html"
            )

        hashed_password = generate_password_hash(
            password
        )

        try:

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO users
                (name, email, password)
                VALUES (%s, %s, %s)
                """,
                (
                    name,
                    email,
                    hashed_password
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

            flash(
                "Registration successful! Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except mysql.connector.Error as error:

            print(error)

            if error.errno == 1062:

                flash(
                    "Email already registered.",
                    "error"
                )

            else:

                flash(
                    "Registration failed. Please try again.",
                    "error"
                )

            return render_template(
                "register.html"
            )

    return render_template(
        "register.html"
    )

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == os.environ.get("ADMIN_USERNAME", "admin") and password == os.environ.get("ADMIN_PASSWORD", ""):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin username or password.")

    return render_template("admin_login.html")


# =========================
# Admin Dashboard
# =========================

@app.route("/admin")
def admin_dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Total Users
    cursor.execute(
        "SELECT COUNT(*) AS total FROM users"
    )
    total_users = cursor.fetchone()["total"]

    # Total Pets
    cursor.execute(
        "SELECT COUNT(*) AS total FROM pets"
    )
    total_pets = cursor.fetchone()["total"]

    # Total Vaccinations
    cursor.execute(
        "SELECT COUNT(*) AS total FROM vaccinations"
    )
    total_vaccinations = cursor.fetchone()["total"]

    # Total Health Records
    cursor.execute(
        "SELECT COUNT(*) AS total FROM health_records"
    )
    total_health_records = cursor.fetchone()["total"]

    # All Users
    cursor.execute("""
        SELECT
            id,
            name,
            email
        FROM users
        ORDER BY id DESC
    """)

    users = cursor.fetchall()

    # All Health Reports
    cursor.execute("""
        SELECT
            h.id,
            u.name AS user_name,
            u.email AS user_email,
            p.pet_name,
            p.pet_type,
            h.record_type,
            h.record_date,
            h.details,
            h.report_file
        FROM health_records h
        JOIN users u
            ON h.user_id = u.id
        JOIN pets p
            ON h.pet_id = p.id
        ORDER BY h.record_date DESC
    """)

    health_reports = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_pets=total_pets,
        total_vaccinations=total_vaccinations,
        total_health_records=total_health_records,
        users=users,
        health_reports=health_reports
    )


# =========================
# Admin - Users
# =========================

@app.route("/admin/users")
def admin_users():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            created_at
        FROM users
        ORDER BY id DESC
    """)

    users = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_users.html",
        users=users
    )

# =========================
# Admin - Pets
# =========================

@app.route("/admin/pets")
def admin_pets():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            p.id,
            p.pet_name,
            p.pet_type,
            p.breed,
            p.age,
            p.weight,
            u.name AS user_name,
            u.email AS user_email
        FROM pets p
        JOIN users u
            ON p.user_id = u.id
        ORDER BY p.id DESC
    """)

    pets = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_pets.html",
        pets=pets
    )   

# =========================
# Admin - Vaccinations
# =========================

@app.route("/admin/vaccinations")
def admin_vaccinations():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            v.id,
            u.name AS user_name,
            u.email AS user_email,
            p.pet_name,
            p.pet_type,
            v.vaccine_name,
            v.vaccination_date,
            v.next_due_date,
            v.notes
        FROM vaccinations v
        JOIN users u
            ON v.user_id = u.id
        JOIN pets p
            ON v.pet_id = p.id
        ORDER BY v.vaccination_date DESC
    """)

    vaccinations = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_vaccinations.html",
        vaccinations=vaccinations
    )

# =========================
# Admin - Health Reports
# =========================

@app.route("/admin/health-reports")
def admin_health_reports():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            h.id,
            u.name AS user_name,
            u.email AS user_email,
            p.pet_name,
            p.pet_type,
            h.record_date,
            h.record_type,
            h.details,
            h.report_file
        FROM health_records h
        JOIN users u
            ON h.user_id = u.id
        JOIN pets p
            ON h.pet_id = p.id
        ORDER BY h.record_date DESC
    """)

    health_reports = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_health_reports.html",
        health_reports=health_reports
    )

@app.route("/admin-logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


# Admin Login Check

# =========================
# Login
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    # Check whether the login form was submitted
    if request.method == "POST":

        # Get email from the login form
        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        # Get password from the login form
        password = request.form.get(
            "password",
            ""
        )

        # Check if email or password is empty
        if not email or not password:

            flash(
                "Email and password are required.",
                "error"
            )

            return render_template(
                "login.html"
            )

        # =========================
        # Admin Login Check
        # =========================
        # Check admin email and password
        if email == os.environ.get("ADMIN_EMAIL", "admin@petcareai.com") and password == os.environ.get("ADMIN_PASSWORD", ""):

            # Store admin login status in session
            session["admin_logged_in"] = True

            # Open Admin Dashboard
            return redirect(
                url_for("admin_dashboard")
            )

        # =========================
        # Normal User Login
        # =========================

        try:

            # Connect to MySQL database
            conn = get_db_connection()

            # Create database cursor
            cursor = conn.cursor(
                dictionary=True
            )

            # Find user by email
            cursor.execute(
                """
                SELECT id, name, email, password
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            # Get user data
            user = cursor.fetchone()

            # Close cursor and database connection
            cursor.close()
            conn.close()

            # Check user password
            if user and check_password_hash(
                user["password"],
                password
            ):

                # Store user information in session
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]

                # Show successful login message
                flash(
                    "Login successful!",
                    "success"
                )

                # Open normal User Dashboard
                return redirect(
                    url_for("dashboard")
                )

            # Show error if login details are wrong
            flash(
                "Invalid email or password.",
                "error"
            )

        except mysql.connector.Error as error:

            # Print database error in terminal
            print(error)

            # Show database error message
            flash(
                "Database connection failed.",
                "error"
            )

    # Open Login page
    return render_template(
        "login.html"
    )

# =========================
# Dashboard
# =========================

@app.route("/dashboard")
@login_required
def dashboard():

    from datetime import date

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        user_id = session["user_id"]

        # -----------------------------
        # Total Pets
        # -----------------------------
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM pets
            WHERE user_id = %s
        """, (user_id,))

        total_pets = cursor.fetchone()["total"]

        # -----------------------------
        # Upcoming Vaccinations
        # -----------------------------
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM vaccinations
            WHERE user_id = %s
            AND next_due_date IS NOT NULL
            AND next_due_date >= %s
        """, (user_id, date.today()))

        upcoming_vaccines = cursor.fetchone()["total"]

        # -----------------------------
        # Health Records
        # -----------------------------
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM health_records
            WHERE user_id = %s
        """, (user_id,))

        health_records = cursor.fetchone()["total"]

        # -----------------------------
        # Reminders - next 7 days
        # -----------------------------
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM vaccinations
            WHERE user_id = %s
            AND next_due_date IS NOT NULL
            AND next_due_date >= %s
            AND next_due_date <= DATE_ADD(%s, INTERVAL 7 DAY)
        """, (user_id, date.today(), date.today()))

        reminders = cursor.fetchone()["total"]

        # -----------------------------
        # My Pets
        # -----------------------------
        cursor.execute("""
            SELECT
                id,
                pet_name,
                pet_type,
                breed,
                age,
                weight
            FROM pets
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT 4
        """, (user_id,))

        pets = cursor.fetchall()
        print("HEALTH RECORD PETS:", pets)

        # -----------------------------
        # Upcoming Vaccinations
        # -----------------------------
        cursor.execute("""
            SELECT
                v.vaccine_name,
                v.next_due_date,
                p.pet_name,
                p.pet_type
            FROM vaccinations v
            JOIN pets p
                ON v.pet_id = p.id
            WHERE v.user_id = %s
            AND v.next_due_date IS NOT NULL
            AND v.next_due_date >= %s
            ORDER BY v.next_due_date ASC
            LIMIT 5
        """, (user_id, date.today()))

        upcoming = cursor.fetchall()

        # Calculate days remaining
        for item in upcoming:
            item["days_left"] = (
                item["next_due_date"] - date.today()
            ).days

        cursor.close()
        conn.close()

        return render_template(
            "dashboard.html",
            total_pets=total_pets,
            upcoming_vaccines=upcoming_vaccines,
            health_records=health_records,
            reminders=reminders,
            pets=pets,
            upcoming=upcoming
        )

    except mysql.connector.Error as error:

        print(error)

        return render_template(
            "dashboard.html",
            total_pets=0,
            upcoming_vaccines=0,
            health_records=0,
            reminders=0,
            pets=[],
            upcoming=[]
        )
# =========================
# Contact Us
# =========================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    # Check whether the user submitted the contact form
    if request.method == "POST":

        # Get data from the contact form
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        message = request.form["message"]

        # Connect to MySQL database
        db = get_db_connection()
        cursor = db.cursor()

        # Save contact message into database
        cursor.execute("""
            INSERT INTO contact_messages
            (name, email, phone, message)
            VALUES (%s, %s, %s, %s)
        """, (name, email, phone, message))

        # Save changes
        db.commit()

        # Close database connection
        cursor.close()
        db.close()

        # Show success message
        flash("Your message has been sent successfully!")

        # Reload Contact Us page
        return redirect(url_for("contact"))

    # Open Contact Us page
    return render_template("contact.html")

# =========================
# Add Pet
# =========================

@app.route("/add-pet", methods=["GET", "POST"])
@login_required
def add_pet():

    if request.method == "POST":

        pet_name = request.form.get(
            "pet_name",
            ""
        ).strip()

        pet_type = request.form.get(
            "pet_type",
            ""
        ).strip()

        breed = request.form.get(
            "breed",
            ""
        ).strip()

        age = request.form.get(
            "age",
            ""
        ).strip()

        weight = request.form.get(
            "weight",
            ""
        ).strip()

        if not pet_name or not pet_type:

            flash(
                "Pet name and pet type are required.",
                "error"
            )

            return render_template(
                "add_pet.html"
            )

        try:

            age_value = int(age) if age else None
            weight_value = float(weight) if weight else None

        except ValueError:

            flash(
                "Please enter valid age and weight.",
                "error"
            )

            return render_template(
                "add_pet.html"
            )

        try:

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO pets
                (
                    user_id,
                    pet_name,
                    pet_type,
                    breed,
                    age,
                    weight
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    pet_name,
                    pet_type,
                    breed,
                    age_value,
                    weight_value
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

            flash(
                "Pet added successfully!",
                "success"
            )

            return redirect(
                url_for("my_pets")
            )

        except mysql.connector.Error as error:

            print(error)

            flash(
                "Unable to save pet.",
                "error"
            )

    return render_template(
        "add_pet.html"
    )


# =========================
# My Pets
# =========================

@app.route("/pets")
@login_required
def my_pets():

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                id,
                pet_name,
                pet_type,
                breed,
                age,
                weight
            FROM pets
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (session["user_id"],)
        )

        pets = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "my_pets.html",
            pets=pets
        )

    except mysql.connector.Error as error:

        print(error)

        flash(
            "Unable to load pets.",
            "error"
        )

        return render_template(
            "my_pets.html",
            pets=[]
        )

# =========================
# Edit Pet
# =========================

@app.route("/edit-pet/<int:pet_id>", methods=["GET", "POST"])
@login_required
def edit_pet(pet_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get selected pet
    cursor.execute("""
        SELECT id, pet_name, pet_type, breed, age, weight
        FROM pets
        WHERE id = %s
        AND user_id = %s
    """, (
        pet_id,
        session["user_id"]
    ))

    pet = cursor.fetchone()

    if not pet:
        cursor.close()
        conn.close()

        flash("Pet not found.", "error")
        return redirect(url_for("my_pets"))

    # Update pet
    if request.method == "POST":

        pet_name = request.form.get("pet_name", "").strip()
        pet_type = request.form.get("pet_type", "").strip()
        breed = request.form.get("breed", "").strip()
        age = request.form.get("age", "").strip()
        weight = request.form.get("weight", "").strip()

        if not pet_name or not pet_type:

            flash(
                "Pet name and pet type are required.",
                "error"
            )

        else:

            try:
                age_value = int(age) if age else None
                weight_value = float(weight) if weight else None

                cursor.execute("""
                    UPDATE pets
                    SET
                        pet_name = %s,
                        pet_type = %s,
                        breed = %s,
                        age = %s,
                        weight = %s
                    WHERE id = %s
                    AND user_id = %s
                """, (
                    pet_name,
                    pet_type,
                    breed,
                    age_value,
                    weight_value,
                    pet_id,
                    session["user_id"]
                ))

                conn.commit()

                flash(
                    "Pet updated successfully!",
                    "success"
                )

                cursor.close()
                conn.close()

                return redirect(url_for("my_pets"))

            except ValueError:

                flash(
                    "Please enter valid age and weight.",
                    "error"
                )

    cursor.close()
    conn.close()

    return render_template(
        "edit_pet.html",
        pet=pet
    )


# =========================
# Delete Pet
# =========================

@app.route("/delete-pet/<int:pet_id>", methods=["POST"])
@login_required
def delete_pet(pet_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM pets
        WHERE id = %s
        AND user_id = %s
    """, (
        pet_id,
        session["user_id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash(
        "Pet deleted successfully!",
        "success"
    )

    return redirect(url_for("my_pets"))


# =========================
# Vaccination
# =========================

@app.route("/vaccination", methods=["GET", "POST"])
@login_required
def vaccination():

    try:

        conn = get_db_connection()
        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT id, pet_name, pet_type
            FROM pets
            WHERE user_id = %s
            ORDER BY pet_name
            """,
            (session["user_id"],)
        )

        pets = cursor.fetchall()

        if request.method == "POST":

            pet_id = request.form.get(
                "pet_id"
            )

            vaccine_name = request.form.get(
                "vaccine_name",
                ""
            ).strip()

            vaccination_date = request.form.get(
                "vaccination_date"
            )

            next_due_date = request.form.get(
                "next_due_date"
            )

            notes = request.form.get(
                "notes",
                ""
            ).strip()

            if not pet_id or not vaccine_name or not vaccination_date:

                flash(
                    "Please fill the required vaccination fields.",
                    "error"
                )

            else:

                cursor.execute(
                    """
                    SELECT id
                    FROM pets
                    WHERE id = %s
                    AND user_id = %s
                    """,
                    (
                        pet_id,
                        session["user_id"]
                    )
                )

                pet = cursor.fetchone()

                if not pet:

                    flash(
                        "Invalid pet selected.",
                        "error"
                    )

                else:

                    cursor.execute(
                        """
                        INSERT INTO vaccinations
                        (
                            user_id,
                            pet_id,
                            vaccine_name,
                            vaccination_date,
                            next_due_date,
                            notes
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            session["user_id"],
                            pet_id,
                            vaccine_name,
                            vaccination_date,
                            next_due_date if next_due_date else None,
                            notes
                        )
                    )

                    conn.commit()

                    flash(
                        "Vaccination saved successfully!",
                        "success"
                    )

        cursor.execute(
    """
    SELECT
        v.id,
        v.vaccine_name,
        v.vaccination_date,
        v.next_due_date,
        v.notes,
        p.pet_name,
        p.pet_type
    FROM vaccinations v
    JOIN pets p
        ON v.pet_id = p.id
    WHERE v.user_id = %s
    ORDER BY v.vaccination_date DESC
    """,
    (session["user_id"],)
)

        vaccinations = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "vaccination.html",
            pets=pets,
            vaccinations=vaccinations
        )

    except mysql.connector.Error as error:

        print(error)

        flash(
            "Unable to load vaccination records.",
            "error"
        )

        return render_template(
            "vaccination.html",
            pets=[],
            vaccinations=[]
        )

# =========================
# Edit Vaccination
# =========================

@app.route("/edit-vaccination/<int:vaccination_id>", methods=["GET", "POST"])
@login_required
def edit_vaccination(vaccination_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            v.id,
            v.pet_id,
            v.vaccine_name,
            v.vaccination_date,
            v.next_due_date,
            v.notes,
            p.pet_name
        FROM vaccinations v
        JOIN pets p
            ON v.pet_id = p.id
        WHERE v.id = %s
        AND v.user_id = %s
    """, (
        vaccination_id,
        session["user_id"]
    ))

    vaccination = cursor.fetchone()

    if not vaccination:
        cursor.close()
        conn.close()

        flash("Vaccination record not found.", "error")
        return redirect(url_for("vaccination"))

    if request.method == "POST":

        vaccine_name = request.form.get(
            "vaccine_name", ""
        ).strip()

        vaccination_date = request.form.get(
            "vaccination_date"
        )

        next_due_date = request.form.get(
            "next_due_date"
        )

        notes = request.form.get(
            "notes", ""
        ).strip()

        if not vaccine_name or not vaccination_date:

            flash(
                "Vaccine name and vaccination date are required.",
                "error"
            )

        else:

            cursor.execute("""
                UPDATE vaccinations
                SET
                    vaccine_name = %s,
                    vaccination_date = %s,
                    next_due_date = %s,
                    notes = %s
                WHERE id = %s
                AND user_id = %s
            """, (
                vaccine_name,
                vaccination_date,
                next_due_date if next_due_date else None,
                notes,
                vaccination_id,
                session["user_id"]
            ))

            conn.commit()

            cursor.close()
            conn.close()

            flash(
                "Vaccination updated successfully!",
                "success"
            )

            return redirect(url_for("vaccination"))

    cursor.close()
    conn.close()

    return render_template(
        "edit_vaccination.html",
        vaccination=vaccination
    )


# =========================
# Delete Vaccination
# =========================

@app.route("/delete-vaccination/<int:vaccination_id>", methods=["POST"])
@login_required
def delete_vaccination(vaccination_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM vaccinations
        WHERE id = %s
        AND user_id = %s
    """, (
        vaccination_id,
        session["user_id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash(
        "Vaccination deleted successfully!",
        "success"
    )

    return redirect(url_for("vaccination"))

# =========================
# AI Health Checker
# =========================

@app.route("/ai-health", methods=["GET", "POST"])
@login_required
def ai_health():

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get logged-in user's pets
        cursor.execute("""
            SELECT id, pet_name, pet_type
            FROM pets
            WHERE user_id = %s
            ORDER BY pet_name
        """, (session["user_id"],))

        pets = cursor.fetchall()

        result = None

        if request.method == "POST":

            symptoms = request.form.get(
                "symptoms",
                ""
            ).strip().lower()

            pet_id = request.form.get("pet_id")

            if not symptoms or not pet_id:

                flash(
                    "Please select a pet and enter symptoms.",
                    "error"
                )

            else:

                # Check selected pet belongs to logged-in user
                cursor.execute("""
                    SELECT id, pet_name, pet_type
                    FROM pets
                    WHERE id = %s
                    AND user_id = %s
                """, (
                    pet_id,
                    session["user_id"]
                ))

                pet = cursor.fetchone()

                if not pet:

                    flash(
                        "Invalid pet selected.",
                        "error"
                    )

                else:

                    pet_type = pet["pet_type"].lower()

                    # =========================
                    # Urgent Symptoms
                    # =========================

                    urgent_words = [
                        "difficulty breathing",
                        "breathing problem",
                        "cannot breathe",
                        "severe bleeding",
                        "unconscious",
                        "seizure",
                        "collapse",
                        "cannot stand",
                        "poison",
                        "poisoning"
                    ]

                    # =========================
                    # Symptom-Specific Guidance
                    # =========================

                    if any(
                        word in symptoms
                        for word in urgent_words
                    ):

                        result = {
                            "title": "Urgent Veterinary Attention",
                            "message":
                                "The symptoms described may require "
                                "prompt professional attention.",
                            "action":
                                "Contact a qualified veterinarian "
                                "or emergency veterinary service "
                                "as soon as possible.",
                            "level_class": "urgent"
                        }

                    elif (
                        "vomiting" in symptoms
                        or "throwing up" in symptoms
                    ):

                        result = {
                            "title": "Possible Digestive Concern",
                            "message":
                                "Vomiting can have different causes "
                                "and should be monitored carefully.",
                            "action":
                                "Monitor your pet and contact a "
                                "veterinarian if vomiting continues, "
                                "worsens, or your pet seems unwell.",
                            "level_class": "moderate"
                        }

                    elif (
                        "diarrhea" in symptoms
                        or "loose motion" in symptoms
                    ):

                        result = {
                            "title": "Digestive Health Concern",
                            "message":
                                "Diarrhea may occur for different "
                                "reasons and should be monitored.",
                            "action":
                                "Keep your pet under observation and "
                                "contact a veterinarian if the problem "
                                "continues or worsens.",
                            "level_class": "moderate"
                        }

                    elif (
                        "not eating" in symptoms
                        or "loss of appetite" in symptoms
                        or "no appetite" in symptoms
                    ):

                        result = {
                            "title": "Appetite Concern",
                            "message":
                                "A change in appetite can have different "
                                "causes and may need attention.",
                            "action":
                                "Monitor your pet's eating and drinking "
                                "and contact a veterinarian if the "
                                "problem continues.",
                            "level_class": "moderate"
                        }

                    elif (
                        "cough" in symptoms
                        or "coughing" in symptoms
                    ):

                        result = {
                            "title": "Respiratory Concern",
                            "message":
                                "Coughing can have different causes "
                                "and should be monitored.",
                            "action":
                                "Observe your pet and contact a "
                                "veterinarian if coughing continues "
                                "or becomes worse.",
                            "level_class": "moderate"
                        }

                    elif (
                        "limping" in symptoms
                        or "cannot walk" in symptoms
                        or "walking problem" in symptoms
                    ):

                        result = {
                            "title": "Mobility Concern",
                            "message":
                                "Limping or difficulty walking may "
                                "indicate a problem that needs attention.",
                            "action":
                                "Limit strenuous activity and consider "
                                "contacting a veterinarian for proper "
                                "evaluation.",
                            "level_class": "moderate"
                        }

                    elif (
                        "very tired" in symptoms
                        or "weak" in symptoms
                        or "lethargic" in symptoms
                    ):

                        result = {
                            "title": "Low Energy Concern",
                            "message":
                                "Unusual tiredness or weakness can have "
                                "different causes.",
                            "action":
                                "Monitor your pet closely and contact "
                                "a veterinarian if the weakness continues "
                                "or your pet's condition concerns you.",
                            "level_class": "moderate"
                        }

                    elif "fever" in symptoms:

                        result = {
                            "title": "Possible Fever Concern",
                            "message":
                                "A suspected fever may be associated "
                                "with different health conditions.",
                            "action":
                                "Contact a veterinarian for appropriate "
                                "evaluation, especially if other symptoms "
                                "are present.",
                            "level_class": "moderate"
                        }

                    elif (
                        "itching" in symptoms
                        or "itchy" in symptoms
                        or "scratching" in symptoms
                    ):

                        result = {
                            "title": "Skin Concern",
                            "message":
                                "Itching or frequent scratching can have "
                                "different causes.",
                            "action":
                                "Monitor the affected area and contact "
                                "a veterinarian if the problem persists "
                                "or becomes worse.",
                            "level_class": "moderate"
                        }

                    else:

                        result = {
                            "title": "General Health Guidance",
                            "message":
                                "The entered symptoms do not match "
                                "the specific patterns checked by this "
                                "basic health checker.",
                            "action":
                                "Continue observing your pet and contact "
                                "a qualified veterinarian if symptoms "
                                "persist, worsen, or you are concerned.",
                            "level_class": "general"
                        }

        cursor.close()
        conn.close()

        return render_template(
            "ai_health.html",
            pets=pets,
            result=result
        )

    except mysql.connector.Error as error:

        print(error)

        flash(
            "Unable to load AI Health Checker.",
            "error"
        )

        return render_template(
            "ai_health.html",
            pets=[],
            result=None
        )

# =========================
# Health Records
# =========================

@app.route("/health-records", methods=["GET", "POST"])
@login_required
def health_records():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get user's pets
    cursor.execute("""
        SELECT id, pet_name, pet_type
        FROM pets
        WHERE user_id = %s
        ORDER BY pet_name
    """, (session["user_id"],))

    pets = cursor.fetchall()

    if request.method == "POST":

        pet_id = request.form.get("pet_id")
        record_date = request.form.get("record_date")
        record_type = request.form.get("record_type", "").strip()
        details = request.form.get("details", "").strip()

        report_file = request.files.get("report_file")

        # Required fields
        if not pet_id or not record_date or not record_type or not details:

            flash(
                "Please fill all required fields.",
                "error"
            )

        else:

            # Check pet belongs to logged-in user
            cursor.execute("""
                SELECT id
                FROM pets
                WHERE id = %s
                AND user_id = %s
            """, (
                pet_id,
                session["user_id"]
            ))

            pet = cursor.fetchone()

            if not pet:

                flash(
                    "Invalid pet selected.",
                    "error"
                )

            else:

                saved_report_name = None

                # -----------------------------
                # Upload report (optional)
                # -----------------------------

                if report_file and report_file.filename:

                    original_name = secure_filename(
                        report_file.filename
                    )

                    allowed_extensions = {
                        "pdf",
                        "jpg",
                        "jpeg",
                        "png"
                    }

                    extension = ""

                    if "." in original_name:
                        extension = original_name.rsplit(
                            ".", 1
                        )[1].lower()

                    if extension not in allowed_extensions:

                        flash(
                            "Only PDF, JPG, JPEG and PNG files are allowed.",
                            "error"
                        )

                    else:

                        upload_folder = os.path.join(
                            "static",
                            "uploads"
                        )

                        os.makedirs(
                            upload_folder,
                            exist_ok=True
                        )

                        saved_report_name = (
                            f"{session['user_id']}_"
                            f"{pet_id}_"
                            f"{original_name}"
                        )

                        report_path = os.path.join(
                            upload_folder,
                            saved_report_name
                        )

                        report_file.save(report_path)

                # -----------------------------
                # Save Health Record
                # -----------------------------

                if (
                    not report_file
                    or not report_file.filename
                    or saved_report_name
                ):

                    cursor.execute("""
                        INSERT INTO health_records
                        (
                            user_id,
                            pet_id,
                            record_date,
                            record_type,
                            details,
                            report_file
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        session["user_id"],
                        pet_id,
                        record_date,
                        record_type,
                        details,
                        saved_report_name
                    ))

                    conn.commit()

                    flash(
                        "Health record saved successfully!",
                        "success"
                    )


    # -----------------------------
    # Get saved records
    # -----------------------------

    cursor.execute("""
        SELECT
            h.id,
            h.record_date,
            h.record_type,
            h.details,
            h.report_file,
            p.pet_name,
            p.pet_type
        FROM health_records h
        JOIN pets p
            ON h.pet_id = p.id
        WHERE h.user_id = %s
        ORDER BY h.record_date DESC
    """, (session["user_id"],))

    records = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "health_records.html",
        pets=pets,
        records=records
    )

@app.route("/nearby-vet")
@login_required
def nearby_vet():
    return render_template("nearby_vet.html")
@app.route("/notifications")
@login_required
def notifications():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            vaccinations.vaccine_name,
            vaccinations.next_due_date,
            pets.pet_name,
            pets.pet_type
        FROM vaccinations
        JOIN pets
            ON vaccinations.pet_id = pets.id
        WHERE vaccinations.user_id = %s
        AND vaccinations.next_due_date IS NOT NULL
        ORDER BY vaccinations.next_due_date ASC
    """, (session["user_id"],))

    notifications = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "notifications.html",
        notifications=notifications
    )
@app.route("/profile")
@login_required
def profile():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, email
        FROM users
        WHERE id = %s
    """, (session["user_id"],))

    user = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM pets
        WHERE user_id = %s
    """, (session["user_id"],))

    total_pets = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM vaccinations v
        JOIN pets p ON v.pet_id = p.id
        WHERE p.user_id = %s
    """, (session["user_id"],))

    total_vaccinations = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM health_records h
        JOIN pets p ON h.pet_id = p.id
        WHERE p.user_id = %s
    """, (session["user_id"],))

    total_health_records = cursor.fetchone()["total"]

    cursor.close()
    db.close()

    return render_template(
        "profile.html",
        user=user,
        total_pets=total_pets,
        total_vaccinations=total_vaccinations,
        total_health_records=total_health_records
    )
# =========================
# Logout
# =========================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# =========================
# Start Application
# =========================

init_db()

check_vaccination_reminders()

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5500
    )

