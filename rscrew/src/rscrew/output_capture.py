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
    
    def __init__(self, output_dir: str = "output", max_files: int = 200):
        self.output_dir = Path(output_dir)
        self.max_files = max_files
        self.ensure_output_dir()
    
    def ensure_output_dir(self):
        """Ensure output directory exists"""
        self.output_dir.mkdir(exist_ok=True)
    
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
            return str(filepath)
            
        except Exception as e:
            print(f"[OUTPUT] Error saving output: {e}")
            return ""
    
    def get_recent_files(self, limit: int = 10) -> List[str]:
        """Get list of recent output files"""
        pattern = str(self.output_dir / "*_inquiry-*_*.txt")
        existing_files = glob.glob(pattern)
        
        # Sort by modification time (newest first)
        files_with_time = [(f, os.path.getmtime(f)) for f in existing_files]
        files_with_time.sort(key=lambda x: x[1], reverse=True)
        
        return [os.path.basename(f) for f, _ in files_with_time[:limit]]


# Global instance for easy access
output_capture = OutputCapture()


def capture_output(prompt: str, output: str, working_dir: str = "", command: str = "") -> str:
    """Convenience function to capture output"""
    return output_capture.save_output(prompt, output, working_dir, command)


if __name__ == "__main__":
    # Test the output capture system
    test_prompt = "for some reason test index file is not appear for test.randellconley.com"
    test_output = "This is a test output from the RC command execution..."
    
    capture = OutputCapture()
    filepath = capture.save_output(test_prompt, test_output, "/home/ubuntu/test", "rc test command")
    print(f"Test output saved to: {filepath}")
    
    # Test filename generation
    test_prompts = [
        "Create a REST API for user management",
        "Fix Apache configuration for SSL",
        "Debug database connection issues",
        "Implement authentication system with JWT tokens"
    ]
    
    for prompt in test_prompts:
        filename = capture.generate_filename(prompt)
        print(f"Prompt: {prompt[:50]}...")
        print(f"Filename: {filename}")
        print()