from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, Set
import asyncio
from pathlib import Path
import os

class FolderEventHandler(FileSystemEventHandler):
    """Handles file system events for monitored folders"""
    
    def __init__(self, folder_id: str, callback):
        self.folder_id = folder_id
        self.callback = callback
        self.processing_files: Set[str] = set()
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        # Only process supported file types
        supported_ext = ['.jpg', '.jpeg', '.png', '.pdf', '.docx', '.xlsx', '.pptx']
        if not any(event.src_path.lower().endswith(ext) for ext in supported_ext):
            return
        
        # Avoid duplicate processing
        if event.src_path in self.processing_files:
            return
        
        self.processing_files.add(event.src_path)
        
        # Schedule async callback
        asyncio.create_task(self.callback(self.folder_id, event.src_path))

class FolderMonitorService:
    """Service to monitor folders for new documents"""
    
    def __init__(self):
        self.observers: Dict[str, Observer] = {} # pyright: ignore[reportInvalidTypeForm]
        self.handlers: Dict[str, FolderEventHandler] = {}
    
    async def start_monitoring(self, folder_id: str, folder_path: str, callback):
        """Start monitoring a folder"""
        
        # Stop existing monitor if any
        await self.stop_monitoring(folder_id)
        
        # Create folder if doesn't exist
        Path(folder_path).mkdir(parents=True, exist_ok=True)
        
        # Create event handler
        handler = FolderEventHandler(folder_id, callback)
        self.handlers[folder_id] = handler
        
        # Create and start observer
        observer = Observer()
        observer.schedule(handler, folder_path, recursive=False)
        observer.start()
        
        self.observers[folder_id] = observer
        
        print(f"✓ Started monitoring folder: {folder_path}")
        return True
    
    async def stop_monitoring(self, folder_id: str):
        """Stop monitoring a folder"""
        if folder_id in self.observers:
            self.observers[folder_id].stop()
            self.observers[folder_id].join()
            del self.observers[folder_id]
            print(f"✓ Stopped monitoring folder: {folder_id}")
    
    def is_monitoring(self, folder_id: str) -> bool:
        """Check if folder is being monitored"""
        return folder_id in self.observers and self.observers[folder_id].is_alive()
    
    async def shutdown(self):
        """Stop all monitors"""
        for folder_id in list(self.observers.keys()):
            await self.stop_monitoring(folder_id)

# Global instance
folder_monitor_service = FolderMonitorService()