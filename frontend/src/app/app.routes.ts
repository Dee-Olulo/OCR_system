// frontend/src/app/app.routes.ts

import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth-guard';
import { LayoutComponent } from './shared/components/layout/layout';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login')
      .then(m => m.LoginComponent)
  },
  {
    path: 'register',
    loadComponent: () => import('./features/auth/register/register')
      .then(m => m.RegisterComponent)
  },
  {
    path: '',
    component: LayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard/dashboard')
          .then(m => m.DashboardComponent)
      },
      {
        path: 'documents',
        loadComponent: () => import('./features/documents/document-list/document-list')
          .then(m => m.DocumentListComponent)
      },
      {
        path: 'documents/:id',
        loadComponent: () => import('./features/documents/document-detail/document-detail')
          .then(m => m.DocumentDetailComponent)
      },
      {
        path: 'upload',
        loadComponent: () => import('./features/documents/document-upload/document-upload')
          .then(m => m.DocumentUploadComponent)
      }
    ]
  },
  {
    path: '**',
    redirectTo: 'dashboard'
  }
];