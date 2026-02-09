// frontend/src/app/core/models/folder.model.ts

export interface Folder {
  id: string;
  name: string;
  path: string;
  auto_process: boolean;
  is_monitoring: boolean;
  created_at: string;
}

export interface FolderCreate {
  name: string;
  path: string;
  auto_process: boolean;
}

export interface Task {
  id: string;
  task_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  result?: any;
  retry_count?: number;
}

export interface TaskStats {
  total: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export interface Notification {
  type: string;
  message: string;
  document_id?: string;
  timestamp?: string;
}