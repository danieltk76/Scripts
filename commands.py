import os
import time
import random
import shlex
import requests
import base64
import subprocess

class VirtualFileSystem:
    def __init__(self):
        self.root = {
            'home': {
                'user': {
                    'documents': {'file1.txt': 'Content of file1', 'file2.txt': 'Content of file2'},
                    'downloads': {},
                    '.bashrc': 'export PATH=$PATH:/usr/local/bin',
                    'hello.py': 'output = "Hello, World!"',
                    'greet.sh': 'echo "Hello from Bash!"'
                }
            },
            'etc': {'hosts': '127.0.0.1 localhost'},
            'var': {'log': {'syslog': 'System log content'}},
            'usr': {'bin': {}, 'local': {'bin': {}}}
        }
        self.current_dir = ['home', 'user']
        self.env_vars = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/home/user'}

    def get_current_path(self):
        return '/' + '/'.join(self.current_dir)

    def resolve_path(self, path):
        if path.startswith('/'):
            return path.strip('/').split('/')
        else:
            return self.current_dir + path.split('/')

    def dir_exists(self, path):
        current = self.root
        for dir in path:
            if dir in current and isinstance(current[dir], dict):
                current = current[dir]
            else:
                return False
        return True

    def get_dir_contents(self, path):
        current = self.root
        for dir in path:
            current = current[dir]
        return current

