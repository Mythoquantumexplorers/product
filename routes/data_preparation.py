# routes/about.py

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify, Blueprint, current_app
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from models import Company, Workspace, File, Dashboard, Report, Chart
import pandas as pd
from models import db
import os
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import MinMaxScaler, StandardScaler, Normalizer, MaxAbsScaler
import numpy as np

# Create the Blueprint
data_preparation_bp = Blueprint('data_preparation', __name__)

# Define the view function inside the blueprint
@data_preparation_bp.route('/workspace/<int:workspace_id>/prepare', methods=['GET', 'POST'])
@login_required
def prepare_data(workspace_id):
    try:
        # Fetch the workspace
        workspace = Workspace.query.get_or_404(workspace_id)
        files = File.query.filter_by(workspace_id=workspace_id).all()
        data_file = next((file for file in files if file.filename.endswith(('.xls', '.xlsx'))), None)
        data_type = None
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
                data_type = str(data[selected_column].dtype)
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

            elif 'column_to_modify' in request.form:  
                # Handle NULL Values
                column = request.form.get('column_to_modify')
                replace_option = request.form.get('replace_option')
                null_action = request.form.get('null_action')
                if pd.api.types.is_numeric_dtype(data[column]):
                    if null_action == 'none':
                        pass
                    elif null_action == 'drop':
                        data = data.dropna(subset=[column])
                    elif replace_option == 'mean':
                        mean_value = data[column].mean()
                        data[column].fillna(mean_value, inplace=True)
                    elif replace_option == 'median':
                        median_value = data[column].median()
                        data[column].fillna(median_value, inplace=True)
                    elif replace_option == 'mode':
                        mode_value = data[column].mode()[0]  # Mode returns a Series, so take the first value
                        data[column].fillna(mode_value, inplace=True)
                    elif replace_option == 'manual':
                        replace_value = request.form.get('replace_value')
                        data[column].fillna(replace_value, inplace=True)
                
                flash("NULL handling applied successfully!", "success")
                
                # Handle encoding --
                encoding_type = request.form['encoding_type']
                if encoding_type == 'one_hot':
                    if data[column].dtype == 'object' or data[column].dtype.name == 'category':
                        data = pd.get_dummies(data, columns=[column], drop_first=True)
                        flash(f"One-Hot Encoding applied to column: {column}", "success")
                    else:
                        flash(f"Column '{column}' is not categorical. One-hot encoding skipped.", "warning")
                elif encoding_type == 'label':
                    if data[column].dtype == 'object' or data[column].dtype.name == 'category':
                        label_encoder = LabelEncoder()
                        data[column] = label_encoder.fit_transform(data[column])
                        flash(f"Label Encoding applied to column: {column}", "success")
                    else:
                        flash(f"Column '{column}' is not categorical. Label encoding skipped.", "warning")
                else:
                    pass

                # Normalization --
                normalization_type = request.form.get('normalization_type')
                if column in data.columns:
                    if normalization_type == 'min_max':
                        scaler = MinMaxScaler()
                        data[column] = scaler.fit_transform(data[[column]])
                    elif normalization_type == 'z_score':
                        scaler = StandardScaler()
                        data[column] = scaler.fit_transform(data[[column]])
                    elif normalization_type == 'l1':
                        scaler = Normalizer(norm='l1')
                        data[column] = scaler.fit_transform(data[[column]])
                    elif normalization_type == 'l2':
                        scaler = Normalizer(norm='l2')
                        data[column] = scaler.fit_transform(data[[column]])
                    elif normalization_type == 'log':
                        data[column] = np.log1p(data[column].replace(0, np.nan)).fillna(0)  # Avoid log(0)
                    elif normalization_type == 'max_abs':
                        scaler = MaxAbsScaler()
                        data[column] = scaler.fit_transform(data[[column]])

                # Handling outliers --
                outlier_action = request.form.get('outlier_action')
                outlier_method = request.form.get('outlier_method')
                z_score_threshold = float(request.form.get('z_score_threshold', 3.0))  # Default threshold for Z-Score
                replacement_type = request.form.get('replacement_type', 'mean')  # Default to mean replacement

                if column in data.columns:
                    if outlier_action == 'remove_outliers' or outlier_action == 'replace_outliers':
                        if outlier_method == 'z_score':
                            mean = data[column].mean()
                            std = data[column].std()
                            z_scores = (data[column] - mean) / std
                            outliers = z_scores.abs() > z_score_threshold
                        elif outlier_method == 'iqr':
                            q1 = data[column].quantile(0.25)
                            q3 = data[column].quantile(0.75)
                            iqr = q3 - q1
                            lower_bound = q1 - 1.5 * iqr
                            upper_bound = q3 + 1.5 * iqr
                            outliers = (data[column] < lower_bound) | (data[column] > upper_bound)

                        if outlier_action == 'remove_outliers':
                            data = data[~outliers]
                        elif outlier_action == 'replace_outliers':
                            if replacement_type == 'mean':
                                replacement = data[column].mean()
                            elif replacement_type == 'median':
                                replacement = data[column].median()
                            elif replacement_type == 'mode':
                                replacement = data[column].mode()[0]
                            data.loc[outliers, column] = replacement

                # Save the modified data back to the original file
                data.to_excel(file_path, index=False)  # Save changes to the same file path
                data_file.file_path = file_path  # Update the file path in the database if needed
                db.session.commit()  # Commit changes to the database

                flash("Dataset encoded successfully!", "success")
            
            # Save modified file
            upload_foler = current_app.config['UPLOAD_FOLDER']
            modified_file_path = os.path.join(upload_foler, f"{data_file.filename}")
            data.to_excel(modified_file_path, index=False)
            data_file.file_path = modified_file_path
            db.session.commit()
            flash("Dataset modified successfully!", "success")


        return render_template(
            'prepare_data.html',
            workspace=workspace,
            columns=data.columns,
            selected_column=selected_column,
            statistics=statistics,
            data_type = data_type,
            data=data
        )

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        print("Error1 is:",e)
        return redirect(url_for('workspaces'))



