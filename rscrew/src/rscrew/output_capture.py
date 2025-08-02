"""
Console Output Capture System for RSCrew

Automatically captures and saves console output from RC command executions
with contextual naming and metadata tracking.
"""

import os
import re
import glob
from datetime import datetime
from typing import Optional, List
from pathlib import Path


class OutputCapture:
    """Handles automatic capture and storage of console output"""
    
    def __init__(self, output_dir: Optional[str] = None, max_files: int = 200):
        if output_dir is None:
            # Auto-detect project root and use its output directory
            project_root = self.find_project_root()
            if project_root:
                self.output_dir = project_root / "output"
                self.output_source = "project"
            else:
                # Fallback to user's home directory
                self.output_dir = Path.home() / ".rscrew" / "output"
                self.output_source = "fallback"
        else:
            self.output_dir = Path(output_dir)
            self.output_source = "custom"
        
        self.max_files = max_files
        self.ensure_output_dir()
    
    def find_project_root(self) -> Optional[Path]:
        """Find RSCrew project root by looking for pyproject.toml with rscrew content"""
        # Start from the module's location
        current_path = Path(__file__).parent
        
        # Walk up the directory tree looking for pyproject.toml
        for parent in [current_path] + list(current_path.parents):
            pyproject_path = parent / "pyproject.toml"
            if pyproject_path.exists():
                try:
                    with open(pyproject_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        # Check if this is the RSCrew project
                        if 'rscrew' in content and ('name' in content or 'project' in content):
                            return parent
                except Exception:
                    continue
        
        # Also check common RSCrew installation paths
        common_paths = [
            Path("/home/ubuntu/environment/rsc02/rscrew"),
            Path("/home/ubuntu/environment/workbench/rsc02/rscrew"),
        ]
        
        for path in common_paths:
            if path.exists() and (path / "pyproject.toml").exists():
                try:
                    with open(path / "pyproject.toml", 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        if 'rscrew' in content:
                            return path
                except Exception:
                    continue
        
        return None
    
    def ensure_output_dir(self):
        """Ensure output directory exists with proper error handling"""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Provide feedback about where outputs will be saved
            if self.output_source == "project":
                print(f"[OUTPUT] Using project output directory: {self.output_dir}")
            elif self.output_source == "fallback":
                print(f"[OUTPUT] Using fallback output directory: {self.output_dir}")
            elif self.output_source == "custom":
                print(f"[OUTPUT] Using custom output directory: {self.output_dir}")
                
        except PermissionError as e:
            print(f"[OUTPUT] ERROR: Permission denied creating output directory: {self.output_dir}")
            print(f"[OUTPUT] Error details: {e}")
            
            # Try fallback to temp directory
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "rscrew_output"
            try:
                temp_dir.mkdir(parents=True, exist_ok=True)
                self.output_dir = temp_dir
                self.output_source = "temp"
                print(f"[OUTPUT] Using temporary directory as fallback: {self.output_dir}")
            except Exception as temp_error:
                print(f"[OUTPUT] CRITICAL: Cannot create any output directory: {temp_error}")
                raise
                
        except Exception as e:
            print(f"[OUTPUT] ERROR: Failed to create output directory: {e}")
            raise
    
    def generate_context_summary(self, prompt: str, max_length: int = 40) -> str:
        """Generate a contextual summary for filename from user prompt"""
        # Convert to lowercase and extract meaningful words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', prompt.lower())
        
        # Filter out common words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
            'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy',
            'did', 'she', 'use', 'her', 'way', 'many', 'oil', 'sit', 'set', 'run',
            'some', 'want', 'with', 'have', 'this', 'will', 'your', 'from', 'they',
            'know', 'want', 'been', 'good', 'much', 'said', 'each', 'make', 'most',
            'over', 'such', 'very', 'what', 'well', 'were', 'here', 'just', 'like',
            'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well',
            'were', 'when', 'where', 'which', 'while', 'would', 'there', 'could',
            'should', 'something', 'anything', 'everything', 'nothing', 'someone',
            'anyone', 'everyone', 'please', 'need', 'want', 'create', 'build'
        }
        
        # Keep meaningful words
        meaningful_words = [word for word in words if word not in stop_words and len(word) >= 3]
        
        # Take first 3-4 most relevant words
        context_words = meaningful_words[:4]
        
        if not context_words:
            # Fallback to first few words if no meaningful words found
            fallback_words = prompt.lower().split()[:3]
            context_words = [re.sub(r'[^a-z0-9]', '', word) for word in fallback_words if word]
        
        # Join with hyphens and limit length
        context = '-'.join(context_words)
        if len(context) > max_length:
            context = context[:max_length].rstrip('-')
        
        return context or 'general-inquiry'
    
    def get_next_inquiry_number(self) -> int:
        """Get the next inquiry number based on existing files"""
        pattern = str(self.output_dir / "*_inquiry-*_*.txt")
        existing_files = glob.glob(pattern)
        
        if not existing_files:
            return 1
        
        # Extract inquiry numbers from existing files
        numbers = []
        for file_path in existing_files:
            filename = os.path.basename(file_path)
            match = re.search(r'inquiry-(\d+)', filename)
            if match:
                numbers.append(int(match.group(1)))
        
        return max(numbers, default=0) + 1
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        # Replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '-', filename)
        # Replace multiple hyphens with single hyphen
        filename = re.sub(r'-+', '-', filename)
        # Remove leading/trailing hyphens
        filename = filename.strip('-')
        return filename
    
    def generate_filename(self, prompt: str) -> str:
        """Generate contextual filename for output"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        inquiry_num = self.get_next_inquiry_number()
        context = self.generate_context_summary(prompt)
        
        filename = f"{timestamp}_inquiry-{inquiry_num:03d}_{context}.txt"
        return self.sanitize_filename(filename)
    
    def cleanup_old_files(self):
        """Remove oldest files if we exceed max_files limit"""
        pattern = str(self.output_dir / "*_inquiry-*_*.txt")
        existing_files = glob.glob(pattern)
        
        if len(existing_files) <= self.max_files:
            return
        
        # Sort by modification time (oldest first)
        files_with_time = [(f, os.path.getmtime(f)) for f in existing_files]
        files_with_time.sort(key=lambda x: x[1])
        
        # Remove oldest files
        files_to_remove = len(existing_files) - self.max_files
        for file_path, _ in files_with_time[:files_to_remove]:
            try:
                os.remove(file_path)
                print(f"[OUTPUT] Removed old file: {os.path.basename(file_path)}")
            except OSError:
                pass  # Ignore errors when removing files
    
    def save_output(self, prompt: str, output: str, working_dir: str = "", command: str = "") -> str:
        """Save console output with metadata"""
        filename = self.generate_filename(prompt)
        filepath = self.output_dir / filename
        
        # Create metadata header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"""=== RSCrew Console Output ===
Timestamp: {timestamp}
Command: {command or 'rc ' + prompt[:50] + ('...' if len(prompt) > 50 else '')}
Initial Prompt: {prompt}
Working Directory: {working_dir or os.getcwd()}
=== Output Start ===
"""
        
        footer = "\n=== Output End ==="
        
        # Write file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(header)
                f.write(output)
                f.write(footer)
            
            # Cleanup old files
            self.cleanup_old_files()
            
            print(f"[OUTPUT] Saved to: {filename}")
            print(f"[OUTPUT] Full path: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"[OUTPUT] Error saving output to {filepath}: {e}")
            return ""
    
    def get_recent_files(self, limit: int = 10) -> List[str]:
        """Get list of recent output files"""
        pattern = str(self.output_dir / "*_inquiry-*_*.txt")
        existing_files = glob.glob(pattern)
        
        # Sort by modification time (newest first)
        files_with_time = [(f, os.path.getmtime(f)) for f in existing_files]
        files_with_time.sort(key=lambda x: x[1], reverse=True)
        
        return [os.path.basename(f) for f, _ in files_with_time[:limit]]


# Global instance for easy access (lazy initialization)
_output_capture_instance = None


def get_output_capture() -> OutputCapture:
    """Get or create the global output capture instance"""
    global _output_capture_instance
    if _output_capture_instance is None:
        _output_capture_instance = OutputCapture()
    return _output_capture_instance


def capture_output(prompt: str, output: str, working_dir: str = "", command: str = "") -> str:
    """Convenience function to capture output"""
    return get_output_capture().save_output(prompt, output, working_dir, command)


if __name__ == "__main__":
    # Test the output capture system
    test_prompt = "for some reason test index file is not appear for test.randellconley.com"
    test_output = "This is a test output from the RC command execution..."
    
    # Test the new auto-detection functionality
    print("=== Testing OutputCapture Auto-Detection ===")
    capture = OutputCapture()
    print(f"Output directory: {capture.output_dir}")
    print(f"Output source: {capture.output_source}")
    
    filepath = capture.save_output(test_prompt, test_output, "/home/ubuntu/test", "rc test command")
    print(f"Test output saved to: {filepath}")
    
    # Test filename generation
    test_prompts = [
        "Create a REST API for user management",
        "Fix Apache configuration for SSL", 
        "Debug database connection issues",
        "Implement authentication system with JWT tokens"
    ]
    
    print("\n=== Testing Filename Generation ===")
    for prompt in test_prompts:
        filename = capture.generate_filename(prompt)
        print(f"Prompt: {prompt[:50]}...")
        print(f"Filename: {filename}")
        print()
    
    # Test project root detection
    print("=== Testing Project Root Detection ===")
    project_root = capture.find_project_root()
    print(f"Detected project root: {project_root}")
    
    # Test convenience function
    print("\n=== Testing Convenience Function ===")
    test_filepath = capture_output("Test convenience function", "Test output content")
    print(f"Convenience function result: {test_filepath}")