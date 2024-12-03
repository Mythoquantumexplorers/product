
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
    
    print("reched here")

    if request.method == 'POST':
        # Get user inputs
        x_column = request.form.get('x_column')
        y_column = request.form.get('y_column')
        chart_title = request.form.get('chart_title')
        chart_description = request.form.get('chart_description')
        chart_type = request.form.get('chart_type')  # e.g., line, bar, scatter

        # Validate inputs
        if not chart_type or (chart_type not in ['histogram', 'boxplot', 'pie', 'line', 'bar', 'scatter', 'heatmap', 'pairplot', 'violin', 'kde']):
            flash("Invalid or unsupported chart type.", "error")
            return redirect(request.url)

        try:
            plt.style.use('seaborn')  # Improve visual appearance
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

            # Save the chart
            chart_filename = f"chart_{workspace_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png"
            chart_path = os.path.join(app.config['UPLOAD_FOLDER'], chart_filename)
            plt.savefig(chart_path)
            plt.close()

            print("reched here")

            # Generate AI Report
            prompt = f"""
            Analyze the following data and generate a report:
            Chart Title: {chart_title or 'Untitled Chart'}
            Chart Type: {chart_type}
            X-Column: {x_column}, Y-Column: {y_column}

            Data Overview:
            X-Column Values: {df[x_column].head(10).tolist()}
            Y-Column Values: {df[y_column].head(10).tolist()}

            Identify key trends, patterns, or outliers in the data.
            """
            


            genai.configure(api_key="AIzaSyAgtKUZS-HsyvfKLiHDXtK2wc2SRCytSic")
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            print(response.text)
            full_description=(response.text) 
            
            new_chart = Chart(
                title=chart_title or "Untitled Chart",
                description=full_description,
                image_file_path=chart_path,
                workspace_id=workspace_id
            )
            db.session.add(new_chart)
            db.session.commit()

            flash("Chart created successfully!", "success")
            return redirect(url_for('workspace', workspace_id=workspace_id))
        except Exception as e:
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