from flask import request, redirect, url_for, flash
import pandas as pd
import pandas as pd
from flask import request, redirect, url_for, flash

@data_preparation_bp.route('/workspace/<int:workspace_id>/prepare/combine_split_columns', methods=['POST'])
def combine_split_columns(workspace_id):
    """
    Handles combining and splitting of columns based on user input.
    """
    workspace = Workspace.query.get_or_404(workspace_id)
    files = File.query.filter_by(workspace_id=workspace_id).all()
    data_file = next((file for file in files if file.filename.endswith(('.xls', '.xlsx'))), None)
    if not data_file:
        return "No Excel file found in the workspace.", 404
    action_type = request.form.get('action_type')  # 'combine' or 'split'


    file_path = data_file.file_path
    data = pd.read_excel(file_path)

    try:
        if action_type == "combine":
            # Combine Columns Logic
            columns_to_combine = request.form.getlist('columns_to_combine')
            delimiter = request.form.get('combine_delimiter', ",")
            new_column_name = request.form.get('new_column_name', "combined_column")

            if not columns_to_combine:
                flash("Please select at least two columns to combine.", "error")
                return redirect(url_for('data_preparation.prepare_data', workspace_id=workspace_id))

            # Combine selected columns into a new column
            data[new_column_name] = data[columns_to_combine].astype(str).agg(delimiter.join, axis=1)

        elif action_type == "split":
            # Split Column Logic
            column_to_split = request.form.get('column_to_split')
            delimiter = request.form.get('split_delimiter', ",")
            new_columns = request.form.get('split_new_columns', "").split(",")
            
            print("reached here ....")
            
            if not column_to_split or not delimiter or not new_columns:
                flash("Please provide a column, delimiter, and new column names for splitting.", "error")
                return redirect(url_for('data_preparation.prepare_data', workspace_id=workspace_id))

            # Perform splitting operation
            split_data = data[column_to_split].str.split(delimiter, expand=True)

            # Map split parts to new column names
            for i, col_name in enumerate(new_columns):
                if i < split_data.shape[1]:  # Only assign if index is valid
                    data[col_name.strip()] = split_data[i]

        else:
            flash("Invalid action type.", "error")
            return redirect(url_for('data_preparation.prepare_data', workspace_id=workspace_id))

        # Save updated data back to the workspace
        print("reached here to save...")
        upload_foler = current_app.config['UPLOAD_FOLDER']
        modified_file_path = os.path.join(upload_foler, f"{data_file.filename}")
        data.to_excel(modified_file_path, index=False)
        data_file.file_path = modified_file_path
        db.session.commit()
        flash("Dataset modified successfully!", "success")

    except Exception as e:
        flash(f"Error processing columns: {str(e)}", "error")

    return redirect(url_for('data_preparation.prepare_data', workspace_id=workspace_id))



