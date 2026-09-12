import { useState } from 'react';
import { Link } from 'react-router';
import { useAuthStore } from '@/store/authStore';
import { ArrowLeft, Mail, Zap } from 'lucide-react';

export function ForgotPassword() {
  const { forgotPassword, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    try {
      const msg = await forgotPassword(email);
      setMessage(msg);
      setSubmitted(true);
    } catch {
      // Error handled by store
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900">
            <Zap className="h-6 w-6 text-cyan-400" />
          </div>
          <span className="text-xl font-bold text-slate-900">Lead Intelligence</span>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-sm border border-slate-200">
          {!submitted ? (
            <>
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 mb-4">
                <Mail className="h-6 w-6 text-blue-600" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 mb-1">Forgot password?</h2>
              <p className="text-sm text-slate-500 mb-6">
                No worries, we'll send you reset instructions.
              </p>

              {error && (
                <div className="mb-4 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Email address
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    placeholder="you@company.com"
                    required
                    autoFocus
                  />
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    'Reset password'
                  )}
                </button>
              </form>
            </>
          ) : (
            <>
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 mb-4">
                <Mail className="h-6 w-6 text-emerald-600" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 mb-1">Check your email</h2>
              <p className="text-sm text-slate-500 mb-6">{message}</p>

              <button
                onClick={() => {
                  setSubmitted(false);
                  setEmail('');
                }}
                className="text-sm font-medium text-blue-600 hover:text-blue-700"
              >
                Didn't receive the email? Click to resend
              </button>
            </>
          )}

          <div className="mt-6 pt-6 border-t border-slate-100">
            <Link
              to="/login"
              className="flex items-center justify-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
