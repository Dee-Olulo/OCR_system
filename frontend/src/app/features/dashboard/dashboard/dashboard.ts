// frontend/src/app/features/dashboard/dashboard.component.ts

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { DocumentService } from '../../../core/services/document';
import { AuthService } from '../../../core/services/auth';
import { DocumentStats } from '../../../core/models/document.model';
import { Observable } from 'rxjs';
import { User } from '../../../core/models/user.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss']
})
export class DashboardComponent implements OnInit {
  private documentService = inject(DocumentService);
  private authService = inject(AuthService);
  
  stats: DocumentStats | null = null;
  loading = true;
  currentUser$: Observable<User | null>;
  
  constructor() {
    this.currentUser$ = this.authService.currentUser$;
  }
  
  ngOnInit(): void {
    this.loadStats();
  }
  
  loadStats(): void {
    this.loading = true;
    this.documentService.getDocumentStats().subscribe({
      next: (stats) => {
        this.stats = stats;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading stats:', error);
        this.loading = false;
      }
    });
  }
}