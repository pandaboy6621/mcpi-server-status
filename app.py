import json, os
from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    if os.path.exists("status.json"):
        with open("status.json", "r") as f:
            servers = json.load(f)
    else:
        servers = []

    html_template = """
    <html>
    <head>
        <title>MCPI Server List</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; margin: 40px; background: #222; color: white; }
            table { width: 100%; border-collapse: collapse; background: #333; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #444; }
            th { background-color: #4CAF50; color: white; }
            .online { color: #4af626; font-weight: bold; }
            .offline { color: #ff4444; }
        </style>
    </head>
    <body>
        <h1>MCPI Server Status</h1>
        <table>
            <tr>
                <th>Address</th>
                <th>Status</th>
                <th>Server Name</th>
            </tr>
            {% for server in servers %}
            <tr>
                <td>{{ server.address }}</td>
                <td class="{{ server.status.lower() }}">{{ server.status }}</td>
                <td>{{ server.name if server.name else '---' }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html_template, servers=servers)

if __name__ == "__main__":
    app.run(debug=True)