class Commands:
    def __init__(self, vfs):
        self.vfs = vfs

    def cd(self, args):
        if not args:
            path = self.vfs.env_vars['HOME']
        else:
            path = args[0]
        
        new_path = self.vfs.resolve_path(path)
        if self.vfs.dir_exists(new_path):
            self.vfs.current_dir = new_path
            return f"Changed to {self.vfs.get_current_path()}"
        else:
            return f"cd: {path}: No such file or directory"

    def ls(self, args):
        path = self.vfs.current_dir if not args else self.vfs.resolve_path(args[0])
        if self.vfs.dir_exists(path):
            contents = self.vfs.get_dir_contents(path)
            return ' '.join(contents.keys())
        else:
            return f"ls: cannot access '{args[0]}': No such file or directory"

    def pwd(self, args):
        return self.vfs.get_current_path()

    def cat(self, args):
        if not args:
            return "cat: missing operand"
        path = self.vfs.resolve_path(args[0])
        parent_path, filename = path[:-1], path[-1]
        if self.vfs.dir_exists(parent_path):
            parent_dir = self.vfs.get_dir_contents(parent_path)
            if filename in parent_dir and isinstance(parent_dir[filename], str):
                return parent_dir[filename]
            else:
                return f"cat: {args[0]}: No such file"
        else:
            return f"cat: {args[0]}: No such file or directory"

    def echo(self, args):
        if '>' in args:
            output_index = args.index('>')
            content = ' '.join(args[:output_index])
            filename = args[output_index + 1]
            mode = 'w'  # overwrite by default
            if output_index > 0 and args[output_index - 1] == '>>':
                mode = 'a'  # append mode
            return self.save_file([filename, content, mode])
        else:
            return ' '.join(args)

    def mkdir(self, args):
        if not args:
            return "mkdir: missing operand"
        path = self.vfs.resolve_path(args[0])
        parent_path, new_dir = path[:-1], path[-1]
        if self.vfs.dir_exists(parent_path):
            parent_dir = self.vfs.get_dir_contents(parent_path)
            if new_dir not in parent_dir:
                parent_dir[new_dir] = {}
                return f"Directory '{args[0]}' created"
            else:
                return f"mkdir: cannot create directory '{args[0]}': File exists"
        else:
            return f"mkdir: cannot create directory '{args[0]}': No such file or directory"

    def touch(self, args):
        if not args:
            return "touch: missing file operand"
        path = self.vfs.resolve_path(args[0])
        parent_path, filename = path[:-1], path[-1]
        if self.vfs.dir_exists(parent_path):
            parent_dir = self.vfs.get_dir_contents(parent_path)
            if filename not in parent_dir:
                parent_dir[filename] = ''
                return f"File '{args[0]}' created"
            else:
                return f"touch: cannot touch '{args[0]}': File exists"
        else:
            return f"touch: cannot touch '{args[0]}': No such file or directory"

    def rm(self, args):
        if not args:
            return "rm: missing operand"
        path = self.vfs.resolve_path(args[0])
        parent_path, filename = path[:-1], path[-1]
        if self.vfs.dir_exists(parent_path):
            parent_dir = self.vfs.get_dir_contents(parent_path)
            if filename in parent_dir:
                del parent_dir[filename]
                return f"Removed '{args[0]}'"
            else:
                return f"rm: cannot remove '{args[0]}': No such file or directory"
        else:
            return f"rm: cannot remove '{args[0]}': No such file or directory"

    def mv(self, args):
        if len(args) != 2:
            return "mv: missing file operand"
        source = self.vfs.resolve_path(args[0])
        dest = self.vfs.resolve_path(args[1])
        source_parent, source_name = source[:-1], source[-1]
        dest_parent, dest_name = dest[:-1], dest[-1]
        
        if self.vfs.dir_exists(source_parent) and self.vfs.dir_exists(dest_parent):
            source_dir = self.vfs.get_dir_contents(source_parent)
            dest_dir = self.vfs.get_dir_contents(dest_parent)
            if source_name in source_dir:
                dest_dir[dest_name] = source_dir[source_name]
                del source_dir[source_name]
                return f"Moved '{args[0]}' to '{args[1]}'"
            else:
                return f"mv: cannot stat '{args[0]}': No such file or directory"
        else:
            return f"mv: cannot move '{args[0]}' to '{args[1]}': No such file or directory"

    def cp(self, args):
        if len(args) != 2:
            return "cp: missing file operand"
        source = self.vfs.resolve_path(args[0])
        dest = self.vfs.resolve_path(args[1])
        source_parent, source_name = source[:-1], source[-1]
        dest_parent, dest_name = dest[:-1], dest[-1]
        
        if self.vfs.dir_exists(source_parent) and self.vfs.dir_exists(dest_parent):
            source_dir = self.vfs.get_dir_contents(source_parent)
            dest_dir = self.vfs.get_dir_contents(dest_parent)
            if source_name in source_dir:
                dest_dir[dest_name] = source_dir[source_name]
                return f"Copied '{args[0]}' to '{args[1]}'"
            else:
                return f"cp: cannot stat '{args[0]}': No such file or directory"
        else:
            return f"cp: cannot copy '{args[0]}' to '{args[1]}': No such file or directory"

    def grep(self, args):
        if len(args) < 2:
            return "grep: missing operand"
        pattern = args[0]
        filename = args[1]
        path = self.vfs.resolve_path(filename)
        parent_path, filename = path[:-1], path[-1]
        if self.vfs.dir_exists(parent_path):
            parent_dir = self.vfs.get_dir_contents(parent_path)
            if filename in parent_dir and isinstance(parent_dir[filename], str):
                content = parent_dir[filename]
                matches = [line for line in content.split('\n') if pattern in line]
                return '\n'.join(matches) if matches else ''
            else:
                return f"grep: {filename}: No such file or directory"
        else:
            return f"grep: {filename}: No such file or directory"

    def chmod(self, args):
        return "chmod: Operation not permitted in this virtual environment"

    def chown(self, args):
        return "chown: Operation not permitted in this virtual environment"

    def ps(self, args):
        processes = [
            "PID TTY          TIME CMD",
            "  1 ?        00:00:01 systemd",
            "  2 ?        00:00:00 kthreadd",
            "  3 ?        00:00:00 rcu_gp",
            "  4 ?        00:00:00 rcu_par_gp",
            "  6 ?        00:00:00 kworker/0:0H-kblockd",
            "  8 ?        00:00:00 mm_percpu_wq",
            "  9 ?        00:00:00 ksoftirqd/0",
            " 10 ?        00:00:00 rcu_sched",
            " 11 ?        00:00:00 migration/0",
            " 12 ?        00:00:00 idle_inject/0"
        ]
        return '\n'.join(processes)

    def top(self, args):
        return "top: Command not available in this virtual environment"

    def df(self, args):
        df_output = [
            "Filesystem     1K-blocks      Used Available Use% Mounted on",
            "/dev/sda1       41251136  12348908  26786844  32% /",
            "tmpfs            1639732         0   1639732   0% /dev/shm",
            "/dev/sda2      204800000 102400000 102400000  50% /home"
        ]
        return '\n'.join(df_output)

    def free(self, args):
        free_output = [
            "              total        used        free      shared  buff/cache   available",
            "Mem:        8201468     3123456     2145678      234567     2932334     4567890",
            "Swap:       2097152      123456     1973696"
        ]
        return '\n'.join(free_output)

    def uname(self, args):
        return "Linux virtual 5.4.0-42-generic #46-Ubuntu SMP Fri Jul 10 00:24:02 UTC 2020 x86_64 x86_64 x86_64 GNU/Linux"

    def whoami(self, args):
        return "user"

    def date(self, args):
        return time.strftime("%a %b %d %H:%M:%S %Z %Y", time.localtime())

    def help(self, args):
        commands = [
            "cd", "ls", "pwd", "cat", "echo", "mkdir", "touch", "rm", "mv", "cp",
            "grep", "chmod", "chown", "ps", "top", "df", "free", "uname", "whoami",
            "date", "help", "clear", "git", "sudo", "python", "bash", "nano"
        ]
        return "Available commands: " + ", ".join(commands)

    def git(self, args):
        if len(args) < 1:
            return "usage: git <command> [<args>]"
        
        if args[0] == "clone":
            if len(args) < 2:
                return "usage: git clone <repository>"
            
            repo_url = args[1]
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            
            try:
                # Simulate cloning by fetching the repository contents
                api_url = f"https://api.github.com/repos/{'/'.join(repo_url.split('/')[-2:]).replace('.git', '')}/contents"
                response = requests.get(api_url)
                response.raise_for_status()
                
                files = response.json()
                cloned_files = {}
                
                for file in files:
                    if file['type'] == 'file':
                        file_content = requests.get(file['download_url']).text
                        cloned_files[file['name']] = file_content
                
                # Add the cloned repository to the virtual file system
                current_dir = self.vfs.get_dir_contents(self.vfs.current_dir)
                current_dir[repo_name] = cloned_files
                
                return f"Cloned '{repo_url}' into '{repo_name}'"
            except requests.exceptions.RequestException as e:
                return f"Error cloning repository: {str(e)}"
        else:
            return f"git {args[0]}: command not implemented"

    def clear(self, args):
        return "CLEAR_TERMINAL"

    def sudo(self, args):
        if not args:
            return "sudo: a command is required"
        command = " ".join(args)
        return f"[Simulated sudo] Executing: {command}\nPassword: ********\nCommand executed with root privileges."

    def python(self, args):
        if not args:
            return "python: file name is required"
        filename = args[0]
        path = self.vfs.resolve_path(filename)
        parent_path, filename = path[:-1], path[-1]
        if self.vfs.dir_exists(parent_path):
            parent_dir = self.vfs.get_dir_contents(parent_path)
            if filename in parent_dir and filename.endswith('.py'):
                content = parent_dir[filename]
                try:
                    # Execute the Python code in a safe environment
                    local_vars = {}
                    exec(content, {}, local_vars)
                    return f"Executed {filename}\nOutput: {local_vars.get('output', 'No output')}"
                except Exception as e:
                    return f"Error executing {filename}: {str(e)}"
            else:
                return f"python: can't open file '{filename}': [Errno 2] No such file or directory"
        else:
            return f"python: can't open file '{filename}': [Errno 2] No such file or directory"

    def bash(self, args):
        if not args:
            return "bash: file name is required"
        filename = args[0]
        path = self.vfs.resolve_path(filename)
        parent_path, filename = path[:-1], path[-1]
        if self.vfs.dir_exists(parent_path):
            parent_dir = self.vfs.get_dir_contents(parent_path)
            if filename in parent_dir and filename.endswith('.sh'):
                content = parent_dir[filename]
                try:
                    # Execute the bash script in a controlled environment
                    result = subprocess.run(['bash', '-c', content], capture_output=True, text=True, timeout=5)
                    return f"Executed {filename}\nOutput:\n{result.stdout}\nErrors:\n{result.stderr}"
                except subprocess.TimeoutExpired:
                    return f"Error: {filename} execution timed out"
                except Exception as e:
                    return f"Error executing {filename}: {str(e)}"
            else:
                return f"bash: {filename}: No such file or directory"
        else:
            return f"bash: {filename}: No such file or directory"

    def nano(self, args):
        if not args:
            return "nano: filename is required"
        filename = args[0]
        path = self.vfs.resolve_path(filename)
        parent_path, filename = path[:-1], path[-1]
        if self.vfs.dir_exists(parent_path):
            parent_dir = self.vfs.get_dir_contents(parent_path)
            content = parent_dir.get(filename, '')
            return f"EDIT_FILE:{filename}:{content}"
        else:
            return f"nano: {filename}: No such file or directory"

    def save_file(self, args):
        if len(args) < 2:
            return "save_file: invalid arguments"
        filename, content = args[0], args[1]
        mode = args[2] if len(args) > 2 else 'w'
        path = self.vfs.resolve_path(filename)
        parent_path, filename = path[:-1], path[-1]
        if self.vfs.dir_exists(parent_path):
            parent_dir = self.vfs.get_dir_contents(parent_path)
            if mode == 'a' and filename in parent_dir:
                parent_dir[filename] += content
            else:
                parent_dir[filename] = content
            return f"File '{filename}' updated successfully"
        else:
            return f"save_file: {filename}: No such file or directory"

    def python3(self, args):
        if not args:
            return "python3: file name is required"
        filename = args[0]
        path = self.vfs.resolve_path(filename)
        parent_path, filename = path[:-1], path[-1]
        if self.vfs.dir_exists(parent_path):
            parent_dir = self.vfs.get_dir_contents(parent_path)
            if filename in parent_dir and filename.endswith('.py'):
                content = parent_dir[filename]
                try:
                    # Execute the Python code in a safe environment
                    local_vars = {}
                    exec(content, {}, local_vars)
                    return f"Executed {filename}\nOutput: {local_vars.get('output', 'No output')}"
                except Exception as e:
                    return f"Error executing {filename}: {str(e)}"
            else:
                return f"python3: can't open file '{filename}': [Errno 2] No such file or directory"
        else:
            return f"python3: can't open file '{filename}': [Errno 2] No such file or directory"

def execute_command(command, vfs):
    cmd = Commands(vfs)
    args = shlex.split(command)
    command_name = args[0]
    command_args = args[1:]

    if hasattr(cmd, command_name):
        return getattr(cmd, command_name)(command_args)
    else:
        return f"Command not found: {command_name}"

