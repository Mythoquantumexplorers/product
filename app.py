#imports --
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from models import db
import os
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from models import Company, Workspace, File, Dashboard, Report, Chart
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt



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
    print(current_user.is_authenticated)
    return render_template('home.html',login=current_user.is_authenticated)

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
def datagrid2():
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
    if not current_user.is_authenticated:
        print("NOt ok")
    company_id = current_user.id  
    workspaces = Workspace.query.filter_by(company_id=company_id).all() 
    all_reports = []
    for w in workspaces:
        reports_of_w = Report.query.filter_by(workspace_id=w.id).all()
        for r in reports_of_w:
            all_reports.append(r)
    
    context = {
        'dashboards':all_reports,
        'active_page': 'reports'
    }
    return render_template('reports.html',context=context)    


@app.route('/workspace/<int:workspace_id>')
@login_required
def workspace(workspace_id):
    workspace = Workspace.query.get_or_404(workspace_id)
    files = File.query.filter_by(workspace_id=workspace_id).all() 
    reports = Report.query.filter_by(workspace_id=workspace_id).all()
    dashboards = Dashboard.query.filter_by(workspace_id=workspace_id).all()
    charts = Chart.query.filter_by(workspace_id=workspace_id).all()
    context = {
        'workspace': workspace,
        'active_page': 'workspaces',
        'files': files,
        'reports': reports,
        'charts' : charts,
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
        description = request.form.get('description')
        datafile = request.files.get('datafile')

        print(description)

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
            image_file_path = image_path,
            description=description
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
    

@app.route('/datagrid/<int:workspace_id>')
@login_required
def datagrid(workspace_id):
    # Fetch the workspace and associated files
    workspace = Workspace.query.get_or_404(workspace_id)
    files = File.query.filter_by(workspace_id=workspace_id).all()

    # Find the first XLS/XLSX file
    excel_file = next((file for file in files if file.filename.endswith(('.xls', '.xlsx'))), None)

    if not excel_file:
        return "No Excel file found in the workspace.", 404

    # Read the Excel file using Pandas
    file_path = excel_file.file_path  # Adjust to your file storage logic
    df = pd.read_excel(file_path)

    # Default statistics
    total_rows = len(df)
    total_columns = len(df.columns)
    total_null_values = int(df.isnull().sum().sum())  # Sum of all null values across all columns

    # Prepare column statistics
    column_stats = {
        col: {
            "null_values": int(df[col].isnull().sum()),  # Convert to Python int
            "unique_values": int(df[col].nunique()),    # Convert to Python int
            "max_value": df[col].max().item() if pd.api.types.is_numeric_dtype(df[col]) else None,
            "min_value": df[col].min().item() if pd.api.types.is_numeric_dtype(df[col]) else None,
            "sum": df[col].sum().item() if pd.api.types.is_numeric_dtype(df[col]) else None,
            "data_type": str(df[col].dtype),
        }
        for col in df.columns
    }

    # Pass data to template
    context = {
        'workspace': workspace,
        'columns': df.columns.tolist(),
        'rows': df.values.tolist(),
        'column_stats': column_stats,
        'total_rows': total_rows,
        'total_columns': total_columns,
        'total_null_values': total_null_values,
        'filename': excel_file.filename
    }

    return render_template('datagrid.html', context=context)





@app.route('/create_chart/<int:workspace_id>', methods=['GET', 'POST'])
@login_required
def create_chart(workspace_id):
    # Fetch the workspace
    workspace = Workspace.query.get_or_404(workspace_id)
    files = File.query.filter_by(workspace_id=workspace_id).all()

    # Find the first XLS/XLSX file
    excel_file = next((file for file in files if file.filename.endswith(('.xls', '.xlsx'))), None)

    if not excel_file:
        return "No Excel file found in the workspace.", 404

    # Read the Excel file using Pandas
    file_path = excel_file.file_path
    df = pd.read_excel(file_path)

    if request.method == 'POST':
        print("I'm here")
        # Get user inputs
        x_column = request.form.get('x_column')
        y_column = request.form.get('y_column')
        chart_title = request.form.get('chart_title')
        chart_description = request.form.get('chart_description')
        chart_type = request.form.get('chart_type')  # e.g., line, bar, scatter
        print(x_column,y_column,chart_title,chart_description,chart_type)
        # Validate inputs
        if not chart_type or (chart_type not in ['histogram', 'boxplot', 'pie', 'line', 'bar', 'scatter', 'heatmap', 'pairplot', 'violin', 'kde']):
            flash("Invalid or unsupported chart type.", "error")
            return redirect(request.url)

        try:
            print("Is it ok till here")
            # plt.style.use('seaborn')  # Improve visual appearance
            plt.figure(figsize=(10, 6))
            
            # Generate the selected chart
            if chart_type == 'line':
                plt.plot(df[x_column], df[y_column], marker='o', label=y_column)
            elif chart_type == 'bar':
                plt.bar(df[x_column], df[y_column], label=y_column)
            elif chart_type == 'scatter':
                plt.scatter(df[x_column], df[y_column], label=y_column)
            elif chart_type == 'histogram':
                plt.hist(df[x_column], bins=10, label=x_column, alpha=0.7)
            elif chart_type == 'boxplot':
                df[[x_column, y_column]].boxplot()
            elif chart_type == 'pie':
                plt.pie(df[x_column].value_counts(), labels=df[x_column].value_counts().index, autopct='%1.1f%%')
            elif chart_type == 'heatmap':
                import seaborn as sns
                sns.heatmap(df.corr(), annot=True, fmt=".2f", cmap="coolwarm")
            elif chart_type == 'pairplot':
                import seaborn as sns
                sns.pairplot(df)
            elif chart_type == 'violin':
                import seaborn as sns
                sns.violinplot(x=df[x_column], y=df[y_column])
            elif chart_type == 'kde':
                import seaborn as sns
                sns.kdeplot(df[x_column], label=x_column)

            plt.title(chart_title or "Chart")
            plt.xlabel(x_column)
            plt.ylabel(y_column)
            plt.legend()  # Add legend for clarity
            print("Is it ok till here")
            # Save the chart
            chart_filename = f"chart_{workspace_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png"
            chart_path = os.path.join(app.config['UPLOAD_FOLDER'], chart_filename)
            plt.savefig(chart_path)
            plt.close()

            # Save chart details to the database
            new_chart = Chart(
                title=chart_title or "Untitled Chart",
                description=chart_description,
                image_file_path=chart_path,
                workspace_id=workspace_id
            )
            db.session.add(new_chart)
            db.session.commit()

            flash("Chart created successfully!", "success")
            return redirect(url_for('workspace', workspace_id=workspace_id))
        except Exception as e:
            print(e)
            flash(f"An error occurred while creating the chart: {str(e)}", "error")
            return redirect(request.url)

    # Prepare context for GET request
    context = {
        'workspace': workspace,
        'columns': df.columns.tolist(),
        'active_page': 'create_chart',
        'chart_types': ['line', 'bar', 'scatter', 'histogram', 'boxplot', 'pie', 'heatmap', 'pairplot', 'violin', 'kde']
    }
    return render_template('create_chart.html', context=context)





@app.route('/view_charts/<int:workspace_id>')
@login_required
def view_charts(workspace_id):
    # Fetch the workspace and its associated charts
    workspace = Workspace.query.get_or_404(workspace_id)
    charts = Chart.query.filter_by(workspace_id=workspace_id).all()

    # Prepare context for template
    context = {
        'workspace': workspace,
        'charts': charts,
        'active_page': 'view_charts'
    }
    return render_template('view_charts.html', context=context)




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

@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/delete_workspace/<int:workspace_id>', methods=['POST'])
def delete_workspace(workspace_id):
    try:
        # Fetch the workspace by ID
        workspace = Workspace.query.get(workspace_id)
        
        if not workspace:
            flash('Workspace not found', 'error')
            return redirect(url_for('workspaces'))  # Redirect to the workspaces page

        # Delete related files
        for file in workspace.files:
            db.session.delete(file)

        # Delete related reports
        for report in workspace.reports:
            db.session.delete(report)

        # Delete related dashboards
        for dashboard in workspace.dashboards:
            db.session.delete(dashboard)

        # Delete related charts
        related_charts = Chart.query.filter_by(workspace_id=workspace.id).all()
        for chart in related_charts:
            db.session.delete(chart)

        # Finally, delete the workspace itself
        db.session.delete(workspace)

        # Commit the changes to the database
        db.session.commit()

        flash('Workspace and related data deleted successfully', 'success')
        return redirect(url_for('workspaces'))  # Redirect to the workspaces page

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting workspace: {str(e)}', 'error')
        return redirect(url_for('workspaces'))

if __name__ == '__main__':
    app.run(debug=True)
