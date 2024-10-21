from flask import Flask, render_template, request, jsonify
from commands import VirtualFileSystem, execute_command
import requests

app = Flask(__name__)

vfs = VirtualFileSystem()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute():
    command = request.json['command']
    output = execute_command(command, vfs)
    return jsonify({'output': output})

@app.route('/save_file', methods=['POST'])
def save_file():
    filename = request.json['filename']
    content = request.json['content']
    output = execute_command(f"save_file {filename} {content}", vfs)
    return jsonify({'output': output})

if __name__ == '__main__':
    app.run(debug=True)
