#imports --
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory

from models import db
import os
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from models import Company, Workspace, File, Dashboard, Report, Chart
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Avoid Tkinter backend for Flask

import matplotlib.pyplot as plt
import google.generativeai as genai
import seaborn as sns
from faker import Faker
import random
from markdown import markdown
from sklearn.cluster import DBSCAN







fake = Faker()
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
        return render_template('signup.html',login=current_user.is_authenticated)

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
    return render_template('login.html',login=current_user.is_authenticated)


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
    return render_template('workspaces.html',context=context, company_name=current_user.name)


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
    return render_template('dashboards.html', context=context, company_name=current_user.name)


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
    return render_template('reports.html',context=context, company_name=current_user.name)    


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
    return render_template('workspace.html',context=context, company_name=current_user.name)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect('/login')

@app.route('/add_workspace', methods=['GET','POST'])
@login_required
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
        return redirect(url_for('prepare_data', workspace_id=new_workspace.id))

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

    return render_template('datagrid.html', context=context, company_name=current_user.name)



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
    
    file_name = files[0].filename
    
    print(file_name)

    if request.method == 'POST':
        print("I'm here")
        print("reched here.....")

        # Get user inputs
        x_column = request.form.get('x_column')
        y_column = request.form.get('y_column')
        chart_title = request.form.get('chart_title')
        chart_description = request.form.get('chart_description')
        chart_type = request.form.get('chart_type')  # e.g., line, bar, scatter
        print(x_column,y_column,chart_title,chart_description,chart_type)
        
        print(x_column,y_column)

        # Validate inputs
        if not chart_type or (chart_type not in ['histogram', 'boxplot', 'pie', 'line', 'bar', 'scatter', 'heatmap', 'pairplot', 'violin', 'kde']):
            flash("Invalid or unsupported chart type.", "error")
            return redirect(request.url)

        try:
            print("Is it ok till here")
            # plt.style.use('seaborn')  # Improve visual appearance
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
                sns.heatmap(df.corr(), annot=True, fmt=".2f", cmap="coolwarm")
            elif chart_type == 'pairplot':
                sns.pairplot(df)
            elif chart_type == 'violin':
                sns.violinplot(x=df[x_column], y=df[y_column])
            elif chart_type == 'kde':
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

            print("reached here ......")

            # Generate AI Report
            prompt = f"""
            Analyze the following data and generate a report:
            Chart Title: {chart_title or 'Untitled Chart'}
            Chart Type: {chart_type}
            X-Column: {x_column}, Y-Column: {y_column}

            Data Overview:
            X-Column Values: {df[x_column].head(10).tolist()}
            Y-Column Values: {df[y_column].head(10).tolist()}

            Identify key trends, patterns, or outliers in the data and {chart_description}.
            """
            
            print(prompt)


            genai.configure(api_key="AIzaSyAgtKUZS-HsyvfKLiHDXtK2wc2SRCytSic")
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            full_description = markdown(response.text.strip())

            # Log the response for debugging
            print("Generated Report:", full_description)
            
            new_chart = Chart(
                title=chart_title or "Untitled Chart",
                description=full_description,
                image_file_path=chart_path,
                workspace_id=workspace_id
            )
            db.session.add(new_chart)
            db.session.commit()

            flash("Chart created successfully!", "success")
            context = {
                'workspace': workspace,
                'file_name': file_name,
                'columns': df.columns.tolist(),
                'active_page': 'create_chart',
                'chart_types': ['line', 'bar', 'scatter', 'histogram', 'boxplot', 'pie', 'heatmap', 'pairplot', 'violin', 'kde'],
                'chart': new_chart if 'new_chart' in locals() else None  # Add fallback

            }
            return render_template('create_chart.html', context=context)
                    
        except Exception as e:
            print(e)
            flash(f"An error occurred while creating the chart: {str(e)}", "error")
            context = {
                'workspace': workspace,
                'file_name': file_name,
                'columns': df.columns.tolist(),
                'active_page': 'create_chart',
                'chart_types': ['line', 'bar', 'scatter', 'histogram', 'boxplot', 'pie', 'heatmap', 'pairplot', 'violin', 'kde'],
                'chart': None  # Ensure chart is set explicitly

            }
            return render_template('create_chart.html', context=context, company_name=current_user.name)

    # Prepare context for GET request
    context = {
        'workspace': workspace,
        'file_name': file_name,
        'columns': df.columns.tolist(),
        'active_page': 'create_chart',
        'chart_types': ['line', 'bar', 'scatter', 'histogram', 'boxplot', 'pie', 'heatmap', 'pairplot', 'violin', 'kde']
    }
    return render_template('create_chart.html', context=context, company_name=current_user.name)


## Generation of Report
from weasyprint import HTML
from flask import make_response
from weasyprint import HTML
from flask import send_file
import os

