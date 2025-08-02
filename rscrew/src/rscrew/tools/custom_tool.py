from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
import json
from pathlib import Path


class ReadFileInput(BaseModel):
    """Input schema for ReadFile tool."""
    file_path: str = Field(..., description="Path to the file to read (relative or absolute)")

class ReadFile(BaseTool):
    name: str = "read_file"
    description: str = (
        "Read the contents of a file. Use this to examine code, configuration files, "
        "documentation, or any text-based files in the project or execution directory."
    )
    args_schema: Type[BaseModel] = ReadFileInput

    def _run(self, file_path: str) -> str:
        try:
            # Convert to absolute path if relative
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"File: {file_path}\nContent:\n{content}"
        except FileNotFoundError:
            return f"Error: File '{file_path}' not found."
        except PermissionError:
            return f"Error: Permission denied reading '{file_path}'."
        except UnicodeDecodeError:
            return f"Error: Cannot read '{file_path}' - appears to be a binary file."
        except Exception as e:
            return f"Error reading file '{file_path}': {str(e)}"


class WriteFileInput(BaseModel):
    """Input schema for WriteFile tool."""
    file_path: str = Field(..., description="Path to the file to write (relative or absolute)")
    content: str = Field(..., description="Content to write to the file")

class WriteFile(BaseTool):
    name: str = "write_file"
    description: str = (
        "Write content to a file. Use this to create new files or update existing ones "
        "with improved code, documentation, or configuration."
    )
    args_schema: Type[BaseModel] = WriteFileInput

    def _run(self, file_path: str, content: str) -> str:
        try:
            # Convert to absolute path if relative
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"Successfully wrote to file: {file_path}"
        except PermissionError:
            return f"Error: Permission denied writing to '{file_path}'."
        except Exception as e:
            return f"Error writing to file '{file_path}': {str(e)}"


class ListDirectoryInput(BaseModel):
    """Input schema for ListDirectory tool."""
    directory_path: str = Field(..., description="Path to the directory to list (relative or absolute)")

class ListDirectory(BaseTool):
    name: str = "list_directory"
    description: str = (
        "List files and directories in a given path. Use this to explore project structure "
        "and understand the organization of files."
    )
    args_schema: Type[BaseModel] = ListDirectoryInput

    def _run(self, directory_path: str) -> str:
        try:
            # Convert to absolute path if relative
            if not os.path.isabs(directory_path):
                directory_path = os.path.abspath(directory_path)
            
            if not os.path.exists(directory_path):
                return f"Error: Directory '{directory_path}' does not exist."
            
            if not os.path.isdir(directory_path):
                return f"Error: '{directory_path}' is not a directory."
            
            items = []
            for item in sorted(os.listdir(directory_path)):
                item_path = os.path.join(directory_path, item)
                if os.path.isdir(item_path):
                    items.append(f"📁 {item}/")
                else:
                    size = os.path.getsize(item_path)
                    items.append(f"📄 {item} ({size} bytes)")
            
            if not items:
                return f"Directory '{directory_path}' is empty."
            
            return f"Contents of '{directory_path}':\n" + "\n".join(items)
        except PermissionError:
            return f"Error: Permission denied accessing '{directory_path}'."
        except Exception as e:
            return f"Error listing directory '{directory_path}': {str(e)}"


class FindFilesInput(BaseModel):
    """Input schema for FindFiles tool."""
    pattern: str = Field(..., description="File pattern to search for (e.g., '*.py', '*.md', 'config*')")
    directory: str = Field(default=".", description="Directory to search in (default: current directory)")

class FindFiles(BaseTool):
    name: str = "find_files"
    description: str = (
        "Find files matching a pattern in a directory and its subdirectories. "
        "Use this to locate specific types of files or files with certain names."
    )
    args_schema: Type[BaseModel] = FindFilesInput

    def _run(self, pattern: str, directory: str = ".") -> str:
        try:
            import glob
            
            # Convert to absolute path if relative
            if not os.path.isabs(directory):
                directory = os.path.abspath(directory)
            
            # Search for files matching the pattern
            search_pattern = os.path.join(directory, "**", pattern)
            matches = glob.glob(search_pattern, recursive=True)
            
            if not matches:
                return f"No files matching '{pattern}' found in '{directory}' and its subdirectories."
            
            # Sort and format results
            matches.sort()
            result_lines = [f"Found {len(matches)} files matching '{pattern}':"]
            for match in matches:
                rel_path = os.path.relpath(match, directory)
                size = os.path.getsize(match) if os.path.isfile(match) else 0
                result_lines.append(f"  📄 {rel_path} ({size} bytes)")
            
            return "\n".join(result_lines)
        except Exception as e:
            return f"Error searching for files: {str(e)}"


class GetFileInfoInput(BaseModel):
    """Input schema for GetFileInfo tool."""
    file_path: str = Field(..., description="Path to the file to get information about")

class GetFileInfo(BaseTool):
    name: str = "get_file_info"
    description: str = (
        "Get detailed information about a file including size, modification time, "
        "and basic content analysis for code files."
    )
    args_schema: Type[BaseModel] = GetFileInfoInput

    def _run(self, file_path: str) -> str:
        try:
            # Convert to absolute path if relative
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            if not os.path.exists(file_path):
                return f"Error: File '{file_path}' does not exist."
            
            stat = os.stat(file_path)
            size = stat.st_size
            mtime = stat.st_mtime
            
            import datetime
            mod_time = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            info = [
                f"File: {file_path}",
                f"Size: {size} bytes",
                f"Modified: {mod_time}",
            ]
            
            # Add content analysis for text files
            if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.md', '.txt', '.yaml', '.yml', '.json', '.xml', '.html', '.css')):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        info.append(f"Lines: {len(lines)}")
                        
                        # Count non-empty lines
                        non_empty = sum(1 for line in lines if line.strip())
                        info.append(f"Non-empty lines: {non_empty}")
                        
                        # Basic language detection
                        if file_path.endswith('.py'):
                            info.append("Type: Python source code")
                        elif file_path.endswith(('.js', '.ts')):
                            info.append("Type: JavaScript/TypeScript source code")
                        elif file_path.endswith('.md'):
                            info.append("Type: Markdown documentation")
                        elif file_path.endswith(('.yaml', '.yml')):
                            info.append("Type: YAML configuration")
                        elif file_path.endswith('.json'):
                            info.append("Type: JSON data")
                        
                except UnicodeDecodeError:
                    info.append("Type: Binary file")
            
            return "\n".join(info)
        except Exception as e:
            return f"Error getting file info: {str(e)}"
