# routes/about.py

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify, Blueprint, current_app
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from models import Company, Workspace, File, Dashboard, Report, Chart
import pandas as pd
from models import db
import os


# Create the Blueprint
data_preparation_bp = Blueprint('data_preparation', __name__)

# Define the view function inside the blueprint
@data_preparation_bp.route('/workspace/<int:workspace_id>/prepare', methods=['GET', 'POST'])
@login_required
def prepare_data(workspace_id):
    print("Reached Here\n")
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

        print("yha tk thik hai")

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
            upload_foler = current_app.config['UPLOAD_FOLDER']
            modified_file_path = os.path.join(upload_foler, f"{data_file.filename}")
            data.to_excel(modified_file_path, index=False)
            data_file.file_path = modified_file_path
            db.session.commit()
            flash("Dataset modified successfully!", "success")
        print("Okk till here")
        return render_template(
            'prepare_data.html',
            workspace=workspace,
            columns=data.columns,
            selected_column=selected_column,
            statistics=statistics
        )

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        print("Error1 is:",e)
        return redirect(url_for('workspaces'))
