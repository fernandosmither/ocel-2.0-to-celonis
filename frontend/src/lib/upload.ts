import { CONFIG } from './config';

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface UploadResult {
  uuid: string;
}

export class UploadError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = 'UploadError';
  }
}

export async function uploadFile(
  file: File,
  onProgress?: (progress: UploadProgress) => void
): Promise<UploadResult> {
  // Validate file type
  if (!file.name.toLowerCase().endsWith('.jsonocel')) {
    throw new UploadError('File must be a .jsonocel file');
  }

  // Validate file size (e.g., max 100MB)
  const maxSize = 100 * 1024 * 1024; // 100MB
  if (file.size > maxSize) {
    throw new UploadError('File size must be less than 100MB');
  }

  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();

    // Track upload progress
    if (onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const progress: UploadProgress = {
            loaded: event.loaded,
            total: event.total,
            percentage: Math.round((event.loaded / event.total) * 100),
          };
          onProgress(progress);
        }
      };
    }

    // Handle completion
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const result: UploadResult = JSON.parse(xhr.responseText);
          resolve(result);
        } catch (error) {
          reject(new UploadError('Invalid response from server'));
        }
      } else {
        const errorMessage = xhr.statusText || 'Upload failed';
        reject(new UploadError(errorMessage, xhr.status));
      }
    };

    // Handle errors
    xhr.onerror = () => {
      reject(new UploadError('Network error during upload'));
    };

    xhr.ontimeout = () => {
      reject(new UploadError('Upload timed out'));
    };

    // Configure request
    xhr.open('POST', CONFIG.UPLOAD_URL);
    xhr.timeout = 300000; // 5 minutes timeout

    // Start upload
    xhr.send(formData);
  });
} 