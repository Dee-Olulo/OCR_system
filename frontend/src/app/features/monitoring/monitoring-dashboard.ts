// frontend/src/app/features/monitoring/monitoring-dashboard.component.ts

import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { FolderService } from '../../core/services/folder';
import { WebSocketService } from '../../core/services/websocket';
import { Folder, Task, TaskStats, Notification } from '../../core/models/folder.model';
import { Subscription } from 'rxjs';
import { AddFolderDialogComponent } from './add-folder/add-folder';

@Component({
  selector: 'app-monitoring-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatChipsModule,
    MatSnackBarModule,
    MatBadgeModule,
    MatTooltipModule,
    MatDialogModule
  ],
  templateUrl: './monitoring-dashboard.html',
  styleUrls: ['./monitoring-dashboard.scss']
})
export class MonitoringDashboardComponent implements OnInit, OnDestroy {
  private folderService = inject(FolderService);
  private wsService = inject(WebSocketService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);
  
  folders: Folder[] = [];
  recentTasks: Task[] = [];
  taskStats: TaskStats = {
    total: 0,
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0
  };
  
  isConnected = false;
  notificationCount = 0;
  
  private notificationSubscription?: Subscription;
  private connectionSubscription?: Subscription;
  
  displayedColumns: string[] = ['status', 'task_type', 'created_at', 'actions'];
  
  ngOnInit(): void {
    this.loadData();
    this.setupWebSocket();
    
    // Refresh data every 30 seconds
    setInterval(() => this.loadData(), 30000);
  }
  
  ngOnDestroy(): void {
    this.notificationSubscription?.unsubscribe();
    this.connectionSubscription?.unsubscribe();
    this.wsService.disconnect();
  }
  
  loadData(): void {
    // Load folders
    this.folderService.listFolders().subscribe({
      next: (response) => {
        this.folders = response.folders;
      },
      error: (error) => {
        console.error('Error loading folders:', error);
      }
    });
    
    // Load recent tasks
    this.folderService.listTasks(undefined, 10).subscribe({
      next: (response) => {
        this.recentTasks = response.tasks;
      },
      error: (error) => {
        console.error('Error loading tasks:', error);
      }
    });
    
    // Load task stats
    this.folderService.getTaskStats().subscribe({
      next: (stats) => {
        this.taskStats = stats;
      },
      error: (error) => {
        console.error('Error loading stats:', error);
      }
    });
  }
  
  setupWebSocket(): void {
    // Get user ID from localStorage (you might get this differently)
    const token = localStorage.getItem('access_token');
    if (token) {
      // Decode JWT to get user ID (simplified - you might have an auth service for this)
      const userId = 'user_123'; // Replace with actual user ID
      this.wsService.connect(userId);
    }
    
    // Subscribe to connection status
    this.connectionSubscription = this.wsService.connectionStatus$.subscribe({
      next: (connected) => {
        this.isConnected = connected;
      }
    });
    
    // Subscribe to notifications
    this.notificationSubscription = this.wsService.notifications$.subscribe({
      next: (notification) => {
        if (notification) {
          this.handleNotification(notification);
        }
      }
    });
  }
  
  handleNotification(notification: Notification): void {
    this.notificationCount++;
    
    // Show snackbar
    this.snackBar.open(notification.message, 'View', {
      duration: 5000,
      horizontalPosition: 'end',
      verticalPosition: 'top'
    });
    
    // Reload data
    this.loadData();
  }
  
  openAddFolderDialog(): void {
    const dialogRef = this.dialog.open(AddFolderDialogComponent, {
      width: '600px',
      disableClose: false
    });
    
    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.createFolder(result);
      }
    });
  }
  
  createFolder(folderData: any): void {
    this.folderService.createFolder(folderData).subscribe({
      next: (response) => {
        this.snackBar.open(`Folder "${folderData.name}" created successfully`, 'Close', { duration: 3000 });
        this.loadData();
      },
      error: (error) => {
        this.snackBar.open('Failed to create folder', 'Close', { duration: 3000 });
        console.error('Error creating folder:', error);
      }
    });
  }
  
  startMonitoring(folder: Folder): void {
    this.folderService.startMonitoring(folder.id).subscribe({
      next: () => {
        this.snackBar.open(`Started monitoring: ${folder.name}`, 'Close', { duration: 3000 });
        this.loadData();
      },
      error: (error) => {
        this.snackBar.open('Failed to start monitoring', 'Close', { duration: 3000 });
      }
    });
  }
  
  stopMonitoring(folder: Folder): void {
    this.folderService.stopMonitoring(folder.id).subscribe({
      next: () => {
        this.snackBar.open(`Stopped monitoring: ${folder.name}`, 'Close', { duration: 3000 });
        this.loadData();
      },
      error: (error) => {
        this.snackBar.open('Failed to stop monitoring', 'Close', { duration: 3000 });
      }
    });
  }
  
  retryTask(task: Task): void {
    this.folderService.retryTask(task.id).subscribe({
      next: () => {
        this.snackBar.open('Task queued for retry', 'Close', { duration: 3000 });
        this.loadData();
      },
      error: (error) => {
        this.snackBar.open('Failed to retry task', 'Close', { duration: 3000 });
      }
    });
  }
  
  getStatusColor(status: string): string {
    switch (status) {
      case 'completed': return 'primary';
      case 'processing': return 'accent';
      case 'failed': return 'warn';
      case 'pending': return '';
      default: return '';
    }
  }
  
  getMonitoringCount(): number {
    return this.folders.filter(f => f.is_monitoring).length;
  }
  
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString();
  }
}