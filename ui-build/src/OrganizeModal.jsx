import React from 'react';
import { X, AlertCircle, CheckCircle, Loader, Pause, XCircle } from 'lucide-react';

export default function OrganizeModal({ account, progress, onPause, onCancel, onRetry, onClose }) {
  if (!progress) return null;
  console.log("🎨 OrganizeModal rendered with progress:", progress);

  const progressPercent = progress.progress_percent || 0;
  const isRunning = progress.status === 'running';
  const isPaused = progress.status === 'paused';
  const isError = progress.status === 'error';
  const isComplete = progress.status === 'completed';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-xl font-bold text-charcoal">
            {isComplete ? 'Organization Complete' : 'Organizing Mailbox'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Account Info */}
          <div className="text-sm text-gray-600">
            <strong>{account.email}</strong> ({account.provider})
          </div>

          {/* Progress Bar */}
          {!isComplete && (
            <>
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div 
                  className={`h-full transition-all duration-500 ${
                    isError ? 'bg-red-500' : isPaused ? 'bg-yellow-500' : 'bg-seafoam'
                  }`}
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <div className="text-center text-sm font-medium text-gray-700">
                {progress.processed_count?.toLocaleString()} / {progress.total_emails?.toLocaleString()} emails
                <span className="text-gray-500 ml-2">({progressPercent.toFixed(1)}%)</span>
              </div>
              {progress.categorizing_total > 0 && (
                <div className="mt-2 text-center text-xs text-gray-600">
                  Categorizing: {progress.categorizing_count} / {progress.categorizing_total}
                </div>
              )}
            </>
          )}

          {/* Status Message */}
          <div className="flex items-center gap-2 text-sm">
            {isRunning && <Loader className="w-4 h-4 animate-spin text-seafoam" />}
            {isPaused && <Pause className="w-4 h-4 text-yellow-500" />}
            {isError && <AlertCircle className="w-4 h-4 text-red-500" />}
            {isComplete && <CheckCircle className="w-4 h-4 text-green-500" />}
            
            <span className={`font-medium ${
              isError ? 'text-red-600' : 
              isPaused ? 'text-yellow-600' : 
              isComplete ? 'text-green-600' : 
              'text-gray-700'
            }`}>
              {isRunning && 'Categorizing and organizing emails...'}
              {isPaused && 'Paused - Click Resume to continue'}
              {isError && `Error: ${progress.last_error}`}
              {isComplete && 'All emails organized successfully!'}
            </span>
          </div>

          {/* Statistics */}
          <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
            <div className="text-center">
              <div className="text-2xl font-bold text-red-500">{progress.spam_count || 0}</div>
              <div className="text-xs text-gray-500">Spam</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-500">{progress.moved_count || 0}</div>
              <div className="text-xs text-gray-500">Organized</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-500">{progress.unsure_count || 0}</div>
              <div className="text-xs text-gray-500">Unsure</div>
            </div>
          </div>

          {/* ETA */}
          {isRunning && progress.estimated_completion && (
            <div className="text-sm text-gray-500 text-center">
              Est. completion: {new Date(progress.estimated_completion).toLocaleTimeString()}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3 p-6 bg-gray-50 rounded-b-xl">
          {isRunning && (
            <>
              <button
                onClick={onPause}
                className="flex-1 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors flex items-center justify-center gap-2"
              >
                <Pause className="w-4 h-4" />
                Pause
              </button>
              <button
                onClick={onCancel}
                className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center justify-center gap-2"
              >
                <XCircle className="w-4 h-4" />
                Cancel
              </button>
            </>
          )}

          {isPaused && (
            <>
              <button
                onClick={onPause}
                className="flex-1 px-4 py-2 bg-seafoam text-white rounded-lg hover:bg-teal-600 transition-colors"
              >
                Resume
              </button>
              <button
                onClick={onCancel}
                className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
              >
                Cancel
              </button>
            </>
          )}

          {isError && (
            <>
              <button
                onClick={onRetry}
                className="flex-1 px-4 py-2 bg-seafoam text-white rounded-lg hover:bg-teal-600 transition-colors"
              >
                Retry
              </button>
              <button
                onClick={onCancel}
                className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
              >
                Cancel
              </button>
            </>
          )}

          {isComplete && (
            <button
              onClick={onClose}
              className="w-full px-4 py-2 bg-seafoam text-white rounded-lg hover:bg-teal-600 transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
