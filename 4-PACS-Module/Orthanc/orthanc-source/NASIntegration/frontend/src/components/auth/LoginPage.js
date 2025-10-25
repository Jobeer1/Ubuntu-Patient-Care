import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Eye, EyeOff, Shield, Activity } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../common/LoadingSpinner';

const LoginPage = () => {
  const [showPin, setShowPin] = useState(false);
  const { login, loginLoading } = useAuth();
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  const onSubmit = (data) => {
    login(data);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-primary-600 rounded-full flex items-center justify-center mb-4">
            <Activity className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900">
            Orthanc NAS
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Sign in to your medical imaging system
          </p>
        </div>

        {/* Login Form */}
        <div className="card">
          <div className="card-content">
            <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
              {/* Username Field */}
              <div>
                <label htmlFor="username" className="label">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  className={`input ${errors.username ? 'border-red-500' : ''}`}
                  placeholder="Enter your username"
                  {...register('username', {
                    required: 'Username is required',
                    minLength: {
                      value: 2,
                      message: 'Username must be at least 2 characters',
                    },
                  })}
                />
                {errors.username && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.username.message}
                  </p>
                )}
              </div>

              {/* PIN Field */}
              <div>
                <label htmlFor="pin" className="label">
                  PIN
                </label>
                <div className="relative">
                  <input
                    id="pin"
                    type={showPin ? 'text' : 'password'}
                    autoComplete="current-password"
                    className={`input pr-10 ${errors.pin ? 'border-red-500' : ''}`}
                    placeholder="Enter your PIN"
                    {...register('pin', {
                      required: 'PIN is required',
                      minLength: {
                        value: 4,
                        message: 'PIN must be at least 4 characters',
                      },
                    })}
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    onClick={() => setShowPin(!showPin)}
                  >
                    {showPin ? (
                      <EyeOff className="h-4 w-4 text-gray-400" />
                    ) : (
                      <Eye className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>
                {errors.pin && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.pin.message}
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loginLoading}
                className="btn-primary w-full flex items-center justify-center"
              >
                {loginLoading ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Signing in...
                  </>
                ) : (
                  <>
                    <Shield className="h-4 w-4 mr-2" />
                    Sign in
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Security Notice */}
        <div className="text-center">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-center mb-2">
              <Shield className="h-5 w-5 text-blue-600 mr-2" />
              <span className="text-sm font-medium text-blue-800">
                Secure Medical System
              </span>
            </div>
            <p className="text-xs text-blue-600">
              This system contains protected health information (PHI).
              Unauthorized access is prohibited and monitored.
            </p>
          </div>
        </div>

        {/* Demo Credentials */}
        <div className="text-center">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-xs text-yellow-800 font-medium mb-2">
              Demo Credentials
            </p>
            <div className="text-xs text-yellow-700 space-y-1">
              <div>Admin: username=<code>admin</code>, pin=<code>admin123</code></div>
              <div>User: username=<code>doctor1</code>, pin=<code>doctor123</code></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;