import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router';
import { apiClient } from '@/api/client';
import { Button, Input } from '@/components/ui';
import { Lock, Loader2, ArrowRight } from 'lucide-react';
import { useToast } from '@/hooks/useToast';

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();
  const toast = useToast();
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!token) {
      toast.error('Invalid link', 'No reset token provided in URL.');
      return;
    }

    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    
    if (password.length < 8) {
      toast.error('Password too short', 'Password must be at least 8 characters.');
      return;
    }

    setIsLoading(true);
    try {
      await apiClient.post('/auth/reset-password', { token, new_password: password });
      setSuccess(true);
      toast.success('Password reset successful', 'You can now log in with your new password.');
    } catch (err: any) {
      toast.error('Reset failed', err.response?.data?.detail || 'The reset link may have expired.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 bg-white p-8 rounded-2xl shadow-xl">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-900 shadow-sm">
            <Lock className="h-6 w-6 text-white" />
          </div>
          <h2 className="mt-6 text-3xl font-bold tracking-tight text-slate-900">
            Reset Password
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {success ? 'Your password has been changed.' : 'Enter your new password below.'}
          </p>
        </div>

        {success ? (
          <div className="mt-8 space-y-6">
            <Button className="w-full flex items-center justify-center gap-2" onClick={() => navigate('/login')}>
              Go to Login <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  New Password
                </label>
                <Input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full"
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Confirm Password
                </label>
                <Input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <Button type="submit" className="w-full" disabled={isLoading || !token}>
              {isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              {isLoading ? 'Resetting...' : 'Reset Password'}
            </Button>
            
            {!token && (
              <p className="text-center text-sm text-red-500 mt-2">
                Missing reset token in URL. Please use the link from your email.
              </p>
            )}
            
            <div className="text-center text-sm">
              <Link to="/login" className="font-medium text-blue-600 hover:text-blue-500">
                Back to login
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
