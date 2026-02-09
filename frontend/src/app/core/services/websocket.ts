// frontend/src/app/core/services/websocket.service.ts

import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Notification } from '../models/folder.model';

@Injectable({
  providedIn: 'root'
})
export class WebSocketService {
  private socket: WebSocket | null = null;
  private notificationsSubject = new BehaviorSubject<Notification | null>(null);
  private connectionStatusSubject = new BehaviorSubject<boolean>(false);
  
  notifications$: Observable<Notification | null> = this.notificationsSubject.asObservable();
  connectionStatus$: Observable<boolean> = this.connectionStatusSubject.asObservable();
  
  connect(userId: string): void {
    if (this.socket) {
      this.disconnect();
    }
    
    const wsUrl = `ws://localhost:8000/ws/${userId}`;
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = () => {
      console.log('✓ WebSocket connected');
      this.connectionStatusSubject.next(true);
    };
    
    this.socket.onmessage = (event) => {
      try {
        const notification: Notification = JSON.parse(event.data);
        this.notificationsSubject.next(notification);
      } catch (error) {
        console.error('Error parsing notification:', error);
      }
    };
    
    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.connectionStatusSubject.next(false);
    };
    
    this.socket.onclose = () => {
      console.log('WebSocket disconnected');
      this.connectionStatusSubject.next(false);
      
      // Auto-reconnect after 5 seconds
      setTimeout(() => {
        if (!this.socket || this.socket.readyState === WebSocket.CLOSED) {
          console.log('Attempting to reconnect...');
          this.connect(userId);
        }
      }, 5000);
    };
  }
  
  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.connectionStatusSubject.next(false);
    }
  }
  
  send(message: any): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }
}