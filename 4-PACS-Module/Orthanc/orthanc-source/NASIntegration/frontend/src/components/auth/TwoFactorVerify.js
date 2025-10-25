import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Shield, Smartphone, Key } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../common/LoadingSpinner';

const TwoFactorVerify = () => {
  const [method, setMethod] = useState('totp');
  const { verify2FA, verify2FALoading, user } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm();

  const onSubmit = (data) => {
    verify2FA({ code: data.code, method });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-primary-600 rounded-full flex items-center justify-center mb-4">
            <Shield className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900">
            Two-Factor Authentication
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Welcome back, {user?.username}. Please verify your identity.
          </p>
        </div>

        {/* 2FA Form */}
        <div className="card">
          <div className="card-content">
            {/* Method Selection */}
            <div className="mb-6">
              <div className="flex space-x-2">
                <button
                  type="button"
                  onClick={() => setMethod('totp')}
                  className={`flex-1 flex items-center justify-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    method === 'totp'
                      ? 'bg-primary-100 text-primary-700 border border-primary-200'
                      : 'bg-gray-50 text-gray-700 border border-gray-200 hover:bg-gray-100'
                  }`}
                >
                  <Smartphone className="h-4 w-4 mr-2" />
                  Authenticator App
                </button>
                <button
                  type="button"
                  onClick={() => setMethod('backup_codes')}
                  className={`flex-1 flex items-center justify-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    method === 'backup_codes'
                      ? 'bg-primary-100 text-primary-700 border border-primary-200'
                      : 'bg-gray-50 text-gray-700 border border-gray-200 hover:bg-gray-100'
                  }`}
                >
                  <Key className="h-4 w-4 mr-2" />
                  Backup Code
                </button>
              </div>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Code Input */}
              <div>
                <label htmlFor="code" className="label">
                  {method === 'totp' ? 'Authenticator Code' : 'Backup Code'}
                </label>
                <input
                  id="code"
                  type="text"
                  maxLength={method === 'totp' ? '6' : '8'}
                  className={`input text-center text-lg tracking-widest ${errors.code ? 'border-red-500' : ''}`}
                  placeholder={method === 'totp' ? '000000' : '00000000'}
                  {...register('code', {
                    required: 'Code is required',
                    pattern: {
                      value: method === 'totp' ? /^\d{6}$/ : /^\d{8}$/,
                      message: `Code must be ${method === 'totp' ? '6' : '8'} digits`,
                    },
                  })}
                />
                {errors.code && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.code.message}
                  </p>
                )}
                <p className="mt-2 text-xs text-gray-500">
                  {method === 'totp' 
                    ? 'Enter the 6-digit code from your authenticator app'
                    : 'Enter one of your 8-digit backup codes'
                  }
                </p>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={verify2FALoading}
                className="btn-primary w-full"
              >
                {verify2FALoading ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Verifying...
                  </>
                ) : (
                  'Verify Code'
                )}
              </button>
            </form>

            {/* Help Text */}
            <div className="mt-6 text-center">
              <p className="text-xs text-gray-500">
                Having trouble? Contact your system administrator for assistance.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TwoFactorVerify;