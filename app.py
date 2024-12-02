#imports --
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from models import db
import os
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from models import Company, Workspace, File, Dashboard, Report
from datetime import datetime

#initialization --
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'  # Use your database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Path to store uploaded files
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Ensure upload folder exists
app.secret_key = os.urandom(24)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)  # Bind LoginManager to your Flask app
login_manager.login_view = 'login'  # Set the login route
with app.app_context():
    db.create_all()

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return Company.query.get(int(user_id))

# Route for the home page
@app.route('/')
def home():
    return render_template('home.html')

# Route for the about page
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        print("Hey")
        # Get form data
        name = request.form.get('companyFullName')
        email = request.form.get('companyEmail')
        password = request.form.get('companyPassword')
        website_url = request.form.get('companyWebsite')
        print(name,email,password)
        # Validate form data (optional but recommended)
        if (not name) or (not email) or (not password):
            print("Please fill out all required fields!")
            return redirect('/signup')
        
        existing_company = Company.query.filter_by(email=email).first()
        if existing_company:
            print("fuck")
            flash("A company with this email already exists!", "error")
            return redirect('/signup')

        # Hash the password for security
        hashed_password = generate_password_hash(password)

        # Create a new Company object
        new_company = Company(
            name=name,
            email=email,
            password=hashed_password,
            website_url=website_url
        )
        print("I'm here")
        try:
            # Add the company to the database
            print("I'm here also")
            db.session.add(new_company)
            db.session.commit()
            flash("Company created successfully!", "success")
            return redirect('/login')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", "error")
            return redirect('/signup')
    else:
        return render_template('signup.html')

@app.route('/datagrid')
def datagrid():
    return render_template('datagrid.html')

@app.route('/selectcolumns')
def selectcolumns():
    return render_template('selectcolumns.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        # Get form data
        email = request.form.get('companyEmail')
        password = request.form.get('companyPassword')
        print(email,password)
        # Find the company by email
        company = Company.query.filter_by(email=email).first()

        if company and check_password_hash(company.password, password):
            # If company exists and password matches
            login_user(company)  # Log the company in (store in session)
            flash("Login successful!", "success")
            return redirect('/workspaces')  # Redirect to dashboard or a protected route
        else:
            flash("Invalid email or password", "error")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/workspaces')
@login_required
def workspaces():
    if not current_user.is_authenticated:
        print("NOt ok")
    company_id = current_user.id  
    workspaces = Workspace.query.filter_by(company_id=company_id).all() 
    context = {
        'workspaces': workspaces,
        'active_page': 'workspaces'
    }
    return render_template('workspaces.html',context=context)

@app.route('/dashboards')
@login_required
def dashboards():
    # dashboard_data = [
    #     {'title': 'Sales Overview', 'description': 'A comprehensive overview of sales metrics.', 'date': 'Nov 28, 2024'},
    #     {'title': 'Customer Insights', 'description': 'Analyze customer behavior and demographics.', 'date': 'Nov 25, 2024'},
    # ]
    if not current_user.is_authenticated:
        print("NOt ok")
    company_id = current_user.id  
    workspaces = Workspace.query.filter_by(company_id=company_id).all() 
    all_dashboards = []
    for w in workspaces:
        dashboards_of_w = Dashboard.query.filter_by(workspace_id=w.id).all()
        for d in dashboards_of_w:
            all_dashboards.append(d)
    
    context = {
        'dashboards':all_dashboards,
        'active_page': 'dashboards'
    }
    return render_template('dashboards.html', context=context)


@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html',active_page='reports')    


@app.route('/workspace/<int:workspace_id>')
@login_required
def workspace(workspace_id):
    workspace = Workspace.query.get_or_404(workspace_id)
    files = File.query.filter_by(workspace_id=workspace_id).all() 
    reports = Report.query.filter_by(workspace_id=workspace_id).all()
    dashboards = Dashboard.query.filter_by(workspace_id=workspace_id).all()
    context = {
        'workspace': workspace,
        'active_page': 'workspaces',
        'files': files,
        'reports': reports,
        'dashboards': dashboards
    }
    return render_template('workspace.html',context=context)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect('/login')

@app.route('/add_workspace', methods=['GET','POST'])
def add_workspace():
    try:
        # Get form data
        title = request.form.get('title')
        image = request.files.get('image')
        datafile = request.files.get('datafile')

        # Validate files
        if not image or not datafile:
            flash("Both image and data file are required.", "error")
            return redirect(request.url)

        # Secure filenames
        image_filename = secure_filename(image.filename)
        datafile_filename = secure_filename(datafile.filename)

        # Save files to the upload folder
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        datafile_path = os.path.join(app.config['UPLOAD_FOLDER'], datafile_filename)
        image.save(image_path)
        datafile.save(datafile_path)

        # Create and save the workspace
        new_workspace = Workspace(
            name=title,
            created_on=datetime.utcnow(),
            company_id=current_user.id,  # Assuming company_id is linked to the logged-in user
            image_file_path = image_path
        )
        db.session.add(new_workspace)
        db.session.commit()

        # Associate files with the workspace
        # image_file = File(filename=image_filename, file_path=image_path, workspace_id=new_workspace.id)
        data_file = File(filename=datafile_filename, file_path=datafile_path, workspace_id=new_workspace.id)

        # db.session.add(image_file)
        db.session.add(data_file)
        db.session.commit()

        flash("Workspace created successfully!", "success")
        return redirect(url_for('workspaces', workspace_id=new_workspace.id))

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(request.url)
    

# @app.route('/delete_workspace/<int:workspace_id>', methods=['POST'])
# def delete_workspace(workspace_id):
#     try:
#         # Query the workspace to delete
#         workspace = Workspace.query.get_or_404(workspace_id)
#         print(workspace)
#         # Delete the workspace
#         db.session.delete(workspace)
#         db.session.commit()
#         flash('Workspace deleted successfully!', 'success')
#     except Exception as e:
#         print("Some error occured")
#         db.session.rollback()
#         flash(f'Error occurred while deleting workspace: {str(e)}', 'danger')
#         print(str(e))
#     return redirect(url_for('workspaces')) 

# Static route for 'uploads'
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

if __name__ == '__main__':
    app.run(debug=True)
