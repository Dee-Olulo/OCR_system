// frontend/src/app/core/services/folder.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Folder, FolderCreate, Task, TaskStats } from '../models/folder.model';

@Injectable({
  providedIn: 'root'
})
export class FolderService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/folders`;
  private taskUrl = `${environment.apiUrl}/tasks`;
  
  // Folder Management
  createFolder(folderData: FolderCreate): Observable<any> {
    return this.http.post(this.apiUrl, folderData);
  }
  
  listFolders(): Observable<{ folders: Folder[] }> {
    return this.http.get<{ folders: Folder[] }>(this.apiUrl);
  }
  
  startMonitoring(folderId: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/${folderId}/start`, {});
  }
  
  stopMonitoring(folderId: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/${folderId}/stop`, {});
  }
  
  deleteFolder(folderId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${folderId}`);
  }
  
  // Task Management
  listTasks(status?: string, limit: number = 50): Observable<{ tasks: Task[], total: number }> {
    let url = `${this.taskUrl}?limit=${limit}`;
    if (status) {
      url += `&status=${status}`;
    }
    return this.http.get<{ tasks: Task[], total: number }>(url);
  }
  
  getTask(taskId: string): Observable<Task> {
    return this.http.get<Task>(`${this.taskUrl}/${taskId}`);
  }
  
  retryTask(taskId: string): Observable<any> {
    return this.http.post(`${this.taskUrl}/${taskId}/retry`, {});
  }
  
  deleteTask(taskId: string): Observable<any> {
    return this.http.delete(`${this.taskUrl}/${taskId}`);
  }
  
  getTaskStats(): Observable<TaskStats> {
    return this.http.get<TaskStats>(`${this.taskUrl}/stats/summary`);
  }
  
  cancelPendingTasks(): Observable<any> {
    return this.http.post(`${this.taskUrl}/batch/cancel`, {});
  }
  
  cleanupOldTasks(days: number = 30): Observable<any> {
    return this.http.delete(`${this.taskUrl}/batch/cleanup?days=${days}`);
  }
}