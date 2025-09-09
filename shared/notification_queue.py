"""
Notification Queue System for Inter-Process Communication
Handles notifications between streaming_data.py and Flask app
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

class NotificationQueue:
    def __init__(self, file_path: str = "shared/notifications.json", max_notifications: int = 100):
        self.file_path = file_path
        self.max_notifications = max_notifications
        self.lock = threading.Lock()
        self._ensure_directory()
        
    def _ensure_directory(self):
        """Ensure the directory exists for the notification file"""
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
    def _read_notifications(self) -> List[Dict[str, Any]]:
        """Read notifications from file"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('notifications', [])
            return []
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            return []
    
    def _write_notifications(self, notifications: List[Dict[str, Any]]):
        """Write notifications to file"""
        try:
            data = {
                'notifications': notifications,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except (PermissionError, OSError) as e:
            print(f"Error writing notifications: {e}")
    
    def add_notification(self, notification_type: str, message: str, device_name: str, 
                        user_id: str = None, status: str = None, **kwargs):
        """Add a new notification to the queue"""
        with self.lock:
            notifications = self._read_notifications()
            
            new_notification = {
                'id': f"{int(time.time()*1000)}_{len(notifications)}",  # Unique ID
                'type': notification_type,
                'message': message,
                'device_name': device_name,
                'user_id': user_id,
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'read': False,
                **kwargs  # Additional data
            }
            
            notifications.append(new_notification)
            
            # Keep only the latest notifications (FIFO)
            if len(notifications) > self.max_notifications:
                notifications = notifications[-self.max_notifications:]
            
            self._write_notifications(notifications)
            return new_notification['id']
    
    def get_notifications(self, limit: int = None, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get notifications from the queue"""
        with self.lock:
            notifications = self._read_notifications()
            
            if unread_only:
                notifications = [n for n in notifications if not n.get('read', False)]
            
            # Sort by timestamp (newest first)
            notifications.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            if limit:
                notifications = notifications[:limit]
                
            return notifications
    
    def mark_as_read(self, notification_ids: List[str] = None):
        """Mark notifications as read"""
        with self.lock:
            notifications = self._read_notifications()
            
            for notification in notifications:
                if notification_ids is None or notification['id'] in notification_ids:
                    notification['read'] = True
            
            self._write_notifications(notifications)
    
    def clear_notifications(self):
        """Clear all notifications"""
        with self.lock:
            self._write_notifications([])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        with self.lock:
            notifications = self._read_notifications()
            
            total = len(notifications)
            unread = len([n for n in notifications if not n.get('read', False)])
            
            # Count by type
            type_counts = {}
            for notification in notifications:
                type_name = notification.get('type', 'unknown')
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            # Count by device
            device_counts = {}
            for notification in notifications:
                device_name = notification.get('device_name', 'unknown')
                device_counts[device_name] = device_counts.get(device_name, 0) + 1
            
            return {
                'total': total,
                'unread': unread,
                'by_type': type_counts,
                'by_device': device_counts,
                'last_notification': notifications[-1] if notifications else None
            }

# Global instance for easy import
notification_queue = NotificationQueue()
