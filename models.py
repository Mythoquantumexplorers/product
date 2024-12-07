from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

# 1. Company Model
class Company(UserMixin, db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    website_url = db.Column(db.String(255), nullable=True)

    # Relationships
    workspaces = db.relationship('Workspace', backref='company', lazy=True)

    def __repr__(self):
        return f"<Company {self.name}>"

# 2. Workspace Model
class Workspace(db.Model):
    __tablename__ = 'workspaces'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)
    image_file_path = db.Column(db.String(255), nullable=False)

    # One-to-Many relationship with File
    files = db.relationship('File', backref='workspace', lazy=True)
    
    # Foreign Key
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    # Relationships
    reports = db.relationship('Report', backref='workspace', lazy=True)
    dashboards = db.relationship('Dashboard', backref='workspace', lazy=True)

    def __repr__(self):
        return f"<Workspace {self.name}>"
    

    
class File(db.Model):
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)  # Path to the file storage location
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False)
    
    def __repr__(self):
        return f"<File {self.filename}>"


# 3. Report Model
class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    report_file = db.Column(db.String(255), nullable=False)  # Path to the file

    # Foreign Key
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False)

    def __repr__(self):
        return f"<Report {self.title}>"

# 4. Dashboard Model
class Dashboard(db.Model):
    __tablename__ = 'dashboards'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    json_file_path = db.Column(db.String(255), nullable=False)

    # Foreign Key
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False)
    def __repr__(self):
        return f"<Dashboard {self.title}>"




# 4. Chart Model
class Chart(db.Model):
    __tablename__ = 'chart'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    image_file_path = db.Column(db.String(255), nullable=False)

    # Foreign Key
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False)

    def __repr__(self):
        return f"<Chart {self.title}>"
    