@data_preparation_bp.route('/data-preparation/convert-datatype/<int:workspace_id>', methods=['POST'])
def convert_datatype(workspace_id):
    workspace = Workspace.query.get_or_404(workspace_id)
    files = File.query.filter_by(workspace_id=workspace_id).all()
    data_file = next((file for file in files if file.filename.endswith(('.xls', '.xlsx'))), None)
    if not data_file:
        return "No Excel file found in the workspace.", 404

    file_path = data_file.file_path
    data = pd.read_excel(file_path)

    column_name = request.form.get('column_name')
    new_data_type = request.form.get('new_data_type')

    if not column_name or not new_data_type:
        flash("Invalid input for datatype conversion.", "error")
        return redirect(url_for('data_preparation.prepare_data', workspace_id=workspace_id))

    try:
        # Perform datatype conversion
        if new_data_type == "int":
            data[column_name] = data[column_name].astype(int)
        elif new_data_type == "float":
            data[column_name] = data[column_name].astype(float)
        elif new_data_type == "str":
            data[column_name] = data[column_name].astype(str)
        elif new_data_type == "datetime":
            data[column_name] = pd.to_datetime(data[column_name])
        else:
            flash("Unsupported datatype selected.", "error")
            return redirect(url_for('data_preparation.prepare_data', workspace_id=workspace_id))

        flash(f"Column '{column_name}' converted to {new_data_type}.", "success")
        # Save modified file
        print("reached here...")
        upload_foler = current_app.config['UPLOAD_FOLDER']
        modified_file_path = os.path.join(upload_foler, f"{data_file.filename}")
        data.to_excel(modified_file_path, index=False)
        data_file.file_path = modified_file_path
        db.session.commit()
        flash("Dataset modified successfully!", "success")
    except Exception as e:
        flash(f"Error converting column '{column_name}' to {new_data_type}: {str(e)}", "error")
        print("Error in conversion is:",e)
    return redirect(url_for('data_preparation.prepare_data', workspace_id=workspace_id))


@data_preparation_bp.route('/workspace/<int:workspace_id>/prepare/filter', methods=['POST'])
def filter_data(workspace_id):
    workspace = Workspace.query.get_or_404(workspace_id)
    files = File.query.filter_by(workspace_id=workspace_id).all()
    data_file = next((file for file in files if file.filename.endswith(('.xls', '.xlsx'))), None)
    if not data_file:
        return "No Excel file found in the workspace.", 404

    file_path = data_file.file_path
    data = pd.read_excel(file_path)
    # Get the filter criteria from the form
    column_to_filter = request.form.get('filter_column')
    filter_min = request.form.get('filter_min')
    filter_max = request.form.get('filter_max')

    # Convert the min/max values to numeric if provided
    if filter_min:
        filter_min = float(filter_min)
    if filter_max:
        filter_max = float(filter_max)

    # Apply the filter if both min and max are provided
    if filter_min is not None and filter_max is not None:
        filtered_data = data[(data[column_to_filter] >= filter_min) & (data[column_to_filter] <= filter_max)]
    else:
        filtered_data = data
    # Save modified file
    print("reached here...")
    upload_foler = current_app.config['UPLOAD_FOLDER']
    modified_file_path = os.path.join(upload_foler, f"{data_file.filename}")
    filtered_data.to_excel(modified_file_path, index=False)
    data_file.file_path = modified_file_path
    db.session.commit()
    flash("Dataset modified successfully!", "success")
    # Send the filtered data back to the template
    return render_template(
        'prepare_data.html',
        workspace=workspace,
        columns=data.columns.tolist(),
        data=filtered_data
    )
