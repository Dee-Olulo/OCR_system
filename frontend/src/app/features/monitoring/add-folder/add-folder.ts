// frontend/src/app/features/monitoring/add-folder-dialog/add-folder-dialog.component.ts

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-add-folder-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCheckboxModule,
    MatIconModule
  ],
  template: `
    <h2 mat-dialog-title>
      <mat-icon>create_new_folder</mat-icon>
      Add Monitored Folder
    </h2>
    
    <mat-dialog-content>
      <form [formGroup]="folderForm">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Folder Name</mat-label>
          <input matInput formControlName="name" placeholder="e.g., Invoice Folder">
          <mat-icon matPrefix>label</mat-icon>
          <mat-error *ngIf="folderForm.get('name')?.hasError('required')">
            Folder name is required
          </mat-error>
        </mat-form-field>
        
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Folder Path</mat-label>
          <input matInput formControlName="path" placeholder="e.g., C:\\Documents\\Invoices">
          <mat-icon matPrefix>folder</mat-icon>
          <mat-hint>Enter the full path to the folder you want to monitor</mat-hint>
          <mat-error *ngIf="folderForm.get('path')?.hasError('required')">
            Folder path is required
          </mat-error>
        </mat-form-field>
        
        <div class="checkbox-container">
          <mat-checkbox formControlName="auto_process">
            Automatically process new files
          </mat-checkbox>
        </div>
      </form>
    </mat-dialog-content>
    
    <mat-dialog-actions align="end">
      <button mat-button (click)="onCancel()">Cancel</button>
      <button mat-raised-button color="primary" (click)="onSave()" [disabled]="!folderForm.valid">
        <mat-icon>add</mat-icon>
        Add Folder
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    .full-width {
      width: 100%;
      margin-bottom: 16px;
    }
    
    mat-dialog-content {
      min-width: 500px;
      padding: 20px;
    }
    
    h2 {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .checkbox-container {
      margin: 16px 0;
    }
    
    mat-dialog-actions {
      padding: 16px 24px;
    }
  `]
})
export class AddFolderDialogComponent {
  private fb = inject(FormBuilder);
  private dialogRef = inject(MatDialogRef<AddFolderDialogComponent>);
  
  folderForm: FormGroup;
  
  constructor() {
    this.folderForm = this.fb.group({
      name: ['', Validators.required],
      path: ['', Validators.required],
      auto_process: [true]
    });
  }
  
  onCancel(): void {
    this.dialogRef.close();
  }
  
  onSave(): void {
    if (this.folderForm.valid) {
      this.dialogRef.close(this.folderForm.value);
    }
  }
}