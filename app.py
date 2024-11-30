from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)

# Route for the home page
@app.route('/')
def home():
    return render_template('home.html')

# Route for the about page
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        # TODO: implement logic of login 
        return redirect('/workspaces')
    return render_template('login.html')

@app.route('/workspaces')
def workspaces():
    return render_template('workspaces.html',active_page='workspace')

@app.route('/dashboards')
def dashboards():
    dashboard_data = [
        {'title': 'Sales Overview', 'description': 'A comprehensive overview of sales metrics.', 'date': 'Nov 28, 2024'},
        {'title': 'Customer Insights', 'description': 'Analyze customer behavior and demographics.', 'date': 'Nov 25, 2024'},
    ]
    return render_template('dashboards.html', dashboards=dashboard_data, active_page='dashboards')


@app.route('/reports')
def reports():
    return render_template('reports.html',active_page='reports')    



if __name__ == '__main__':
    app.run(debug=True)
