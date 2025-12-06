import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Shield, Smartphone, Copy, Download, CheckCircle } from 'lucide-react';
import QRCode from 'qrcode.react';
import toast from 'react-hot-toast';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../common/LoadingSpinner';

const TwoFactorSetup = () => {
  const [step, setStep] = useState(1);
  const [qrCodeData, setQrCodeData] = useState(null);
  const [manualKey, setManualKey] = useState('');
  const [backupCodes, setBackupCodes] = useState([]);
  
  const {
    setup2FA,
    verify2FASetup,
    generateBackupCodes,
    setup2FALoading,
    verify2FASetupLoading,
    generateBackupCodesLoading,
    setup2FAData,
    backupCodesData,
  } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm();

  // Initialize 2FA setup on component mount
  useEffect(() => {
    setup2FA();
  }, [setup2FA]);

  // Handle setup data
  useEffect(() => {
    if (setup2FAData?.success) {
      const setupData = setup2FAData.setup_data;
      setQrCodeData(setupData.qr_code);
      setManualKey(setupData.manual_entry_key);
    }
  }, [setup2FAData]);

  // Handle backup codes data
  useEffect(() => {
    if (backupCodesData?.success) {
      setBackupCodes(backupCodesData.backup_codes);
      setStep(3);
    }
  }, [backupCodesData]);

  const onVerifyCode = (data) => {
    verify2FASetup({ code: data.code });
  };

  const handleGenerateBackupCodes = () => {
    generateBackupCodes();
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      toast.success('Copied to clipboard!');
    });
  };

  const downloadBackupCodes = () => {
    const content = backupCodes.join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'orthanc-backup-codes.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Backup codes downloaded!');
  };

  const renderStep1 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto h-16 w-16 bg-primary-600 rounded-full flex items-center justify-center mb-4">
          <Shield className="h-8 w-8 text-white" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">
          Set Up Two-Factor Authentication
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Enhance your account security with 2FA
        </p>
      </div>

      {setup2FALoading ? (
        <div className="text-center py-8">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-sm text-gray-600">Setting up 2FA...</p>
        </div>
      ) : qrCodeData ? (
        <div className="space-y-6">
          {/* QR Code */}
          <div className="text-center">
            <div className="bg-white p-4 rounded-lg border inline-block">
              <QRCode value={qrCodeData.replace('data:image/png;base64,', '')} size={200} />
            </div>
            <p className="mt-2 text-sm text-gray-600">
              Scan this QR code with your authenticator app
            </p>
          </div>

          {/* Manual Entry */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-gray-900 mb-2">
              Can't scan? Enter this code manually:
            </h3>
            <div className="flex items-center space-x-2">
              <code className="flex-1 bg-white px-3 py-2 rounded border text-sm font-mono">
                {manualKey}
              </code>
              <button
                type="button"
                onClick={() => copyToClipboard(manualKey)}
                className="btn-outline btn-sm"
              >
                <Copy className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Instructions */}
          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-blue-900 mb-2">
              Instructions:
            </h3>
            <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
              <li>Install an authenticator app (Google Authenticator, Authy, etc.)</li>
              <li>Scan the QR code or enter the manual code</li>
              <li>Enter the 6-digit code from your app below</li>
            </ol>
          </div>

          {/* Verification Form */}
          <form onSubmit={handleSubmit(onVerifyCode)} className="space-y-4">
            <div>
              <label htmlFor="code" className="label">
                Verification Code
              </label>
              <input
                id="code"
                type="text"
                maxLength="6"
                className={`input text-center text-lg tracking-widest ${errors.code ? 'border-red-500' : ''}`}
                placeholder="000000"
                {...register('code', {
                  required: 'Verification code is required',
                  pattern: {
                    value: /^\d{6}$/,
                    message: 'Code must be 6 digits',
                  },
                })}
              />
              {errors.code && (
                <p className="mt-1 text-sm text-red-600">
                  {errors.code.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={verify2FASetupLoading}
              className="btn-primary w-full"
            >
              {verify2FASetupLoading ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Verifying...
                </>
              ) : (
                'Verify and Enable 2FA'
              )}
            </button>
          </form>
        </div>
      ) : (
        <div className="text-center py-8">
          <p className="text-red-600">Failed to initialize 2FA setup. Please try again.</p>
          <button
            onClick={() => setup2FA()}
            className="btn-primary mt-4"
          >
            Retry Setup
          </button>
        </div>
      )}
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto h-16 w-16 bg-green-600 rounded-full flex items-center justify-center mb-4">
          <CheckCircle className="h-8 w-8 text-white" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">
          2FA Setup Complete!
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Your account is now protected with two-factor authentication
        </p>
      </div>

      <div className="bg-green-50 p-4 rounded-lg">
        <h3 className="text-sm font-medium text-green-900 mb-2">
          What's Next?
        </h3>
        <p className="text-sm text-green-800">
          Generate backup codes to ensure you can always access your account,
          even if you lose your authenticator device.
        </p>
      </div>

      <button
        onClick={handleGenerateBackupCodes}
        disabled={generateBackupCodesLoading}
        className="btn-primary w-full"
      >
        {generateBackupCodesLoading ? (
          <>
            <LoadingSpinner size="sm" className="mr-2" />
            Generating...
          </>
        ) : (
          <>
            <Download className="h-4 w-4 mr-2" />
            Generate Backup Codes
          </>
        )}
      </button>

      <button
        onClick={() => window.location.href = '/'}
        className="btn-outline w-full"
      >
        Skip for Now
      </button>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto h-16 w-16 bg-yellow-600 rounded-full flex items-center justify-center mb-4">
          <Download className="h-8 w-8 text-white" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">
          Save Your Backup Codes
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Store these codes in a safe place. Each code can only be used once.
        </p>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
        <div className="flex items-center mb-2">
          <Shield className="h-5 w-5 text-yellow-600 mr-2" />
          <span className="text-sm font-medium text-yellow-800">
            Important Security Notice
          </span>
        </div>
        <p className="text-xs text-yellow-700">
          These backup codes can be used to access your account if you lose your authenticator device.
          Keep them secure and don't share them with anyone.
        </p>
      </div>

      <div className="bg-white border rounded-lg p-4">
        <div className="grid grid-cols-2 gap-2 font-mono text-sm">
          {backupCodes.map((code, index) => (
            <div key={index} className="bg-gray-50 p-2 rounded text-center">
              {code}
            </div>
          ))}
        </div>
      </div>

      <div className="flex space-x-3">
        <button
          onClick={downloadBackupCodes}
          className="btn-primary flex-1"
        >
          <Download className="h-4 w-4 mr-2" />
          Download
        </button>
        <button
          onClick={() => copyToClipboard(backupCodes.join('\n'))}
          className="btn-outline flex-1"
        >
          <Copy className="h-4 w-4 mr-2" />
          Copy
        </button>
      </div>

      <button
        onClick={() => window.location.href = '/'}
        className="btn-secondary w-full"
      >
        Continue to Dashboard
      </button>
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        <div className="card">
          <div className="card-content">
            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TwoFactorSetup;