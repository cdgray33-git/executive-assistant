import React, { useState } from 'react';
import { X, Mail, AlertCircle } from 'lucide-react';

export default function StartOrganizeModal({ account, onStart, onClose }) {
  const [batchSize, setBatchSize] = useState(3000);
  const [error, setError] = useState('');

  const handleStart = () => {
    if (batchSize < 100 || batchSize > 10000) {
      setError('Batch size must be between 100 and 10,000');
      return;
    }
    onStart(account.account_id, batchSize);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-xl font-bold text-charcoal">Start Mailbox Organization</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Account Info */}
          <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
            <Mail className="w-5 h-5 text-seafoam" />
            <div>
              <div className="font-semibold text-charcoal">{account.email}</div>
              <div className="text-sm text-gray-500">{account.provider}</div>
            </div>
          </div>

          {/* Batch Size Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Batch Size (emails per round)
            </label>
            <input
              type="number"
              value={batchSize}
              onChange={(e) => {
                setBatchSize(parseInt(e.target.value) || 3000);
                setError('');
              }}
              min="100"
              max="10000"
              step="100"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-seafoam focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Recommended: 3000. Lower values = faster rounds, more frequent pauses.
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Info Box */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              <strong>What happens:</strong><br/>
              • Spam detection on {batchSize.toLocaleString()} emails<br/>
              • Auto-categorize kept emails<br/>
              • You can pause/resume anytime
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleStart}
            className="flex-1 px-4 py-2 bg-seafoam text-white rounded-lg hover:bg-teal-600 transition-colors font-medium"
          >
            Start Organization
          </button>
        </div>
      </div>
    </div>
  );
}