@app.route('/workspace/<int:workspace_id>/report/create', methods=['GET', 'POST'])
def create_report(workspace_id):
    # Fetch all charts associated with the workspace
    charts = Chart.query.filter_by(workspace_id=workspace_id).all()
    
    if request.method == 'POST':
        selected_chart_ids = request.form.getlist('charts')
        if not selected_chart_ids:
            flash('Please select at least one chart to generate a report.', 'warning')
            return render_template('create_report.html', charts=charts, workspace_id=workspace_id)
        
        # Fetch selected charts
        selected_charts = Chart.query.filter(Chart.id.in_(selected_chart_ids)).all()
        
        # Build the prompt with chart descriptions
        prompt = "Generate a comprehensive report based on the following charts:\n"
        for chart in selected_charts:
            prompt += f"\n- {chart.title}: {chart.description or 'No description provided'}"
        
        # Generate content using Gemini API
        genai.configure(api_key="AIzaSyAgtKUZS-HsyvfKLiHDXtK2wc2SRCytSic")
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        # Format the content for PDF
        full_report = markdown(response.text.strip())
        
        # Build the HTML content with chart images
        pdf_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #007BFF; text-align: center; }}
                h3 {{ margin-top: 20px; }}
                ul {{ padding-left: 20px; }}
                .chart-image {{ max-width: 100%; height: auto; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h1>{request.form.get('report_name')}</h1>
            <h3>Charts Included:</h3>
            <ul>
        """
        
        # Add the selected charts with images
        for chart in selected_charts:
            pdf_content += f"<li>{chart.title}</li>"
            # Assuming 'image_file_path' stores the file path of the chart image
            image_path = chart.image_file_path  # Make sure the images are served via Flask's static folder
            pdf_content += f'<img src="{image_path}" class="chart-image" alt="{chart.title}">'
        
        pdf_content += f"""
            </ul>
            <h3>Generated Report:</h3>
            {full_report}
        </body>
        </html>
        """
        
        # Generate the PDF
        pdf_file_path = f"uploads/report_{workspace_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        HTML(string=pdf_content).write_pdf(pdf_file_path)
        
        # Save the report to the database
        new_report = Report(
            title=request.form.get('report_name'),
            description=f"Generated report for selected charts in Workspace {workspace_id}.",
            report_file=pdf_file_path,
            workspace_id=workspace_id,
            created_on=datetime.utcnow()
        )
        db.session.add(new_report)
        db.session.commit()
        
        flash('Report generated successfully!', 'success')
        return redirect(url_for('workspace', workspace_id=workspace_id))
    
    context = {
        'active_page': 'create_report'
    }
    
    return render_template('create_report.html', charts=charts, workspace_id=workspace_id, context=context)


from flask import send_file

@app.route('/report/<int:report_id>/view', methods=['GET'])
def view_report(report_id):
    # Fetch the report from the database
    report = Report.query.get_or_404(report_id)
    try:
        return send_file(report.report_file, as_attachment=False, download_name=f"{report.title}.pdf", mimetype='application/pdf')
    except FileNotFoundError:
        flash('Report file not found.', 'error')
        return redirect(url_for('workspace_reports', workspace_id=report.workspace_id))


import os

@app.route('/report/<int:report_id>/delete', methods=['POST'])
def delete_report(report_id):
    # Fetch the report from the database
    report = Report.query.get_or_404(report_id)
    file_path = report.report_file
    
    # Remove the file
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete the record from the database
    db.session.delete(report)
    db.session.commit()
    
    flash('Report deleted successfully.', 'success')
    return redirect(url_for('workspace', workspace_id=report.workspace_id))



@app.route('/view_chart/<int:id>')
@login_required
def view_chart(id):
    
    # Fetch the chart associated with the given id
    chart = Chart.query.filter_by(id=id).first()  # Use first() to get a single object
    
    if not chart:
        flash('Chart not found.', 'danger')
        return redirect(url_for('workspace'))  # Redirect if chart doesn't exist
    
    context = {
        'active_page': 'view_chart'
    }
    
    return render_template('view_chart.html', context=context, company_name=current_user.name, chart=chart)



@app.route('/view_charts/<int:workspace_id>')
@login_required
def view_charts(workspace_id):
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Fetch charts associated with the workspace
    charts = Chart.query.filter_by(workspace_id=workspace_id).all()
    
    # Pagination logic
    page = request.args.get('page', 1, type=int)  # Get the current page number from the query string
    charts_per_page = 4
    start_idx = (page - 1) * charts_per_page
    end_idx = start_idx + charts_per_page
    paginated_charts = charts[start_idx:end_idx]
    
    # Calculate total pages
    total_pages = (len(charts) + charts_per_page - 1) // charts_per_page
    
    context = {
        'workspace': workspace,
        'charts': paginated_charts,
        'current_page': page,
        'total_pages': total_pages,
        'active_page': 'view_charts'
    }
    return render_template('view_charts.html', context=context, company_name=current_user.name)


# Static route for 'uploads'
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/delete_workspace/<int:workspace_id>', methods=['POST'])
@login_required
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
    


@app.route('/workspace/<int:workspace_id>/dashboard/create', methods=['GET', 'POST'])
@login_required
def create_dashboard(workspace_id):
    # Fetch all charts for the workspace
    charts = Chart.query.filter_by(workspace_id=workspace_id).all()

    # Fetch existing dashboard data, if any
    existing_dashboard = File.query.filter_by(workspace_id=workspace_id, filename='dashboard.json').first()
    layout_data = None
    if existing_dashboard:
        with open(existing_dashboard.file_path, 'r') as f:
            layout_data = f.read()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        layout_data = request.form['layout_data']

        # Save dashboard layout to a file
        dashboard_path = os.path.join('uploads', f'dashboard_{workspace_id}.json')
        with open(dashboard_path, 'w') as f:
            f.write(layout_data)

        # Update File table entry
        file_entry = File.query.filter_by(workspace_id=workspace_id, filename='dashboard.json').first()
        if not file_entry:
            file_entry = File(
                filename='dashboard.json',
                file_path=dashboard_path,
                workspace_id=workspace_id
            )
            db.session.add(file_entry)
        else:
            file_entry.file_path = dashboard_path

        db.session.commit()
        return redirect(url_for('create_dashboard', workspace_id=workspace_id))

    return render_template('dashboard_create.html', charts=charts, layout_data=layout_data)




@app.route('/delete_chart/<int:chart_id>', methods=['POST'])
@login_required
def delete_chart(chart_id):

    chart = Chart.query.get_or_404(chart_id)
    workspace_id=chart.workspace_id
    # Check if the user has permission to delete this chart
    workspace = Workspace.query.get_or_404(chart.workspace_id)
    if not current_user.is_authenticated:
        flash("You don't have permission to delete this chart.", "error")
        return redirect(url_for('workspace_details', workspace_id=workspace.id))

    # Delete the chart image file if it exists
    if os.path.exists(chart.image_file_path):
        os.remove(chart.image_file_path)

    # Delete the chart from the database
    db.session.delete(chart)
    db.session.commit()
    
    flash("Chart deleted successfully.", "success")
    return redirect(url_for('workspace', workspace_id=workspace_id))



@app.route('/apply_model', methods=['POST'])
def apply_model():
    selected_file = request.form['selected_file']
    financial_model = request.form['financial_model']
    
    print("The selected file here is: ")
    print(selected_file)
    
    if financial_model == "Customer Segmentation":
        return redirect(url_for('clustering_form', selected_file=selected_file))
    
    # Handle other financial models (Risk Assessment, Portfolio Optimization, etc.)
    # For now, we can just return a message.
    return f"Applying model {financial_model} to file {selected_file}"

@app.route('/clustering_form')
def clustering_form():
    selected_file = request.args.get('selected_file')
    
    print("The selected file in the clustering here is: ")
    print(selected_file)
    
    context = {
        'active_page': 'workspace',  # Set the active page or any other data you need
    }

    
    if not selected_file:
        return "File not selected", 400
    
    # Load the Excel file (adjust the path as necessary)
    df = pd.read_excel(f'./uploads/{selected_file}')
    
    # Get the list of columns in the file (you can also filter for numerical columns if needed)
    columns = df.select_dtypes(include=['number']).columns.tolist()
    
    context = {
        'active_page': 'financialmmodel',  # Set the active page or any other data you need
    }


    return render_template('clustering_form.html', selected_file=selected_file, columns=columns, context=context)


# Ensure the directory for saving plots exists
plot_dir = 'static/charts'
if not os.path.exists(plot_dir):
    os.makedirs(plot_dir)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    


from flask import render_template, request
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import dendrogram, linkage

@app.route('/clustering_results', methods=['POST'])
def clustering_results():
    selected_file = request.form.get('selected_file')
    columns = request.form.getlist('columns')
    eps = float(request.form['eps'])
    min_samples = int(request.form['min_samples'])
    clustering_algo = request.form.get('clustering_algo')  # Get selected clustering algorithm

    # Load the file and select the specified columns
    df = pd.read_excel(f'./uploads/{selected_file}')
    X = df[columns].values  # Selecting only the chosen columns for clustering
    X_scaled = StandardScaler().fit_transform(X)  # Scaling the data for better clustering results

    # Perform selected clustering algorithm
    if clustering_algo == 'DBSCAN':
        model = DBSCAN(eps=eps, min_samples=min_samples)
        clusters = model.fit_predict(X_scaled)
    elif clustering_algo == 'Agglomerative':
        model = AgglomerativeClustering(n_clusters=None, distance_threshold=eps)
        clusters = model.fit_predict(X_scaled)
    else:
        clusters = []  # Handle default case or unknown algorithm

    # Add the cluster results to the dataframe
    df['Cluster'] = clusters

    # Optional: Save the result to a new file
    result_file = f'clustering_result_{selected_file}'
    df.to_excel(result_file)

    # Visualization: Scatter Plot with different colors for clusters
    scatter_plot_path = f'static/charts/scatter_plot_{selected_file}.png'
    plt.figure(figsize=(8, 6))
    sns.scatterplot(x=df[columns[0]], y=df[columns[1]], hue=df['Cluster'], palette='tab10', marker='o')
    plt.title(f'{clustering_algo} Clustering - Scatter Plot')
    plt.xlabel(columns[0])
    plt.ylabel(columns[1])
    plt.legend(title='Cluster', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(scatter_plot_path)
    plt.close()

    # Visualization: Pairplot (only if more than 2 columns are selected)
    pairplot_path = None
    if len(columns) > 2:
        pairplot_path = f'static/charts/pairplot_{selected_file}.png'
        sns.pairplot(df, hue="Cluster", vars=columns, palette='tab10')
        plt.savefig(pairplot_path)
        plt.close()

    # Visualization: Hierarchical Clustering Dendrogram
    dendrogram_path = None
    if clustering_algo == 'Agglomerative' and len(columns) > 1:
        Z = linkage(X_scaled, 'ward')
        dendrogram_path = f'static/charts/dendrogram_{selected_file}.png'
        plt.figure(figsize=(10, 7))
        dendrogram(Z)
        plt.title(f'{clustering_algo} Dendrogram')
        plt.xlabel('Data Points')
        plt.ylabel('Euclidean Distance')
        plt.tight_layout()
        plt.savefig(dendrogram_path)
        plt.close()

    context = {
        'active_page': 'workspace',  # Set the active page or any other data you need
    }
    # Display results
    return render_template('clustering_result.html', 
                           result=df.head().to_html(), 
                           scatter_plot_path=scatter_plot_path, 
                           pairplot_path=pairplot_path,
                           dendrogram_path=dendrogram_path,
                           context=context,
                           selected_file=selected_file)










@app.route('/workspace/<int:workspace_id>/prepare', methods=['GET', 'POST'])
@login_required
def prepare_data(workspace_id):
    try:
        # Fetch the workspace
        workspace = Workspace.query.get_or_404(workspace_id)
        files = File.query.filter_by(workspace_id=workspace_id).all()
        data_file = next((file for file in files if file.filename.endswith(('.xls', '.xlsx'))), None)

        if not data_file:
            return "No Excel file found in the workspace.", 404

        file_path = data_file.file_path
        data = pd.read_excel(file_path)
        selected_column = None
        statistics = None

        if request.method == 'POST':
            if 'columns' in request.form:  # Form 1: Column Selection
                selected_columns = request.form.getlist('columns')
                if selected_columns:
                    data = data[selected_columns]
                    flash("Columns selected successfully!", "success")
            elif 'selected_column' in request.form:  # Form 2: Column Details
                selected_column = request.form.get('selected_column')
                statistics = {}

                # Check if the selected column is numeric
                if pd.api.types.is_numeric_dtype(data[selected_column]):
                    statistics["mean"] = data[selected_column].mean()
                    statistics["median"] = data[selected_column].median()
                    statistics["std"] = data[selected_column].std()
                else:
                    # Set statistics to "N/A" for non-numeric columns
                    statistics["mean"] = "N/A"
                    statistics["median"] = "N/A"
                    statistics["std"] = "N/A"

                # Always calculate the null count
                statistics["null_count"] = data[selected_column].isnull().sum()

            elif 'column_to_modify' in request.form:  # Handle NULL Values
                column = request.form.get('column_to_modify')
                null_action = request.form.get('null_action')
                if null_action == 'drop':
                    data = data.dropna(subset=[column])
                elif null_action == 'replace':
                    replacement_value = request.form.get('replace_value')
                    data[column].fillna(replacement_value, inplace=True)
                flash("NULL handling applied successfully!", "success")
            
            # Save modified file
            modified_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{data_file.filename}")
            data.to_excel(modified_file_path, index=False)
            data_file.file_path = modified_file_path
            db.session.commit()
            flash("Dataset modified successfully!", "success")
        return render_template(
            'prepare_data.html',
            workspace=workspace,
            columns=data.columns,
            selected_column=selected_column,
            statistics=statistics
        )

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        print("Error is:",e)
        return redirect(url_for('workspaces'))




if __name__ == '__main__':
    app.run(debug=True)