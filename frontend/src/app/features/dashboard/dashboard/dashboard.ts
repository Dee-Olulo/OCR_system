// frontend/src/app/features/dashboard/dashboard.component.ts

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
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
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss'],
})
export class DashboardComponent implements OnInit {
  private documentService = inject(DocumentService);
  private authService     = inject(AuthService);

  stats:        DocumentStats | null = null;
  loading       = true;
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
        this.stats   = stats;
        this.loading = false;
      },
      error: () => {
        // Default to zeroed stats so the template always renders
        this.stats   = { total: 0, completed: 0, processing: 0, pending: 0, failed: 0 };
        this.loading = false;
      },
    });
  }

  // ── Computed ──────────────────────────────────────────────────────────────

  get timeOfDay(): string {
    const h = new Date().getHours();
    if (h < 12) return 'morning';
    if (h < 17) return 'afternoon';
    return 'evening';
  }

  get successRate(): number {
    if (!this.stats || !this.stats.total) return 0;
    return Math.round((this.stats.completed / this.stats.total) * 100);
  }
}